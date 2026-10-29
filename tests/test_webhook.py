import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import main, notify
from backend.contact import first_name, spoken_number
from backend.discovery import ProjectDiscovery, VoicemailSummary

client = TestClient(main.app)
AGENT = Path(__file__).resolve().parents[1] / "dialogflow" / "agent"


@pytest.fixture
def outbox(monkeypatch):
    """Capture texts and emails instead of sending them."""
    box = {"sms": [], "email": [], "sms_ok": True, "email_ok": True}

    def sms(to, body):
        box["sms"].append((to, body))
        return box["sms_ok"]

    def email(to, subject, body):
        box["email"].append((to, subject, body))
        return box["email_ok"]

    monkeypatch.setattr(main, "send_sms", sms)
    monkeypatch.setattr(main, "send_email", email)
    monkeypatch.setenv("OWNER_CELL", "+13145550100")
    monkeypatch.setenv("OWNER_EMAIL", "owner@example.com")
    return box


def call(tag, **params):
    r = client.post("/webhook", json={"fulfillmentInfo": {"tag": tag},
                                      "sessionInfo": {"parameters": params}})
    return r.status_code, r.json()


def said(body):
    return " ".join(m["text"]["text"][0] for m in body["fulfillmentResponse"]["messages"] if "text" in m)


def params_of(body):
    return body["sessionInfo"]["parameters"]


LEAD = dict(caller_first_name="Maria", callback_number="3145550123",
            project_needs="Move our WordPress site off AWS", project_follow_up="Within two months",
            project_discovery={"summary": "WordPress on AWS to Google Cloud, two months."})


# ------------------------------------------------------------------ contact intake
@pytest.mark.parametrize("raw,expected", [
    ("Maria", "Maria"), ("hi this is maria lopez", "Maria"), ("My name is JAMES", "James"),
    ("yeah it's DeShawn", "DeShawn"), ("I'm O'Neil", "O'Neil"), ("um", ""), ("", ""), (None, ""),
])
def test_first_name(raw, expected):
    assert first_name(raw) == expected


def test_spoken_number():
    assert spoken_number("3145550123") == "3 1 4, 5 5 5, 0 1 2 3"


def test_greet_is_short():
    _, body = call("greet-caller", caller_name_raw="this is maria")
    assert said(body) == "Hi Maria."
    assert params_of(body)["caller_first_name"] == "Maria"


def test_offer_callback_reads_last_four_only():
    _, body = call("offer-callback", caller_number="+13145550123")
    assert "ending in 0 1 2 3" in said(body)
    assert params_of(body)["callback_candidate"] == "3145550123"


def test_offer_callback_without_caller_id_is_silent():
    _, body = call("offer-callback")
    assert "fulfillmentResponse" not in body
    assert params_of(body)["callback_candidate"] is None


def test_confirm_callback_reads_back():
    _, body = call("confirm-callback", callback_number_raw="(314) 555-0199")
    assert said(body) == "That's 3 1 4, 5 5 5, 0 1 9 9, right?"


# ------------------------------------------------------------------ discovery, lead, booking
def test_discovery_passes_name(monkeypatch):
    seen = {}

    def fake(needs, name=None):
        seen["name"] = name
        return ProjectDiscovery(project_type="cloud", current_platform="AWS", target_platform=None,
                                customer_problem=None, timeline=None, requirements=[], summary="s",
                                follow_up_question="Got it. When do you need it done?")

    monkeypatch.setattr(main, "discover_project", fake)
    _, body = call("discover-project", project_needs="move off AWS", caller_first_name="Maria")
    assert seen["name"] == "Maria"
    assert params_of(body)["discovery_status"] == "complete"


