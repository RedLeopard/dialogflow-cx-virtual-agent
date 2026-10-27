# CX Project Notes

## October 27, 2026 checkpoint

### Completed

- Built and API-tested consultation intake with an authenticated backend and Gemini project discovery.
- Exported and reviewed the agent configuration, then committed the snapshot.
- Created a published flow version and production environment.
- Granted the permissions required for the native Twilio integration.
- Created the Twilio connector and routed incoming calls to its Studio Flow.
- Enabled sentiment analysis. Sentiment-based routing and callback processing are not implemented.

### Current issue and deployment boundary

The first phone call disconnected because the connector sent a welcome event without a matching event handler. Added the matching handler to Draft and confirmed the API update.

Publication of this fix to production has not been confirmed. A new version creation command was proposed, but no result was supplied. Verify Draft and production before assuming the phone uses the fix.

A later call was reported to sound clunky and did not identify the company. Full phone acceptance testing has not passed. The configuration export in Git predates the welcome-event fix.

### Agreed next experience

The phone experience should identify Cloud Systems Direct, superseding the earlier independent-branding plan.

Opening:

> Thanks for calling Cloud Systems Direct. I'm your virtual assistant. Before we get started, may I have your name?

Then:

1. Capture the caller's name.
2. Explicitly pass the incoming caller number from Twilio into the conversation and verify the mapping.
3. Ask whether the calling number is the best callback number.
4. If not, or caller ID is unavailable, collect an alternative and read it back for confirmation.
5. Ask what the caller needs, then continue project discovery without repeating questions already answered.

Callback confirmation is separate from permission to send SMS. Caller ID is not proof of identity.

This greeting, name capture, incoming-number mapping, and callback confirmation are planned and not yet implemented.

### Next work in order

1. Verify which version is deployed and reconcile the welcome-event fix.
2. Audition a more natural supported voice.
3. Implement the company greeting and contact intake.
4. Publish the intended version and test the actual phone conversation.
5. Test name corrections, alternative numbers, unavailable caller ID, silence, interruptions, failure handling, and ending.
6. Re-export and commit the verified configuration.
7. Merge follow-up answers into structured discovery and summaries.
8. Expand discovery for marketing, website, and app requests.
9. Add confirmed database persistence.
10. Verify US messaging registration readiness, then add explicit SMS permission and booking-link sending.
11. Add confirmed customer message capture and grounded service answers.

Do not claim that a request was saved, a text delivered, or an appointment booked without a confirmed backend result. A spoken long booking URL needs a better phone ending.

### Working approach

Prefer terminal commands for supported GCP work and use the console for connector setup where required. Guide one step at a time and mark completion only from returned evidence. Keep earlier milestones intact and append progress updates.

Current resume point: documentation saved before starting the contact-intake implementation.
