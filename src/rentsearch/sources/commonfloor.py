import json
import re
from typing import List, Optional

import requests

from rentsearch.models import PropertyListing
from rentsearch.sources.base import ListingSource
from rentsearch.textsignals import detect_veg_only

SEARCH_URL = "https://www.commonfloor.com/chennai-property/for-rent"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Accept": "text/html,application/xhtml+xml",
}

LD_JSON_RE = re.compile(r"<script type='application/ld\+json'>(.*?)</script>", re.DOTALL)
TYPE_MAP = {"Apartment": "apartment", "House": "individual_house"}

AGE_RE = re.compile(r"(\d+)(?:\s*(?:to|-)\s*\d+)?\s*years?\s*old", re.IGNORECASE)
BATHROOMS_RE = re.compile(r"(\d+)\s*bathrooms?", re.IGNORECASE)


def _parse_age_years(description: str) -> Optional[int]:
    match = AGE_RE.search(description)
    return int(match.group(1)) if match else None


def _parse_bathrooms(description: str) -> Optional[int]:
    match = BATHROOMS_RE.search(description)
    return int(match.group(1)) if match else None


def _parse_number_of_rooms(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    # CommonFloor sometimes reports this as "4+" (4 or more BHK) instead of a plain number.
    match = re.match(r"(\d+)", str(value))
    return int(match.group(1)) if match else None


def _parse_furnishing(description: str) -> Optional[str]:
    text = description.lower()
    if "unfurnished" in text:
        return "Unfurnished"
    if "fully furnished" in text:
        return "Full"
    if "semi furnished" in text:
        return "Semi"
    return None


def _parse_parking(description: str) -> str:
    text = description.lower()
    if "parking is not available" in text or "no parking" in text:
        return "none"
    if "parking is available" in text:
        return "car"
    return "unknown"


def _parse_property_type(schema_types: list) -> str:
    for t in schema_types or []:
        if t in TYPE_MAP:
            return TYPE_MAP[t]
    return "unknown"


def _parse_latlon(geo: dict):
    lat, lon = geo.get("latitude"), geo.get("longitude")
    try:
        lat_f, lon_f = float(lat), float(lon)
    except (TypeError, ValueError):
        return None, None
    if lat_f == 0.0 and lon_f == 0.0:
        return None, None
    return lat_f, lon_f


class CommonFloorSource(ListingSource):
    name = "commonfloor"

    def fetch(self, config: dict) -> List[PropertyListing]:
        max_pages = config.get("commonfloor_max_pages", 5)
        seen_ids = set()
        listings: List[PropertyListing] = []

        for page in range(1, max_pages + 1):
            response = requests.get(SEARCH_URL, params={"page": page}, headers=HEADERS, timeout=20)
            response.raise_for_status()
            blocks = LD_JSON_RE.findall(response.text)
            if not blocks:
                break
            for block in blocks:
                listing = self._to_listing(block)
                if listing is None or listing.source_id in seen_ids:
                    continue
                seen_ids.add(listing.source_id)
                listings.append(listing)
        return listings

    def _to_listing(self, ld_json_block: str) -> Optional[PropertyListing]:
        try:
            raw = json.loads(ld_json_block)
        except json.JSONDecodeError:
            return None

        url_path = raw.get("URL", "")
        source_id = url_path.rstrip("/").rsplit("/", 1)[-1] or None
        title = raw.get("name", "")
        description = raw.get("description", "")
        address = raw.get("address") or {}
        offers = raw.get("offers") or {}
        lat, lon = _parse_latlon(raw.get("geo") or {})

        return PropertyListing(
            source=self.name,
            source_id=source_id,
            url=f"https://www.commonfloor.com{url_path}" if url_path.startswith("/") else url_path,
            title=title,
            locality=address.get("addressLocality", ""),
            address=address.get("streetAddress") or address.get("addressLocality", ""),
            latitude=lat,
            longitude=lon,
            rent=int(offers.get("price") or 0),
            deposit=None,
            maintenance=None,
            bhk=_parse_number_of_rooms(raw.get("numberOfRooms")),
            property_type=_parse_property_type(raw.get("@type")),
            age_years=_parse_age_years(description),
            parking=_parse_parking(description),
            furnishing=_parse_furnishing(description),
            bathrooms=_parse_bathrooms(description),
            description_raw=description or title,
            posting_date=None,
            image_url=raw.get("image"),
            non_veg_allowed=detect_veg_only(title, description),
        )
