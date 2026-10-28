# Dialogflow CX Virtual Agent

A conversational customer experience project built with Google Cloud Dialogflow CX and configured through REST API calls authenticated with the Google Cloud CLI.

## Milestone 1: Consultation Intake

Implemented and manually tested a two-turn consultation workflow:

1. The user requests a consultation.
2. The agent recognizes the consultation.request intent.
3. The agent asks what the user needs help with.
4. A required form parameter captures the answer as project_needs.
5. The agent provides an external Calendly booking link.
6. The conversation transitions to END_SESSION.

A custom welcome response is also implemented and tested.

## Example Conversation

User: I would like to schedule a consultation.

Agent: I can help you get started with a consultation. What would you like help with?

User: I need help migrating my website to Google Cloud.

Agent: Thank you for sharing your project needs. You can choose an available time for a 30-minute consultation using the provided booking link.

## Implementation

- Dialogflow CX flows, intents, pages, and form parameters
- Six training phrases for the consultation request intent
- @sys.any system entity for free-text project needs
- Conditional routing after required form completion
- REST API configuration using curl
- Google Cloud CLI authentication
- Cloud Logging enabled
- Agent deployed in us-central1

## Validation

Manual API tests confirmed:

- The welcome intent returns the configured greeting.
- A consultation request transitions to the Consultation Request page.
- The agent prompts for project_needs.
- The next user response fills the required parameter.
- The agent returns the booking link and reaches END_SESSION.

## Current Limitations

- Project needs are captured in the conversation session; no CRM or database integration is implemented.
- The booking link directs users to Calendly; the agent does not create appointments.
- Twilio voice and SMS integration are not implemented.
- Vertex AI features are not implemented.
- Service inquiry and technical support routes are not implemented.

## Roadmap

- Export and sanitize agent configuration for reproducible setup
- Add reusable configuration and test scripts
- Integrate Twilio voice
- Add an option to deliver the booking link through SMS
- Persist consultation requests through a backend
- Add company knowledge and generative AI capabilities
- Expand fallback handling and conversation testing

## Security

Do not commit credentials, access tokens, service account keys, or customer data.

## Expanded Scope and Planned Architecture

The next phase extends the tested consultation intake into a conversational assistant with natural project discovery, SMS booking links, and customer message capture.

The existing consultation workflow remains the completed first milestone. The capabilities below are planned and have not yet been implemented.

### Architecture

| Component | Planned responsibility |
|---|---|
| Dialogflow CX | Manage conversation state, route requests, collect details, and confirm customer choices |
| Gemini on Vertex AI | Interpret project needs, generate relevant follow-up questions, extract structured details, and summarize requests |
| Python backend on Cloud Run | Handle Dialogflow webhooks, validate information, and coordinate storage and messaging |
| Firestore | Persist consultation requests, confirmed customer messages, and action status |
| Twilio | Provide telephone access through a voice integration and send booking links through its Messaging API |
| Calendly | Let customers select an available consultation time and complete their booking |
| Approved knowledge sources | Ground service answers in reviewed documentation |

### Consultation Booking by SMS

The agent will collect project needs, offer to text the booking link, and confirm the customer's mobile number and permission before triggering the backend.

The backend will save the request and submit the booking link through Twilio. The agent will distinguish SMS submission from confirmed delivery and explain failures accurately.

Customers will complete scheduling in Calendly. Direct appointment creation during the conversation remains a possible future enhancement.

The existing clickable booking link will remain available for chat users.

### Customer Message Capture

Customers will be able to leave their name, callback number, and message.

The agent will read back the captured details, accept corrections, and request confirmation before saving. The backend will preserve the original captured text alongside a separate AI-generated summary.

The initial scope is text capture, including transcribed speech when voice is connected. Audio voicemail recording is a separate future capability.

### Vertex AI Capabilities

Gemini on Vertex AI will support:

- Extracting project type, current platform, problem, and timeline from natural language
- Asking useful follow-up questions without repeating details already provided
- Summarizing consultation requests and customer messages
- Answering service questions using approved knowledge through retrieval and grounding
- Acknowledging missing information instead of inventing details

Dialogflow CX and backend validation will control actions. Generated responses will not serve as proof that a text was delivered, a message was saved, or an appointment was booked.

