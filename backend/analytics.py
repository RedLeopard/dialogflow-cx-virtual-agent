"""Best-effort BigQuery analytics; disabled until BIGQUERY_ENABLED=true.

Only write_records performs I/O, before returning the webhook response so
Cloud Run keeps CPU allocated. This is not a durable queue: failures can lose events.
"""
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from functools import lru_cache

from backend.contact import digits, is_usable_us_number
from backend.notify import log


def enabled() -> bool:
    return os.getenv("BIGQUERY_ENABLED", "false").lower() == "true"


def _text(value, limit=2000):
    return value.strip()[:limit] if isinstance(value, str) else ""


def _digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _category(discovery):
    # Never put arbitrary model/caller text in aggregate event dimensions.
    kind = _text(discovery.get("project_type"), 200).lower()
    for category, pattern in (
        ("customer_experience", r"\b(cx|c\s+x|customer experience|contact cent(?:er|re)|ccaas)\b"),
        ("ai", r"\b(ai|artificial intelligence|machine learning|mlops|generative|agentic)\b"),
        ("data", r"\b(data|database|analytics|etl|elt|warehouse|business intelligence)\b"),
        ("devops", r"\b(devops|platform engineering|sre|site reliability|ci/cd)\b"),
        ("cloud_security", r"\b(security|iam|identity|governance)\b"),
        ("cloud", r"\b(cloud|migration|infrastructure|devops|security)\b"),
        ("website", r"\b(web|website|wordpress|redesign)\b"),
        ("application", r"\b(app|application|software)\b"),
        ("digital_marketing", r"\b(marketing|seo|advertising|social)\b"),
    ):
        if re.search(pattern, kind):
            return category
    return "other" if kind else "unknown"


