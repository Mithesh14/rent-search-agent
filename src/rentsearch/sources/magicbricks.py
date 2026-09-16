import json
import re
from typing import List, Optional

import requests

from rentsearch.models import PropertyListing
from rentsearch.sources.base import ListingSource
from rentsearch.textsignals import detect_veg_only

SEARCH_URL = "https://www.magicbricks.com/property-for-rent/residential-real-estate"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Accept": "text/html,application/xhtml+xml",
}

PROPERTY_TYPE_MAP = {"apartment": "apartment", "independent house": "individual_house", "villa": "individual_house"}
LOCALITY_FROM_URL_RE = re.compile(r"-FOR-Rent-(.+?)-in-Chennai", re.IGNORECASE)


def _extract_preloaded_state(html: str) -> dict:
    marker = "window.SERVER_PRELOADED_STATE_"
    start = html.index(marker)
    start = html.index("{", start)
    depth = 0
    end = None
    for i in range(start, len(html)):
        char = html[i]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    return json.loads(html[start:end])


def _parse_bhk(raw: dict) -> Optional[int]:
    match = re.match(r"(\d+)\s*-?\s*BHK", raw.get("url", ""), re.IGNORECASE) or re.search(r"(\d+)\s*BHK", raw.get("propertyTitle", ""), re.IGNORECASE)
    return int(match.group(1)) if match else None


def _parse_locality(raw: dict) -> str:
    match = LOCALITY_FROM_URL_RE.search(raw.get("url", ""))
    return match.group(1).replace("-", " ") if match else ""


def _parse_latlon(raw: dict):
    coord = raw.get("ltcoordGeo")
    if not coord or "," not in coord:
        return None, None
    try:
        lat_str, lon_str = coord.split(",", 1)
        return float(lat_str), float(lon_str)
    except ValueError:
        return None, None


def _parse_parking(parking_desc: Optional[str]) -> str:
    text = (parking_desc or "").lower()
    if not text or "no parking" in text:
        return "none" if text else "unknown"
    if "covered" in text or "open" in text:
        return "car"
    return "unknown"


class MagicBricksSource(ListingSource):
    name = "magicbricks"

    def fetch(self, config: dict) -> List[PropertyListing]:
        rent_cfg = config.get("rent", {})
        min_rent = rent_cfg.get("min", 5000)
        max_rent = rent_cfg.get("max", 25000)
        max_pages = config.get("magicbricks_max_pages", 5)

        listings: List[PropertyListing] = []
        for page in range(1, max_pages + 1):
            params = {"bedroom": "2", "cityName": "Chennai", "page": page, "budgetMax": max_rent, "budgetMin": min_rent}
            response = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=20)
            response.raise_for_status()
            state = _extract_preloaded_state(response.text)
            raw_items = state.get("searchResult") or []
            if not raw_items:
                break
            listings.extend(self._to_listing(raw) for raw in raw_items)
        return listings

    def _to_listing(self, raw: dict) -> PropertyListing:
        lat, lon = _parse_latlon(raw)
        title = raw.get("propertyTitle", "")
        description = raw.get("dtldesc") or raw.get("seoDesc") or ""
        url_id = raw.get("url", "").rsplit("&id=", 1)
        detail_url = f"https://www.magicbricks.com/{url_id[0]}?id={url_id[1]}" if len(url_id) == 2 else "https://www.magicbricks.com/"

        return PropertyListing(
            source=self.name,
            source_id=str(raw.get("id")) if raw.get("id") else None,
            url=detail_url,
            title=title,
            locality=_parse_locality(raw),
            address=raw.get("landmark") or _parse_locality(raw),
            latitude=lat,
            longitude=lon,
            rent=raw.get("price") or 0,
            deposit=None,
            maintenance=raw.get("maintenanceCharges"),
            bhk=_parse_bhk(raw),
            property_type=PROPERTY_TYPE_MAP.get((raw.get("propTypeD") or "").lower(), "unknown"),
            age_years=None,
            parking=_parse_parking(raw.get("parkingD")),
            furnishing=raw.get("furnishedD"),
            bathrooms=raw.get("bathD"),
            description_raw=description or title,
            posting_date=raw.get("postDateT"),
            image_url=(raw.get("allImgPath") or [None])[0],
            non_veg_allowed=detect_veg_only(title, description),
        )
