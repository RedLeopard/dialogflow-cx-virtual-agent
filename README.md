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
