# Rent Search Agent (v1: search + analysis, no contacting owners)

Finds 2BHK+ rentals under ₹25k/month across nine target Chennai localities, scores them
against `preferences.md` (metro proximity, flood history, ambience, value for money), and
produces a shortlist. Never contacts a landlord/broker automatically — this only searches
and analyzes.

Sibling project to `../Job agent`, same architecture (fetch → dedupe → hard-filter → Claude
scores against a preferences doc → record → report).

## Setup

    cd "Rent agent"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

## Sources

**NoBroker** works out of the box — it's a plain `requests` call to NoBroker's own public
search API (`src/rentsearch/sources/nobroker.py`), reverse-engineered and verified against
live data. It returns exact rent, BHK, deposit, age, parking, and GPS coordinates per
listing, one query per target area in `config/areas.yaml`.

**OLX** cannot be scraped directly from this project — OLX actively blocks non-browser HTTP
clients (confirmed: even a plain `curl` with a full browser User-Agent gets its connection
reset). Instead, `src/rentsearch/sources/olx.py` reads `data/olx_staging.json`, which the
`/find-rentals` skill populates by calling the [OLX India MCP
server](https://github.com/Automate-with-Sanjay/OLX_INDIA_MCP_SERVER)'s `search_listings`
tool directly (Claude Code tool access runs from your machine's own network, not this
sandbox, so it has a much better chance of getting through). To enable it:

    git clone https://github.com/Automate-with-Sanjay/OLX_INDIA_MCP_SERVER.git
    cd OLX_INDIA_MCP_SERVER
    npm install && npm run build

Then add it to Claude Code as an MCP server (check that repo's README for the exact
`claude mcp add` invocation against the built `index.js`). If it isn't configured, the skill
skips OLX for that run and says so — NoBroker alone still produces a useful report.

## Keep `preferences.md` and `config/areas.yaml` current

`preferences.md` is what the scoring step reads for your requirements and decision
thresholds. `config/areas.yaml` holds the search parameters (rent range, target areas) and
the researched metro-station/flood-history reference data — update the rent range or add
areas there, not in code.

## Run a search

In Claude Code, from this directory:

    /find-rentals

This fetches new listings, hard-filters by BHK/rent/parking/type/age/metro-distance, has
Claude score every genuinely new listing against `preferences.md`, and writes
`reports/<today>.md`.

## Run tests

    PYTHONPATH=src pytest tests/ -v

## Data

`data/rentals.db` (SQLite, gitignored) holds every listing ever seen and its status
(`DISCOVERED` → `REVIEWED`, or `REJECTED` by the hard filters). Nothing is deleted — you can
always see what was excluded and why.

## Limitations

- NoBroker's search API only returns a listing title, not a full description — flood/ambience
  signal for NoBroker listings comes mostly from `config/areas.yaml`'s locality-level notes,
  not the listing text itself.
- Flood-history notes in `config/areas.yaml` are manually researched from Dec 2015 and Dec
  2023 (Cyclone Michaung) news coverage, not a live flood-data API. "No specific reports
  found" for a locality means exactly that — it is not a safety guarantee.
- 99acres and MagicBricks are not integrated (deferred — stronger anti-bot protection than
  NoBroker; revisit if NoBroker + OLX aren't producing enough coverage).
- OLX listings staged via the MCP server carry only title/description/price/location — BHK,
  property type, age, and parking for OLX listings depend on the skill extracting them from
  free text, and will often come through as `unknown` rather than a hard filter rejection.

## Privacy

`data/rentals.db` and any staged OLX data are local-only; don't push this repo to a public
remote without checking `data/` and `reports/` are excluded (they're gitignored by default).