### Implementation Priorities

1. Preserve and export the tested consultation milestone.
2. Build the Cloud Run webhook backend.
3. Integrate Gemini on Vertex AI for project discovery.
4. Add mobile-number confirmation and SMS permission.
5. Save requests in Firestore and send booking links through Twilio.
6. Add confirmed customer message capture.
7. Connect and test the Twilio voice integration.
8. Add grounded service answers from approved documentation.

### Quality and Reliability Goals

Test realistic conversations, including corrections, interruptions, unclear requests, declined SMS permission, and backend failures.

Measure task completion, extraction accuracy, grounded-answer quality, response time, and cost per conversation. Protect customer information, authenticate backend requests, secure API credentials, and prevent duplicate actions when requests are retried.

## Progress Update: October 27, 2026

This update records the latest tested milestone. Earlier milestone descriptions and planning sections above are retained as project history; Vertex AI discovery and the Cloud Run backend are now implemented as described below.

### Milestone 2: Authenticated Project Discovery

Built and deployed a Python fulfillment backend, connected it to Dialogflow CX, and manually tested the complete consultation conversation through the detectIntent API.

Completed backend and deployment work:

- Added structured project extraction and follow-up question generation in `backend/discovery.py` using Gemini `gemini-3.5-flash` through Vertex AI's global endpoint.
- Added FastAPI `/health` and `/webhook` endpoints in `backend/main.py`, with input validation and discovery failure responses.
- Pinned tested dependencies in `requirements.txt`.
- Added a Python 3.14 Dockerfile that runs the backend as a non-root user.
- Added Docker and Google Cloud source-upload exclusions.
- Built the container locally and verified its health endpoint.
- Deployed the backend to Cloud Run in `us-central1`, with authentication required, a dedicated runtime service account, and scaling configured from zero to two instances.
- Granted the runtime service account Vertex AI access and the Dialogflow service agent permission to invoke the Cloud Run service.
- Registered the Project Discovery Backend webhook with service-agent ID-token authentication and a 30-second timeout.

### Tested Conversation

1. The customer requests a consultation.
2. The Consultation Request page captures `project_needs`.
3. The conversation transitions to the new Project Follow-up page.
4. Its form prompt invokes the backend using the `discover-project` fulfillment tag.
5. Gemini extracts project type, current and target platforms, customer problem, timeline, requirements, and a summary, then asks one relevant follow-up question.
6. Dialogflow captures the answer as `project_follow_up`.
7. The agent provides the Calendly booking link and transitions to `END_SESSION`.

A manual migration scenario confirmed AWS-to-Google-Cloud extraction, website instability, a relative timeline, and the customer's no-downtime requirement. The Dialogflow webhook returned HTTP 200 in approximately 4.4 seconds. The next turn captured WordPress, EC2, and MySQL details in `project_follow_up`, returned the booking link, and ended the session.

### Current Boundaries

- The follow-up answer is stored separately in session parameters; it is not yet incorporated into the generated discovery summary.
- `discovery_status: complete` indicates successful initial extraction, not a completed booking or exhaustive discovery.
- Intake details are held in conversation session parameters; database persistence is not implemented.
- Calendly handles scheduling externally. The agent does not create appointments.
- The backend has discovery failure responses, but dedicated conversation failure, retry, and correction handling still needs implementation and testing.
- Firestore, Twilio voice, SMS delivery, confirmed customer message capture, and grounded service answers remain planned.
- The updated Dialogflow configuration still needs to be exported and committed for reproducibility.

### Expanded Service Scope and Next Work

The planned intake scope now includes cloud consulting and migrations, marketing requests such as social media, advertising, SEO, and email marketing, website development and redesign, and app development. Dedicated routing and category-specific discovery for the additional services have not yet been implemented or tested.

Next priorities:

1. Export and version the updated Dialogflow pages and webhook configuration.
2. Expand discovery fields, prompts, and routing for marketing, website, and app requests.
3. Incorporate follow-up answers into structured details and summaries, with correction and failure handling.
4. Add confirmed customer details and Firestore persistence.
5. Add mobile-number confirmation and explicit SMS permission before sending booking links through Twilio.
6. Add confirmed customer message capture, Twilio voice, and grounded answers from approved service information.

