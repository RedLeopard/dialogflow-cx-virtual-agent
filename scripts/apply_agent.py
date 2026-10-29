#!/usr/bin/env python3
"""Apply the versioned Dialogflow CX config in dialogflow/agent/ to the live agent.

Updates the Draft agent in place (create-or-update by display name), so existing
versions, environments, and the Twilio connector are untouched. With --publish it
also creates a new flow version and points the production environment at it.

Usage (from the repo root, logged in with gcloud):
    python3 scripts/apply_agent.py --dry-run        # show what would change
    python3 scripts/apply_agent.py                  # update Draft only
    python3 scripts/apply_agent.py --publish        # update Draft, publish, go live

Rollback: point production back at the previous version (printed at the end).
Standard library only.
"""
import argparse
import copy
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PROJECT = "csd-dialogflow-cx-2026"
LOCATION = "us-central1"
AGENT_ID = "616e7277-d596-4d4d-9053-6df11765881d"
ENVIRONMENT_ID = "e7b9ee85-0c39-476b-8764-ac9faf9c3b6f"  # production
START_FLOW_ID = "00000000-0000-0000-0000-000000000000"

AGENT = f"projects/{PROJECT}/locations/{LOCATION}/agents/{AGENT_ID}"
FLOW = f"{AGENT}/flows/{START_FLOW_ID}"
API = f"https://{LOCATION}-dialogflow.googleapis.com/v3"
ROOT = Path(__file__).resolve().parents[1] / "dialogflow" / "agent"
FLOW_DIR = ROOT / "flows" / "Default Start Flow"

# Intents managed by this script (system intents are left alone).
MANAGED_INTENTS = ["confirm.yes", "confirm.no", "agent.handoff"]
# Pages are created in this order; routes are filled in a second pass.
MANAGED_PAGES = [
    "Start Router", "Caller Name", "Callback Number", "Alternate Number", "Confirm Callback",
    "Consultation Request", "Project Follow-up", "Conversation Router", "Booking Offer", "Live Transfer", "Voicemail",
]
SPECIAL_PAGES = {"End Session": "END_SESSION", "End Flow": "END_FLOW"}

DRY_RUN = False
_token = None


def token():
    global _token
    if _token is None:
        _token = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
    return _token


def call(method, path, body=None, query=""):
    url = f"{API}/{path}" + (f"?{query}" if query else "")
    if DRY_RUN and method != "GET":
        print(f"  [dry-run] {method} {path}{'?' + query if query else ''}")
        return {"name": f"{path}/DRY-RUN"}
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {token()}",
        "x-goog-user-project": PROJECT,
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        sys.exit(f"\nERROR {e.code} on {method} {path}\n{detail}")


def list_all(path, key):
    items, page = [], ""
    while True:
        res = call("GET", path, query="pageSize=1000" + (f"&pageToken={page}" if page else ""))
        items += res.get(key, [])
        page = res.get("nextPageToken")
        if not page:
            return items


def load(path):
    return json.loads(Path(path).read_text())


def strip_names(node):
    """Remove local 'name' ids from routes/handlers; Dialogflow assigns real ones."""
    if isinstance(node, dict):
        return {k: strip_names(v) for k, v in node.items() if k != "name"}
    if isinstance(node, list):
        return [strip_names(v) for v in node]
    return node


def resolve(node, intents, pages, webhooks):
    """Swap display names for resource names in intent/targetPage/webhook fields."""
    if isinstance(node, list):
        return [resolve(v, intents, pages, webhooks) for v in node]
    if not isinstance(node, dict):
        return node
    out = {}
    for k, v in node.items():
        if k == "intent" and isinstance(v, str):
            out[k] = lookup(intents, v, "intent")
        elif k == "targetPage" and isinstance(v, str):
            out[k] = f"{FLOW}/pages/{SPECIAL_PAGES[v]}" if v in SPECIAL_PAGES else lookup(pages, v, "page")
        elif k == "webhook" and isinstance(v, str):
            out[k] = lookup(webhooks, v, "webhook")
        elif k == "entityType" and isinstance(v, str) and v.startswith("@sys."):
            # The API wants system entities as full resource names.
            out[k] = f"projects/-/locations/-/agents/-/entityTypes/{v[1:]}"
        else:
            out[k] = resolve(v, intents, pages, webhooks)
    return out


def lookup(table, display_name, kind):
    if display_name not in table:
        sys.exit(f"ERROR: {kind} '{display_name}' not found in the agent.")
    return table[display_name]


