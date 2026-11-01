# Security and secret management

Review date: November 1, 2026. Repository baseline: `c7cb733a43cd0812e971094b942e8753e96939e1`.

## Secret handling in the documented deployment

The Twilio Auth Token is stored in Google Cloud Secret Manager as `twilio-auth-token`. The recorded Cloud Run deployment maps a secret version into `TWILIO_AUTH_TOKEN`; `backend/notify.py` reads the environment variable when authenticating outgoing Twilio Messaging requests. The runtime does not need a token literal committed in Python or included in the public portfolio.

The setup in the archived build history grants `roles/secretmanager.secretAccessor` to the backend service identity on that individual secret. This describes the recorded setup, not a fresh inspection of live IAM policies. Google recommends pinning a specific version for secrets exposed as environment variables; the historical deployment example uses `latest`. Verify the mapping and plan version changes/rotation during deployment rather than silently changing a working service.

The Account SID and messaging-service SID identify Twilio resources; the Auth Token is the authentication secret. Business numbers, webhook URLs, project IDs, and service-account email addresses are not equivalent to passwords or private keys. They can still disclose infrastructure or contact information.

`SMTP_PASSWORD` is also read from the environment, and Secret Manager setup for an SMTP password is documented. Its live mapping and successful email delivery remain unverified. Twilio Functions use their own runtime configuration and platform-managed signature validation; they are not claimed to retrieve their account token from Google Secret Manager.

## Authentication boundaries

- The Dialogflow webhook export sets `serviceAgentAuth` to `ID_TOKEN`. Cloud Run IAM is the documented ingress-authentication boundary; `backend/main.py` does not independently validate an application-level webhook password.
- `/maya-transfer` is documented as a Protected Twilio Function. Twilio validates `X-Twilio-Signature` for Protected Functions before executing the handler.
- On the review date, an unauthenticated GET to the backend `/health` returned **403**. An unsigned GET to `/maya-transfer` with an explicitly invalid, non-dialing step returned **403**. No call was initiated and no notification or credential-validation request was sent by these checks. These are limited observations, not proof of all IAM or signature-validation cases.
- `backend/notify.py` constructs an Authorization header in memory. Its SMS success logs contain only the recipient’s last four digits and message status; the code does not intentionally log the header or Auth Token. Error bodies and exception strings still deserve review as dependencies evolve.

## Repository and history review

Gitleaks **v8.30.1**, downloaded from its official release and verified against the published SHA-256 checksum, scanned the current checkout and all reachable history with secret redaction enabled. Scope: **2 branches, 29 commits, 140 unique reachable blobs, including 138 UTF-8 text blobs**. Both historical screenshot images were also inspected visually.

| Check | Result |
| --- | --- |
| Gitleaks current checkout | 2 matches, both the same UUID-like `customConfigKey` in a Dialogflow flow and its generator. |
| Gitleaks reachable history | 3 historical matches, all for that same configuration value. |
| Additional signature scan of all reachable text blobs | No matches for PEM private keys, Google API keys, GitHub tokens, AWS access-key IDs, OAuth bearer-token patterns, JWTs, credential-bearing URLs, Twilio API-key IDs, or bare 32-hex token candidates. |
| Credential-like filenames in reachable history | No `.env`, credential/service-account JSON, or private-key filename candidates found. |
| Screenshot review | No visible authentication secrets. The owner’s personal phone number is visible in historical screenshots; the proposed current replacement masks it as `xxx-xxxx`. |

**Conclusion:** no confirmed exposed authentication credentials were identified in this scope. This is not a claim that every string is safe or that credentials have never existed elsewhere.

### Configuration-key finding

The generic API-key rule matched the same UUID-like value under `customConfigKey` in:

- `dialogflow/agent/flows/Default Start Flow/Default Start Flow.json`
- `scripts/build_agent.py`

Its observed use is NLU configuration, not an Authorization header or a secret lookup. Its meaning could not be confirmed in the public API schema checked during this review, so it remains **unclassified metadata**, not a confirmed credential leak and not an automatically allowlisted false positive. Confirm its provenance with the exported agent configuration or Google support before removing it, rotating anything on its behalf, or adding a scanner exception. Raw matched values are omitted here.

## Caller data and remaining work

Secret Manager protects credentials; it does not automatically redact caller information. The backend deliberately logs lead details and voicemail transcripts in Cloud Logging. Restrict log access and define retention/redaction appropriate to that information. Keep raw transcripts and full callback numbers out of public examples and aggregate Power BI views. The proposed current Studio screenshot masks the owner cell number as `xxx-xxxx`. Earlier images remain retrievable from existing Git history; replacing the current image does not remove historical copies. Any history rewrite would require separate approval and coordination.

Before claiming a complete security posture, verify current Cloud Run secret references without displaying values, per-secret IAM grants, secret rotation/version pinning, logging access and retention, and both legitimate and invalid invocation cases. The proposed ignore-file hardening excludes additional common key and credential filenames from Git and Docker contexts; it is not a substitute for scanning or rotation after a real leak.

This review did **not** inspect secret values, authenticated cloud configuration, GitHub Actions logs/artifacts, third-party forks, inaccessible/deleted history, local laptop shell history, or every provider integration. The proposal includes firm-name anonymization in public documentation and a masked replacement screenshot. Runtime prompts and account configuration are unchanged. No history rewrite, credential rotation, deployment, or public GitHub change was performed as part of preparing these findings.

## References

- [Google Cloud: configure secrets for Cloud Run](https://docs.cloud.google.com/run/docs/configuring/services/secrets)
- [Twilio: Function and Asset visibility](https://www.twilio.com/docs/serverless/functions-assets/visibility)
- [Gitleaks official releases](https://github.com/gitleaks/gitleaks/releases)
