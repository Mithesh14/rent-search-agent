---
name: find-rentals
description: Run the rent search — fetch new listings from NoBroker, OLX, and MagicBricks, hard-filter, view each listing's photo, score against preferences.md, and produce today's shortlist. Use when the user runs /find-rentals.
---

# Find Rentals

Run these steps in order, in the project root (`~/rental-skill`).

1. Run `PYTHONPATH=src python3 -m rentsearch.fetch`. This fetches from NoBroker, OLX, and
   MagicBricks (all native adapters — no MCP server or staging file needed), dedupes, stores
   everything in `data/rentals.db`, computes each listing's distance to the nearest known
   metro station and its locality's flood notes, and deterministically filters out anything
   that fails the hard constraints (BHK, rent, car parking, property type, age, metro
   distance, veg-only — see `src/rentsearch/filters.py`) into `REJECTED`. Report any
   `failed_sources` in the output to the user, but continue — a partial run still has value.

2. Query the unscored listings: run a short Python one-liner or script using
   `rentsearch.db.connect` + `rentsearch.db.get_unscored_discovered(conn)` against
   `data/rentals.db` to get every row where `status = 'DISCOVERED' AND match_score IS NULL`.

3. Read `preferences.md` in full.

4. For each unscored listing:
   - If it has an `image_url`, download it and actually view it with the Read tool before
     judging `photo_vibe` — don't guess from the title. NoBroker's image host needs a
     `Referer: https://www.nobroker.in/` header or it 403s; OLX and MagicBricks images don't:
     `curl -sL -H "Referer: https://www.nobroker.in/" -o /tmp/listing_<id>.jpg "<image_url>"`.
     If there's no image or the download fails, `photo_vibe` is `UNKNOWN`.
   - Evaluate the listing against `preferences.md` using its stored fields — including
     `metro_distance_km`, `nearest_metro_station`, `flood_notes`, and the photo you just
     viewed. Produce:
     - `match_score` (0-100)
     - `hard_constraints_json`: `{"metro_proximity": "PASS"|"FAIL"|"UNKNOWN", "flood_risk":
       "PASS"|"FAIL"|"UNKNOWN", "ambience": "PASS"|"FAIL"|"UNKNOWN", "value_for_money":
       "PASS"|"FAIL"|"UNKNOWN", "photo_vibe": "PASS"|"FAIL"|"UNKNOWN"}` — using the judgment
       framework in `preferences.md`.
     - `decision`: `SHORTLIST` only if score ≥ 80 and every constraint is `PASS`; `SKIP` if any
       constraint is `FAIL` (regardless of score) or score < 60; otherwise `CONSIDER`.
     - `reasoning_json`: `{"strong_points": "...", "concerns": "...", "flood_context": "...",
       "why_not_shortlist": "..."}`

   Then run:
   `PYTHONPATH=src python3 -m rentsearch.record_score --listing-id <id> --match-score <n> --decision <d> --hard-constraints-json '<json>' --reasoning-json '<json>'`

   This will raise an error if a `FAIL` constraint is paired with anything other than `SKIP` —
   fix the decision and retry rather than working around the validation.

5. Once every unscored listing is recorded, run `PYTHONPATH=src python3 -m rentsearch.report`.
   This prints the report and saves it to `reports/<today>.md`.

6. Build a clean HTML dashboard from this run: Shortlist first (as cards — title, rent, BHK,
   locality, metro distance/station, why it matched, link to the live listing, and the photo
   itself if available), then Consider, then Skip (compact list with reason), then a small
   filtered-out-counts-by-reason section. Include the run timestamp and which sources
   contributed. Load the `artifact-design` skill before writing it.

   Before publishing, call `Artifact` with `action: "list"`, `scope: "mine"` and look for a
   previously published artifact titled `chennai_rent_search`. If found, read it with
   `action: "read"` first, then republish to that same `url` so this stays one
   continuously-updated dashboard instead of a new link every run. If none exists yet,
   publish a new one with title `chennai_rent_search` and a house-emoji favicon.

7. Show the full report to the user in chat, leading with the Shortlist section, and give them
   the artifact link. (If running headless/unattended with no one to show chat output to, the
   artifact URL is the durable output — make sure step 6 actually completed and was not skipped.)

Never contact a landlord, broker, or seller, and never submit any inquiry or application as
part of this command — this skill only searches and analyzes.
