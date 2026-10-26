# CSD Dialogflow CX

A conversational customer experience project for Cloud Systems Direct, built with Google Cloud Dialogflow CX.

## Purpose

Develop a virtual assistant that helps customers explore cloud services, request consultations, and get technical support.

The project will document the integration of an existing Twilio phone system with Dialogflow CX, with planned Vertex AI capabilities for answers grounded in company information.

## Current Status

- Created a dedicated Google Cloud project.
- Enabled the Dialogflow and Vertex AI APIs.
- Created a Dialogflow CX agent in us-central1.
- Configured English, America/Chicago time zone, and Cloud Logging.
- Conversation design and Twilio integration are in development.

## Planned Capabilities

- Cloud service inquiries
- Consultation qualification and lead capture
- Technical support intake and routing
- Company knowledge integration
- Voice access through an existing Twilio number

## Repository Structure

- docs/: Architecture, conversation design, and implementation decisions
- agent/: Dialogflow CX agent exports
- backend/: Backend integration code
- scripts/: Setup and deployment scripts

## Technology

- Google Cloud Dialogflow CX
- Twilio Programmable Voice
- Vertex AI (planned)
- Cloud Run (planned)

## Security

Credentials, access tokens, service account keys, and customer data must not be committed to this repository.
