"""Pull promo/voucher codes out of a deal page."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

# Words that suggest a page is worth opening to look for a code.
HINTS = re.compile(
    r"\b(promo code|coupon|voucher code|discount code|use code|code:|promocode)\b", re.I
)

# "code: ABC123" / "promo code ABC-123" / "use code “ABC123”"
_LABELLED = re.compile(
    r"(?:promo\s*code|coupon\s*code|voucher\s*code|discount\s*code|use\s+code|code)\s*"
    r"[:\-–]?\s*[\"“'\[]?\s*([A-Z0-9][A-Z0-9._-]{2,24})\b",
)

# Obvious false positives that look like codes.
_STOPWORDS = {
    "FREE", "SALE", "OFF", "NEW", "ONLY", "TODAY", "HERE", "AND", "THE", "FOR",
    "WITH", "FROM", "NOV", "DEC", "JAN", "FEB", "MAR", "APR", "JUN", "JUL",
    "AUG", "SEP", "OCT", "MAY", "SGD", "GST", "USD", "HTTP", "HTTPS", "WWW",
    "TERMS", "APPLY", "VALID", "UNTIL", "TILL", "MORE", "SHOP", "NOW",
}


def looks_promising(text: str) -> bool:
    return bool(HINTS.search(text or ""))


def extract(html: str, limit: int = 5) -> list[str]:
    """Return plausible promo codes found in the page body."""
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return []
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = re.sub(r"\s+", " ", soup.get_text(" "))

    found: list[str] = []
    for match in _LABELLED.finditer(text):
        code = match.group(1).strip(".-_")
        if code.upper() in _STOPWORDS:
            continue
        if code.isdigit() and len(code) < 5:
            continue
        if not any(c.isalpha() for c in code):
            continue
        if code not in found:
            found.append(code)
        if len(found) >= limit:
            break
    return found
