# Rent Search Agent (v1: search + analysis, no contacting owners)

Finds 2BHK+ rentals under ₹25k/month across nine target Chennai localities, scores them
against `preferences.md` (metro proximity, flood history, ambience, photo vibe, value for
money), and produces a shortlist. Never contacts a landlord/broker automatically — this only
searches and analyzes.

Lives at `~/rental-skill` (deliberately outside `~/Desktop`/`~/Documents`/`~/Downloads` —
those are macOS TCC-protected and block unattended `launchd` jobs from reading/writing here).

## Setup

    cd ~/rental-skill
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

## Sources

All four sources are native Python adapters — no MCP server, no staging file, no browser
automation. Each was reverse-engineered and verified against live data.

**NoBroker** (`sources/nobroker.py`) — a plain `requests` call to NoBroker's own public
search API. Returns exact rent, BHK, deposit, age, parking, and GPS coordinates per listing,
one query per target area. Only gives a title, not a full description.

**OLX** (`sources/olx.py`) — OLX fingerprints the TLS handshake and blocks plain
`requests`/`curl` outright (confirmed: even a full browser User-Agent gets the connection
reset). [`curl_cffi`](https://github.com/lexiforest/curl_cffi) impersonates a real Chrome TLS
signature and gets through reliably. Once past that, OLX's own search API
(`/api/relevance/v4/search`, undocumented but returns clean JSON) gives full descriptions,
structured parameters (BHK, bathrooms, furnishing, car-parking count), and a photo — the
richest of the four sources for structured fields. Its public pagination doesn't work for
anonymous requests, so each generic query is effectively capped at one page (~40 results).

**MagicBricks** (`sources/magicbricks.py`) — no anti-bot fight needed at all; a plain
`requests` call gets a normal 200. The search results page embeds a real JSON blob
(`window.SERVER_PRELOADED_STATE_`) with rent, BHK (parsed from the listing's URL slug),
property type, furnishing, parking, floor, coordinates, and a photo. Detail-page URLs are
reconstructed from that same JSON field and are best-effort — they occasionally 404 if
MagicBricks' routing wants session context a plain request doesn't have; the underlying data
is still reliable.

**CommonFloor** (`sources/commonfloor.py`) — no anti-bot fight at all, and no custom state
parsing either: listings are embedded as standard `schema.org` JSON-LD
(`<script type='application/ld+json'>`), the easiest of the four to parse. Gives BHK, rent,
address/locality, real GPS coordinates (a placeholder-`0.0` pair means the site itself didn't
have coordinates for that one, not a parsing failure), property type (`Apartment`/`House`
maps directly to apartment/individual_house), and a genuinely rich free-text description —
age, furnishing, parking, and floor are parsed out of that description with regexes since the
structured schema doesn't carry them as separate fields. Pagination has some overlap between
pages (deduped within the adapter) but is otherwise usable.

**99acres and Housing.com are not integrated.** Both returned outright blocks (403/417/406)
even with `curl_cffi`'s TLS impersonation — their anti-bot is stronger (likely
behavioral/Akamai-managed-challenge, not just a TLS fingerprint check) and every working
public scraper for them uses a real headless browser (Playwright/Selenium). Not worth the
added fragility for a background job; revisit only if the three current sources stop being
enough.

## Keep `preferences.md` and `config/areas.yaml` current

`preferences.md` is what the scoring step reads for your requirements and decision
thresholds. `config/areas.yaml` holds the search parameters (rent range, target areas) and
the researched metro-station/flood-history reference data — update the rent range or add
areas there, not in code.

## Run a search

In Claude Code, from this directory:

    /find-rentals

This fetches new listings, hard-filters by BHK/rent/car-parking/type/age/metro-distance/
veg-only, has Claude view each surviving listing's photo and score it against
`preferences.md`, and writes `reports/<today>.md` plus an updated Artifact dashboard.

## Run tests

    PYTHONPATH=src pytest tests/ -v

## Scheduled runs (launchd)

Two `launchd` agents (`~/Library/LaunchAgents/com.mithesh.rent-search-{morning,afternoon}.plist`,
9AM/5PM daily) run `scripts/run-find-rentals.sh`, which activates the venv and invokes
`claude -p` headlessly against the `/find-rentals` skill in this directory. Logs land in
`logs/` (gitignored).

**Update:** an earlier version of this doc suspected Sophos endpoint security was silently
killing `launchd`-triggered `claude -p` runs (based on `log show` evidence of Sophos
inspecting the process). That diagnosis was wrong, or at least incomplete — a scheduled
9AM run was confirmed to complete successfully end-to-end (fetched all 4 sources, viewed
photos, scored 30 listings). It just took ~25 minutes, longer than earlier test-and-check
windows allowed for.

**Known limitation, actually confirmed:** the Artifact publish/update step doesn't reliably
work from a headless `claude -p` session — after that successful run, `Artifact list` showed
no new/updated dashboard, but the skill had still written the full dashboard HTML to
`reports/dashboard.html` locally as it built it. Likely the `Artifact` tool needs the
interactive app's rendering surface, which a bare `-p` CLI process doesn't have. Until that's
resolved, treat `reports/dashboard.html` (open it directly in a browser) as the real
scheduled-run output, not the claude.ai artifact link.

To check whether a scheduled run actually produced anything: `cat logs/morning.log` (or
`afternoon.log`), or just open `reports/dashboard.html` and check its timestamp.

## Data

`data/rentals.db` (SQLite, gitignored) holds every listing ever seen and its status
(`DISCOVERED` → `REVIEWED`, or `REJECTED` by the hard filters). Nothing is deleted — you can
always see what was excluded and why.

## Limitations

- NoBroker's search API only returns a listing title, not a full description — flood/ambience
  signal for NoBroker listings comes mostly from `config/areas.yaml`'s locality-level notes
  and the photo, not listing text.
- Flood-history notes in `config/areas.yaml` are manually researched from Dec 2015 and Dec
  2023 (Cyclone Michaung) news coverage, not a live flood-data API. "No specific reports
  found" for a locality means exactly that — it is not a safety guarantee.
- 99acres and Housing.com are not integrated — see Sources above.
- The veg-only hard filter (`non_veg_allowed`) is keyword-based (`textsignals.py`) against
  title/description text — it catches explicit "vegetarian only" phrasing but can't detect an
  unstated preference the landlord only mentions on a call.
- Age is unknown for every OLX and MagicBricks listing (neither exposes a property-age field)
  and only sometimes known for CommonFloor (parsed from free text, not a structured field) —
  the age filter mostly only actively rejects NoBroker listings.
- OLX's anonymous search API returns one page (~40 results) per query and doesn't support
  scoping the query text to a locality (adding an area name to the query returns zero results
  — it does near-literal phrase matching, not free-text relevance). `sources/olx.py` runs a
  few generic city-wide queries instead and tags locality from the response afterwards.
- MagicBricks detail-page links are reconstructed from data the site embeds for that purpose
  and are usually correct, but can occasionally 404.

## Privacy

This repo is public (`config/areas.yaml`, `preferences.md`, and all source code) — it
contains rental preferences (budget, target areas) but no credentials or account data.
`data/rentals.db` and `reports/` are local-only and gitignored; double-check that stays true
before adding anything else to the repo.
