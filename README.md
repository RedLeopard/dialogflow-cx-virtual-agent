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

## Progress Update: October 28, 2026 - Caller Experience v2 (deployed; see live status below)

Implements the agreed company greeting and contact intake, and reworks the copy so the agent sounds like Cloud Systems Direct instead of a generic bot. Committed on branch `caller-experience-v2`. Deployment status is recorded in the next section.

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

## Progress Update: October 28, 2026 (evening) - v2 Live on the Phone Line

This section records what is actually deployed. It supersedes the deployment status above.

### Live now

| Component | State |
|---|---|
| Dialogflow `production` environment | Flow **version 3** (`caller-experience-20261028-1933`) |
| Previous production version | Version 2 (`consultation-v2`, welcome-event fix). Version 1 is the original consultation flow. |
| Cloud Run `cx-backend` | Revision `cx-backend-00002-swq`, deployed with `--cpu-boost` and `--min-instances 1` |
| Code | Branch `caller-experience-v2` (not yet merged to `main`) |

Earlier the same evening, production was found still running version 1 even though version 2 had been created; it was switched to version 2 before v3 was published.

### How it was deployed

1. `gcloud run deploy cx-backend --source . --region us-central1 --project csd-dialogflow-cx-2026 --cpu-boost --min-instances 1`
2. `python3 scripts/apply_agent.py --dry-run`, then `python3 scripts/apply_agent.py --publish`.
   The script updates the Draft agent from `dialogflow/agent/` by display name (intents, webhook timeout, pages, start flow), creates a new flow version, and points `production` at it. It leaves the Twilio connector and older versions untouched.

**Rollback:** point `production` back at version 2:

```bash
curl -s -X PATCH -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "x-goog-user-project: csd-dialogflow-cx-2026" -H "Content-Type: application/json" \
  "https://us-central1-dialogflow.googleapis.com/v3/projects/csd-dialogflow-cx-2026/locations/us-central1/agents/616e7277-d596-4d4d-9053-6df11765881d/environments/e7b9ee85-0c39-476b-8764-ac9faf9c3b6f?updateMask=versionConfigs" \
  -d '{"versionConfigs":[{"version":"projects/csd-dialogflow-cx-2026/locations/us-central1/agents/616e7277-d596-4d4d-9053-6df11765881d/flows/00000000-0000-0000-0000-000000000000/versions/2"}]}'
```

### Mac setup notes

- gcloud's default project on the Mac is `ancestoriq`. Set `PROJECT_ID=csd-dialogflow-cx-2026` (or pass `--project`) for every command in this repo.
- The python.org build of Python 3.14 needed `Install Certificates.command` before `apply_agent.py` could reach Google APIs.

### First phone test of v3

Confirmed: company greeting, name capture, callback-number capture with read-back, Gemini follow-up, no URL read aloud.

Owner feedback: **not premium yet.**

- The default voice is not acceptable.
- Too much talking, not enough action. Prompts and Gemini replies need to be shorter.
- The agent never offered to text the booking link, and no link was sent. (SMS sending is not implemented.)
- The callback number and caller details are **not sent or stored anywhere** yet. They exist only in the Dialogflow session and are lost when the call ends.
- Caller ID is not passed from Twilio yet, so the agent always asks for the number.

### Next work, in order

1. **Lead delivery:** after every call, send the owner the caller's name, callback number, request, and Gemini summary, and store the record (Firestore).
2. **Text the booking link:** ask permission, send through Twilio Messaging from the backend, and confirm only on a successful Twilio response. Requires A2P 10DLC registration for US delivery.
3. **Shorter, more action-oriented conversation:** trim the greeting, the needs prompt, the Gemini acknowledgment, and the close.
4. **Voice:** audition and set a more natural Google voice on the Twilio connector or Studio widget.
5. **Caller ID:** pass `caller_number = {{trigger.call.From}}` from the Studio Connect Virtual Agent widget so the agent can offer the calling number instead of asking.
6. **Missed-call handling:** ring the owner first, then hand to the agent to take a message.
7. Merge `caller-experience-v2` into `main` and re-export the live agent after verification.

## Progress Update: October 28, 2026 (night) - Premium Call Flow v4 (built, not yet deployed)

Built in response to the first v3 phone test ("too much talking, no link sent, number goes nowhere"). Code is on branch `caller-experience-v2`; deployment steps are below. Until they are run, production stays on version 3.

### What the caller gets

