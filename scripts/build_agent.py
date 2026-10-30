#!/usr/bin/env python3
"""Generate the Dialogflow CX flow, pages, and custom intents in dialogflow/agent/.

Edit the conversation here, run `python3 scripts/build_agent.py`, review the
JSON diff, then deploy with `python3 scripts/apply_agent.py --publish`.
Ids are deterministic so regenerating does not churn the diff.
"""
import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "dialogflow" / "agent"
FLOW_DIR = ROOT / "flows" / "Default Start Flow"
PAGES = FLOW_DIR / "pages"
WEBHOOK = "Project Discovery Backend"
NS = uuid.UUID("2f1d7c3e-5b7a-4c1e-9a55-0c5d1c5d2026")


def uid(*key):
    return str(uuid.uuid5(NS, "/".join(key)))


def text(*variants):
    return {"text": {"text": list(variants)}, "languageCode": "en"}


def spoken(words):
    return {"outputAudioText": {"text": words}, "languageCode": "en"}


def webhook(tag):
    return {"webhook": WEBHOOK, "tag": tag}


def handler(owner, event, *messages, target=None):
    h = {"event": event, "triggerFulfillment": {"messages": list(messages)}, "name": uid(owner, event)}
    if target:
        h["targetPage"] = target
    return h


def route(owner, key, target=None, fulfillment=None, intent=None, condition=None, params=None):
    r = {"name": uid(owner, key)}
    if intent:
        r["intent"] = intent
    if condition:
        r["condition"] = condition
    if fulfillment or params:
        r["triggerFulfillment"] = dict(fulfillment or {})
        if params:
            r["triggerFulfillment"]["setParameterActions"] = [
                {"parameter": k, "value": v} for k, v in params.items()
            ]
    if target:
        r["targetPage"] = target
    return r


def form(owner, param, entity, prompt, reprompts=()):
    fill = {"initialPromptFulfillment": prompt}
    if reprompts:
        fill["repromptEventHandlers"] = [handler(owner, ev, msg) for ev, msg in reprompts]
    return {"parameters": [{"displayName": param, "required": True, "entityType": entity, "fillBehavior": fill}]}


def page(name, **fields):
    return {"name": uid("page", name), "displayName": name, **fields}


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


FINAL = '$page.params.status = "FINAL"'

# ---------------------------------------------------------------- copy (keep it short)
# One plain text greeting, spoken on the phone. Do not add an outputAudioText
# version: when one is present the phone speaks only that and skips the
# "Who am I speaking with?" prompt, leaving dead air.
GREETING = (
    "Hey there, and thank you for calling Cloud Systems Direct. I'm Maya. "
    "Great ideas deserve the right team behind them."
)
NO_MATCH = text("Sorry, could you say that another way?", "Sorry, one more time?")
NO_INPUT = text("Are you still there?", "Take your time, I'm here.")
YES_NO = text("Just a yes or no is perfect.")

# ---------------------------------------------------------------- start flow
start_flow = {
    "name": "00000000-0000-0000-0000-000000000000",
    "displayName": "Default Start Flow",
    "description": "Cloud Systems Direct phone assistant: greeting, contact intake, discovery, "
                   "booking text, live transfer, and smart voicemail.",
    "transitionRoutes": [
        route("flow", "welcome", intent="Default Welcome Intent", target="Start Router"),
        route("flow", "consultation", intent="consultation.request", condition="$session.params.caller_first_name = null", target="Start Router"),
        # Available on every page, except while taking a voicemail after a missed transfer.
        route("flow", "handoff", intent="agent.handoff",
              condition='$session.params.mode != "voicemail"', target="Live Transfer"),
    ],
    "eventHandlers": [
        # Twilio's connector sends this event when the call connects.
        handler("flow", "Default Welcome Intent", target="Start Router"),
        # Backup entry for a Studio widget configured with welcomeIntent=VOICEMAIL.
        handler("flow", "VOICEMAIL", target="Voicemail"),
        handler("flow", "sys.no-match-default", NO_MATCH),
        handler("flow", "sys.no-input-default", NO_INPUT),
    ],
    "nluSettings": {"modelType": "MODEL_TYPE_ADVANCED", "classificationThreshold": 0.30000001},
    "nluSettingsList": [{
        "modelType": "MODEL_TYPE_ADVANCED",
        "classificationThreshold": 0.30000001,
        "customConfigKey": "a2f6529d-2e26-468c-8448-4c0e7b9a9633",
        "languageCode": "en",
    }],
}
for h in start_flow["eventHandlers"]:
    if not h["triggerFulfillment"]["messages"]:
        del h["triggerFulfillment"]

