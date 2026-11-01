# Maya · Dialogflow CX Virtual Agent

A business phone solution for **a working technology firm**, designed and built by Edward Thornton with Dialogflow CX, Gemini on Vertex AI, and FastAPI on Cloud Run. Maya captures caller details, answers service questions, and guides callers toward a consultation, an accepted live transfer, or a message for follow-up.

The business purpose is to turn an incoming inquiry into an actionable next step, preserve context for the person responding, and make follow-up measurable. The repository documents the operating solution, real-call validation, and the next improvements. BigQuery and Power BI are planned additions to close the loop from caller interaction to business insight.

**Checkpoint: November 1, 2026.** The owner confirmed the press-1 transfer now works after correcting the destination number. The published Studio flow routes unaccepted transfers back to Maya for message capture; decline/no-answer checks and end-to-end message delivery remain to be verified.

## Phone flow

<a href="docs/images/cx-phone.jpg?v=20261101-redacted"><img src="docs/images/cx-phone.jpg?v=20261101-redacted" alt="Published Twilio Studio flow showing Maya, screened_transfer, and the Return connection to missed_call_message" width="720"></a>

*Published Studio flow: incoming call → Maya → screened transfer. The owner answers and presses 1 before connection; the Return path leads to Maya’s message-taking session. The older transfer/status widgets remain visible but are outside the active handoff route. The owner’s phone number is masked as `xxx-xxxx`. Click to enlarge.*

## Current status

| Area | Status |
| --- | --- |
| Phone intake | Branded greeting, caller name, and callback confirmation exercised on calls. |
| Conversation | Contextual discovery, corrections, and service answers implemented and evaluated. |
| Booking and alerts | Booking-link and owner-alert texts received. Customers schedule in Calendly. |
| Live transfer | Owner confirmed the press-1 transfer works after correcting the destination number. |
| Missed-call messages | Studio Return is connected to Maya; unanswered return was previously observed. Decline/no-answer screening checks and full message delivery remain unverified. |
| Analytics | BigQuery event storage and Power BI reporting are planned; no analytics pipeline or dashboard is implemented yet. |

## Architecture

```mermaid
flowchart LR
    accTitle: Maya architecture overview
    accDescr: Twilio connects calls to Maya. The backend uses Gemini and sends booking links. Twilio also transfers calls to the owner.

    phone("`**Phone calls**
Twilio Voice + Studio`")
    maya("`**Maya**
Dialogflow CX`")
    backend("`**Backend**
FastAPI on Cloud Run`")
    ai("`**AI answers**
Gemini on Vertex AI`")
    booking("`**Booking texts**
Twilio + Calendly`")
    owner("`**Live transfer**
