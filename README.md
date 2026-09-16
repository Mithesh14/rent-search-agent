# Rent Search Agent (v1: search + analysis, no contacting owners)

Finds 2BHK+ rentals under ₹25k/month across nine target Chennai localities, scores them
against `preferences.md` (metro proximity, flood history, ambience, photo vibe, value for
money), and produces a shortlist. Never contacts a landlord/broker automatically — this only
searches and analyzes.

Sibling project to `../Job agent`, same architecture (fetch → dedupe → hard-filter → Claude
scores against a preferences doc → record → report).

## Setup

    cd "Rent agent"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

## Sources

All three sources are native Python adapters — no MCP server, no staging file, no browser
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
richest of the three sources. Its public pagination doesn't work for anonymous requests, so
each area query is effectively capped at one page (~40 results).

**MagicBricks** (`sources/magicbricks.py`) — no anti-bot fight needed at all; a plain
`requests` call gets a normal 200. The search results page embeds a real JSON blob
(`window.SERVER_PRELOADED_STATE_`) with rent, BHK (parsed from the listing's URL slug),
property type, furnishing, parking, floor, coordinates, and a photo. Detail-page URLs are
reconstructed from that same JSON field and are best-effort — they occasionally 404 if
MagicBricks' routing wants session context a plain request doesn't have; the underlying data
is still reliable.

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
- Age is unknown for every OLX and MagicBricks listing (neither source exposes a property-age
  field the way NoBroker does) — the age filter only actively rejects NoBroker listings.
- OLX's anonymous search API returns one page (~40 results) per area query — no working
  pagination without a logged-in session.
- MagicBricks detail-page links are reconstructed from data the site embeds for that purpose
  and are usually correct, but can occasionally 404.

## Privacy

This repo is public (`config/areas.yaml`, `preferences.md`, and all source code) — it
contains rental preferences (budget, target areas) but no credentials or account data.
`data/rentals.db` and `reports/` are local-only and gitignored; double-check that stays true
before adding anything else to the repo.
