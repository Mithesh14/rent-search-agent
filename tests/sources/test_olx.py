from unittest.mock import patch

from rentsearch.sources.olx import GENERIC_QUERIES, OlxSource

FIXTURE_ITEM = {
    "id": 1855622038,
    "title": "2 bhk flat for Rent in Guindy",
    "description": "2 bhk in 2nd floor, bike parking available",
    "created_at": "2026-09-14T13:13:18+05:30",
    "price": {"value": {"raw": 17000.0}},
    "locations_resolved": {"SUBLOCALITY_LEVEL_1_name": "Guindy", "ADMIN_LEVEL_3_name": "Chennai"},
    "images": [{"url": "https://apollo.olx.in:443/v1/files/5qaitert527u2-IN/image"}],
    "parameters": [
        {"key": "type", "value": "rent-apartments", "value_name": "Flats / Apartments"},
        {"key": "rooms", "value": "2", "value_name": "2"},
        {"key": "bathrooms", "value": "1", "value_name": "1"},
        {"key": "furnished", "value": "semi", "value_name": "Semi-Furnished"},
        {"key": "maintenance", "value": "750", "value_name": "750"},
        {"key": "carparking", "value": "0", "value_name": "0"},
    ],
}


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_fetch_maps_fields():
    source = OlxSource()
    config = {"rent": {"min": 8000, "max": 25000}}
    with patch("rentsearch.sources.olx.curl_requests.get", return_value=FakeResponse({"data": [FIXTURE_ITEM]})) as mock_get:
        listings = source.fetch(config)

    assert len(listings) == 1
    listing = listings[0]
    assert listing.source == "olx"
    assert listing.source_id == "1855622038"
    assert listing.rent == 17000
    assert listing.bhk == 2
    assert listing.bathrooms == 1
    assert listing.furnishing == "Semi-Furnished"
    assert listing.maintenance == 750
    assert listing.parking == "none"
    assert listing.property_type == "apartment"
    assert listing.locality == "Guindy"
    assert listing.image_url == "https://apollo.olx.in:443/v1/files/5qaitert527u2-IN/image"
    assert "iid-1855622038" in listing.url
    # one call per generic query, not per area (OLX's search does near-literal phrase
    # matching, so an area name in the query text returns zero results -- see olx.py)
    assert mock_get.call_count == len(GENERIC_QUERIES)


def test_car_parking_count_maps_to_car():
    source = OlxSource()
    item = {**FIXTURE_ITEM, "parameters": [{"key": "carparking", "value": "1", "value_name": "1"}]}
    config = {"rent": {"min": 8000, "max": 25000}}
    with patch("rentsearch.sources.olx.curl_requests.get", return_value=FakeResponse({"data": [item]})):
        listings = source.fetch(config)
    assert listings[0].parking == "car"


def test_veg_only_title_detected():
    source = OlxSource()
    item = {**FIXTURE_ITEM, "title": "Flat For Rent 2BHK Only Vegetarian Family-"}
    config = {"rent": {"min": 8000, "max": 25000}}
    with patch("rentsearch.sources.olx.curl_requests.get", return_value=FakeResponse({"data": [item]})):
        listings = source.fetch(config)
    assert listings[0].non_veg_allowed is False


def test_rent_outside_range_is_excluded():
    source = OlxSource()
    item = {**FIXTURE_ITEM, "price": {"value": {"raw": 50000.0}}}
    config = {"rent": {"min": 8000, "max": 25000}}
    with patch("rentsearch.sources.olx.curl_requests.get", return_value=FakeResponse({"data": [item]})):
        listings = source.fetch(config)
    assert listings == []


def test_dedupes_across_generic_queries():
    source = OlxSource()
    config = {"rent": {"min": 8000, "max": 25000}}
    with patch("rentsearch.sources.olx.curl_requests.get", return_value=FakeResponse({"data": [FIXTURE_ITEM]})):
        listings = source.fetch(config)
    assert len(listings) == 1
