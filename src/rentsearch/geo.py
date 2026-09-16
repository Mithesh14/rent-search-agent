import math
from typing import Dict, List, Optional, Tuple

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def nearest_metro_station(lat: float, lon: float, stations: List[Dict]) -> Optional[Tuple[Dict, float]]:
    if not stations:
        return None
    best = min(stations, key=lambda s: haversine_km(lat, lon, s["lat"], s["lon"]))
    return best, haversine_km(lat, lon, best["lat"], best["lon"])


def find_area(text: str, areas: List[Dict]) -> Optional[Dict]:
    if not text:
        return None
    haystack = text.lower()
    for area in areas:
        if area["name"].lower() in haystack:
            return area
    return None
