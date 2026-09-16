import json
import sys
from datetime import datetime, timezone
from typing import List, Optional

import yaml

from rentsearch import db, geo
from rentsearch.dedupe import compute_dedupe_key, compute_listing_id
from rentsearch.filters import check_filters
from rentsearch.sources.commonfloor import CommonFloorSource
from rentsearch.sources.magicbricks import MagicBricksSource
from rentsearch.sources.nobroker import NoBrokerSource
from rentsearch.sources.olx import OlxSource
from rentsearch.sources.squareyards import SquareYardsSource

DB_PATH = "data/rentals.db"
CONFIG_PATH = "config/areas.yaml"

DEFAULT_SOURCES = [NoBrokerSource(), OlxSource(), MagicBricksSource(), CommonFloorSource(), SquareYardsSource()]


def load_config(path: str = CONFIG_PATH) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def _attach_geo(listing, config: dict) -> dict:
    stations = config.get("metro_stations", [])
    areas = config.get("areas", [])
    area = geo.find_area(f"{listing.locality} {listing.address}", areas)

    if listing.latitude is not None and listing.longitude is not None:
        lat, lon = listing.latitude, listing.longitude
    elif area is not None:
        lat, lon = area["lat"], area["lon"]
    else:
        return {"metro_distance_km": None, "nearest_metro_station": None, "flood_notes": None}

    result = geo.nearest_metro_station(lat, lon, stations)
    return {
        "metro_distance_km": round(result[1], 2) if result else None,
        "nearest_metro_station": result[0]["name"] if result else None,
        "flood_notes": area["flood_notes"].strip() if area else None,
    }


def run(db_path: str = DB_PATH, config: Optional[dict] = None, sources: Optional[List] = None) -> dict:
    config = load_config() if config is None else config
    sources = DEFAULT_SOURCES if sources is None else sources
    db.init_db(db_path)

    summary = {"inserted": 0, "updated": 0, "unchanged": 0, "filtered": 0, "failed_sources": []}
    now = datetime.now(timezone.utc).isoformat()

    with db.connect(db_path) as conn:
        for source in sources:
            try:
                listings = source.fetch(config)
            except Exception as exc:
                summary["failed_sources"].append({"source": source.name, "error": str(exc)})
                continue
            for listing in listings:
                dedupe_key = compute_dedupe_key(listing)
                listing_id = compute_listing_id(dedupe_key)
                description_hash = listing.description_hash()
                geo_info = _attach_geo(listing, config)
                result = db.upsert_listing(conn, listing_id, dedupe_key, listing, description_hash, geo_info, now)
                summary[result] += 1
                if result in ("inserted", "updated"):
                    reason = check_filters(listing, geo_info.get("metro_distance_km"))
                    if reason:
                        db.mark_rejected(conn, listing_id, reason)
                        summary["filtered"] += 1
    return summary


if __name__ == "__main__":
    outcome = run()
    print(json.dumps(outcome, indent=2))
    if outcome["failed_sources"]:
        sys.exit(1)
