"""Read deals out of a standard WordPress / RSS 2.0 feed.

Works for any deal blog that publishes /feed/ - add more in config.json.
"""
from __future__ import annotations

import html as html_lib
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup

NS = {"content": "http://purl.org/rss/1.0/modules/content/"}


def _text(node, tag: str, default: str = "") -> str:
    found = node.find(tag)
    return (found.text or default).strip() if found is not None and found.text else default


def _strip_html(raw: str) -> tuple[str, str | None]:
    """Return (plain summary, first image url) from an RSS description."""
    if not raw:
        return "", None
    soup = BeautifulSoup(html_lib.unescape(raw), "html.parser")
    img = soup.find("img")
    image = img.get("src") if img else None
    text = re.sub(r"\s+", " ", soup.get_text(" ")).strip()
    # Deal blogs append a "Read more at ..." call to action.
    text = re.split(
        r"(?:\[\s*)?(?:Read more at|Visit .* for the full post)", text, maxsplit=1
    )[0]
    return text.strip(" .[]"), image


def _published(node) -> str | None:
    raw = _text(node, "pubDate")
    if not raw:
        return None
    try:
        return parsedate_to_datetime(raw).isoformat()
    except (TypeError, ValueError):
        return None


def parse(xml_text: str, source_name: str) -> list[dict]:
    """Turn feed XML into deal dicts. Returns [] on malformed input."""
    try:
        root = ET.fromstring(xml_text.strip())
    except ET.ParseError:
        print(f"  warn {source_name}: feed did not parse as XML")
        return []

    deals: list[dict] = []
    for item in root.iter("item"):
        link = _text(item, "link")
        title = html_lib.unescape(_text(item, "title"))
        if not link or not title:
            continue

        body = _text(item, "description")
        full = item.find("content:encoded", NS)
        if full is not None and full.text:
            body = full.text
        summary, image = _strip_html(body)

        deals.append({
            "title": title,
            "url": link.split("?")[0],
            "summary": summary[:400],
            "image": image,
            "categories": [
                html_lib.unescape(c.text.strip())
                for c in item.findall("category") if c.text
            ],
            "published": _published(item),
            "source": source_name,
            "status": None,
        })
    return deals
