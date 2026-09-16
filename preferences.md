# Rental Preferences — Mithesh A

> Source of truth for rental matching. The scoring step reads this file directly. Update it
> whenever your budget, must-haves, or target areas change.

## Hard constraints (already enforced in code — `rentsearch.filters`)

These are checked deterministically before Claude ever sees a listing. If a listing survived
to the `DISCOVERED` state, it already passed all of these:

- **BHK:** 2 or more.
- **Rent:** ≤ ₹25,000/month.
- **Parking:** car parking present ("car" or "both"), or unknown. Bike-only does not satisfy
  this — car parking is compulsory, not "any parking."
- **Property type:** apartment or independent house (not a shared room, PG, etc.), or unknown.
- **Age:** under 5 years, or unknown.
- **Metro distance:** ≤ 6 km from the nearest known metro station (a generous ceiling — the
  real 3–5 km judgment below is more precise and is made per-listing during scoring).
- **Food preference:** I'm non-vegetarian. Skip any listing that explicitly says the building
  or society is vegetarian-only / doesn't allow non-veg (`non_veg_allowed = False` in the
  data). Silence on the topic is normal and fine — most listings say nothing either way.

## Judgment criteria — evaluate these during scoring, per listing

For each of the five `hard_constraints_json` keys below, mark `PASS`, `FAIL`, or `UNKNOWN`.
Any single `FAIL` forces `decision = SKIP` regardless of score (see `record_score.py`).

1. **`metro_proximity`** — PASS if the listing's stored `metro_distance_km` is within 3–5 km
   of an *existing, operational* Chennai Metro station (Blue/Green lines — see
   `config/areas.yaml`'s `metro_stations` list, all real and running today, not Phase 2).
   Under 3 km is even better, call it out. Over 5 km but under the 6 km hard ceiling: mark
   `UNKNOWN` rather than an automatic `FAIL` and note it as a concern — don't silently exclude
   a listing that's otherwise excellent over half a kilometre.

2. **`flood_risk`** — PASS if `config/areas.yaml`'s `flood_notes` for that listing's locality
   don't indicate elevated risk, AND the listing's own description doesn't mention past
   waterlogging. `FAIL` only for confirmed elevated-risk areas (Kotturpuram, Adyar, Alandur,
   Ashok Nagar are the ones with confirmed Dec 2015/Dec 2023 flooding reports in
   `areas.yaml`) — and even then, weigh floor level if known (a 2nd-floor-or-higher unit in a
   flood-prone area is a materially different risk than ground floor). Localities with "no
   specific reports found" are `UNKNOWN`, not `PASS` — the absence of a news report is not
   evidence of safety.

3. **`ambience`** — your judgment call from the listing's title/description/locality
   character (residential vs. commercial/main-road frontage, known-noisy areas, proximity to
   industrial or heavy-traffic corridors). Mark `UNKNOWN` rather than guessing if the listing
   gives no signal either way.

4. **`value_for_money`** — compare rent, size (if known), furnishing, and amenities against
   other listings seen in the same run for a similar locality/BHK. This is necessarily
   relative, not absolute — note what you're comparing against in `reasoning_json`.

5. **`photo_vibe`** — actually look at the listing's photo (download `image_url` and view it,
   don't guess from text). `FAIL` if the photo shows a place that's visibly run-down, dark,
   cramped, poorly maintained, or otherwise low-appeal — a real example that should FAIL: "2
   BHK Flat, Wisva, West Saidapet Bus Depot" (dingy, unappealing interior, bus-depot-adjacent).
   `PASS` if it looks clean, reasonably modern, and well-kept for the price point. `UNKNOWN`
   only if there's no image at all or it fails to load — don't skip this check just because
   it's more work than reading text.

## Decision thresholds

- `SHORTLIST`: score ≥ 80 and no `FAIL` constraints.
- `SKIP`: any `FAIL` constraint, or score < 60.
- `CONSIDER`: everything else.

## Target areas

Kotturpuram, Guindy, Adyar, Ekkatuthangal, Alandur, Ashok Nagar, Pazhavanthangal, Nanganallur,
St Thomas Mount. "Good location" in this project means one of these nine areas — not Chennai
generally. All nine already sit within ~5 km of an existing (not upcoming) metro station per
the distance data in `config/areas.yaml`; Adyar is the farthest at ~4.85 km and Kotturpuram at
~3.5 km, both still inside the target range.

## Sources

NoBroker, OLX, MagicBricks, CommonFloor, and SquareYards are all native adapters (no MCP
server or staging file needed — see `README.md` for how each one actually reaches its site).

## What's not built yet (v2)

- 99acres and Housing.com (both need a real headless browser — their anti-bot is stronger
  than a TLS-fingerprint-level block; not worth it for a scheduled unattended job yet).
- Fetching full listing descriptions from NoBroker's detail pages (the list API only returns
  a title, not a description, which limits `ambience`/`photo_vibe` signal for NoBroker
  listings specifically to whatever the title and photo show).
