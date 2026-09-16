import json
from unittest.mock import patch

from rentsearch.sources.magicbricks import MagicBricksSource

FIXTURE_ITEM = {
    "id": 86328445,
    "url": "2-BHK-990-Sq-ft-Multistorey-Apartment-FOR-Rent-Guindy-in-Chennai&id=4d423836333238343435",
    "propertyTitle": "2 BHK Flat for Rent In Guindy",
    "price": 18000,
    "parkingD": "1 Covered",
    "propTypeD": "Apartment",
    "furnishedD": "Semi-Furnished",
    "bathD": 2,
    "ltcoordGeo": "13.0092746,80.2130846",
    "dtldesc": "2bhk semi furnished flat for rent near main road",
    "postDateT": "2026-09-05T11:22:43.000Z",
    "allImgPath": ["https://img.staticmb.com/mbphoto/sample.jpg"],
    "landmark": "close to Guindy metro",
}


def _fixture_html(items):
    state = json.dumps({"searchResult": items})
    return f"<html><script>window.SERVER_PRELOADED_STATE_ = {state};</script></html>"


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


def test_fetch_maps_fields_and_stops_on_empty_page():
    source = MagicBricksSource()
    config = {"rent": {"min": 8000, "max": 25000}, "magicbricks_max_pages": 5}

    responses = [FakeResponse(_fixture_html([FIXTURE_ITEM])), FakeResponse(_fixture_html([]))]
    with patch("rentsearch.sources.magicbricks.requests.get", side_effect=responses) as mock_get:
        listings = source.fetch(config)

    assert len(listings) == 1
    listing = listings[0]
    assert listing.source == "magicbricks"
    assert listing.source_id == "86328445"
    assert listing.rent == 18000
    assert listing.bhk == 2
    assert listing.property_type == "apartment"
    assert listing.parking == "car"
    assert listing.furnishing == "Semi-Furnished"
    assert listing.bathrooms == 2
    assert listing.locality == "Guindy"
    assert listing.latitude == 13.0092746
    assert listing.longitude == 80.2130846
    assert listing.image_url == "https://img.staticmb.com/mbphoto/sample.jpg"
    assert listing.url == "https://www.magicbricks.com/2-BHK-990-Sq-ft-Multistorey-Apartment-FOR-Rent-Guindy-in-Chennai?id=4d423836333238343435"
    assert mock_get.call_count == 2


def test_no_parking_maps_to_none():
    source = MagicBricksSource()
    item = {**FIXTURE_ITEM, "parkingD": "No Parking"}
    config = {"rent": {"min": 8000, "max": 25000}, "magicbricks_max_pages": 1}
    with patch("rentsearch.sources.magicbricks.requests.get", return_value=FakeResponse(_fixture_html([item]))):
        listings = source.fetch(config)
    assert listings[0].parking == "none"


def test_veg_only_description_detected():
    source = MagicBricksSource()
    item = {**FIXTURE_ITEM, "dtldesc": "Strictly vegetarian tenants only"}
    config = {"rent": {"min": 8000, "max": 25000}, "magicbricks_max_pages": 1}
    with patch("rentsearch.sources.magicbricks.requests.get", return_value=FakeResponse(_fixture_html([item]))):
        listings = source.fetch(config)
    assert listings[0].non_veg_allowed is False
