import base64
import json
from typing import List, Optional

import requests

from rentsearch.models import PropertyListing
from rentsearch.sources.base import ListingSource
from rentsearch.textsignals import detect_veg_only

SEARCH_URL = "https://www.nobroker.in/api/v3/multi/property/RENT/filter"
SITE_BASE_URL = "https://www.nobroker.in"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:105.0) Gecko/20100101 Firefox/105.0",
    "Accept": "application/json",
}

PARKING_MAP = {"NONE": "none", "TWO_WHEELER": "bike", "FOUR_WHEELER": "car", "BOTH": "both"}
BUILDING_TYPE_MAP = {"AP": "apartment", "IH": "individual_house"}


def _fix_image_url(raw_url: Optional[str]) -> Optional[str]:
    if not raw_url:
        return None
    return "https:" + raw_url if raw_url.startswith("//") else raw_url


def _parse_bhk(type_code: str) -> Optional[int]:
    if not type_code:
        return None
    if type_code.startswith("RK"):
        return 0  # room + kitchen studio — below 2BHK, not "unknown"
    if not type_code.startswith("BHK"):
        return None
    try:
        return int(type_code[3:])
    except ValueError:
        return None


class NoBrokerSource(ListingSource):
    name = "nobroker"

    def _search_param(self, area: dict) -> str:
        payload = [{"lat": area["lat"], "lon": area["lon"], "placeName": area["name"], "showMap": False}]
        return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")

    def fetch_area(self, area: dict, config: dict) -> List[PropertyListing]:
        rent_cfg = config.get("rent", {})
        min_rent = rent_cfg.get("min", 5000)
        max_rent = rent_cfg.get("max", 25000)
        building_types = ",".join(config.get("building_types", ["AP", "IH"]))
        max_pages = config.get("max_pages_per_area", 5)

        listings: List[PropertyListing] = []
        for page_no in range(1, max_pages + 1):
            params = {
                "pageNo": page_no,
                "searchParam": self._search_param(area),
                "sharedAccomodation": 0,
                "orderBy": "nbRank,desc",
                "radius": 2,
                "propertyType": "rent",
                "rent": f"{min_rent},{max_rent}",
                "buildingType": building_types,
                "city": "chennai",
            }
            response = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=15)
            response.raise_for_status()
            raw_items = response.json().get("data") or []
            if not raw_items:
                break
            listings.extend(self._to_listing(raw, area["name"]) for raw in raw_items)
        return listings

    def _to_listing(self, raw: dict, area_name: str) -> PropertyListing:
        return PropertyListing(
            source=self.name,
            source_id=str(raw.get("id")) if raw.get("id") else None,
            url=SITE_BASE_URL + raw.get("detailUrl", ""),
            title=raw.get("propertyTitle", ""),
            locality=raw.get("locality") or area_name,
            address=raw.get("address", ""),
            latitude=raw.get("latitude"),
            longitude=raw.get("longitude"),
            rent=raw.get("rent", 0),
            deposit=raw.get("deposit"),
            maintenance=raw.get("maintenanceAmount") or raw.get("maintenance"),
            bhk=_parse_bhk(raw.get("type", "")),
            property_type=BUILDING_TYPE_MAP.get(raw.get("buildingType"), "unknown"),
            age_years=raw.get("propertyAge"),
            parking=PARKING_MAP.get(raw.get("parking"), "unknown"),
            furnishing=raw.get("furnishingDesc"),
            bathrooms=raw.get("bathroom"),
            description_raw=raw.get("propertyTitle", ""),
            image_url=_fix_image_url(raw.get("originalImageUrl")),
            non_veg_allowed=detect_veg_only(raw.get("propertyTitle")),
        )

    def fetch(self, config: dict) -> List[PropertyListing]:
        listings: List[PropertyListing] = []
        for area in config.get("areas", []):
            listings.extend(self.fetch_area(area, config))
        return listings
