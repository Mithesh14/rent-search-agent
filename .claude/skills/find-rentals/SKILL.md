---
name: find-rentals
description: Run the rent search — fetch new listings from NoBroker (and OLX if configured), hard-filter, score against preferences.md, and produce today's shortlist. Use when the user runs /find-rentals.
---

# Find Rentals

Run these steps in order, in the project root (the `Rent agent` directory).

1. **Try to stage OLX results (optional, best-effort).** Check whether an OLX MCP server tool
   (something like `search_listings` from the OLX India MCP server) is available in this
   session. If it is:
   - Read `config/areas.yaml`'s `areas` list.
   - For each target area, call `search_listings` with a query like `"2 bhk flat for rent in
     <area>"`, `location="chennai"`, `min_price` and `max_price` from `config/areas.yaml`'s
     `rent` block.
   - For each result, read its title and description and do your best to extract `bhk`
     (integer), `property_type` (`"apartment"` / `"individual_house"` / `"unknown"`),
     `parking` (`"car"` / `"bike"` / `"both"` / `"none"` / `"unknown"`), and `age_years` if
     mentioned. Leave any field you can't confidently determine as `null`/`"unknown"` — don't
     guess.
   - Write the combined list as JSON to `data/olx_staging.json`, one object per listing with
     keys: `id`, `title`, `url`, `location`, `raw_price`, `description`, `created_at`, plus the
     extracted `bhk`/`property_type`/`parking`/`age_years`.
   - If the tool isn't available, skip this step entirely and mention in your final summary to
     the user that OLX wasn't included in this run (don't fail the whole command over it).

2. Run `PYTHONPATH=src python3 -m rentsearch.fetch`. This fetches from NoBroker (and OLX if
   step 1 staged anything), dedupes, stores everything in `data/rentals.db`, computes each
   listing's distance to the nearest known metro station and its locality's flood notes, and
   deterministically filters out anything that fails the hard constraints (BHK, rent, parking,
   property type, age, metro distance — see `src/rentsearch/filters.py`) into `REJECTED`.
   Report any `failed_sources` in the output to the user, but continue — a partial run still
   has value.

3. Query the unscored listings: run a short Python one-liner or script using
   `rentsearch.db.connect` + `rentsearch.db.get_unscored_discovered(conn)` against
   `data/rentals.db` to get every row where `status = 'DISCOVERED' AND match_score IS NULL`.

4. Read `preferences.md` in full.

5. For each unscored listing, evaluate it against `preferences.md` using its stored fields —
   including `metro_distance_km`, `nearest_metro_station`, and `flood_notes`, which were
   already computed in step 2, plus the listing's own title/description. Produce:
   - `match_score` (0-100)
   - `hard_constraints_json`: `{"metro_proximity": "PASS"|"FAIL"|"UNKNOWN", "flood_risk":
     "PASS"|"FAIL"|"UNKNOWN", "ambience": "PASS"|"FAIL"|"UNKNOWN", "value_for_money":
     "PASS"|"FAIL"|"UNKNOWN"}` — using the judgment framework in `preferences.md`.
   - `decision`: `SHORTLIST` only if score ≥ 80 and every constraint is `PASS`; `SKIP` if any
     constraint is `FAIL` (regardless of score) or score < 60; otherwise `CONSIDER`.
   - `reasoning_json`: `{"strong_points": "...", "concerns": "...", "flood_context": "...",
     "why_not_shortlist": "..."}`

   Then run:
   `PYTHONPATH=src python3 -m rentsearch.record_score --listing-id <id> --match-score <n> --decision <d> --hard-constraints-json '<json>' --reasoning-json '<json>'`

   This will raise an error if a `FAIL` constraint is paired with anything other than `SKIP` —
   fix the decision and retry rather than working around the validation.

6. Once every unscored listing is recorded, run `PYTHONPATH=src python3 -m rentsearch.report`.
   This prints the report and saves it to `reports/<today>.md`.

7. Build a clean HTML dashboard from this run: Shortlist first (as cards — title, rent, BHK,
   locality, metro distance/station, why it matched, link to the live listing), then Consider,
   then Skip (compact list with reason), then a small filtered-out-counts-by-reason section.
   Include the run timestamp and note whether OLX was included this run. Load the
   `artifact-design` skill before writing it.

   Before publishing, call `Artifact` with `action: "list"`, `scope: "mine"` and look for a
   previously published artifact titled `chennai_rent_search`. If found, read it with
   `action: "read"` first, then republish to that same `url` so this stays one
   continuously-updated dashboard instead of a new link every run. If none exists yet,
   publish a new one with title `chennai_rent_search` and a house-emoji favicon.

8. Show the full report to the user in chat, leading with the Shortlist section, and give them
   the artifact link. (If running headless/unattended with no one to show chat output to, the
   artifact URL is the durable output — make sure step 7 actually completed and was not skipped.)

Never contact a landlord, broker, or seller, and never submit any inquiry or application as
part of this command — this skill only searches and analyzes.
