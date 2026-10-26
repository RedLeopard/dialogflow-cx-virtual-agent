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
