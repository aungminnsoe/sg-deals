# SG Deals

Scrapes current Singapore deals and promo codes, publishes them as JSON on
GitHub Pages, and serves them to an iPhone Shortcut. No server, no API keys,
no cost — GitHub Actions does the work on a schedule.

```
GitHub Actions (every 6h)  →  docs/deals.json  →  GitHub Pages  →  iPhone Shortcut
```

## Sources

| Source | How | Notes |
|---|---|---|
| [SingPromos](https://singpromos.com) | RSS feeds + "ongoing today" listing | Main source. Covers KFC, McDonald's, Shopee, Amazon, banks, warehouse sales |
| [Great Deals Singapore](https://www.greatdeals.com.sg) | RSS feed | Second opinion, different editorial picks |

**Why not scrape Amazon/Shopee/KFC directly?** They are JavaScript apps behind
bot protection, their terms forbid scraping, and a GitHub Actions IP gets
blocked within minutes. Deal blogs republish the same offers in plain HTML and
RSS, which is stable and cheap to read. You still get Amazon and Shopee deals —
just via a source that doesn't fight back.

## Setup (about 10 minutes)

1. **Create the repo.** On GitHub, New repository → name it `sg-deals` → Public
   (Pages is free on public repos) → Create.
2. **Upload these files.** Either `git push`, or use GitHub's "uploading an
   existing file" link and drag the whole folder in.
3. **Let Actions write back.** Settings → Actions → General → Workflow
   permissions → **Read and write permissions** → Save.
4. **Turn on Pages.** Settings → Pages → Source: *Deploy from a branch* →
   Branch `main`, folder **`/docs`** → Save.
5. **Run it once.** Actions tab → *Scrape SG deals* → Run workflow.
   (The first run is also what creates `deals.json`.)
6. Your URLs are now:
   - Page: `https://<your-username>.github.io/sg-deals/`
   - All deals: `https://<your-username>.github.io/sg-deals/deals.json`
   - Merchant list: `https://<your-username>.github.io/sg-deals/merchants.json`
   - One merchant: `https://<your-username>.github.io/sg-deals/m/kfc.json`
   - **New since last run:** `https://<your-username>.github.io/sg-deals/new.json`
   - **Watchlist only:** `https://<your-username>.github.io/sg-deals/watchlist.json`

## Notifications

The scraper remembers every deal it has seen in `docs/seen.json`, so each run
can tell you what's genuinely new. There are two ways to get told, and they
work independently.

### Option A — ntfy push (real notifications, needs a free app)

1. Install **ntfy** from the App Store.
2. Pick a long, unguessable topic name, e.g. `sgdeals-7f3k9x2p`. Anyone who
   knows a topic name can read its messages, so don't use something guessable
   like `sgdeals`.
3. In the ntfy app: **+** → subscribe to that topic.
4. On GitHub: Settings → Secrets and variables → Actions → **New repository
   secret** → name `NTFY_TOPIC`, value your topic name.

That's it. The secret keeps the topic out of your public repo. Every run that
finds new deals pushes one grouped notification; tapping it opens the first
deal. Runs with nothing new send nothing.

### Option B — iPhone Shortcut automation (no extra app)

A Shortcuts automation reads `new.json` on a schedule and shows a
notification. Setup is in [SHORTCUT.md](SHORTCUT.md). It only fires when your
phone runs the automation, so it's less immediate than ntfy, but there's
nothing to install.

**The first run never notifies.** It records the current deals as a baseline,
otherwise you'd get one notification for every deal in the archive. New deals
start reporting from the second run.

## Watchlist

`watchlist` in `config.json` is a list of merchants you care about. Deals from
them get `"watched": true`, appear in `watchlist.json`, and show under a
**Watching** chip on the page. It ships with the travel sites:

```json
"watchlist": ["Trip.com", "Agoda", "Booking.com", "Klook", "Expedia", "Singapore Airlines"]
```

Set `notify.only_watchlist` to `true` if you want notifications for these
merchants only. Names must match the merchant names in
`scraper/merchants.py` exactly.

## The iPhone Shortcut

See **[SHORTCUT.md](SHORTCUT.md)** for the step-by-step build. Short version:
fetch `merchants.json` → pick a merchant from a menu → fetch
`m/<slug>.json` → pick a deal → open it in Safari.

## JSON shape

```json
{
  "generated_at": "2026-11-19T02:00:08+00:00",
  "count": 142,
  "deals": [
    {
      "id": "309946",
      "title": "7-Eleven S'pore $1 Deals & Bottled Drink Offers Till 1 Dec",
      "url": "https://singpromos.com/dining-restaurants-food/...",
      "summary": "Save 33% on a citrusy frozen treat…",
      "image": "https://cdn.singpromos.com/…jpg",
      "merchants": ["7-Eleven"],
      "codes": ["BF2026"],
      "expires": "2026-12-01",
      "status": "On Today",
      "source": "SingPromos",
      "published": "2026-11-18T10:06:52+00:00",
      "categories": ["Eat & Drink"]
    }
  ]
}
```

## Tuning it

Everything you'd want to change lives in `config.json`:

- **`feeds`** — add any deal blog that publishes `/feed/`. The parser is a
  generic RSS reader, so most WordPress sites just work.
- **`ontoday.pages`** — how many pages of SingPromos' "ongoing" listing to read.
  3 pages ≈ 30 currently-valid deals; raise it for more.
- **`exclude_url_patterns`** — categories to drop. `/news/` and
  `/motor-vehicles/` are excluded because COE and ERP posts aren't deals.
- **`max_detail_fetches`** — how many deal pages to open looking for promo
  codes. Each one is an extra HTTP request, so keep it modest.
- **`watchlist`** — merchants to flag and (optionally) notify about.
- **`notify.only_watchlist`** — `true` sends notifications only for watchlist
  merchants; `false` sends them for everything new.
- **`notify.max_per_run`** — caps how many deals one notification lists. The
  rest become "…and N more".

Per-merchant feeds don't exist on these sites — `singpromos.com/tag/agoda/feed/`
silently redirects to the main feed — so merchant coverage comes from brand
detection across all feeds, not from a feed per shop.

To add merchants to the filter menu, edit `BRANDS` in `scraper/merchants.py`.
Anything not in that list still shows up — it just gets a merchant name guessed
from the first words of the headline.

## Running it locally

```bash
pip install -r requirements.txt
python scraper/main.py
# then: open docs/index.html
```

## Known limits

- **Expiry dates are heuristic.** They're parsed out of headlines like
  "Till 1 Dec" — reliable most of the time, not always. Always check the
  merchant's own terms before you count on a deal.
- **Promo codes are best-effort.** The extractor looks for text like
  "promo code: XXXX". Codes shown only inside images won't be found.
- **A blog changing its HTML can break the listing scraper.** The RSS feeds
  will keep working, so you'd get fewer deals rather than none. The workflow
  keeps the previous `deals.json` if a run returns nothing.
- Deal content belongs to the sites linked above; this just indexes headlines
  and links back to them.
