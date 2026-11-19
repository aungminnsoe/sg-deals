# Building the iPhone Shortcut

Replace `YOURNAME` below with your GitHub username throughout.

Base URL: `https://YOURNAME.github.io/sg-deals`

---

## Shortcut 1 — "SG Deals" (pick a merchant, then a deal)

Open the **Shortcuts** app → **+** → name it *SG Deals*. Add these actions in
order (search for each action name in the bottom search bar).

### Step 1 — fetch the merchant list

1. **Get Contents of URL**
   - URL: `https://YOURNAME.github.io/sg-deals/merchants.json`
2. **Get Dictionary Value**
   - Get: **Value** for key `merchants`
   - in: *Contents of URL*

### Step 2 — show the merchant menu

3. **Choose from List**
   - from: *Dictionary Value*
   - Tap the action to expand it, and set **Prompt** to `Which shop?`

   Each list row is a dictionary, so iOS shows it as `name`. If it looks
   cluttered, that's fine — the next step only reads the `slug`.

4. **Get Dictionary Value**
   - Get: **Value** for key `slug`
   - in: *Chosen Item*

### Step 3 — fetch that merchant's deals

5. **Text**
   - Content: `https://YOURNAME.github.io/sg-deals/m/` then insert the
     *Dictionary Value* variable from step 4, then `.json`

   (To insert a variable: tap in the text field, then tap the variable chip
   that appears above the keyboard.)

6. **Get Contents of URL**
   - URL: the *Text* from step 5
7. **Get Dictionary Value**
   - Get: **Value** for key `deals`

### Step 4 — pick a deal and open it

8. **Choose from List**
   - from: *Dictionary Value*
   - Prompt: `Pick a deal`
9. **Get Dictionary Value**
   - Get: **Value** for key `url`
   - in: *Chosen Item*
10. **Open URLs**
    - URL: *Dictionary Value*

Done. Run it — you should get a merchant menu, then a deal list, then Safari.

### Making the deal list readable

By default **Choose from List** shows raw dictionaries. To show clean titles,
insert this between steps 7 and 8:

- **Repeat with Each** (over *Dictionary Value*)
  - **Get Dictionary Value** → key `title` → in *Repeat Item*
  - **Text** → the *Dictionary Value*, then ` — `, then another
    **Get Dictionary Value** for key `expires`
  - **Add to Variable** → variable name `Titles`
- End Repeat

Then **Choose from List** over `Titles`, and use **Index** matching to find the
original deal. Honestly, the simpler route is the next shortcut.

---

## Shortcut 2 — "Today's Deals" (one tap, no menus)

Simplest possible version, good for a home-screen button.

1. **Get Contents of URL** → `https://YOURNAME.github.io/sg-deals/deals.json`
2. **Get Dictionary Value** → key `deals`
3. **Repeat with Each**
   - **Get Dictionary Value** → key `title` → in *Repeat Item*
   - **Add to Variable** → `Lines`
4. End Repeat
5. **Combine Text** → *Lines*, separated by **New Lines**
6. **Quick Look**

---

## Shortcut 3 — "Deal Codes" (copy a promo code)

1. **Get Contents of URL** → `https://YOURNAME.github.io/sg-deals/deals.json`
2. **Get Dictionary Value** → key `deals`
3. **Filter Files** *(works on lists too)* — or use **Repeat with Each** and
   skip items whose `codes` is empty
4. **Choose from List**
5. **Get Dictionary Value** → key `codes`
6. **Get Item from List** → First Item
7. **Copy to Clipboard**
8. **Show Notification** → "Code copied"

---

## Shortcut 4 — "New Deals" (notification when something new appears)

This is Option B from the README: no extra app, just Shortcuts.

1. **Get Contents of URL** → `https://YOURNAME.github.io/sg-deals/new.json`
2. **Get Dictionary Value** → key `count`
3. **If** → *Dictionary Value* → **is greater than** → `0`
   - **Get Dictionary Value** → key `deals` → in *Contents of URL*
   - **Repeat with Each** (over *Dictionary Value*)
     - **Get Dictionary Value** → key `title` → in *Repeat Item*
     - **Add to Variable** → `Lines`
   - End Repeat
   - **Combine Text** → *Lines*, separated by **New Lines**
   - **Show Notification**
     - Title: `New SG deals`
     - Body: *Combined Text*
4. **Otherwise** → leave empty (stay quiet when there's nothing new)
5. End If

Then schedule it: **Automation** tab → **+** → **Time of Day** → pick a couple
of times a day → **Run Immediately**, *Notify When Run* **off** → choose
*New Deals*.

Set the times a little after the scraper runs. The workflow fires at 02:00,
08:00, 14:00 and 20:00 UTC, which is 10am, 4pm, 10pm and 4am Singapore time —
so 10:30am and 4:30pm are good choices.

**To watch only travel deals**, point step 1 at `watchlist.json` instead of
`new.json`. Edit the `watchlist` in `config.json` to change which merchants
that covers.

---

## Running it automatically

Shortcuts app → **Automation** tab → **+** → **Time of Day** → pick a time →
**Run Immediately** (turn *Notify When Run* off) → choose *Today's Deals*.

Pair it with a **Show Notification** action at the end to get a daily deal
nudge without opening anything.

## Home-screen button

In the Shortcuts app, long-press the shortcut → **Share** → **Add to Home
Screen**.

## If it returns nothing

- Open the JSON URL in Safari first. If you get a 404, Pages isn't on yet
  (Settings → Pages → branch `main`, folder `/docs`) or the Action hasn't run.
- Pages can take a couple of minutes to publish after a commit.
- Check the merchant slug: `m/kfc.json`, `m/mcdonald-s.json`,
  `m/charles-keith.json`. The exact slugs are listed in `merchants.json`.