# ---------------------------------------------------------------- pages
pages = [
    page("Start Router", transitionRoutes=[
        # Studio's second Virtual Agent widget passes mode=voicemail after a missed transfer.
        route("router", "voicemail", condition='$session.params.mode = "voicemail"', target="Voicemail"),
        route("router", "greeting", condition="true", target="Caller Name",
              fulfillment={"messages": [text(GREETING)]}),
    ]),
    page("Caller Name",
         form=form("Caller Name", "caller_name_raw", "@sys.any",
                   {"messages": [text("Who do I have the pleasure of speaking with today?")]},
                   [("sys.no-input-default", text("Sorry, who am I speaking with?"))]),
         transitionRoutes=[route("Caller Name", "done", condition=FINAL,
                                 fulfillment=webhook("greet-caller"), target="Callback Number")]),
    page("Callback Number",
         # Backend offers the caller ID if Twilio passed it, else leaves callback_candidate empty.
         entryFulfillment=webhook("offer-callback"),
         transitionRoutes=[
             route("Callback Number", "no-caller-id", condition="$session.params.callback_candidate = null",
                   target="Alternate Number"),
             route("Callback Number", "yes", intent="confirm.yes", target="Consultation Request",
                   params={"callback_number": "$session.params.callback_candidate"}),
             route("Callback Number", "no", intent="confirm.no", target="Alternate Number"),
         ],
         eventHandlers=[handler("Callback Number", "sys.no-match-default", YES_NO)]),
    page("Alternate Number",
         form=form("Alternate Number", "callback_number_raw", "@sys.phone-number",
                   {"messages": [text("What's the best number to reach you?")]},
                   [("sys.no-match-default", text("Sorry, what's the number, with area code?")),
                    ("sys.no-input-default", text("What's the best number to reach you?"))]),
         transitionRoutes=[route("Alternate Number", "done", condition=FINAL,
                                 fulfillment=webhook("confirm-callback"), target="Confirm Callback")]),
    page("Confirm Callback",
         transitionRoutes=[
             route("Confirm Callback", "yes", intent="confirm.yes", target="Consultation Request",
                   params={"callback_number": "$session.params.callback_number_raw"}),
             route("Confirm Callback", "no", intent="confirm.no", target="Alternate Number",
                   fulfillment={"messages": [text("Sorry, let's try again.")]},
                   params={"callback_number_raw": None}),
         ],
         eventHandlers=[handler("Confirm Callback", "sys.no-match-default", YES_NO)]),
    page("Consultation Request",
         form=form("Consultation Request", "project_needs", "@sys.any",
                   {"messages": [text("What can we help you with today?")]}),
         transitionRoutes=[route("Consultation Request", "done", condition=FINAL, target="Project Follow-up")]),
    page("Project Follow-up",
         entryFulfillment=webhook("start-conversation"),
         form=form("Project Follow-up", "project_follow_up", "@sys.any", {"messages": []}),
         transitionRoutes=[
             route("Project Follow-up", "action", condition='$session.params.conversation_action = "offer_booking" OR $session.params.conversation_action = "handoff" OR $session.params.conversation_action = "take_message"',
                   target="Conversation Router"),
             route("Project Follow-up", "done", condition=FINAL, target="Conversation Router"),
         ]),
    page("Conversation Router",
         entryFulfillment=webhook("continue-conversation"),
         transitionRoutes=[
             route("Conversation Router", "handoff", condition='$session.params.conversation_action = "handoff"',
                   target="Live Transfer"),
             route("Conversation Router", "message", condition='$session.params.conversation_action = "take_message"',
                   target="Voicemail", params={"message_requested": True}),
             route("Conversation Router", "booking", condition='$session.params.conversation_action = "offer_booking"',
                   fulfillment=webhook("finish-discovery"), target="Booking Offer"),
             route("Conversation Router", "continue", condition="true", target="Project Follow-up"),
         ]),
    page("Booking Offer",
         transitionRoutes=[
             route("Booking Offer", "no-number", condition="$session.params.booking_offerable = false",
                   target="End Session",
                   fulfillment={"messages": [text("Our team will be in touch soon. Thanks for calling Cloud Systems Direct.")]}),
             route("Booking Offer", "yes", intent="confirm.yes", target="End Session",
                   fulfillment=webhook("send-booking-link")),
             route("Booking Offer", "no", intent="confirm.no", target="Message Offer"),
             route("Booking Offer", "message", intent="message.request", target="Voicemail",
                   params={"message_requested": True}),
         ],
         eventHandlers=[handler("Booking Offer", "sys.no-match-default",
                                text("Just a yes or no. Want the booking link by text?"))]),
    page("Message Offer",
         entryFulfillment={"messages": [text("No problem. Would you like to leave a message for our team instead?")]},
         transitionRoutes=[
             route("Message Offer", "yes", intent="confirm.yes", target="Voicemail",
                   params={"message_requested": True}),
             route("Message Offer", "message", intent="message.request", target="Voicemail",
                   params={"message_requested": True}),
             route("Message Offer", "no", intent="confirm.no", target="End Session",
                   fulfillment={"messages": [text("No problem. Thanks for calling Cloud Systems Direct.")]}),
         ],
         eventHandlers=[handler("Message Offer", "sys.no-match-default",
                                text("Would you like to leave a message?"))]),
    page("Live Transfer",
         # Backend texts the owner a heads-up and returns a live agent handoff to Twilio.
         entryFulfillment=webhook("handoff")),
    page("Voicemail",
         form=form("Voicemail", "voicemail_message", "@sys.any", webhook("voicemail-intro"),
                   [("sys.no-input-default", text("Go ahead whenever you're ready."))]),
         transitionRoutes=[route("Voicemail", "done", condition=FINAL,
                                 fulfillment=webhook("voicemail-save"), target="End Session")]),
]