def test_discovery_failure_keeps_moving(monkeypatch):
    monkeypatch.setattr(main, "discover_project", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
    _, body = call("discover-project", project_needs="new website")
    assert said(body) == main.FALLBACK_FOLLOW_UP
    assert params_of(body)["discovery_status"] == "failed"


def test_finish_discovery_sends_lead_and_offers_text(outbox):
    _, body = call("finish-discovery", **LEAD)
    (to, sms), = outbox["sms"]
    assert to == "+13145550100"
    assert "Maria - (314) 555-0123" in sms and "WordPress" in sms
    assert outbox["email"][0][0] == "owner@example.com"
    assert "text you a link" in said(body)
    assert params_of(body)["lead_notified"] is True


def test_finish_discovery_does_not_double_notify(outbox):
    call("finish-discovery", **LEAD, lead_notified=True)
    assert outbox["sms"] == [] and outbox["email"] == []


def test_send_booking_link_texts_caller(outbox):
    _, body = call("send-booking-link", **LEAD, lead_notified=True)
    (to, sms), = outbox["sms"]
    assert to == "3145550123"
    assert main.BOOKING_URL in sms and "STOP" in sms
    assert "on its way" in said(body)
    assert "http" not in said(body)  # never spoken
    assert params_of(body)["booking_sms_sent"] is True


def test_send_booking_link_not_resent(outbox):
    _, body = call("send-booking-link", **LEAD, booking_sms_sent=True)
    assert outbox["sms"] == []
    assert "already" in said(body)


def test_send_booking_link_failure_is_honest(outbox):
    outbox["sms_ok"] = False
    _, body = call("send-booking-link", **LEAD, lead_notified=True)
    assert "couldn't send" in said(body)
    assert params_of(body)["booking_sms_sent"] is False


def test_decline_booking(outbox):
    _, body = call("decline-booking", **LEAD, lead_notified=True)
    assert "ending in 0 1 2 3" in said(body)


# ------------------------------------------------------------------ transfer and voicemail
def test_handoff_alerts_owner_and_requests_transfer(outbox):
    _, body = call("handoff", **LEAD)
    assert outbox["sms"][0][0] == "+13145550100"
    assert "Transferring" in outbox["sms"][0][1]
    msgs = body["fulfillmentResponse"]["messages"]
    handoff = [m for m in msgs if "liveAgentHandoff" in m][0]["liveAgentHandoff"]["metadata"]
    assert handoff["caller_first_name"] == "Maria" and handoff["callback_number"] == "3145550123"


def test_voicemail_intro_uses_name():
    _, body = call("voicemail-intro", caller_first_name="Maria")
    assert said(body).startswith("Sorry Maria, nobody could pick up")


def test_voicemail_save_delivers_summary(outbox, monkeypatch):
    monkeypatch.setattr(main, "summarize_voicemail", lambda m, n=None: VoicemailSummary(
        summary="Needs a migration quote before Friday.", urgency="urgent",
        callback_requested=True, spoken_recap="Got it, a migration quote before Friday."))
    _, body = call("voicemail-save", voicemail_message="Please call me about a quote before Friday",
                   caller_first_name="Maria", callback_number="3145550123")
    assert outbox["sms"][0][1].startswith("URGENT Voicemail from Maria - (314) 555-0123")
    assert "Full message:\nPlease call me" in outbox["email"][0][2]
    assert said(body).startswith("Got it, a migration quote before Friday. I've sent your message")
    assert params_of(body)["voicemail_delivered"] is True


def test_voicemail_uses_caller_id_and_survives_gemini_failure(outbox, monkeypatch):
    monkeypatch.setattr(main, "summarize_voicemail", lambda *a, **k: (_ for _ in ()).throw(RuntimeError()))
    _, body = call("voicemail-save", voicemail_message="Call me back", caller_number="+13145550177")
    assert "(314) 555-0177" in outbox["sms"][0][1]
    assert "ending in 0 1 7 7" in said(body)


def test_voicemail_never_claims_delivery_when_both_channels_fail(outbox, monkeypatch):
    outbox["sms_ok"] = outbox["email_ok"] = False
    monkeypatch.setattr(main, "summarize_voicemail", lambda *a, **k: (_ for _ in ()).throw(RuntimeError()))
    _, body = call("voicemail-save", voicemail_message="Call me back", callback_number="3145550123")
    assert "sent your message" not in said(body)
    assert params_of(body)["voicemail_delivered"] is False


# ------------------------------------------------------------------ notify helpers
def test_sms_skips_without_config(monkeypatch):
    for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_MESSAGING_SERVICE_SID", "TWILIO_FROM_NUMBER"):
        monkeypatch.delenv(k, raising=False)
    assert notify.send_sms("3145550123", "hi") is False


def test_e164():
    assert notify.e164("3145550123") == "+13145550123"
    assert notify.e164("+13145550123") == "+13145550123"
    assert notify.e164("555") == ""


def test_unknown_tag_rejected():
    assert call("nope")[0] == 400


# ------------------------------------------------------------------ agent package integrity
def test_flow_references_resolve():
    flow_dir = AGENT / "flows" / "Default Start Flow"
    pages = {p.stem for p in (flow_dir / "pages").glob("*.json")} | {"End Session"}
    intents = {p.name for p in (AGENT / "intents").iterdir()}
    for f in [flow_dir / "Default Start Flow.json", *(flow_dir / "pages").glob("*.json")]:
        data = json.loads(f.read_text())
        for target in _find(data, "targetPage"):
            assert target in pages, f"{f.name}: unknown page {target}"
        for intent in _find(data, "intent"):
            assert intent in intents, f"{f.name}: unknown intent {intent}"
        for tag in _find(data, "tag"):
            assert tag in main.HANDLERS, f"{f.name}: unhandled webhook tag {tag}"


def test_no_url_is_ever_spoken():
    flow_dir = AGENT / "flows" / "Default Start Flow"
    for f in [flow_dir / "Default Start Flow.json", *(flow_dir / "pages").glob("*.json")]:
        assert not re.search(r"https?://", f.read_text()), f"{f.name} contains a URL"


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
