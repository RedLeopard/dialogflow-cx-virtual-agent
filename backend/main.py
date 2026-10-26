from fastapi import FastAPI, HTTPException
from google.genai.errors import APIError
from pydantic import BaseModel, Field, ValidationError

from backend.discovery import discover_project

app = FastAPI(title="Dialogflow CX Fulfillment")


class FulfillmentInfo(BaseModel):
    tag: str


class SessionInfo(BaseModel):
    parameters: dict = Field(default_factory=dict)


class WebhookRequest(BaseModel):
    fulfillmentInfo: FulfillmentInfo
    sessionInfo: SessionInfo


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhook")
def webhook(request: WebhookRequest):
    if request.fulfillmentInfo.tag != "discover-project":
        raise HTTPException(status_code=400, detail="Unsupported fulfillment tag")

    needs = request.sessionInfo.parameters.get("project_needs")
    if not isinstance(needs, str) or not needs.strip():
        raise HTTPException(status_code=400, detail="project_needs is required")
    if len(needs) > 12000:
        raise HTTPException(status_code=400, detail="project_needs is too long")

    try:
        result = discover_project(needs)
    except (APIError, RuntimeError, ValidationError):
        return {
            "fulfillmentResponse": {
                "messages": [{
                    "text": {"text": [
                        "I could not analyze those details right now. "
                        "Would you like to try again?"
                    ]}
                }]
            },
            "sessionInfo": {
                "parameters": {
                    "discovery_status": "failed",
                    "project_discovery": None
                }
            }
        }

    return {
        "fulfillmentResponse": {
            "messages": [{
                "text": {"text": [result.follow_up_question]}
            }]
        },
        "sessionInfo": {
            "parameters": {
                "discovery_status": "complete",
                "project_discovery": result.model_dump()
            }
        }
    }
