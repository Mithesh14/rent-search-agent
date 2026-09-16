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

## Judgment criteria — evaluate these during scoring, per listing

For each of the four `hard_constraints_json` keys below, mark `PASS`, `FAIL`, or `UNKNOWN`.
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

## What's not built yet (v2)

- 99acres/MagicBricks as additional sources (deferred — stronger anti-bot protection).
- Fetching full listing descriptions from NoBroker's detail pages (the list API only returns
  a title, not a description) or from OLX's `get_listing_details` tool (currently only
  `search_listings` results are staged — worth adding for listings that look promising).
