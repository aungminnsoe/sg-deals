"""Scrape SingPromos' "ongoing today" listing.

The feed only carries the newest ~15 posts; this listing carries everything
that is valid *right now*, which is what we actually want.

Deliberately written not to depend on CSS class names (they change). We find
links that match the post-URL shape and read the status badge from the text
around them.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

# https://singpromos.com/<category>/<slug>-<postid>/
POST_URL = re.compile(r"^https?://(?:www\.)?singpromos\.com/[a-z0-9-]+/[a-z0-9-]+-(\d{4,})/?$", re.I)

STATUS_WORDS = [
    "EXPIRED", "LAST DAY", "ENDS TODAY", "STARTED TODAY",
    "COMING SOON", "STARTS TOMORROW", "ON TODAY",
]


def _status_near(anchor) -> str | None:
    """Read the status badge from the card that contains this link."""
    node = anchor
    for _ in range(4):
        node = node.parent
        if node is None:
            return None
        blob = " ".join(node.get_text(" ").split()).upper()
        for word in STATUS_WORDS:
            if word in blob:
                return word.title()
    return None


def parse(html: str, source_name: str = "SingPromos") -> list[dict]:
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return []

    seen: set[str] = set()
    deals: list[dict] = []

    for a in soup.find_all("a", href=True):
        href = a["href"].split("?")[0]
        if not POST_URL.match(href) or href in seen:
            continue
        title = " ".join(a.get_text(" ").split())
        if len(title) < 15:          # image-only link; the text link follows
            continue
        seen.add(href)

        img = a.find("img")
        node = a
        for _ in range(3):              # walk up to the card and look again
            if img is not None:
                break
            node = node.parent
            if node is None:
                break
            img = node.find("img")

        deals.append({
            "title": title,
            "url": href,
            "summary": "",
            "image": img.get("src") if img else None,
            "categories": [href.split("/")[3].replace("-", " ")] if len(href.split("/")) > 4 else [],
            "published": None,
            "source": source_name,
            "status": _status_near(a),
        })
    return deals
