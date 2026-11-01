"""Offline analytics regression checks. No credentials, calls, or cloud writes."""
import json
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from backend import analytics, main
from tests.test_webhook import LEAD, outbox

SID = "CA" + "a" * 32
SESSION = "projects/example/locations/us-central1/agents/agent/sessions/session-one"


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    monkeypatch.setenv("BIGQUERY_ENABLED", "true")
    monkeypatch.setenv("BIGQUERY_PROJECT", "csd-dialogflow-cx-2026")
    monkeypatch.setenv("BIGQUERY_DATASET", "maya_analytics")


def request(tag="finish-discovery", **params):
    return {"fulfillmentInfo": {"tag": tag}, "detectIntentResponseId": "response-123",
            "sessionInfo": {"session": SESSION, "parameters": {"call_id": SID, **LEAD, **params}}}


def response(**params):
    return {"sessionInfo": {"parameters": params}}


def types(events):
    return {e["event_type"] for e in events}


def test_disabled_does_not_build_or_write(monkeypatch):
    monkeypatch.delenv("BIGQUERY_ENABLED")
    client = Mock()
    monkeypatch.setattr(analytics, "_client", client)
    assert analytics.records_for(request(), response()) == ({}, [], [])
    analytics.write_records([{"event_id": "id"}], [])
    client.assert_not_called()


def test_stable_event_identity_and_no_raw_contacts_in_event_rows():
    original = request()
    state, events, leads = analytics.records_for(original, response(lead_notified=True))
    assert original == request()  # No mutation of the caller's request.
    assert state["analytics_call_id"] == SID
    assert len({e["event_id"] for e in events}) == len(events)
    assert [e["event_id"] for e in events] == [e["event_id"] for e in analytics.records_for(original, response(lead_notified=True))[1]]
    serialized = json.dumps(events)
    for private in ("Maria", "3145550123", "WordPress on AWS", "Move our WordPress", SESSION):
        assert private not in serialized
    assert leads[0]["callback_number"] == "+13145550123"
    assert leads[0]["project_summary"] == LEAD["project_discovery"]["summary"]
    assert "notification_accepted" in types(events)
    assert "notification_delivered" not in types(events)


def test_new_request_id_produces_new_event_ids():
    first = request()
    second = {**first, "detectIntentResponseId": "different"}
    assert analytics.records_for(first, response())[1][0]["event_id"] != analytics.records_for(second, response())[1][0]["event_id"]


def test_return_session_reuses_call_and_lead_identity():
    state, _, first = analytics.records_for(request(), response())
    later = request("voicemail-save", **state)
    later["sessionInfo"]["session"] = "different-session"
    state2, events, second = analytics.records_for(later, response(analytics_message_summary="Please call tomorrow."))
    assert first[0]["lead_id"] == second[0]["lead_id"]
    assert first[0]["created_at"] == second[0]["created_at"]
    assert second[0]["message_summary"] == "Please call tomorrow."
    assert state2["analytics_call_id"] == SID


def test_session_fallback_is_stable_and_phone_is_not_a_call_id():
    req = request(call_id="+13145550123")
    state, events, _ = analytics.records_for(req, response())
    assert state["analytics_call_id"].startswith("df_")
    req["sessionInfo"]["parameters"].update(state)
    assert analytics.records_for(req, response())[0]["analytics_call_id"] == state["analytics_call_id"]


def test_missing_identity_skips(capsys):
    req = request(call_id="")
    req["sessionInfo"]["session"] = None
    assert analytics.records_for(req, response()) == ({}, [], [])
    assert "missing call/session identity" in capsys.readouterr().out


@pytest.mark.parametrize("tag,updates,expected", [
    ("handoff", {}, {"webhook_processed", "transfer_requested"}),
    ("send-booking-link", {"booking_sms_sent": True}, {"webhook_processed", "booking_link_sent"}),
    ("send-booking-link", {"booking_sms_sent": False}, {"webhook_processed", "booking_link_failed"}),
    ("decline-booking", {}, {"webhook_processed", "booking_declined"}),
    ("voicemail-save", {"voicemail_delivered": False}, {"webhook_processed", "message_captured"}),
])
def test_metrics_only_assert_observed_outcomes(tag, updates, expected):
    _, events, _ = analytics.records_for(request(tag), response(**updates))
    assert types(events) == expected
    assert not types(events) & {"call_started", "call_completed", "transfer_accepted", "booking_confirmed", "notification_delivered"}


