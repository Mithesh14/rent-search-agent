from typing import Optional

from rentsearch.models import PropertyListing

MAX_RENT = 25000
MIN_BHK = 2
MAX_AGE_YEARS = 5
ALLOWED_PROPERTY_TYPES = {"apartment", "individual_house"}
# Car parking is compulsory (not "any parking") — bike-only doesn't satisfy the requirement.
CAR_CAPABLE_PARKING = {"car", "both"}
# Generous ceiling for the pre-filter — the user's actual "3 to 5 km" preference is judged
# precisely by Claude during scoring, using the exact stored distance. This just drops
# listings that are unambiguously too far, tolerant of GPS/locality-centroid imprecision.
MAX_METRO_DISTANCE_KM = 6.0


def check_filters(listing: PropertyListing, metro_distance_km: Optional[float]) -> Optional[str]:
    if listing.rent and listing.rent > MAX_RENT:
        return f"filtered: rent-over-{MAX_RENT}"
    if listing.bhk is not None and listing.bhk < MIN_BHK:
        return "filtered: bhk-under-2"
    if listing.property_type != "unknown" and listing.property_type not in ALLOWED_PROPERTY_TYPES:
        return "filtered: property-type-not-allowed"
    if listing.parking not in CAR_CAPABLE_PARKING and listing.parking != "unknown":
        return "filtered: no-car-parking"
    if listing.age_years is not None and listing.age_years >= MAX_AGE_YEARS:
        return "filtered: age-5-plus"
    if metro_distance_km is not None and metro_distance_km > MAX_METRO_DISTANCE_KM:
        return f"filtered: metro-over-{MAX_METRO_DISTANCE_KM}km"
    return None
