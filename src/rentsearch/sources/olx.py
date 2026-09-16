import json
from pathlib import Path
from typing import List

from rentsearch.models import PropertyListing
from rentsearch.sources.base import ListingSource

# OLX actively blocks non-browser HTTP clients (confirmed: even a plain curl with a full
# browser User-Agent gets its TLS/HTTP2 stream reset), so this source can't hit OLX directly
# like nobroker.py does. Instead, the find-rentals skill calls the OLX India MCP server's
# search_listings/get_listing_details tools (Claude Code tool access, not this Python
# process) and writes normalized results here before rentsearch.fetch runs. If that staging
# file is missing, this source contributes nothing to the run rather than failing it.
STAGING_PATH = "data/olx_staging.json"


class OlxSource(ListingSource):
    name = "olx"

    def fetch(self, config: dict, staging_path: str = STAGING_PATH) -> List[PropertyListing]:
        path = Path(staging_path)
        if not path.exists():
            return []
        raw_items = json.loads(path.read_text() or "[]")
        return [self._to_listing(item) for item in raw_items]

    def _to_listing(self, raw: dict) -> PropertyListing:
        return PropertyListing(
            source=self.name,
            source_id=str(raw.get("id")) if raw.get("id") else None,
            url=raw.get("url", ""),
            title=raw.get("title", ""),
            locality=raw.get("locality") or raw.get("location", ""),
            address=raw.get("location", ""),
            latitude=raw.get("latitude"),
            longitude=raw.get("longitude"),
            rent=raw.get("raw_price") or raw.get("price") or 0,
            deposit=raw.get("deposit"),
            maintenance=raw.get("maintenance"),
            bhk=raw.get("bhk"),
            property_type=raw.get("property_type", "unknown"),
            age_years=raw.get("age_years"),
            parking=raw.get("parking", "unknown"),
            furnishing=raw.get("furnishing"),
            bathrooms=raw.get("bathrooms"),
            description_raw=raw.get("description", ""),
            posting_date=raw.get("created_at"),
        )