> **Agent:** Thanks for calling Cloud Systems Direct, your cloud, web, and marketing team. I'm the virtual assistant. Who am I speaking with?
> **Caller:** Maria.
> **Agent:** Hi Maria. Is the number you're calling from, ending in 0 1 2 3, the best way to reach you?
> **Caller:** Yes.
> **Agent:** What can we help you with today?
> **Caller:** Our WordPress site on AWS keeps crashing and we want to move to Google Cloud.
> **Agent (Gemini, one sentence):** Got it, a move off AWS. When do you need it done?
> **Caller:** Within two months.
> **Agent:** Got it. Want me to text you a link to book a 30-minute consultation with our team?
> **Caller:** Yes.
> **Agent:** Done, it's on its way. Thanks for calling Cloud Systems Direct, Maria. Talk soon.

At the same moment, the owner gets a text and an email with the lead: name, callback number, request, follow-up answer, and Gemini summary.

**Live transfer:** at any point the caller can say "talk to a person". The owner gets a heads-up text with who is calling and why, and Twilio rings the owner's cell.

**Smart voicemail:** if the owner does not answer, the assistant comes back: "Sorry Maria, nobody could pick up just now. What message would you like to leave for the team?" Gemini recaps it back in one line ("Got it, you need a quote before Friday."), flags urgency, and the owner gets the transcript plus summary by text and email. The assistant says the message was sent only if Twilio or the mail server accepted it.

### Changes

- `backend/notify.py`: Twilio Messaging (REST, standard library) and SMTP email. Never raises; logs one JSON line per event (`lead_captured`, `sms_accepted`, `sms_failed`, `voicemail`, `handoff`, ...), so Cloud Logging also keeps a record of every lead and voicemail.
- `backend/main.py`: new tags `finish-discovery`, `send-booking-link`, `decline-booking`, `handoff`, `voicemail-intro`, `voicemail-save`; shorter copy everywhere; reads only the last four digits of caller ID aloud; no duplicate texts on retry (`booking_sms_sent`, `lead_notified`).
- `backend/discovery.py`: Gemini follow-ups capped at one sentence (25 words); new `summarize_voicemail`.
- `scripts/build_agent.py`: generates all flow, page, and intent JSON (edit the conversation here, then rerun). New pages `Start Router`, `Booking Offer`, `Live Transfer`, `Voicemail`; new intent `agent.handoff`.
- `scripts/apply_agent.py`: now manages the new pages and intent.
- Tests: 31 passing, including "no URL is ever spoken" and "voicemail never claims delivery when both channels fail".

### Configuration (Cloud Run environment)

| Variable | Value | Secret? |
|---|---|---|
| `TWILIO_ACCOUNT_SID` | `AC...` from the Twilio console home page | no |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | **yes**, Secret Manager `twilio-auth-token` |
| `TWILIO_MESSAGING_SERVICE_SID` | `MG...` of the Messaging Service with the approved A2P campaign | no |
| `OWNER_CELL` | owner's cell in E.164, e.g. `+13145550100` | no |
| `OWNER_EMAIL` | where lead and voicemail emails go | no |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_FROM` | mail server settings (Gmail/Workspace: `smtp.gmail.com`, `587`) | no |
| `SMTP_PASSWORD` | app password for `SMTP_USER` | **yes**, Secret Manager `smtp-password` |
| `BOOKING_URL` | optional; defaults to the Calendly 30-minute link | no |

Texting works without the SMTP settings, and email works without Twilio; the agent only needs one channel to succeed.

### Deploy

```bash
export PROJECT_ID=csd-dialogflow-cx-2026
SA=$(gcloud run services describe cx-backend --region us-central1 --project $PROJECT_ID \
  --format='value(spec.template.spec.serviceAccountName)')

# 1. Store the Twilio auth token (typed, not saved in shell history)
gcloud services enable secretmanager.googleapis.com --project $PROJECT_ID
read -s "TW?Twilio auth token: "; echo
printf '%s' "$TW" | gcloud secrets create twilio-auth-token --data-file=- --project $PROJECT_ID; unset TW
gcloud secrets add-iam-policy-binding twilio-auth-token --project $PROJECT_ID \
  --member "serviceAccount:$SA" --role roles/secretmanager.secretAccessor

# 2. Deploy the backend with its settings
gcloud run deploy cx-backend --source . --region us-central1 --project $PROJECT_ID --cpu-boost \
  --update-env-vars TWILIO_ACCOUNT_SID=AC...,TWILIO_MESSAGING_SERVICE_SID=MG...,OWNER_CELL=+1...,OWNER_EMAIL=... \
  --update-secrets TWILIO_AUTH_TOKEN=twilio-auth-token:latest

