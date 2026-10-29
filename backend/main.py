import os
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException
from google.genai.errors import APIError
from httpx import HTTPError
from pydantic import BaseModel, Field, ValidationError

from backend.contact import digits, first_name, is_usable_us_number, spoken_number
from backend.discovery import discover_project, summarize_voicemail
from backend.conversation import generate_turn, history_from
from backend.notify import log, send_email, send_sms

app = FastAPI(title="Cloud Systems Direct - Dialogflow CX Fulfillment")

BOOKING_URL = os.getenv("BOOKING_URL", "https://calendly.com/cloudsystems/30-minute-consultation")
COMPANY = "Cloud Systems Direct"

# Used when discovery fails so the caller still gets a natural next question.
FALLBACK_FOLLOW_UP = "Got it. What kind of timeline are you working with?"
GEMINI_ERRORS = (APIError, HTTPError, RuntimeError, ValidationError, ValueError, KeyError, OSError)


class FulfillmentInfo(BaseModel):
    tag: str


class SessionInfo(BaseModel):
    session: str | None = None
    parameters: dict = Field(default_factory=dict)


class WebhookRequest(BaseModel):
    fulfillmentInfo: FulfillmentInfo
    sessionInfo: SessionInfo


# ------------------------------------------------------------------ helpers
def respond(*messages, handoff: dict | None = None, **parameters):
    body: dict = {"sessionInfo": {"parameters": parameters}}
    out = [{"text": {"text": [m]}} for m in messages if m]
    if handoff is not None:
        out.append({"liveAgentHandoff": {"metadata": handoff}})
    if out:
        body["fulfillmentResponse"] = {"messages": out}
    return body


def text_param(params: dict, key: str) -> str:
    value = params.get(key)
    return value.strip() if isinstance(value, str) else ""


def callback_digits(params: dict) -> str:
    """Confirmed callback number, else the caller ID Twilio passed in."""
    for key in ("callback_number", "caller_number"):
        number = digits(params.get(key))
        if is_usable_us_number(number):
            return number
    return ""


def pretty(number: str) -> str:
    return f"({number[:3]}) {number[3:6]}-{number[6:]}" if len(number) == 10 else (number or "no number")


def ending_in(number: str) -> str:
    return " ".join(number[-4:])


def name_part(params: dict, lead: str = ", ") -> str:
    name = text_param(params, "caller_first_name")
    return f"{lead}{name}" if name else ""


def discovery_summary(params: dict) -> str:
    discovery = params.get("project_discovery")
    if isinstance(discovery, dict) and isinstance(discovery.get("summary"), str):
        return discovery["summary"]
    return ""


def notify_owner(subject: str, sms_body: str, email_body: str) -> bool:
    """Text and email the owner in parallel. True if at least one was accepted."""
    with ThreadPoolExecutor(max_workers=2) as pool:
        sms = pool.submit(send_sms, os.getenv("OWNER_CELL", ""), sms_body)
        email = pool.submit(send_email, os.getenv("OWNER_EMAIL", ""), subject, email_body)
        return bool(sms.result()) | bool(email.result())


def lead_lines(params: dict) -> list[str]:
    name = text_param(params, "caller_first_name") or "Unknown name"
    lines = [f"{name} - {pretty(callback_digits(params))}"]
    if needs := text_param(params, "project_needs"):
        lines.append(f"Needs: {needs}")
    if follow_up := text_param(params, "project_follow_up"):
        lines.append(f"Follow-up: {follow_up}")
    for turn in history_from(params.get("conversation_history")):
        if turn["role"] == "user":
            lines.append(f"Caller: {turn['text']}")
    if summary := discovery_summary(params):
        lines.append(f"Summary: {summary}")
    return lines