Public-facing branding will remain independent of Cloud Systems Direct.

## Progress Update: October 27, 2026 - Twilio Voice and Contact Intake

This checkpoint supersedes earlier voice-integration status and branding plans. The phone experience will identify the company as **Cloud Systems Direct**, as requested during live-call review. Earlier sections remain as project history.

### Completed Configuration

- Exported and reviewed the current Dialogflow JSON package, then committed it under `dialogflow/agent/` in commit `fd28aa5`.
- Added `.gcloudignore` and excluded local `backups/` from Git and Cloud Run source uploads.
- Enabled the Cloud Resource Manager API and granted Twilio's documented production service account the Dialogflow API Reader and Dialogflow API Client roles in the CX project.
- Created Default Start Flow version `1`, named `consultation-v1`, and deployed it to the `production` environment.
- Created the native Twilio connector `cx-phone`, using English, the default bot voice, and sentiment analysis enabled. No status callback URL is configured, and no sentiment-based routing or response logic exists.
- Changed the existing Twilio number's incoming voice routing from its forwarding Function to the generated `cx-phone` Studio Flow. The existing forwarding Functions remain available for rollback. Messaging configuration was left unchanged.

### First Call Findings and Welcome Fix

The first call reached Studio and the connector but disconnected with Twilio error `32601`. Dialogflow reported that no handler existed for the event `Default Welcome Intent`. The connector field had been set to the intent's display name, which Twilio sent as an event; an intent route alone did not handle that event.

Added a matching `Default Welcome Intent` event handler to the Draft start flow using a targeted REST PATCH, preserving the existing routes and fallback handlers. The PATCH response confirmed the new handler.

**Deployment boundary:** creation of `consultation-v2` and promotion of the welcome fix to `production` have not been confirmed. A later call was reported to have an unsatisfactory voice and greeting, but its exact deployed version and complete conversation outcome were not verified. Do not treat voice acceptance testing as passed.

The exported configuration at `fd28aa5` predates the welcome event patch. Re-export and commit the updated configuration after the next verified deployment.

### Agreed Next Experience: Company Greeting and Contact Intake

Before project discovery, the phone conversation should:

1. Identify Cloud Systems Direct and introduce the virtual assistant.
2. Ask for the caller's name.
3. Use the incoming caller number from Twilio when available, after explicitly passing it into Dialogflow session parameters and verifying the mapping.
4. Ask whether the calling number is the best callback number.
5. If it is not, or caller ID is unavailable, collect an alternative and read it back for confirmation.
6. Ask what the caller needs and continue into project discovery.

Proposed opening:

> Thanks for calling Cloud Systems Direct. I'm your virtual assistant. Before we get started, may I have your name?

Then confirm the preferred callback number and ask:

> What can we help you with today?

Name capture, caller-number mapping, callback confirmation, and the improved greeting are **planned, not implemented**. Caller ID is a callback candidate, not verified identity. Callback confirmation is separate from explicit SMS permission.

### Next Implementation and Verification

1. Inspect the current Draft and production versions to resolve the welcome-fix deployment state.
2. Select and audition a more natural supported voice; the default voice has not met the caller-experience requirement.
3. Implement the company greeting and contact-intake pages, including corrections, unavailable caller ID, and alternative callback numbers.
4. Publish the intended flow version to `production`, then test the actual phone path through greeting, contact confirmation, discovery, follow-up, and ending.
5. Re-export the deployed configuration and update the checkpoint notes.
6. Incorporate follow-up answers into structured discovery and summaries, expand service categories, and improve failure/retry handling.
7. Add confirmed Firestore persistence, then explicit SMS permission and booking-link delivery.

Firestore, SMS sending, confirmed customer message capture, and grounded service answers remain unimplemented. The console displayed an A2P 10DLC registration requirement for US messaging; verify registration readiness before implementing US SMS delivery. The agent must not claim that details were saved, a text delivered, or an appointment booked without a confirmed backend result.

Detailed resume checkpoint: [Project notes](docs/project-notes.md).

## Progress Update: October 28, 2026 - Caller Experience v2 (built, not yet deployed)

