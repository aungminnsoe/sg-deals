"""Best-effort extraction of an end date from a deal headline.

Deal blogs write validity into the title, e.g.
  "... Till 1 Dec",  "... until 18 Nov 2026",  "... from 19-22 Nov 2026".
This is heuristic: when nothing parses we return None and the deal is kept.
"""
from __future__ import annotations

import re
from datetime import date

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

# Non-capturing on purpose: the patterns below define their own groups.
_MON = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*"

# "till 1 Dec 2026" / "until 18 Nov" / "ends 3 December 2026" / "through 5 Jan"
_TILL = re.compile(
    rf"\b(?:till|until|til|thru|through|ends?(?:\s+on)?|valid\s+(?:till|until))\s+"
    rf"(\d{{1,2}})\s*(?:st|nd|rd|th)?\s+({_MON})\.?\s*(\d{{4}})?",
    re.I,
)
# "19-22 Nov 2026" / "24 November - 7 December 2026"
_RANGE = re.compile(
    rf"\b\d{{1,2}}\s*(?:{_MON}\.?)?\s*(?:[-–]|\bto\b)\s*(\d{{1,2}})\s+({_MON})\.?\s*(\d{{4}})?",
    re.I,
)


def _build(day: int, month_word: str, year: str | None, today: date) -> date | None:
    month = MONTHS.get(month_word.lower().rstrip("."))
    if not month:
        return None
    if year:
        try:
            return date(int(year), month, day)
        except ValueError:
            return None
    # No year given: take this year, unless that lands well in the past,
    # in which case the writer meant next year.
    try:
        guess = date(today.year, month, day)
    except ValueError:
        return None
    if (today - guess).days > 60:
        try:
            guess = date(today.year + 1, month, day)
        except ValueError:
            return None
    return guess


def end_date(title: str, today: date | None = None) -> date | None:
    today = today or date.today()
    for pattern in (_TILL, _RANGE):
        m = pattern.search(title)
        if m:
            got = _build(int(m.group(1)), m.group(2), m.group(3), today)
            if got:
                return got
    return None


def is_expired(title: str, today: date | None = None) -> bool:
    today = today or date.today()
    if re.match(r"^\s*\(expired\)", title, re.I):
        return True
    end = end_date(title, today)
    return bool(end and end < today)
