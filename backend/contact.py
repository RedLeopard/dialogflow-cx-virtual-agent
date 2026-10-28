"""Deterministic helpers for caller contact intake (no model calls, so they stay fast)."""
import re

_NAME_LEAD_INS = re.compile(
    r"^\s*(?:hi|hey|hello|yeah|yes|oh|um+|uh+|well|so)?[\s,.!]*"
    r"(?:my name is|my name's|the name is|name's|this is|it's|it is|i'm|i am|call me|you're speaking with|speaking with|you've got)?\s*",
    re.IGNORECASE,
)
_NOT_A_NAME = {
    "i", "a", "the", "yes", "no", "yeah", "nope", "hello", "hi", "hey",
    "um", "uh", "sorry", "what", "okay", "ok",
}


def first_name(raw: object) -> str:
    """Return a clean first name from free text like "Hi, this is maria lopez", or ""."""
    if not isinstance(raw, str):
        return ""
    cleaned = _NAME_LEAD_INS.sub("", raw.strip(), count=1)
    for token in re.findall(r"[A-Za-z][A-Za-z'\-]*", cleaned):
        if token.lower() in _NOT_A_NAME:
            continue
        if len(token) > 20:
            return ""
        return token[0].upper() + token[1:].lower() if token.islower() or token.isupper() else token
    return ""


def digits(raw: object) -> str:
    """Normalize a phone number to 10 US digits when possible, else the digits found."""
    if not isinstance(raw, str):
        return ""
    found = re.sub(r"\D", "", raw)
    if len(found) == 11 and found.startswith("1"):
        found = found[1:]
    return found


def is_usable_us_number(number: str) -> bool:
    return len(number) == 10 and number[0] not in "01"


def spoken_number(number: str) -> str:
    """'3145550123' -> '3 1 4, 5 5 5, 0 1 2 3' so TTS reads digits, not 'three billion'."""
    if is_usable_us_number(number):
        groups = (number[:3], number[3:6], number[6:])
    else:
        groups = (number,)
    return ", ".join(" ".join(g) for g in groups)