def short(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


# ------------------------------------------------------------------ contact intake
def greet_caller(params: dict):
    name = first_name(params.get("caller_name_raw"))
    return respond(f"Hi {name}." if name else "Thanks.", caller_first_name=name or None)


def offer_callback(params: dict):
    number = digits(params.get("caller_number"))
    if not is_usable_us_number(number):
        # No caller ID: the flow asks for a number instead.
        return respond(callback_candidate=None)
    return respond(
        f"Is the number you're calling from, ending in {ending_in(number)}, the best way to reach you?",
        callback_candidate=number,
    )


def confirm_callback(params: dict):
    number = digits(params.get("callback_number_raw"))
    if not number:
        raise HTTPException(status_code=400, detail="callback_number_raw is required")
    return respond(f"That's {spoken_number(number)}, right?", callback_number_raw=number)


# ------------------------------------------------------------------ discovery and booking
CONVERSATION_FALLBACK = "I didn't quite get that. Could you tell me a little more about what you need?"


def conversation_turn(params: dict, utterance: str):
    if not utterance or len(utterance) > 12000:
        raise HTTPException(status_code=400, detail="A customer turn of 1-12000 characters is required")
    history = history_from(params.get("conversation_history"))
    previous = params.get("project_discovery")
    try:
        result = generate_turn(utterance, history,
                               previous if isinstance(previous, dict) else None,
                               text_param(params, "caller_first_name") or None)
    except GEMINI_ERRORS:
        # Retain the caller's words and old verified extraction; never silently
        # turn a model failure into a booking or an invented timeline question.
        log("conversation_failed")
        history += [{"role": "user", "text": utterance},
                    {"role": "assistant", "text": CONVERSATION_FALLBACK}]
        return dict(conversation_history=history_from(history),
                    conversation_reply=CONVERSATION_FALLBACK,
                    conversation_action="continue", discovery_status="failed",
                    project_follow_up=None)

    history.append({"role": "user", "text": utterance})
    if result.reply:
        history.append({"role": "assistant", "text": result.reply})
    return dict(conversation_history=history_from(history),
                conversation_reply=result.reply, conversation_action=result.action,
                discovery_status="complete", project_discovery=result.discovery.model_dump(),
                project_follow_up=None)


def start_conversation(params: dict):
    # On re-entry the router already generated the next response. Speak it once
    # as the form prompt; don't make a second model call for the same turn.
    if history_from(params.get("conversation_history")):
        return respond(text_param(params, "conversation_reply") or CONVERSATION_FALLBACK)
    updates = conversation_turn(params, text_param(params, "project_needs"))
    # A first-turn booking/handoff request is processed by the router, without
    # unnecessarily asking for another answer from the caller.
    return respond(updates["conversation_reply"], **updates)


def continue_conversation(params: dict):
    utterance = text_param(params, "project_follow_up")
    if not utterance:
        return respond()  # router reached from a first-turn booking/handoff
    updates = conversation_turn(params, utterance)
    return respond(**updates)


def discover(params: dict):
    needs = params.get("project_needs")
    if not isinstance(needs, str) or not needs.strip():
        raise HTTPException(status_code=400, detail="project_needs is required")
    if len(needs) > 12000:
        raise HTTPException(status_code=400, detail="project_needs is too long")

    try:
        result = discover_project(needs, text_param(params, "caller_first_name") or None)
    except GEMINI_ERRORS as e:
        log("discovery_failed", detail=str(e))
        return respond(FALLBACK_FOLLOW_UP, discovery_status="failed", project_discovery=None)

    return respond(
        result.follow_up_question,
        discovery_status="complete",
        project_discovery=result.model_dump(),
    )


def finish_discovery(params: dict):
    """Lead is complete: tell the owner right away, then offer the booking text."""
    lines = lead_lines(params)
    log("lead_captured", lead=lines)
    notified = params.get("lead_notified") is True or notify_owner(
        subject=f"New call lead: {lines[0]}",
        sms_body=short("New lead from your AI assistant\n" + "\n".join(lines), 600),
        email_body="New lead from the Cloud Systems Direct phone assistant.\n\n" + "\n\n".join(lines),
    )
    if callback_digits(params):
        offer = "Got it. Want me to text you a link to book a 30-minute consultation with our team?"
    else:
        offer = None
    return respond(offer, lead_notified=notified, booking_offerable=bool(offer))


def send_booking_link(params: dict):
    number = callback_digits(params)
    goodbye = f"Thanks for calling {COMPANY}{name_part(params)}. Talk soon."
    if params.get("booking_sms_sent") is True:
        return respond(f"It's already on its way. {goodbye}")
    if not number:
        return respond(f"I don't have a number to text, but our team will be in touch. {goodbye}")

    name = text_param(params, "caller_first_name")
    body = (
        f"Hi{' ' + name if name else ''}, it's {COMPANY}. Book your 30-minute consultation "
        f"here: {BOOKING_URL}\nReply STOP to opt out."
    )
    if send_sms(number, body):
        return respond(f"Done, it's on its way. {goodbye}", booking_sms_sent=True)
    if params.get("lead_notified") is True:
        return respond(
            f"I couldn't send the text just now, but our team has your details and will reach out soon. {goodbye}",
            booking_sms_sent=False,
        )
    return respond(
        f"I couldn't send the text just now. Please call back shortly and we'll get you scheduled. {goodbye}",
        booking_sms_sent=False,
    )


def decline_booking(params: dict):
    goodbye = f"Thanks for calling {COMPANY}{name_part(params)}."
    number = callback_digits(params)
    if params.get("lead_notified") is True and number:
        return respond(f"No problem. Our team will reach out at the number ending in {ending_in(number)}. {goodbye}")
    return respond(f"No problem. {goodbye}")


# ------------------------------------------------------------------ live transfer and voicemail
def handoff(params: dict):
    """Give the owner a heads-up text, then ask Twilio to transfer the call."""
    lines = lead_lines(params)
    send_sms(os.getenv("OWNER_CELL", ""), short("Transferring a caller to you now\n" + "\n".join(lines), 600))
    log("handoff", lead=lines)
    metadata = {
        "caller_first_name": text_param(params, "caller_first_name"),
        "callback_number": callback_digits(params),
        "project_needs": short(text_param(params, "project_needs"), 300),
    }
    return respond("Sure, connecting you now.", handoff=metadata)


def voicemail_intro(params: dict):
    return respond(
        f"Sorry{name_part(params, ' ')}, nobody could pick up just now. "
        "What message would you like to leave for the team?"
    )


def voicemail_save(params: dict):
    message = text_param(params, "voicemail_message")
    if not message:
        raise HTTPException(status_code=400, detail="voicemail_message is required")
    name = text_param(params, "caller_first_name") or None
    try:
        vm = summarize_voicemail(message, name)
        recap, summary, urgency = vm.spoken_recap, vm.summary, vm.urgency
    except GEMINI_ERRORS as e:
        log("voicemail_summary_failed", detail=str(e))
        recap, summary, urgency = "Got it.", "", "normal"

    number = callback_digits(params)
    who = f"{name or 'Unknown name'} - {pretty(number)}"
    flag = "URGENT " if urgency == "urgent" else ""
    log("voicemail", caller=who, urgency=urgency, summary=summary, message=message)
    delivered = notify_owner(
        subject=f"{flag}Voicemail from {who}",
        sms_body=short(f"{flag}Voicemail from {who}\n{summary or message}", 600),
        email_body=(
            f"Voicemail left with the Cloud Systems Direct phone assistant.\n\n{who}\n"
            f"Urgency: {urgency}\n\nSummary: {summary or '(not available)'}\n\nFull message:\n{message}"
            + (f"\n\nEarlier in the call they said: {params['project_needs']}" if text_param(params, "project_needs") else "")
        ),
    )
    if delivered:
        callback = f", and they'll get back to you at the number ending in {ending_in(number)}" if number else ""
        return respond(f"{recap} I've sent your message to the team{callback}. Thanks for calling {COMPANY}. Goodbye.",
                       voicemail_delivered=True)
    return respond(f"{recap} I'm having trouble delivering messages right now, so please call back a little later. "
                   "Sorry about that.", voicemail_delivered=False)


HANDLERS = {
    "start-conversation": start_conversation,
    "continue-conversation": continue_conversation,
    "greet-caller": greet_caller,
    "offer-callback": offer_callback,
    "confirm-callback": confirm_callback,
    "discover-project": discover,
    "finish-discovery": finish_discovery,
    "send-booking-link": send_booking_link,
    "decline-booking": decline_booking,
    "handoff": handoff,
    "voicemail-intro": voicemail_intro,
    "voicemail-save": voicemail_save,
}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhook")
def webhook(request: WebhookRequest):
    handler = HANDLERS.get(request.fulfillmentInfo.tag)
    if handler is None:
        raise HTTPException(status_code=400, detail="Unsupported fulfillment tag")
    return handler(request.sessionInfo.parameters)