# ---------------------------------------------------------------- intents
INTENTS = {
    "message.request": ["leave a message", "I'd like to leave a message", "can I leave a message",
                        "take a message", "please take a message for the team",
                        "have someone call me back", "I'd prefer a callback",
                        "can the owner call me back", "I just want to leave a message"],
    "confirm.yes": ["yes", "yeah", "yep", "yup", "correct", "that's right", "that is correct",
                    "sure", "that works", "sounds good", "you got it", "perfect", "absolutely",
                    "that's the one", "this number is fine", "yes that's my number",
                    "yes please", "go ahead", "please do", "send it", "text me"],
    "confirm.no": ["no", "nope", "nah", "that's wrong", "that's not right", "incorrect",
                   "not quite", "wrong number", "use a different number", "no that's not it",
                   "that's not my number", "can you use another number", "no thanks",
                   "no thank you", "don't text me", "I'm good"],
    "agent.handoff": ["talk to a person", "speak to someone", "can I talk to someone",
                      "I want to talk to a real person", "real person please", "live agent",
                      "representative", "agent", "operator", "human", "talk to a human",
                      "transfer me", "connect me to someone", "let me speak to the owner",
                      "can I speak with someone on the team", "I'd rather talk to a person",
                      "get me a person", "speak with a manager", "is anyone there I can talk to"],
}


def main():
    dump(FLOW_DIR / "Default Start Flow.json", start_flow)
    for p in pages:
        dump(PAGES / f"{p['displayName']}.json", p)
    for name, phrases in INTENTS.items():
        dump(ROOT / "intents" / name / f"{name}.json", {
            "name": uid("intent", name), "displayName": name, "priority": 500000,
            "numTrainingPhrases": len(phrases),
        })
        dump(ROOT / "intents" / name / "trainingPhrases" / "en.json", {"trainingPhrases": [
            {"id": uid("phrase", name, p), "parts": [{"text": p}], "repeatCount": 1, "languageCode": "en"}
            for p in phrases
        ]})
    print(f"Wrote start flow, {len(pages)} pages, {len(INTENTS)} intents.")


if __name__ == "__main__":
    main()