def wait(operation, label):
    if DRY_RUN:
        return {}
    print(f"  waiting for {label}...", end="", flush=True)
    for _ in range(120):
        op = call("GET", operation["name"])
        if op.get("done"):
            print(" done")
            if "error" in op:
                sys.exit(f"ERROR: {label} failed: {op['error']}")
            return op.get("response", {})
        print(".", end="", flush=True)
        time.sleep(3)
    sys.exit(f"ERROR: timed out waiting for {label}")


def main():
    global DRY_RUN
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="show changes without making them")
    parser.add_argument("--publish", action="store_true", help="create a version and make it live in production")
    args = parser.parse_args()
    DRY_RUN = args.dry_run

    print(f"Agent: {AGENT}\n")

    # 1. Intents -------------------------------------------------------------
    print("Intents")
    intents = {i["displayName"]: i["name"] for i in list_all(f"{AGENT}/intents", "intents")}
    for name in MANAGED_INTENTS:
        phrases = load(ROOT / "intents" / name / "trainingPhrases" / "en.json")["trainingPhrases"]
        body = {
            "displayName": name,
            "priority": 500000,
            "trainingPhrases": [{"parts": p["parts"], "repeatCount": p.get("repeatCount", 1)} for p in phrases],
        }
        if name in intents:
            print(f"  update {name}")
            call("PATCH", intents[name], body, "updateMask=trainingPhrases")
        else:
            print(f"  create {name}")
            intents[name] = call("POST", f"{AGENT}/intents", body)["name"]

    # 2. Webhook timeout -------------------------------------------------------
    print("Webhook")
    webhooks = {w["displayName"]: w["name"] for w in list_all(f"{AGENT}/webhooks", "webhooks")}
    local_hook = load(ROOT / "webhooks" / "Project Discovery Backend.json")
    hook_name = lookup(webhooks, local_hook["displayName"], "webhook")
    print(f"  set timeout to {local_hook['timeout']['seconds']}s")
    call("PATCH", hook_name, {"timeout": local_hook["timeout"]}, "updateMask=timeout")

    # 3. Pages: create any missing (empty), then fill everything ---------------
    print("Pages")
    pages = {p["displayName"]: p["name"] for p in list_all(f"{FLOW}/pages", "pages")}
    for name in MANAGED_PAGES:
        if name not in pages:
            print(f"  create {name}")
            pages[name] = call("POST", f"{FLOW}/pages", {"displayName": name})["name"]
    for name in MANAGED_PAGES:
        local = strip_names(load(FLOW_DIR / "pages" / f"{name}.json"))
        body = resolve(local, intents, pages, webhooks)
        body["name"] = pages[name]
        mask = ",".join(k for k in ("entryFulfillment", "form", "transitionRoutes", "eventHandlers")) + ",displayName"
        # Clear fields that are not in the local file so stale routes do not linger.
        for k in ("entryFulfillment", "form", "transitionRoutes", "eventHandlers"):
            body.setdefault(k, {} if k in ("entryFulfillment", "form") else [])
        print(f"  update {name}")
        call("PATCH", pages[name], body, f"updateMask={mask}")

    # 4. Start flow routes and handlers ----------------------------------------
    print("Start flow")
    local_flow = strip_names(load(FLOW_DIR / "Default Start Flow.json"))
    body = {k: resolve(local_flow[k], intents, pages, webhooks)
            for k in ("description", "transitionRoutes", "eventHandlers")}
    print("  update greeting, routes, and fallback responses")
    call("PATCH", FLOW, body, "updateMask=description,transitionRoutes,eventHandlers")

    print("\nDraft agent updated.")

    if not args.publish:
        print("Draft only. Re-run with --publish to make it live on the phone line.")
        return

    # 5. Publish ---------------------------------------------------------------
    print("\nPublish")
    env = call("GET", f"{AGENT}/environments/{ENVIRONMENT_ID}")
    previous = env.get("versionConfigs", [{}])[0].get("version", "unknown")
    label = time.strftime("caller-experience-%Y%m%d-%H%M")
    op = call("POST", f"{FLOW}/versions", {
        "displayName": label,
        "description": "Cloud Systems Direct greeting, contact intake, voice-ready discovery.",
    })
    version = wait(op, f"version {label}").get("name", f"{FLOW}/versions/DRY-RUN")
    print(f"  created {version.rsplit('/', 1)[-1]} ({label})")
    op = call("PATCH", f"{AGENT}/environments/{ENVIRONMENT_ID}",
              {"versionConfigs": [{"version": version}]}, "updateMask=versionConfigs")
    wait(op, "production switch")
    print(f"\nLIVE: production now runs version {version.rsplit('/', 1)[-1]}.")
    print(f"Rollback: production previously ran version {previous.rsplit('/', 1)[-1]}.")


if __name__ == "__main__":
    main()