# 3. Load the conversation and make it live (creates flow version 4)
python3 scripts/apply_agent.py --dry-run
python3 scripts/apply_agent.py --publish
```

### Twilio Studio changes (console, `cx-phone` flow)

1. **Connect Virtual Agent widget** (the existing one, below called `virtual_agent`):
   - Parameters: `caller_number` = `{{trigger.call.From}}`
   - Configurations: `voiceName` = a premium Google voice to audition, e.g. `en-US-Chirp3-HD-Aoede` (female) or `en-US-Chirp3-HD-Charon` (male); fall back to `en-US-Neural2-F` / `en-US-Neural2-D` if the call fails to connect.
2. **Live Agent Handoff** transition of `virtual_agent` → new **Connect Call To** widget `transfer_to_owner`:
   - Single number: the owner's cell. Caller ID: `{{flow.channel.address}}` (the business number, so transfers are recognizable).
   - Timeout: **15** seconds, so the cell's own voicemail does not answer first (that would count as answered).
3. **Connected Call Ended** of `transfer_to_owner` → **Split Based On** `{{widgets.transfer_to_owner.DialCallStatus}}`:
   - equal to `completed` → nothing (call ends).
   - no condition matches → new **Connect Virtual Agent** widget `voicemail_agent`, same connector, with parameters:
     `mode` = `voicemail`,
     `caller_number` = `{{trigger.call.From}}`,
     `caller_first_name` = `{{widgets.virtual_agent.VirtualAgentProviderData.AgentHandoffParameters.caller_first_name}}`,
     `callback_number` = `{{widgets.virtual_agent.VirtualAgentProviderData.AgentHandoffParameters.callback_number}}`,
     `project_needs` = `{{widgets.virtual_agent.VirtualAgentProviderData.AgentHandoffParameters.project_needs}}`,
     and the same `voiceName` configuration.
4. Publish the Studio flow.

### Verify with real calls

1. Happy path: name, confirm caller ID, request, follow-up, say yes to the text. Expect the booking text on the caller's phone and a lead text and email for the owner.
2. Say "talk to a person". Expect a heads-up text, then the owner's cell rings. Answer once; next time let it ring out and leave a voicemail. Expect the voicemail text and email.
3. Say "no" to the caller ID, give another number, then say "no" to the read-back once.

Unverified until tested on the phone: Chirp 3 HD voice support through the Twilio connector; the Studio Liquid path into `AgentHandoffParameters`; that Dialogflow's `!=` condition treats an unset `mode` as not voicemail; that Twilio speaks `outputAudioText` instead of the text version of the greeting.

**Rollback:** point production at version 3 (same command as in the previous section, ending in `versions/3`). In Studio, revert to the previous published flow revision.

## To Do Tomorrow (October 29, 2026)

Tonight (Oct 28) the plan is to deploy the backend with the Twilio settings and publish the v4 conversation (`apply_agent.py --publish`, production flow version 4). Confirm it actually happened: `apply_agent.py` should have printed "LIVE: production now runs version 4."

What works after tonight: shorter conversation, greeting flows straight into "Who am I speaking with?", name and callback number with read-back, Gemini follow-up, booking link texted to the caller, lead text to the owner's cell.

**Known gap until the Studio work below:** if a caller asks for a person, the call ends instead of ringing the owner.

1. **Clean up the branch.** All work is on `caller-experience-v2`. Squash it into `main` as one commit, then delete the branch so there is only `main`:
   ```bash
   git checkout main && git pull
   git merge --squash caller-experience-v2
   git commit -m "Caller experience upgrade: greeting, contact intake, lead alerts, booking text, transfer, voicemail"
   git push
   git branch -D caller-experience-v2 && git push origin --delete caller-experience-v2
   ```
   From then on, work directly on `main`.
2. **Twilio Studio** (`cx-phone` flow), using the steps in "Premium Call Flow v4" above:
   - Pass caller ID: `caller_number` = `{{trigger.call.From}}`.
   - Wire **Live Agent Handoff** → Connect Call To the owner's cell (15-second timeout) → Split on `DialCallStatus` → voicemail agent with `mode` = `voicemail`.
   - Audition a better voice with `voiceName` (start with `en-US-Chirp3-HD-Aoede`).
3. **Email alerts** through Amazon WorkMail (confirmed by the `autodiscover` DNS record): store the WorkMail password as secret `smtp-password`, then
   `gcloud run services update cx-backend --region us-central1 --project csd-dialogflow-cx-2026 --update-env-vars SMTP_HOST=smtp.mail.us-east-1.awsapps.com,SMTP_PORT=465,SMTP_USER=Et@cloudsystemsdirect.com,SMTP_FROM=Et@cloudsystemsdirect.com --update-secrets SMTP_PASSWORD=smtp-password:latest`
   (grant `cx-backend@csd-dialogflow-cx-2026.iam.gserviceaccount.com` the Secret Accessor role on it first).
4. **Test calls:** happy path with booking text, "talk to a person" answered, "talk to a person" missed then voicemail, wrong number read-back.
5. **Decide on always-on:** `cx-backend` runs with `--min-instances 1` (roughly $5-10/month) to avoid cold-start silence. Turn it off with `--min-instances 0` if the cost is not worth it.

Secrets already stored: `twilio-auth-token` (Secret Manager, readable by the `cx-backend` service account).

## October 29, 2026: Contextual dialogue upgrade (code prepared; not deployed)

### Verified deployment checkpoint

The owner verified that Dialogflow `production` points to flow version **4** and
Cloud Run sends all traffic to revision `cx-backend-00004-t94`. One minimum
instance remains enabled by choice to reduce cold starts. The seven commits from
`caller-experience-v2` were fast-forwarded into `main`; both branches matched at
`585528c`. Earlier instructions to republish v4 or squash the branch are obsolete.
These checks do not prove SMS delivery, transfer wiring, or actual billing costs.

### Why the dialogue felt rigid

The deployed discovery path sends the initial request and caller name to Gemini,
asks one follow-up, then moves to booking. It does not give Gemini the conversation
history or provide a general service-question dialogue loop.

### New implementation

- `backend/conversation.py` supplies limited, editable company service facts and
  recent caller/assistant turns, plus the latest structured discovery details.
- The model is instructed to answer the actual question before asking at most one
  useful follow-up, clarify uncertainty, incorporate corrections, and avoid
  invented platforms, prices, guarantees or completed actions.
- Project Follow-up and the new Conversation Router loop until the caller requests
  booking or has supplied useful project/scoping details without an open question.
  The model proposes the next step; existing backend code performs messaging.
- Replies are bounded to 45 words; invalid output and model/network failures ask
  for clarification without erasing prior details or triggering booking.
- Owner notifications include recent customer turns and the updated summary.
- Legacy discovery tags remain supported so deploying the backend first is
  compatible with production v4.

**Scope:** this changes the discovery conversation after name/callback intake.
Contact collection and booking yes/no prompts remain structured. Questions during
those stages, information supplied all at once, durable lead storage, company
knowledge expansion, and Twilio transfer/voice/caller-ID setup still need work.
The existing handoff requires Studio wiring; do not claim transfer works yet.
Prompt instructions reduce unsupported answers but do not guarantee accuracy.
Conversation memory is session-only (up to 16 recent messages, 2000 characters
per message), not persistent memory across callers. Additional model turns add
usage and latency; actual costs must be measured.

### Validation and rollout

1. `python3 -m pip install -r requirements.txt -r requirements-dev.txt`
2. `python3 -m pytest -q` (offline tests mock model outputs and external messaging).
3. `python3 scripts/evaluate_conversation.py` exercises the real Vertex model using
   a short-lived gcloud token. It prints replies for human review, does not call
   Twilio, and incurs model usage. Review service answers, platform invention,
   AWS-to-Azure correction, clarification, unknown pricing, guarantees, explicit
   booking and instruction injection. API success is not a quality pass.
4. Only after reviewing model replies, deploy the backend using the existing
   Cloud Run deployment procedure, preserving environment, secrets, and min=1.
5. Run `python3 scripts/apply_agent.py --dry-run`, review it, then
   `python3 scripts/apply_agent.py --publish` to load the new page and routes.
   Record the actual newly assigned version; do not assume a version number.
6. Test through Dialogflow production and the actual phone line: multiple turns,
   a correction, a service question, booking permission and delivery, silence,
   failure, and the existing transfer path once Studio is configured.

Live Vertex response quality and the Dialogflow page loop have **not** been
validated from this workspace. Backend tests and generated-package integrity
checks cannot substitute for those tests. Production remains v4 until rollout.
For dialogue rollback, point production back to flow version 4. The new backend
still supports v4's tags. Capture the backend revision before any deployment so
it can also be restored if required.

### October 29 live model evaluation: fixes prepared, not deployed

The owner's Mac is synchronized at `2b37ab6`, and all 43 offline tests pass on
Python 3.14. The first real Vertex evaluation returned four `504 DEADLINE_EXCEEDED`
errors in nine requests; correction/memory and clarification could not be fully
assessed. Successful replies included compound questions and an unsupported claim
that the company has no set pricing. This is not ready for phone deployment.

Follow-up changes set `thinking_level=MINIMAL` for conversational generation,
retain the eight-second request limit, disable automatic retries for these
requests, and explicitly prohibit compound questions and invented pricing policy.
Google documents MINIMAL for low-latency chat with Gemini 3.5 Flash:
https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-3-5-flash
This is latency tuning, not proof that model reasoning caused every timeout.
The evaluation script now prints elapsed time for each request and an error count.
All 43 offline tests still pass after the changes; real-model latency, answer
quality and the production page loop remain unverified. Rerun the evaluation and
review the complete correction/clarification paths before any deployment. More
model calls may incur usage charges. The live phone agent remains unchanged.
