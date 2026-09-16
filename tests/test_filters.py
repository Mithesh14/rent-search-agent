from rentsearch.filters import check_filters
from rentsearch.models import PropertyListing


def _listing(**overrides):
    defaults = dict(
        source="nobroker",
        url="https://example.com/1",
        title="2 BHK Flat",
        locality="Guindy",
        address="Guindy, Chennai",
        rent=20000,
        bhk=2,
        property_type="apartment",
        age_years=3,
        parking="car",
    )
    defaults.update(overrides)
    return PropertyListing(**defaults)


def test_passes_when_everything_within_bounds():
    assert check_filters(_listing(), metro_distance_km=4.0) is None


def test_rejects_over_budget_rent():
    assert check_filters(_listing(rent=30000), metro_distance_km=4.0) == "filtered: rent-over-25000"


def test_rejects_under_2bhk():
    assert check_filters(_listing(bhk=1), metro_distance_km=4.0) == "filtered: bhk-under-2"


def test_unknown_bhk_passes_through():
    assert check_filters(_listing(bhk=None), metro_distance_km=4.0) is None


def test_rejects_disallowed_property_type():
    assert check_filters(_listing(property_type="pg"), metro_distance_km=4.0) == "filtered: property-type-not-allowed"


def test_unknown_property_type_passes_through():
    assert check_filters(_listing(property_type="unknown"), metro_distance_km=4.0) is None


def test_rejects_no_parking():
    assert check_filters(_listing(parking="none"), metro_distance_km=4.0) == "filtered: no-car-parking"


def test_rejects_bike_only_parking():
    assert check_filters(_listing(parking="bike"), metro_distance_km=4.0) == "filtered: no-car-parking"


def test_accepts_both_car_and_bike_parking():
    assert check_filters(_listing(parking="both"), metro_distance_km=4.0) is None


def test_unknown_parking_passes_through():
    assert check_filters(_listing(parking="unknown"), metro_distance_km=4.0) is None


def test_rejects_5_years_or_older():
    assert check_filters(_listing(age_years=5), metro_distance_km=4.0) == "filtered: age-5-plus"


def test_unknown_age_passes_through():
    assert check_filters(_listing(age_years=None), metro_distance_km=4.0) is None


def test_rejects_too_far_from_metro():
    assert check_filters(_listing(), metro_distance_km=7.0) == "filtered: metro-over-6.0km"


def test_unknown_metro_distance_passes_through():
    assert check_filters(_listing(), metro_distance_km=None) is None
