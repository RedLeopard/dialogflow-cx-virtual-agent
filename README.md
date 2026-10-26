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
