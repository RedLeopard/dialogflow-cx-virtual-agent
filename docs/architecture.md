# Maya: solution architecture

**Checkpoint: November 1, 2026.** Designed and built by Edward Thornton for Cloud Systems Direct.

Maya helps a caller reach one of three outcomes: book a consultation, speak with the business owner, or leave a message. Service questions and project discovery support that goal. The [system diagram and component map](../README.md#architecture) show the implemented integrations; the screened transfer and Studio return wiring are now implemented, with remaining fallback and delivery checks documented separately.

## Request and action flow

1. **Receive the call.** Twilio Voice and Studio connect the caller to the native Dialogflow CX connector. Studio owns telephony and transfer routing.
2. **Maintain the conversation.** Dialogflow manages pages, intents, form parameters, and recent conversation context. Its service agent invokes the Cloud Run fulfillment endpoint with an ID token.
3. **Interpret the request.** FastAPI sends the latest utterance, recent history, and previous extracted details to Gemini on Vertex AI. Structured output supplies the reply, updated discovery details, and a proposed action.
4. **Execute the action.** Backend handlers send a booking-link SMS after explicit permission or notify the owner of a lead. For a transfer, fulfillment returns `liveAgentHandoff` to Dialogflow; Studio invokes a protected Twilio Function that calls the owner and requires press-1 acceptance before bridging the caller. An alert SMS alone does not transfer a call.
5. **Complete scheduling externally.** The caller opens the texted Calendly link and selects a time. The backend does not create an appointment through a calendar API.

## Security and service boundaries

| Boundary | Current design |
| --- | --- |
| Voice channel | Twilio's native connector exchanges voice and session information with Dialogflow CX. |
| Fulfillment ingress | Cloud Run requires authenticated invocation using the Dialogflow service agent's ID token. |
| Runtime identity | A dedicated Cloud Run service account accesses Vertex AI and the referenced secret. It is separate from the calling Dialogflow service agent. |
| Credentials | Cloud Run injects the Twilio token from Secret Manager. Credentials stay outside the repository and model prompt. |
| Observability | Backend structured events, including transcribed messages, go to Cloud Logging. Logs are not a dedicated lead database. |

Cloud Run and Dialogflow are deployed in `us-central1`. The documented Gemini configuration uses Vertex's global endpoint. The Google Cloud box in the diagram groups services by provider; it does not represent a VPC or a single regional boundary. This view documents application architecture rather than a private network topology.

## Design decisions and tradeoffs

| Decision | Reason and consequence |
| --- | --- |
| Dialogflow orchestration with Gemini interpretation | Explicit pages and action handlers coordinate the experience while the model interprets varied wording and corrections. The model proposes actions; application handlers perform them. |
| Bounded conversation context | Recent turns and previous discovery details support corrections and reduce repeated questions. Context is session-based; persistent customer memory is future work. |
| Reviewed company facts | Service answers use supplied facts, with explicit wording for applicable pricing and guarantee questions. Broader answer quality still needs real-call evaluation. |
| One warm Cloud Run instance | Reduces cold-start pauses, with an ongoing idle-cost tradeoff. Actual spend has not been verified. |
| Bounded conversational generation | An eight-second request timeout, minimal thinking, and no automatic model retries limit one source of caller delay. These settings do not guarantee end-to-end call latency. |
| External Calendly booking | Provides appointment selection through an existing booking page. Sending a link and completing a booking remain separate outcomes. |

## Failure handling and remaining work

The conversational handler preserves caller wording and prior discovery details when model generation fails, then asks for clarification. Message summarization has a fallback to the captured message. Notification helpers report provider acceptance; they do not track delivery confirmation.

The owner confirmed that the press-1 transfer works after correcting the destination number. The active route is `connect_virtual_agent_1` → `screened_transfer` (TwiML Redirect) → protected `/maya-transfer`. The called leg hears a private acceptance prompt before bridging. If the transfer is not bridged, the function returns the original caller to Studio using `FlowEvent=return`; the redirect widget’s Return output is connected to `missed_call_message`.

This design is intended to keep a carrier voicemail answer from automatically connecting the caller. The published screenshot establishes the wiring, while ignored/declined-call checks and end-to-end message delivery still need verification through the screened route. The older direct-transfer/status widgets remain visible but are outside the active handoff path.

Email notification code is present; successful delivery is unverified. Dedicated lead persistence, audio recording, and in-call appointment creation are future work. Deployment and acceptance checks are in the [current project checkpoint](project-notes.md).

