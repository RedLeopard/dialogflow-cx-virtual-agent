from fastapi import FastAPI, HTTPException
from google.genai.errors import APIError
from pydantic import BaseModel, Field, ValidationError

from backend.contact import digits, first_name, is_usable_us_number, spoken_number
from backend.discovery import discover_project

app = FastAPI(title="Cloud Systems Direct - Dialogflow CX Fulfillment")

# Used when discovery fails so the caller still gets a natural next question
# instead of a dead end.
FALLBACK_FOLLOW_UP = (
    "Thanks, that's really helpful. One more quick question: "
    "what kind of timeline are you working with?"
)


class FulfillmentInfo(BaseModel):
    tag: str


class SessionInfo(BaseModel):
    parameters: dict = Field(default_factory=dict)


class WebhookRequest(BaseModel):
    fulfillmentInfo: FulfillmentInfo
    sessionInfo: SessionInfo


def respond(message: str | None = None, **parameters):
    body: dict = {"sessionInfo": {"parameters": parameters}}
    if message:
        body["fulfillmentResponse"] = {"messages": [{"text": {"text": [message]}}]}
    return body


@app.get("/health")
def health():
    return {"status": "ok"}


def greet_caller(params: dict):
    name = first_name(params.get("caller_name_raw"))
    message = f"Great to meet you, {name}." if name else "Great to meet you."
    return respond(message, caller_first_name=name or None)


def offer_callback(params: dict):
    number = digits(params.get("caller_number"))
    if not is_usable_us_number(number):
        # No caller ID (or not a US number): the flow asks for one instead.
        return respond(callback_candidate=None)
    return respond(
        "If we get disconnected or need to follow up, is the number you're calling "
        f"from, {spoken_number(number)}, the best one to reach you?",
        callback_candidate=number,
    )


def confirm_callback(params: dict):
    number = digits(params.get("callback_number_raw"))
    if not number:
        raise HTTPException(status_code=400, detail="callback_number_raw is required")
    return respond(
        f"Thanks. Just to confirm, that's {spoken_number(number)}. Did I get that right?",
        callback_number_raw=number,
    )


def discover(params: dict):
    needs = params.get("project_needs")
    if not isinstance(needs, str) or not needs.strip():
        raise HTTPException(status_code=400, detail="project_needs is required")
    if len(needs) > 12000:
        raise HTTPException(status_code=400, detail="project_needs is too long")

    caller = params.get("caller_first_name")
    try:
        result = discover_project(needs, caller if isinstance(caller, str) else None)
    except (APIError, RuntimeError, ValidationError):
        return respond(FALLBACK_FOLLOW_UP, discovery_status="failed", project_discovery=None)

    return respond(
        result.follow_up_question,
        discovery_status="complete",
        project_discovery=result.model_dump(),
    )


HANDLERS = {
    "greet-caller": greet_caller,
    "offer-callback": offer_callback,
    "confirm-callback": confirm_callback,
    "discover-project": discover,
}


@app.post("/webhook")
def webhook(request: WebhookRequest):
    handler = HANDLERS.get(request.fulfillmentInfo.tag)
    if handler is None:
        raise HTTPException(status_code=400, detail="Unsupported fulfillment tag")
    return handler(request.sessionInfo.parameters)
