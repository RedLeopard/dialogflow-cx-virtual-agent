"""Outbound text messages (Twilio) and email (SMTP), standard library only.

Configuration comes from environment variables (secrets are mapped in from
Secret Manager by Cloud Run):

    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN      Twilio credentials (secrets)
    TWILIO_MESSAGING_SERVICE_SID or TWILIO_FROM_NUMBER
                                               A2P-registered sender
    OWNER_CELL                                 where lead texts go, e.g. +13145550100
    OWNER_EMAIL                                where lead emails go
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD (secret), SMTP_FROM

Every function returns True only when the provider accepted the message.
Nothing here raises; failures are logged so a call never breaks on them.
"""
import base64
import json
import os
import smtplib
import ssl
import urllib.error
import urllib.parse
import urllib.request
from email.message import EmailMessage

TWILIO_API = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


def log(event: str, **fields):
    """One JSON line per event; Cloud Logging indexes these as structured logs."""
    print(json.dumps({"event": event, **fields}, default=str), flush=True)


def e164(number: str) -> str:
    """10 US digits -> +1XXXXXXXXXX; anything already starting with + is kept."""
    number = (number or "").strip()
    if number.startswith("+"):
        return number
    digits = "".join(c for c in number if c.isdigit())
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    return ""


def send_sms(to: str, body: str) -> bool:
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    service = os.getenv("TWILIO_MESSAGING_SERVICE_SID")
    sender = os.getenv("TWILIO_FROM_NUMBER")
    to = e164(to)
    if not (sid and token and (service or sender) and to):
        log("sms_skipped", reason="missing configuration or number", to_present=bool(to))
        return False

    fields = {"To": to, "Body": body}
    if service:
        fields["MessagingServiceSid"] = service
    else:
        fields["From"] = sender
    auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
    req = urllib.request.Request(
        TWILIO_API.format(sid=sid),
        data=urllib.parse.urlencode(fields).encode(),
        headers={"Authorization": f"Basic {auth}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            result = json.loads(resp.read() or b"{}")
        log("sms_accepted", to_last4=to[-4:], message_sid=result.get("sid"), status=result.get("status"))
        return True
    except urllib.error.HTTPError as e:
        log("sms_failed", to_last4=to[-4:], status=e.code, detail=e.read().decode(errors="replace")[:500])
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        log("sms_failed", to_last4=to[-4:], detail=str(e))
    return False


def send_email(to: str, subject: str, body: str) -> bool:
    host = os.getenv("SMTP_HOST")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    port = int(os.getenv("SMTP_PORT", "587"))
    sender = os.getenv("SMTP_FROM") or user
    if not (host and user and password and to):
        log("email_skipped", reason="missing configuration")
        return False

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        context = ssl.create_default_context()
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=6, context=context) as smtp:
                smtp.login(user, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=6) as smtp:
                smtp.starttls(context=context)
                smtp.login(user, password)
                smtp.send_message(msg)
        log("email_sent", subject=subject)
        return True
    except (smtplib.SMTPException, OSError) as e:
        log("email_failed", detail=str(e))
        return False
