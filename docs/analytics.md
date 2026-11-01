# Maya BigQuery analytics

## Deployment checkpoint

On November 1, 2026, the owner's Terminal output confirmed creation of
`csd-dialogflow-cx-2026.maya_analytics` in `us-central1`, with two tables and
three views. The setup assertion and view queries passed. A subsequent SQL
grant completed successfully for the existing Cloud Run service identity,
`cx-backend@csd-dialogflow-cx-2026.iam.gserviceaccount.com`, with
`roles/bigquery.dataEditor` on this dataset.

The backend integration in this commit is tested offline. A source commit
does not deploy Cloud Run. Live writes, Studio ID mappings, and a real-call
row check remain to be verified. Power BI is not connected. Audio recording
was dropped from the current plan and remains disabled.

## Stored data

| Object | Purpose |
| --- | --- |
| `call_events` | Structured backend observations, event timestamps and IDs, fixed service categories, and known outcomes. No names, phone numbers, raw messages, or raw webhook payloads. |
| `leads` | Append-only lead snapshots with contact details, project needs, project/message summaries, SMS consent, and follow-up status. No audio or full message transcripts. |
| `call_events_deduplicated` | Latest record for each stable event ID. |
| `daily_activity` | Counts of observed calls and supported events by event date in America/Chicago; test rows excluded. |
| `service_demand` | Latest lead snapshots grouped by service and creation date; test rows and contact/message fields excluded. |

Existing full message logging is unchanged. Views omit contact details but are
not a separate access-control boundary. A future Power BI identity should be
granted only the reporting access it needs; no such identity or grant is created
by this integration. No automatic retention/deletion policy is added.

## Events and limits

- Each successful supported webhook records `webhook_processed`. This measures
  backend-observed interactions, not every incoming phone call.
- `finish-discovery` records `lead_captured` and, when newly accepted by an
  owner-notification provider, `notification_accepted`.
- `send-booking-link` records `booking_link_sent` only when the SMS provider
  accepted the request; a failed attempt records `booking_link_failed`.
  Re-entering after `booking_sms_sent=true` does not claim another sent link.
- `handoff` records `transfer_requested`; it does not claim a connected call.
- `voicemail-save` records `message_captured` and saves the generated summary.
  The existing `voicemail_delivered` flag means a provider accepted an owner
  alert; analytics calls this `notification_accepted`, not delivered.
- Booking consent is true on the affirmative booking-text route, false on the
  decline route, and otherwise unknown until an explicit value is available.
- The backend does not produce `call_started`, `call_completed`, transfer
  acceptance, SMS delivery, durations, or `booking_confirmed`. Those require
  separate Twilio/Calendly result integrations; their current report columns
  are not evidence that ingestion of those outcomes exists.
- New lead snapshots use `needs_follow_up`. No completed appointment or
  completed follow-up is inferred from a sent text or a transfer request.

## Preserve call identity in Twilio Studio

In **both** Connect Virtual Agent widgets (`connect_virtual_agent_1` and
`missed_call_message`), add this entry to **Parameters** and preserve every
existing parameter, welcome event, and voice setting:

| Key | Value |
| --- | --- |
| `call_id` | `{{trigger.call.CallSid}}` |

Save and publish the Studio flow. This passes the original inbound Call SID
through a new Maya message-taking session; it is not the caller's phone number.
Preserve the existing name, callback, and project-context mappings as well.

The backend returns `analytics_call_id` and `analytics_created_at` in session
state. If available in the Studio handoff output, preserve that creation time
when entering the second session. Otherwise a returning message session's lead
snapshot can use its later start time. The call and lead identities still
match when both widgets receive the original Call SID.

If Studio has not supplied `call_id`, the backend uses a hash of the Dialogflow
session resource. That fallback is stable within one session but **cannot merge
two different sessions for one phone call**. Until mappings are verified, do
not interpret calls observed as a complete count of distinct phone calls.

## Deploy from the Mac checkout

From `/Users/streetgenius/dialogflow-cx-virtual-agent`, pull the tested commit:

```bash
git pull --ff-only origin main
```

Keep the current ready revision as a rollback reference:

```bash
gcloud run services describe cx-backend \
  --project=csd-dialogflow-cx-2026 --region=us-central1 \
  --format='value(status.latestReadyRevisionName)'
```

Deploy the backend with these additional environment variables:

```bash
gcloud run deploy cx-backend --source . \
  --project=csd-dialogflow-cx-2026 --region=us-central1 \
  --update-env-vars=BIGQUERY_ENABLED=true,BIGQUERY_PROJECT=csd-dialogflow-cx-2026,BIGQUERY_DATASET=maya_analytics,BIGQUERY_LOCATION=us-central1
```

`--update-env-vars` preserves unrelated environment variables and secret
references. The backend uses the existing runtime service identity through
Application Default Credentials; no downloaded service-account key is needed.
No Dialogflow agent rebuild or publish is required for this backend change.

Writes run before returning the webhook response so Cloud Run has CPU during
the work. Each table insertion uses a 1.5-second transport timeout and no SDK
retries. Credential initialization/refresh can add time; no total latency
guarantee is claimed. Measure speech latency on live calls after deployment.
Failures are logged without row content or raw provider errors and do not turn
a successful handler response into a failed call. The events and lead insertions
are independent, not transactional. This is best-effort ingestion: there is no
durable retry queue, so outages or container interruptions can lose records.

Event IDs combine the call identity, Dialogflow request ID (or a deterministic
request hash), and event type. BigQuery insert IDs support best-effort retry
deduplication; the reporting view also deduplicates by event ID. Notification
and call side effects are not made exactly-once by analytics deduplication.

## Verify after deployment

1. Publish the two Studio `call_id` mappings, then make a normal test call.
   Exercise a booking text and a message path; check that speech and alerts
   still work. A real phone test is live activity unless explicitly marked
   with the boolean session parameter `analytics_is_test=true`.
2. Check recent Cloud Run logs for `analytics_written` and `analytics_failed`.
3. Query only structured event fields; avoid posting contact/message rows in
   public screenshots or repository examples:

```bash
bq --project_id=csd-dialogflow-cx-2026 --location=us-central1 query \
  --use_legacy_sql=false '
SELECT event_timestamp, event_type, source, outcome
FROM `csd-dialogflow-cx-2026.maya_analytics.call_events_deduplicated`
WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
ORDER BY event_timestamp DESC
LIMIT 30'
```

Check that one inbound call keeps the same `call_id` on both bot sessions and
the same `lead_id` on its snapshots. If needed, disable the new writes without
reverting the rest of Maya:

```bash
gcloud run services update cx-backend \
  --project=csd-dialogflow-cx-2026 --region=us-central1 \
  --update-env-vars=BIGQUERY_ENABLED=false
```

Next integrations are telephony result events and Power BI reporting.
