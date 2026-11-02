"""Offline service-intake contracts; model responses are mocked, not rated."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend import analytics, conversation, discovery, main, services
from tests.test_conversation import result


@pytest.mark.parametrize('legacy', [False, True])
def test_both_model_entry_points_receive_the_same_open_inquiry_guidance(monkeypatch, legacy):
    seen = {}
    turn = result('The team can discuss your CX engineering project.',
                  action='offer_booking', project_type='cx')

    def generate(**kwargs):
        seen.update(kwargs)
        value = turn.discovery if legacy else turn
        return SimpleNamespace(text=value.model_dump_json())

    client = SimpleNamespace(models=SimpleNamespace(generate_content=generate))
    monkeypatch.setenv('GEMINI_MODEL', 'test-model')
    monkeypatch.setattr(discovery if legacy else conversation, '_client', lambda: client)
    if legacy:
        discovery.discover_project('Do you do CX engineering?')
    else:
        conversation.generate_turn('Do you do CX engineering?', [], None, None)
    instruction = seen['config'].system_instruction
    for guidance in (services.SERVICE_FACTS, services.INQUIRY_GUIDANCE,
                     services.PROJECT_TYPE_GUIDANCE):
        assert guidance in instruction


@pytest.mark.parametrize('question,kind,category', [
    ('Do you do CX engineering?', 'cx', 'customer_experience'),
    ('I need help with C X engineering.', 'cx', 'customer_experience'),
    ('Can you build an AI agent?', 'ai', 'ai'),
    ('We need a database migration.', 'data', 'data'),
    ('Can you help with Kubernetes and CI/CD?', 'devops', 'devops'),
    ('We need a cloud security assessment.', 'security', 'cloud_security'),
    ('We have an edge computing project on Oracle Cloud.', 'cloud', 'cloud'),
])
def test_service_answers_reach_booking_route_and_analytics_without_sending_messages(
        monkeypatch, question, kind, category):
    # This exercises the real webhook and generation adapter, with only the
    # external model and analytics write mocked. It does not prove model quality.
    answer = 'Our team can discuss that project and review the scope with you.'
    turn = result(answer, action='offer_booking', project_type=kind,
                  summary=question)
    monkeypatch.setenv('GEMINI_MODEL', 'test-model')
    monkeypatch.setenv('BIGQUERY_ENABLED', 'true')
    monkeypatch.setattr(conversation, '_client', lambda: SimpleNamespace(
        models=SimpleNamespace(generate_content=lambda **k: SimpleNamespace(
            text=turn.model_dump_json()))))
    written = []
    monkeypatch.setattr(analytics, 'write_records', lambda events, leads: written.extend(events))
    monkeypatch.setattr(main, 'send_sms', lambda *a, **k: pytest.fail('Unrequested SMS'))
    monkeypatch.setattr(main, 'notify_owner', lambda **k: pytest.fail('Premature notification'))
    response = TestClient(main.app).post('/webhook', json={
        'fulfillmentInfo': {'tag': 'start-conversation'},
        'sessionInfo': {'session': 'sessions/service-test',
                        'parameters': {'project_needs': question}},
    })
    assert response.status_code == 200
    body = response.json()
    params = body['sessionInfo']['parameters']
    assert params['conversation_action'] == 'offer_booking'
    assert params['project_discovery']['project_type'] == kind
    assert params['project_discovery']['summary'] == question
    assert body['fulfillmentResponse']['messages'][0]['text']['text'] == [answer]
    assert written and {e['service_category'] for e in written} == {category}


def test_new_categories_cannot_leak_caller_words_into_reporting_dimensions():
    private = 'CX engineering for private-person@example.com'
    assert analytics._category({'project_type': private}) == 'customer_experience'
    assert analytics._category({'project_type': 'private-person@example.com'}) == 'other'


def test_generated_service_intent_is_deployable_and_free_text_intake_stays_open():
    from scripts import apply_agent, build_agent

    assert 'consultation.request' in apply_agent.MANAGED_INTENTS
    phrases = build_agent.INTENTS['consultation.request']
    root = Path(__file__).resolve().parents[1] / 'dialogflow/agent'
    generated = json.loads((root / 'intents/consultation.request/trainingPhrases/en.json').read_text())
    assert [''.join(part['text'] for part in p['parts'])
            for p in generated['trainingPhrases']] == phrases
    for inquiry in ('Do you do CX engineering?', 'We need a data migration',
                    'We want to build an AI agent', 'I have a cloud project that is not on your list'):
        assert inquiry in phrases
    pages = {p['displayName']: p for p in build_agent.pages}
    for name in ('Consultation Request', 'Project Follow-up'):
        assert pages[name]['form']['parameters'][0]['entityType'] == '@sys.any'