def records_for(request: dict, response: dict):
    """Build allowlisted rows and session state; never call cloud services."""
    if not enabled():
        return {}, [], []
    session = request.get("sessionInfo", {})
    params = session.get("parameters", {})
    updates = response.get("sessionInfo", {}).get("parameters", {})
    combined = {**params, **updates}
    now = datetime.now(timezone.utc).isoformat()
    # Studio must pass the ORIGINAL inbound SID to both virtual-agent widgets.
    sid = _text(params.get("call_id"), 100)
    fallback = _text(params.get("analytics_call_id"), 100)
    session_name = _text(session.get("session"), 1000)
    if re.fullmatch(r"CA[0-9a-fA-F]{32}", sid):
        call_id = sid
    elif re.fullmatch(r"(?:CA[0-9a-fA-F]{32}|df_[0-9a-f]{64})", fallback):
        call_id = fallback
    elif session_name:
        call_id = "df_" + _digest(session_name)
    else:
        log("analytics_skipped", reason="missing call/session identity")
        return {}, [], []

    created = _text(params.get("analytics_created_at"), 50)
    try:
        parsed = datetime.fromisoformat(created.replace("Z", "+00:00"))
        created = parsed.astimezone(timezone.utc).isoformat() if parsed.tzinfo else now
    except ValueError:
        created = now
    state = {"analytics_call_id": call_id, "analytics_created_at": created}
    tag = request["fulfillmentInfo"]["tag"]
    # Dialogflow reuses detectIntentResponseId when retrying a webhook request.
    # Hash the request as a deterministic fallback for other authenticated clients.
    request_id = _text(request.get("detectIntentResponseId"), 500) or _digest(
        json.dumps(request, sort_keys=True, separators=(",", ":"), default=str)
    )
    discovery = combined.get("project_discovery")
    discovery = discovery if isinstance(discovery, dict) else {}
    consent = combined.get("analytics_sms_consent")
    consent = consent if type(consent) is bool else None
    if tag == "send-booking-link" and "booking_sms_sent" in updates:
        consent = True  # This fulfillment route follows the affirmative offer.
    elif tag == "decline-booking":
        consent = False
    if consent is not None:
        state["analytics_sms_consent"] = consent
    is_test = params.get("analytics_is_test") is True

    def event(kind, outcome=None):
        return {
            "event_id": _digest(f"{call_id}:{request_id}:{kind}"),
            "event_timestamp": now, "ingested_at": now, "call_id": call_id,
            "dialogflow_session_id": "df_" + _digest(session_name) if session_name else None,
            "event_type": kind, "source": "backend", "outcome": outcome,
            "service_category": _category(discovery), "sms_consent": consent,
            "is_test": is_test,
        }

    events = [event("webhook_processed", tag)]
    if tag == "finish-discovery":
        events.append(event("lead_captured"))
        if params.get("lead_notified") is not True and updates.get("lead_notified") is True:
            events.append(event("notification_accepted", "owner_alert"))
    elif tag == "handoff":
        events.append(event("transfer_requested"))
    elif tag == "voicemail-save":
        events.append(event("message_captured"))
        if updates.get("voicemail_delivered") is True:
            events.append(event("notification_accepted", "message_alert"))
    elif tag == "send-booking-link" and params.get("booking_sms_sent") is not True:
        if updates.get("booking_sms_sent") is True:
            events.append(event("booking_link_sent", "provider_accepted"))
        elif updates.get("booking_sms_sent") is False:
            events.append(event("booking_link_failed"))
    elif tag == "decline-booking":
        events.append(event("booking_declined"))

    leads = []
    if tag in {"finish-discovery", "handoff", "voicemail-save", "send-booking-link", "decline-booking"}:
        number = ""
        for key in ("callback_number", "caller_number"):
            candidate = digits(combined.get(key))
            if is_usable_us_number(candidate):
                number = "+1" + candidate
                break
        leads.append({
            "lead_id": "lead_" + _digest(call_id), "call_id": call_id,
            "created_at": created, "updated_at": now, "ingested_at": now,
            "caller_first_name": _text(combined.get("caller_first_name"), 100) or None,
            "callback_number": number or None, "service_category": _category(discovery),
            "project_needs": _text(combined.get("project_needs"), 12000) or None,
            "project_summary": _text(discovery.get("summary"), 4000) or None,
            "message_summary": _text(combined.get("analytics_message_summary"), 4000) or None,
            "sms_consent": consent, "follow_up_status": "needs_follow_up", "is_test": is_test,
        })
    return state, events, leads


@lru_cache(maxsize=4)
def _client(project, location):
    from google.cloud import bigquery
    return bigquery.Client(project=project, location=location)


def write_records(events: list[dict], leads: list[dict]):
    """Use the Cloud Run service identity. Never log rows or provider errors."""
    if not enabled() or not (events or leads):
        return
    project = os.getenv("BIGQUERY_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT", "")
    dataset = os.getenv("BIGQUERY_DATASET", "maya_analytics")
    location = os.getenv("BIGQUERY_LOCATION", "us-central1")
    if not re.fullmatch(r"[a-z][a-z0-9-]{4,61}[a-z0-9]", project) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", dataset):
        log("analytics_failed", reason="invalid destination configuration")
        return
    try:
        client = _client(project, location)
    except Exception as exc:
        # Analytics must not break an already successful caller interaction.
        log("analytics_failed", stage="client", error_type=type(exc).__name__)
        return
    for table, rows in (("call_events", events), ("leads", leads)):
        if not rows:
            continue
        ids = [row["event_id"] for row in rows] if table == "call_events" else [
            _digest(json.dumps(row, sort_keys=True)) for row in rows
        ]
        try:
            errors = client.insert_rows_json(
                f"{project}.{dataset}.{table}", rows, row_ids=ids, timeout=1.5, retry=None,
                skip_invalid_rows=False, ignore_unknown_values=False,
            )
            if errors:
                log("analytics_failed", table=table, reason="row_errors", error_count=len(errors))
            else:
                log("analytics_written", table=table, row_count=len(rows))
        except Exception as exc:
            log("analytics_failed", table=table, error_type=type(exc).__name__)

