import json
import re
from typing import List, Optional

import requests

from rentsearch.models import PropertyListing
from rentsearch.sources.base import ListingSource
from rentsearch.textsignals import detect_veg_only

BASE_URL = "https://www.squareyards.com/rent"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Accept": "text/html,application/xhtml+xml",
}

# SquareYards' generic "/rent/property-for-rent-in-chennai" page mixes residential listings
# with commercial ones (offices, coworking spaces, warehouses, shops) -- verified live, no
# clean way to tell them apart from a RentAction block alone. These category-scoped URLs
# (found in the site's own nav links) are residential-only, confirmed live.
CATEGORY_PATHS = ["2-bhk-for-rent-in-chennai", "3-bhk-for-rent-in-chennai", "independent-houses-for-rent-in-chennai"]

LD_JSON_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.DOTALL)
PROPERTY_TYPES = {"Apartment", "SingleFamilyResidence", "House"}
TYPE_MAP = {"Apartment": "apartment", "SingleFamilyResidence": "individual_house", "House": "individual_house"}

BHK_RE = re.compile(r"(\d+(?:\.\d+)?)\s*BHK", re.IGNORECASE)
BATHROOMS_RE = re.compile(r"(\d+)[\s-]*bathrooms?", re.IGNORECASE)
AGE_RE = re.compile(r"(\d+)\s*years?\s*old", re.IGNORECASE)


def _safe_leading_int(value) -> Optional[int]:
    # Structured numeric fields have been seen as e.g. "4+" (4 or more), not a plain number.
    match = re.match(r"(\d+)", str(value)) if value is not None else None
    return int(match.group(1)) if match else None


def _parse_bhk_from_text(text: str) -> Optional[int]:
    match = BHK_RE.search(text)
    return int(float(match.group(1))) if match else None


def _parse_bathrooms_from_text(text: str) -> Optional[int]:
    match = BATHROOMS_RE.search(text)
    return int(match.group(1)) if match else None


def _parse_furnishing(text: str) -> Optional[str]:
    lowered = text.lower()
    if "unfurnished" in lowered:
        return "Unfurnished"
    if "semi-furnished" in lowered or "semi furnished" in lowered:
        return "Semi"
    if "furnished" in lowered:
        return "Full"
    return None


def _parse_parking(text: str) -> str:
    lowered = text.lower()
    if "no parking" in lowered or "without parking" in lowered:
        return "none"
    if "parking" in lowered:
        return "car"
    return "unknown"


def _parse_property_type(text: str) -> str:
    lowered = text.lower()
    if "villa" in lowered or "independent house" in lowered or "house" in lowered:
        return "individual_house"
    if "apartment" in lowered or "flat" in lowered or "builder floor" in lowered:
        return "apartment"
    return "unknown"


class SquareYardsSource(ListingSource):
    name = "squareyards"

    def fetch(self, config: dict) -> List[PropertyListing]:
        seen_ids = set()
        listings: List[PropertyListing] = []

        for path in CATEGORY_PATHS:
            response = requests.get(f"{BASE_URL}/{path}", headers=HEADERS, timeout=20)
            response.raise_for_status()
            blocks = [self._parse_block(b) for b in LD_JSON_RE.findall(response.text)]
            blocks = [b for b in blocks if b is not None]

            properties_by_url = {b.get("url"): b for b in blocks if b.get("@type") in PROPERTY_TYPES}
            rent_actions = [b for b in blocks if b.get("@type") == "RentAction"]

            for action in rent_actions:
                listing = self._to_listing(action, properties_by_url.get(action.get("url")))
                if listing is None or listing.source_id in seen_ids:
                    continue
                seen_ids.add(listing.source_id)
                listings.append(listing)
        return listings

    def _parse_block(self, block: str) -> Optional[dict]:
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            return None

    def _to_listing(self, action: dict, matched_property: Optional[dict]) -> Optional[PropertyListing]:
        url = action.get("url", "")
        id_match = re.search(r"/(\d+)$", url)
        if not id_match:
            return None
        source_id = id_match.group(1)

        object_name = (action.get("object") or {}).get("name", "")
        action_description = action.get("description", "")
        property_description = (matched_property or {}).get("description", "")
        title = (matched_property or {}).get("name") or object_name
        combined_text = " ".join(filter(None, [title, object_name, action_description, property_description]))

        location_address = (action.get("location") or {}).get("address") or {}
        property_address = (matched_property or {}).get("address") or {}
        # SquareYards' `addressLocality` is always just "Chennai" (verified live) -- the real
        # sub-locality (e.g. "Ambattur") is in `streetAddress`; `name` is the building/society.
        locality = property_address.get("streetAddress") or location_address.get("streetAddress", "")
        building_name = location_address.get("name") or property_address.get("name")
        address = f"{building_name}, {locality}" if building_name else locality

        geo = (matched_property or {}).get("geo") or {}
        lat, lon = geo.get("latitude"), geo.get("longitude")

        bhk = None
        bathrooms = None
        property_type = "unknown"
        image_url = action.get("image")
        if matched_property:
            bhk = _safe_leading_int(matched_property.get("numberOfRooms"))
            bathrooms = _safe_leading_int(matched_property.get("numberOfBathroomsTotal"))
            property_type = TYPE_MAP.get(matched_property.get("@type"), "unknown")
            image_url = matched_property.get("image") or image_url
        if bhk is None:
            bhk = _parse_bhk_from_text(combined_text)
        if bathrooms is None:
            bathrooms = _parse_bathrooms_from_text(combined_text)
        if property_type == "unknown":
            property_type = _parse_property_type(combined_text)

        return PropertyListing(
            source=self.name,
            source_id=source_id,
            url=url,
            title=title,
            locality=locality,
            address=address,
            latitude=float(lat) if lat is not None else None,
            longitude=float(lon) if lon is not None else None,
            rent=int(action.get("price") or 0),
            deposit=None,
            maintenance=None,
            bhk=bhk,
            property_type=property_type,
            age_years=int(AGE_RE.search(combined_text).group(1)) if AGE_RE.search(combined_text) else None,
            parking=_parse_parking(combined_text),
            furnishing=_parse_furnishing(combined_text),
            bathrooms=bathrooms,
            description_raw=property_description or action_description or title,
            posting_date=action.get("startTime"),
            image_url=image_url,
            non_veg_allowed=detect_veg_only(combined_text),
        )
