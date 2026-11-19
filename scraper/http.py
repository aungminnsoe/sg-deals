"""Tiny HTTP helper: polite, retrying, never raises."""
from __future__ import annotations

import time
import requests

_SESSION = requests.Session()
_LAST_CALL = 0.0


def configure(user_agent: str) -> None:
    _SESSION.headers.update({
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-SG,en;q=0.9",
    })


def get(url: str, timeout: int = 25, delay: float = 0.8, retries: int = 2) -> str | None:
    """Return response text, or None if the fetch failed. Never raises."""
    global _LAST_CALL
    for attempt in range(retries + 1):
        wait = delay - (time.time() - _LAST_CALL)
        if wait > 0:
            time.sleep(wait)
        try:
            resp = _SESSION.get(url, timeout=timeout)
            _LAST_CALL = time.time()
            if resp.status_code == 200:
                return resp.text
            if resp.status_code in (404, 410):
                print(f"  skip {url} -> HTTP {resp.status_code}")
                return None
            print(f"  warn {url} -> HTTP {resp.status_code}")
        except requests.RequestException as exc:
            _LAST_CALL = time.time()
            print(f"  warn {url} -> {exc.__class__.__name__}")
        if attempt < retries:
            time.sleep(2 * (attempt + 1))
    return None