Implements the agreed company greeting and contact intake, and reworks the copy so the agent sounds like Cloud Systems Direct instead of a generic bot. Committed on branch `caller-experience-v2`. Nothing below has been deployed or phone-tested yet.

### New conversation

> **Agent:** Thanks for calling Cloud Systems Direct, where we help businesses with cloud, websites, apps, and digital marketing. I'm the virtual assistant. Who am I speaking with today?
> **Caller:** Hi, this is Maria.
> **Agent:** Great to meet you, Maria. If we get disconnected or need to follow up, is the number you're calling from, 3 1 4, 5 5 5, 0 1 2 3, the best one to reach you?
> **Caller:** Yeah.
> **Agent:** Perfect. So, what can we help you with today? Whether it's a cloud project, a new website or app, or growing your marketing, just tell me in your own words.
> **Caller:** Our WordPress site on AWS keeps going down and we want to move to Google Cloud without downtime.
> **Agent (Gemini):** *A short, specific acknowledgment plus one scoping question, for example:* That sounds frustrating, Maria, and a zero-downtime move is very doable to plan for. Roughly when would you like to be fully on Google Cloud?
> **Caller:** Within the next two months.
> **Agent:** Thank you, that gives our team a great head start. The next step is a 30-minute consultation with a Cloud Systems Direct specialist, and you can pick a time that works for you at calendly dot com slash cloud systems. Thanks for calling Cloud Systems Direct. Have a great day.

If caller ID is missing or the caller says no, the agent asks for the best number, reads it back digit by digit, and accepts corrections.

### Changes

- **Start flow:** branded greeting (separate chat text and spoken versions), `Default Welcome Intent` event handler for the Twilio connector (matches the Oct 27 Draft fix), consultation requests also routed through contact intake, and natural no-match / no-input responses replacing the 12 terse defaults.
- **New pages:** `Caller Name`, `Callback Number`, `Alternate Number`, `Confirm Callback`.
- **New intents:** `confirm.yes`, `confirm.no`.
- **Consultation Request:** asks "what can we help you with" across all four service lines.
- **Project Follow-up:** chat still gets the clickable Calendly link; phone gets a spoken close via `outputAudioText` instead of the full URL read aloud.
- **Backend:** new fast, model-free tags `greet-caller`, `offer-callback`, `confirm-callback` (`backend/contact.py`); discovery prompt now speaks as Cloud Systems Direct, covers cloud, web, app and marketing work, uses the caller's first name, and is written for a voice; Gemini failures now continue with a natural timeline question instead of a dead-end "try again?".
- **Speed:** the Gemini client is created once per container instead of on every request, Gemini calls time out after 8 seconds, and the Dialogflow webhook timeout dropped from 30 to 10 seconds, so a stall falls back to the natural question instead of long silence.
- **Tests:** `tests/test_webhook.py` (name cleanup, number readback, discovery and failure paths, and a check that every page, intent and webhook tag referenced in the flow exists). Run with `pip install -r requirements.txt -r requirements-dev.txt && python -m pytest -q`.

### Rollout steps

1. Run the tests with the pinned dependencies, then redeploy `cx-backend` to Cloud Run as before.
2. Export a backup of the live agent, then apply this package to Draft (console *Restore* from a zip of `dialogflow/agent/`, or create the pages and intents through the REST API).
3. In the Twilio Studio Flow's Connect Virtual Agent widget, pass the caller's number as a parameter: `caller_number` = `{{trigger.call.From}}`. Twilio exposes `<Parameter>` values to Dialogflow as `$session.params.<name>`. Verify the value in a test call before relying on it.
4. Audition a more natural voice with the connector's voice setting or a `voiceName` config on the widget, and pick the one that sounds best on a real phone.
5. Publish a new flow version to `production` and call the number: test the happy path, a declined callback number, a wrong readback, no caller ID, silence, and a Gemini failure.
6. Confirm the phone close is spoken without the URL. If the full link is still read out, switch to channel-specific responses.
7. Re-export the deployed agent and commit it.

### Still not implemented

Firestore persistence, SMS booking links, confirmed message capture, and grounded service answers remain planned. The agent still does not claim details were saved or an appointment was booked.
