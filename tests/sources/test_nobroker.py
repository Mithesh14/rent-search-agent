from unittest.mock import patch

from rentsearch.sources.nobroker import NoBrokerSource

FIXTURE_ITEM = {
    "id": "abc123",
    "type": "BHK2",
    "rent": 18000,
    "deposit": 60000,
    "maintenanceAmount": "1,500",
    "propertyAge": 3,
    "parking": "FOUR_WHEELER",
    "bathroom": 2,
    "locality": "Guindy",
    "address": "Independent House, Some Street, Guindy, chennai",
    "latitude": 13.0086685,
    "longitude": 80.2126063,
    "buildingType": "AP",
    "detailUrl": "/property/2-bhk-apartment-for-rent-in-guindy-chennai-for-rs-18000/abc123/detail",
    "propertyTitle": "2 BHK Flat for Rent In Guindy",
    "furnishingDesc": "Semi",
    "thumbnailImage": "//assets.nobroker.in/images/abc123/abc123_medium.jpg",
}


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_fetch_area_maps_fields_and_stops_on_empty_page():
    source = NoBrokerSource()
    area = {"name": "Guindy", "lat": 13.0086685, "lon": 80.2126063}
    config = {"rent": {"min": 8000, "max": 25000}, "building_types": ["AP", "IH"], "max_pages_per_area": 5}

    responses = [FakeResponse({"data": [FIXTURE_ITEM]}), FakeResponse({"data": []})]
    with patch("rentsearch.sources.nobroker.requests.get", side_effect=responses) as mock_get:
        listings = source.fetch_area(area, config)

    assert len(listings) == 1
    listing = listings[0]
    assert listing.source == "nobroker"
    assert listing.source_id == "abc123"
    assert listing.url == "https://www.nobroker.in/property/2-bhk-apartment-for-rent-in-guindy-chennai-for-rs-18000/abc123/detail"
    assert listing.bhk == 2
    assert listing.rent == 18000
    assert listing.property_type == "apartment"
    assert listing.parking == "car"
    assert listing.age_years == 3
    assert listing.locality == "Guindy"
    assert listing.image_url == "https://assets.nobroker.in/images/abc123/abc123_medium.jpg"
    assert listing.non_veg_allowed is None
    assert mock_get.call_count == 2


def test_veg_only_title_detected():
    source = NoBrokerSource()
    area = {"name": "Guindy", "lat": 13.0086685, "lon": 80.2126063}
    config = {"rent": {"min": 8000, "max": 25000}, "building_types": ["AP", "IH"], "max_pages_per_area": 1}
    veg_item = {**FIXTURE_ITEM, "propertyTitle": "2 BHK Flat Only Vegetarian Family"}

    with patch("rentsearch.sources.nobroker.requests.get", return_value=FakeResponse({"data": [veg_item]})):
        listings = source.fetch_area(area, config)

    assert listings[0].non_veg_allowed is False


def test_rk_studio_maps_to_bhk_zero_not_unknown():
    source = NoBrokerSource()
    area = {"name": "Adyar", "lat": 13.00645, "lon": 80.2577791}
    config = {"rent": {"min": 8000, "max": 25000}, "building_types": ["AP", "IH"], "max_pages_per_area": 1}
    rk_item = {**FIXTURE_ITEM, "type": "RK1"}

    with patch("rentsearch.sources.nobroker.requests.get", return_value=FakeResponse({"data": [rk_item]})):
        listings = source.fetch_area(area, config)

    assert listings[0].bhk == 0


def test_fetch_loops_all_configured_areas():
    source = NoBrokerSource()
    config = {
        "rent": {"min": 8000, "max": 25000},
        "building_types": ["AP", "IH"],
        "max_pages_per_area": 1,
        "areas": [
            {"name": "Guindy", "lat": 13.0086685, "lon": 80.2126063},
            {"name": "Adyar", "lat": 13.00645, "lon": 80.2577791},
        ],
    }
    with patch("rentsearch.sources.nobroker.requests.get", return_value=FakeResponse({"data": [FIXTURE_ITEM]})) as mock_get:
        listings = source.fetch(config)
    assert len(listings) == 2
    assert mock_get.call_count == 2
