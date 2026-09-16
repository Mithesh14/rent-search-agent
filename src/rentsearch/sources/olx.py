from typing import List, Optional

from curl_cffi import requests as curl_requests

from rentsearch.models import PropertyListing
from rentsearch.sources.base import ListingSource
from rentsearch.textsignals import detect_veg_only

# OLX fingerprints the TLS handshake and blocks plain `requests`/curl clients outright
# (verified: even a full browser User-Agent gets the connection reset). curl_cffi
# impersonates a real Chrome TLS signature, which reliably gets through. Its search API
# (undocumented, reverse-engineered from the page's own hydration data) returns clean JSON --
# no HTML scraping or JS evaluation needed.
SEARCH_URL = "https://www.olx.in/api/relevance/v4/search"
CHENNAI_LOCATION_ID = 4059162
RENT_CATEGORY_ID = 1723  # "For Rent: Houses & Apartments"
# OLX's search does near-literal phrase matching, not free-text relevance -- adding an area
# name to the query (e.g. "... in Guindy") returns zero results almost every time, because
# most ad titles don't contain that exact phrase. So we run a few generic queries city-wide
# instead of one per area, and tag locality afterwards (like the other sources) rather than
# trying to scope the query text itself.
GENERIC_QUERIES = ["2 bhk flat for rent", "2 bhk house for rent", "2bhk for rent"]

PROPERTY_TYPE_MAP = {
    "rent-apartments": "apartment",
    "rent-flats": "apartment",
    "rent-houses": "individual_house",
    "rent-independent-house": "individual_house",
}


def _param_value(parameters: list, key: str) -> Optional[str]:
    for param in parameters or []:
        if param.get("key") == key:
            return param.get("value_name") or param.get("value")
    return None


def _param_code(parameters: list, key: str) -> Optional[str]:
    for param in parameters or []:
        if param.get("key") == key:
            return param.get("value")
    return None


def _parse_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


class OlxSource(ListingSource):
    name = "olx"

    def _fetch_query(self, query: str) -> List[dict]:
        # OLX's public search API doesn't honor offset/page params for anonymous requests
        # (verified: identical results regardless) -- one request per query is all we get.
        params = {
            "facet_limit": 1000,
            "location": CHENNAI_LOCATION_ID,
            "category": RENT_CATEGORY_ID,
            "location_facet_limit": 40,
            "platform": "web-desktop",
            "pttenabled": "true",
            "query": query,
            "relaxedfilters": "true",
            "size": 40,
            "spellcheck": "true",
            "user": "anonymous",
        }
        response = curl_requests.get(SEARCH_URL, params=params, impersonate="chrome124", timeout=20)
        response.raise_for_status()
        return response.json().get("data") or []

    def fetch(self, config: dict) -> List[PropertyListing]:
        rent_cfg = config.get("rent", {})
        min_rent = rent_cfg.get("min", 5000)
        max_rent = rent_cfg.get("max", 25000)

        seen_ids = set()
        listings: List[PropertyListing] = []
        for query in GENERIC_QUERIES:
            for raw in self._fetch_query(query):
                if raw.get("id") in seen_ids:
                    continue
                seen_ids.add(raw.get("id"))
                listing = self._to_listing(raw)
                if listing.rent and not (min_rent <= listing.rent <= max_rent):
                    continue
                listings.append(listing)
        return listings

    def _to_listing(self, raw: dict) -> PropertyListing:
        parameters = raw.get("parameters") or []
        locations_resolved = raw.get("locations_resolved") or {}
        locality = locations_resolved.get("SUBLOCALITY_LEVEL_1_name") or locations_resolved.get("ADMIN_LEVEL_3_name", "")
        images = raw.get("images") or []
        title = raw.get("title", "")
        description = raw.get("description", "")

        parking_count = _parse_int(_param_value(parameters, "carparking"))
        parking = "unknown"
        if parking_count is not None:
            parking = "car" if parking_count >= 1 else "none"

        return PropertyListing(
            source=self.name,
            source_id=str(raw.get("id")) if raw.get("id") else None,
            url=self._detail_url(raw),
            title=title,
            locality=locality,
            address=locality,
            latitude=None,
            longitude=None,
            rent=_parse_int((raw.get("price") or {}).get("value", {}).get("raw")) or 0,
            deposit=None,
            maintenance=_parse_int(_param_value(parameters, "maintenance")),
            bhk=_parse_int(_param_value(parameters, "rooms")),
            property_type=PROPERTY_TYPE_MAP.get(_param_code(parameters, "type"), "unknown"),
            age_years=None,
            parking=parking,
            furnishing=_param_value(parameters, "furnished"),
            bathrooms=_parse_int(_param_value(parameters, "bathrooms")),
            description_raw=description or title,
            posting_date=raw.get("created_at"),
            image_url=images[0].get("url") if images else None,
            non_veg_allowed=detect_veg_only(title, description),
        )

    def _detail_url(self, raw: dict) -> str:
        slug = "".join(c if c.isalnum() else "-" for c in raw.get("title", "").lower())
        slug = "-".join(filter(None, slug.split("-")))
        return f"https://www.olx.in/item/{slug}-iid-{raw.get('id')}"