def test_no_duplicate_booking_event_when_link_already_sent():
    _, events, _ = analytics.records_for(request("send-booking-link", booking_sms_sent=True), response())
    assert types(events) == {"webhook_processed"}


def test_consent_is_nullable_and_follows_booking_route():
    assert analytics.records_for(request(), response())[2][0]["sms_consent"] is None
    for tag, update, expected in (("send-booking-link", {"booking_sms_sent": False}, True), ("decline-booking", {}, False)):
        state, events, leads = analytics.records_for(request(tag), response(**update))
        assert state["analytics_sms_consent"] is expected
        assert all(e["sms_consent"] is expected for e in events)
        assert leads[0]["sms_consent"] is expected


def test_test_rows_and_category_are_controlled():
    req = request(analytics_is_test=True, project_discovery={"project_type": "Cloud migration for Maria", "summary": "private"})
    _, events, leads = analytics.records_for(req, response())
    assert all(e["is_test"] is True and e["service_category"] == "cloud" for e in events)
    assert leads[0]["is_test"] is True
    assert "Maria" not in json.dumps(events)


def test_writer_uses_expected_tables_ids_and_timeout(monkeypatch):
    fake = Mock()
    fake.insert_rows_json.return_value = []
    monkeypatch.setattr(analytics, "_client", lambda *a: fake)
    _, events, leads = analytics.records_for(request(), response())
    analytics.write_records(events, leads)
    calls = fake.insert_rows_json.call_args_list
    assert [c.args[0] for c in calls] == ["csd-dialogflow-cx-2026.maya_analytics.call_events", "csd-dialogflow-cx-2026.maya_analytics.leads"]
    assert calls[0].kwargs["row_ids"] == [e["event_id"] for e in events]
    assert all(c.kwargs["retry"] is None and c.kwargs["timeout"] == 1.5 for c in calls)


@pytest.mark.parametrize("failure", ["rows", "exception", "credentials"])
def test_writer_failure_does_not_raise_or_log_private_rows(monkeypatch, capsys, failure):
    fake = Mock()
    fake.insert_rows_json.return_value = [{"errors": [{"message": "PRIVATE_CALLER_DATA"}]}] if failure == "rows" else []
    if failure == "exception":
        fake.insert_rows_json.side_effect = RuntimeError("PRIVATE_CALLER_DATA")
    def factory(*a):
        if failure == "credentials":
            raise RuntimeError("PRIVATE_CALLER_DATA")
        return fake
    monkeypatch.setattr(analytics, "_client", factory)
    _, events, leads = analytics.records_for(request(), response())
    analytics.write_records(events, leads)
    logs = capsys.readouterr().out
    assert "analytics_failed" in logs
    assert "PRIVATE_CALLER_DATA" not in logs
    assert "Maria" not in logs
    if failure != "credentials":
        assert fake.insert_rows_json.call_count == 2  # Event failure does not prevent lead attempt.


def test_webhook_writes_real_result_and_keeps_speech(outbox, monkeypatch):
    written = []
    monkeypatch.setattr(analytics, "write_records", lambda events, leads: written.append((events, leads)))
    result = TestClient(main.app).post("/webhook", json=request("send-booking-link"))
    assert result.status_code == 200
    assert "Done, it's on its way" in json.dumps(result.json())
    assert "booking_link_sent" in types(written[0][0])
    assert result.json()["sessionInfo"]["parameters"]["analytics_call_id"] == SID


def test_preparation_error_cannot_break_call(monkeypatch):
    def fail(*a):
        raise ValueError("private")
    monkeypatch.setattr(analytics, "records_for", fail)
    result = TestClient(main.app).post("/webhook", json=request("greet-caller", caller_name_raw="Maria"))
    assert result.status_code == 200
    assert "Hi Maria." in json.dumps(result.json())
