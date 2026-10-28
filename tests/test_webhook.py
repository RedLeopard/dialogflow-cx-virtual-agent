import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import main
from backend.contact import first_name, spoken_number
from backend.discovery import ProjectDiscovery

client = TestClient(main.app)
AGENT = Path(__file__).resolve().parents[1] / "dialogflow" / "agent"


def call(tag, **params):
    r = client.post("/webhook", json={"fulfillmentInfo": {"tag": tag},
                                      "sessionInfo": {"parameters": params}})
    return r.status_code, r.json()


def said(body):
    return body["fulfillmentResponse"]["messages"][0]["text"]["text"][0]


@pytest.mark.parametrize("raw,expected", [
    ("Maria", "Maria"),
    ("hi this is maria lopez", "Maria"),
    ("My name is JAMES", "James"),
    ("yeah it's DeShawn", "DeShawn"),
    ("I'm O'Neil", "O'Neil"),
    ("um", ""),
    ("", ""),
    (None, ""),
])
def test_first_name(raw, expected):
    assert first_name(raw) == expected


def test_spoken_number():
    assert spoken_number("3145550123") == "3 1 4, 5 5 5, 0 1 2 3"


def test_greet_caller_uses_name():
    code, body = call("greet-caller", caller_name_raw="this is maria")
    assert code == 200
    assert said(body) == "Great to meet you, Maria."
    assert body["sessionInfo"]["parameters"]["caller_first_name"] == "Maria"


def test_greet_caller_without_name():
    _, body = call("greet-caller", caller_name_raw="uh")
    assert said(body) == "Great to meet you."
    assert body["sessionInfo"]["parameters"]["caller_first_name"] is None


def test_offer_callback_with_twilio_number():
    _, body = call("offer-callback", caller_number="+13145550123")
    assert "3 1 4, 5 5 5, 0 1 2 3" in said(body)
    assert body["sessionInfo"]["parameters"]["callback_candidate"] == "3145550123"


def test_offer_callback_without_caller_id_is_silent():
    _, body = call("offer-callback")
    assert "fulfillmentResponse" not in body
    assert body["sessionInfo"]["parameters"]["callback_candidate"] is None


def test_confirm_callback_reads_back():
    _, body = call("confirm-callback", callback_number_raw="(314) 555-0199")
    assert said(body).endswith("3 1 4, 5 5 5, 0 1 9 9. Did I get that right?")
    assert body["sessionInfo"]["parameters"]["callback_number_raw"] == "3145550199"


def test_discovery_passes_name(monkeypatch):
    seen = {}

    def fake(needs, name=None):
        seen["name"] = name
        return ProjectDiscovery(project_type="cloud", current_platform="AWS",
                                target_platform="Google Cloud", customer_problem=None,
                                timeline=None, requirements=[], summary="s",
                                follow_up_question="Got it, Maria. When do you need it live?")

    monkeypatch.setattr(main, "discover_project", fake)
    _, body = call("discover-project", project_needs="move off AWS", caller_first_name="Maria")
    assert seen["name"] == "Maria"
    assert body["sessionInfo"]["parameters"]["discovery_status"] == "complete"


def test_discovery_failure_keeps_conversation_moving(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("down")

    monkeypatch.setattr(main, "discover_project", boom)
    _, body = call("discover-project", project_needs="new website")
    assert said(body) == main.FALLBACK_FOLLOW_UP
    assert body["sessionInfo"]["parameters"]["discovery_status"] == "failed"


def test_unknown_tag_rejected():
    assert call("nope")[0] == 400


def test_flow_references_resolve():
    flow_dir = AGENT / "flows" / "Default Start Flow"
    pages = {p.stem for p in (flow_dir / "pages").glob("*.json")} | {"End Session"}
    intents = {p.name for p in (AGENT / "intents").iterdir()}
    tags = set(main.HANDLERS)
    files = [flow_dir / "Default Start Flow.json", *(flow_dir / "pages").glob("*.json")]
    for f in files:
        text = f.read_text()
        data = json.loads(text)
        for target in _find(data, "targetPage"):
            assert target in pages, f"{f.name}: unknown page {target}"
        for intent in _find(data, "intent"):
            assert intent in intents, f"{f.name}: unknown intent {intent}"
        for tag in _find(data, "tag"):
            assert tag in tags, f"{f.name}: unhandled webhook tag {tag}"


def _find(node, key):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key and isinstance(v, str):
                yield v
            else:
                yield from _find(v, key)
    elif isinstance(node, list):
        for item in node:
            yield from _find(item, key)
