import json
from unittest.mock import patch

from rentsearch.sources.commonfloor import CommonFloorSource

FIXTURE_LD_JSON = {
    "@type": ["Product", "Apartment"],
    "name": "3 BHK Apartment for rent in Ashok Nagar, Chennai at Divya Villa Apartment",
    "URL": "/listing/3-bhk-apartment-for-rent-in-ashok-nagar-chennai/x8losin9s3pk9vf9",
    "image": "https://teja12.kuikr.com/is/p/c/sample.gif",
    "description": (
        "This 3 BHK, 921 sqft apartment is located in Ashok Nagar. It is a fully furnished "
        "property with 2 bathrooms and 2 balconies. It is on floor 5 of a 14 floor building. "
        "5 years old property. Reserved parking is available for residents. Pets are not allowed."
    ),
    "numberOfRooms": "3",
    "address": {"streetAddress": ", Ashok Nagar, Chennai", "addressLocality": "Ashok Nagar"},
    "geo": {"latitude": "13.0359275", "longitude": "80.2145697"},
    "offers": {"price": 40000, "priceCurrency": "INR"},
}


def _html_with_blocks(blocks):
    scripts = "".join(f"<script type='application/ld+json'>{json.dumps(b)}</script>" for b in blocks)
    return f"<html>{scripts}</html>"


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


def test_fetch_maps_fields_and_stops_on_empty_page():
    source = CommonFloorSource()
    responses = [FakeResponse(_html_with_blocks([FIXTURE_LD_JSON])), FakeResponse(_html_with_blocks([]))]
    with patch("rentsearch.sources.commonfloor.requests.get", side_effect=responses) as mock_get:
        listings = source.fetch({"commonfloor_max_pages": 5})

    assert len(listings) == 1
    listing = listings[0]
    assert listing.source == "commonfloor"
    assert listing.source_id == "x8losin9s3pk9vf9"
    assert listing.url == "https://www.commonfloor.com/listing/3-bhk-apartment-for-rent-in-ashok-nagar-chennai/x8losin9s3pk9vf9"
    assert listing.rent == 40000
    assert listing.bhk == 3
    assert listing.property_type == "apartment"
    assert listing.locality == "Ashok Nagar"
    assert listing.latitude == 13.0359275
    assert listing.longitude == 80.2145697
    assert listing.age_years == 5
    assert listing.bathrooms == 2
    assert listing.furnishing == "Full"
    assert listing.parking == "car"
    assert listing.image_url == "https://teja12.kuikr.com/is/p/c/sample.gif"
    assert mock_get.call_count == 2


def test_house_type_maps_to_individual_house():
    source = CommonFloorSource()
    item = {**FIXTURE_LD_JSON, "@type": ["Product", "House"]}
    with patch("rentsearch.sources.commonfloor.requests.get", return_value=FakeResponse(_html_with_blocks([item]))):
        listings = source.fetch({"commonfloor_max_pages": 1})
    assert listings[0].property_type == "individual_house"


def test_placeholder_geo_becomes_none():
    source = CommonFloorSource()
    item = {**FIXTURE_LD_JSON, "geo": {"latitude": "0.0", "longitude": "0.0"}}
    with patch("rentsearch.sources.commonfloor.requests.get", return_value=FakeResponse(_html_with_blocks([item]))):
        listings = source.fetch({"commonfloor_max_pages": 1})
    assert listings[0].latitude is None
    assert listings[0].longitude is None


def test_unfurnished_and_no_parking_parsed():
    source = CommonFloorSource()
    item = {
        **FIXTURE_LD_JSON,
        "description": "This 2 BHK is unfurnished with 1 bathroom. Parking is not available.",
    }
    with patch("rentsearch.sources.commonfloor.requests.get", return_value=FakeResponse(_html_with_blocks([item]))):
        listings = source.fetch({"commonfloor_max_pages": 1})
    assert listings[0].furnishing == "Unfurnished"
    assert listings[0].parking == "none"


def test_veg_only_description_detected():
    source = CommonFloorSource()
    item = {**FIXTURE_LD_JSON, "description": "Strictly vegetarian tenants preferred only."}
    with patch("rentsearch.sources.commonfloor.requests.get", return_value=FakeResponse(_html_with_blocks([item]))):
        listings = source.fetch({"commonfloor_max_pages": 1})
    assert listings[0].non_veg_allowed is False


def test_dedupes_within_run():
    source = CommonFloorSource()
    responses = [
        FakeResponse(_html_with_blocks([FIXTURE_LD_JSON])),
        FakeResponse(_html_with_blocks([FIXTURE_LD_JSON])),
        FakeResponse(_html_with_blocks([])),
    ]
    with patch("rentsearch.sources.commonfloor.requests.get", side_effect=responses):
        listings = source.fetch({"commonfloor_max_pages": 5})
    assert len(listings) == 1


def test_missing_bhk_field_is_none():
    source = CommonFloorSource()
    item = {**FIXTURE_LD_JSON, "numberOfRooms": None}
    del item["numberOfRooms"]
    with patch("rentsearch.sources.commonfloor.requests.get", return_value=FakeResponse(_html_with_blocks([item]))):
        listings = source.fetch({"commonfloor_max_pages": 1})
    assert listings[0].bhk is None
