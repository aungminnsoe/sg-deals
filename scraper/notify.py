"""Remember which deals we've already seen, and push the new ones.

Two pieces:
  * `diff` compares this run's deals against docs/seen.json and returns the
    ones that are genuinely new.
  * `push` sends those to ntfy.sh, which delivers a real push notification to
    the ntfy app on your phone. Free, no account.

If you'd rather not install another app, skip `push` entirely and have the
iPhone Shortcut read docs/new.json on a schedule - see SHORTCUT.md.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

REMEMBER_DAYS = 60


def load_seen(path: Path) -> tuple[dict[str, str], bool]:
    """Return (id -> last-seen date, first_run)."""
    if not path.exists():
        return {}, True
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        seen = data.get("seen", {})
        return (seen, False) if isinstance(seen, dict) else ({}, True)
    except (OSError, ValueError):
        print("  warn seen.json unreadable - treating this as a first run")
        return {}, True


def diff(deals: list[dict], path: Path) -> tuple[list[dict], bool]:
    """Work out which deals are new, then record everything we saw.

    On the very first run nothing counts as new - otherwise you'd get one
    notification per deal in the archive.
    """
    seen, first_run = load_seen(path)
    today = date.today()

    fresh = [d for d in deals if d["id"] not in seen] if not first_run else []

    for deal in deals:
        seen[deal["id"]] = today.isoformat()

    # Forget deals we haven't seen in a while, so the file can't grow forever.
    cutoff = (today - timedelta(days=REMEMBER_DAYS)).isoformat()
    seen = {k: v for k, v in seen.items() if v >= cutoff}

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"updated": today.isoformat(), "seen": seen}, indent=0),
        encoding="utf-8",
    )
    return fresh, first_run


def write_new(fresh: list[dict], first_run: bool, path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "first_run": first_run,
                "count": len(fresh),
                "deals": fresh,
            },
            ensure_ascii=False, indent=1,
        ),
        encoding="utf-8",
    )


def _line(deal: dict) -> str:
    who = " · ".join(deal.get("merchants") or []) or "Deal"
    code = f"  [code {deal['codes'][0]}]" if deal.get("codes") else ""
    return f"{who}: {deal['title']}{code}"


def push(fresh: list[dict], cfg: dict) -> None:
    """Send new deals to an ntfy.sh topic, if one is configured."""
    settings = cfg.get("notify", {})
    # The env var wins, so the topic can live in a GitHub secret rather than
    # in this repo - anyone who knows a topic name can read its messages.
    topic = (os.environ.get("NTFY_TOPIC") or settings.get("ntfy_topic") or "").strip()
    if not topic:
        return
    if not fresh:
        print("notify: nothing new")
        return

    if settings.get("only_watchlist"):
        fresh = [d for d in fresh if d.get("watched")]
        if not fresh:
            print("notify: nothing new on the watchlist")
            return

    limit = int(settings.get("max_per_run", 10))
    shown, extra = fresh[:limit], max(0, len(fresh) - limit)

    body = "\n".join(_line(d) for d in shown)
    if extra:
        body += f"\n…and {extra} more"

    title = (
        f"{len(fresh)} new SG deal" + ("s" if len(fresh) != 1 else "")
    )
    try:
        resp = requests.post(
            f"https://ntfy.sh/{topic}",
            data=body.encode("utf-8"),
            headers={
                "Title": title.encode("utf-8"),
                "Tags": "shopping",
                "Click": shown[0]["url"],
            },
            timeout=20,
        )
        if resp.status_code < 300:
            print(f"notify: pushed {len(shown)} deal(s) to ntfy")
        else:
            print(f"  warn ntfy returned HTTP {resp.status_code}")
    except requests.RequestException as exc:
        # A failed notification must never fail the scrape.
        print(f"  warn ntfy push failed: {exc.__class__.__name__}")