Owner's phone`")

    phone --> maya --> backend
    backend <--> ai
    backend --> booking
    screen("`**Call screening**
Twilio Function`")

    maya -->|Live handoff| screen
    screen -->|Press 1| owner
    screen -->|Unaccepted: take message| maya

    classDef core fill:#eff6ff,stroke:#93c5fd,color:#172554,stroke-width:1.5px
    classDef intelligence fill:#f5f3ff,stroke:#c4b5fd,color:#3b1d64,stroke-width:1.5px
    classDef outcome fill:#ecfdf5,stroke:#86efac,color:#14532d,stroke-width:1.5px
    class phone,maya,backend,screen core
    class ai intelligence
    class booking,owner outcome
```

Twilio connects calls to Maya. The backend supports AI answers and booking texts. Studio invokes a protected Twilio Function for press-1 screening and resumes the message-taking widget when the function returns an unaccepted transfer.

| Component | Responsibility |
| --- | --- |
| Twilio Voice + Studio + Functions | Connect calls to Dialogflow, screen live handoffs with press-1 acceptance, and return unaccepted transfers to Maya. |
| Dialogflow CX | Manage intents, contact intake, conversation state, and action routes. |
| FastAPI on Cloud Run | Authenticate fulfillment requests and coordinate discovery and customer actions. |
| Gemini on Vertex AI | Use recent conversation context for extraction, answers, corrections, and summaries. |
| Twilio Messaging + Calendly | Send permission-based booking links and owner alerts; customers choose a meeting time externally. |

Security, design decisions, and failure handling are covered in the [architecture notes](docs/architecture.md).

## Security and secret management

The documented Cloud Run deployment stores the **Twilio Auth Token in Google Cloud Secret Manager**, under `twilio-auth-token`, and references it through the secret-backed `TWILIO_AUTH_TOKEN` environment variable. [`backend/notify.py`](backend/notify.py) reads that value at runtime to authenticate outgoing Twilio messaging requests; the token value is not hard-coded in the source. The setup grants the backend service identity Secret Accessor on that secret.

- Dialogflow’s exported webhook configuration uses service-agent **ID tokens** to invoke Cloud Run. Backend authentication relies on Cloud Run IAM, rather than an application-level shared password.
- The `/maya-transfer` Function is configured as **Protected**, using Twilio’s request-signature validation before the handler runs.
- Local `.env` files and common credential/key files are excluded from source control and build uploads by the ignore files. Those guards do not remove previously committed content.
- An owner-requested review of both branches and all 29 reachable commits found **no confirmed authentication credentials**. One repeated Dialogflow configuration UUID was flagged by the scanner and remains a metadata-classification review item. Anonymous Cloud Run health and unsigned, non-dialing Function checks each returned HTTP 403.

These observations are bounded evidence, not a guarantee of complete security. Current secret versions, rotation, and exact live IAM grants were not inspected. The [security review and verification notes](docs/security.md) explain the scope, findings, caller-data considerations, and remaining checks. Email secret setup is documented separately; successful email delivery is still unverified.

## Development timeline

| Date | Milestone |
| --- | --- |
| Oct 25, 2026 | Built consultation intake, required form capture, a welcome response, and the external booking-link ending. |
| Oct 26 | Added FastAPI, structured Gemini discovery, Docker packaging, and local service checks. |
| Oct 27 | Deployed authenticated Cloud Run fulfillment and connected the Dialogflow agent to Twilio voice. |
| Oct 28 | Added caller contact intake, shorter prompts, booking texts, lead alerts, and message/handoff handlers. |
| Oct 29 | Added conversation history, correction handling, reviewed policy answers, and model evaluation. Approved Maya’s new greeting. |
| Oct 30 | Confirmed a working cell transfer and added the transfer-status split in Studio. |
| Oct 31–Nov 1 | Added protected call screening, published the Return route to Maya, corrected the owner destination, and confirmed the press-1 transfer works. |

## Validation

- **54 offline tests** passed at the last full run, with model responses and notifications mocked.
- **13 real Vertex requests** completed with zero errors and **1.20–5.32 seconds per generation** in one evaluation. Follow-up fixes constrained unsupported policy answers; these timings do not measure full calls.
- **Phone checks:** owner-confirmed press-1 transfer, previously observed unanswered return to Maya, and received booking/handoff texts. The new screening route still needs decline/no-answer checks and a complete message-delivery test.

Run the offline checks from the repository root:

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q
```

The real-model evaluator is `scripts/evaluate_conversation.py`. Deployment context and operational instructions are in the [current checkpoint](docs/project-notes.md).

## Repository guide

- [`backend/`](backend/) — FastAPI fulfillment, conversational discovery, contact handling, and notifications.
- [`dialogflow/agent/`](dialogflow/agent/) — versioned Dialogflow configuration.
- [`scripts/`](scripts/) and [`tests/`](tests/) — build/apply helpers, model evaluation, and offline checks.
- [`twilio/functions/maya-transfer.js`](twilio/functions/maya-transfer.js) — deployed screening function source; [setup and validation](docs/project-notes.md#screened-transfer-setup).
- [Portfolio page source](docs/dialogflow-cx.html) · [Current checkpoint](docs/project-notes.md) · [Detailed build history](docs/build-history.md) · [Security review](docs/security.md).

## Next milestones

1. Verify ignored, declined, and failed calls through the screened transfer, then check message context and delivery.
2. **Add BigQuery for structured call and outcome history.** Define call/event IDs, timestamps, requested service, transfer attempts and results, message outcomes, SMS consent, and notification status. Capture accepted transfers from actual telephony results, rather than treating a handoff request as a successful connection. Deduplicate webhook retries.
3. **Add Power BI for business reporting.** Build SQL views over the BigQuery events and use Import mode with scheduled refreshes for call volume, accepted-transfer rate, message outcomes, service demand, and follow-up needs. Keep personally identifying details out of the reporting views where they are unnecessary.
4. **Connect activity to outcomes.** Use the reports to identify missed opportunities, improve handoff and message reliability, and prioritize follow-up. Record confirmed appointments only after a Calendly confirmation integration; sending a booking link alone is not a completed booking.
5. Export the tested Studio JSON flow, verify email alerts, and continue real-call evaluation of recognition, corrections, interruptions, and the selected voice.
6. Verify current secret mappings, per-secret IAM access, rotation, and caller-data retention. Resolve the configuration-key scanner finding before adding a narrow scanner exception or an enforced CI scanning workflow.

**End-to-end goal:** capture an inquiry → understand the need → route the caller → preserve the outcome → measure what needs attention → improve the business response. BigQuery is the planned analytical history, and Power BI is the planned reporting layer. Neither is required to answer a call, and analytics collection should not delay the live conversation.

Message transcripts currently use Cloud Logging. Audio recording and in-call appointment creation are not implemented.

