#!/usr/bin/env python3
"""Collect current Singapore deals and write JSON for the iPhone Shortcut.

Outputs (all under docs/, which GitHub Pages serves):
    docs/deals.json          every live deal
    docs/merchants.json      merchant list + counts, for the Shortcut menu
    docs/m/<slug>.json       deals for one merchant
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scraper import codes, dates, feeds, http, merchants, notify, ontoday  # noqa: E402

DOCS = ROOT / "docs"
CONFIG = ROOT / "config.json"


def load_config() -> dict:
    with CONFIG.open(encoding="utf-8") as fh:
        return json.load(fh)


def collect(cfg: dict) -> list[dict]:
    req = cfg["request"]
    raw: list[dict] = []

    for feed in cfg.get("feeds", []):
        print(f"feed  {feed['url']}")
        xml = http.get(feed["url"], req["timeout"], req["delay_seconds"])
        if xml:
            got = feeds.parse(xml, feed["name"])
            print(f"      {len(got)} items")
            raw.extend(got)

    ot = cfg.get("ontoday", {})
    if ot.get("enabled"):
        for page in range(1, int(ot.get("pages", 1)) + 1):
            url = ot["base"] if page == 1 else f"{ot['base'].rstrip('/')}/page/{page}/"
            print(f"list  {url}")
            html = http.get(url, req["timeout"], req["delay_seconds"])
            if html:
                got = ontoday.parse(html)
                print(f"      {len(got)} items")
                raw.extend(got)
    return raw


# SingPromos ends every post URL with its post id, which is the most reliable
# dedupe key. Other sites just get their URL -- do NOT grab a trailing number
# generically, because URLs like /2026/11/19/amazon-sale-november-2026 end in
# a year and would all collide.
_SINGPROMOS_ID = re.compile(
    r"singpromos\.com/[a-z0-9-]+/[a-z0-9-]+-(\d{4,})/?$", re.I
)


def normalise_key(deal: dict) -> str:
    url = deal["url"].rstrip("/").lower()
    match = _SINGPROMOS_ID.search(url)
    return f"singpromos:{match.group(1)}" if match else url


def merge(raw: list[dict]) -> list[dict]:
    """Deduplicate, preferring the record with the most detail."""
    best: dict[str, dict] = {}
    for deal in raw:
        key = normalise_key(deal)
        existing = best.get(key)
        if existing is None:
            best[key] = deal
            continue
        # Keep whichever has more content; carry over any status badge.
        richer = deal if len(deal.get("summary") or "") > len(existing.get("summary") or "") else existing
        richer["status"] = richer.get("status") or deal.get("status") or existing.get("status")
        richer["image"] = richer.get("image") or deal.get("image") or existing.get("image")
        richer["published"] = richer.get("published") or deal.get("published") or existing.get("published")
        best[key] = richer
    return list(best.values())


def enrich(deals: list[dict], cfg: dict) -> list[dict]:
    today = date.today()
    excludes = cfg.get("exclude_url_patterns", [])
    watchlist = set(cfg.get("watchlist", []))
    req = cfg["request"]
    live: list[dict] = []

    for deal in deals:
        if any(pat in deal["url"] for pat in excludes):
            continue
        if (deal.get("status") or "").lower() == "expired":
            continue
        if dates.is_expired(deal["title"], today):
            continue

        deal["title"] = re.sub(r"^\(expired\)\s*", "", deal["title"], flags=re.I).strip()
        end = dates.end_date(deal["title"], today)
        deal["expires"] = end.isoformat() if end else None
        deal["merchants"] = merchants.detect(deal["title"], deal.get("categories"))
        if not deal["merchants"]:
            deal["merchants"] = [merchants.fallback_name(deal["title"])]
        deal["codes"] = []
        deal["id"] = normalise_key(deal)
        deal["watched"] = any(m in watchlist for m in deal["merchants"])
        live.append(deal)

    if cfg.get("fetch_promo_codes"):
        budget = int(cfg.get("max_detail_fetches", 0))
        for deal in live:
            if budget <= 0:
                break
            blob = f"{deal['title']} {deal.get('summary', '')}"
            if not codes.looks_promising(blob):
                continue
            budget -= 1
            page = http.get(deal["url"], req["timeout"], req["delay_seconds"])
            if page:
                found = codes.extract(page)
                if found:
                    deal["codes"] = found
                    print(f"code  {deal['merchants'][0]}: {', '.join(found)}")

    live.sort(key=lambda d: (d.get("published") or "", d["title"]), reverse=True)
    return live


def write_outputs(deals: list[dict]) -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    per_merchant = DOCS / "m"
    for old in per_merchant.glob("*.json"):
        old.unlink()
    per_merchant.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    buckets: dict[str, list[dict]] = {}
    for deal in deals:
        for name in deal["merchants"]:
            buckets.setdefault(name, []).append(deal)

    merchant_index = sorted(
        (
            {"name": name, "slug": merchants.slugify(name), "count": len(items)}
            for name, items in buckets.items()
        ),
        key=lambda m: (-m["count"], m["name"]),
    )

    (DOCS / "deals.json").write_text(
        json.dumps(
            {"generated_at": stamp, "count": len(deals), "deals": deals},
            ensure_ascii=False, indent=1,
        ),
        encoding="utf-8",
    )
    watched = [d for d in deals if d.get("watched")]
    (DOCS / "watchlist.json").write_text(
        json.dumps(
            {"generated_at": stamp, "count": len(watched), "deals": watched},
            ensure_ascii=False, indent=1,
        ),
        encoding="utf-8",
    )
    (DOCS / "merchants.json").write_text(
        json.dumps(
            {"generated_at": stamp, "merchants": merchant_index},
            ensure_ascii=False, indent=1,
        ),
        encoding="utf-8",
    )
    for entry in merchant_index:
        (per_merchant / f"{entry['slug']}.json").write_text(
            json.dumps(
                {
                    "generated_at": stamp,
                    "merchant": entry["name"],
                    "count": entry["count"],
                    "deals": buckets[entry["name"]],
                },
                ensure_ascii=False, indent=1,
            ),
            encoding="utf-8",
        )

    print(f"\nwrote {len(deals)} deals across {len(merchant_index)} merchants -> docs/")


def main() -> int:
    cfg = load_config()
    http.configure(cfg["request"]["user_agent"])

    raw = collect(cfg)
    if not raw:
        print("ERROR: every source failed - keeping the previous deals.json")
        return 1

    deals = enrich(merge(raw), cfg)
    if not deals:
        print("ERROR: nothing survived filtering - keeping the previous deals.json")
        return 1

    # Work out what's new BEFORE writing, so a crash can't mark deals as seen
    # without ever reporting them.
    fresh, first_run = notify.diff(deals, DOCS / "seen.json")
    write_outputs(deals)
    notify.write_new(fresh, first_run, DOCS / "new.json")

    if first_run:
        print("notify: first run, recorded the current deals as the baseline")
    else:
        print(f"notify: {len(fresh)} new since last run")
    notify.push(fresh, cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
