import json
from unittest.mock import patch

from rentsearch.sources.squareyards import SquareYardsSource

RENT_ACTION = {
    "@type": "RentAction",
    "startTime": "2026-09-14T18:30:00.000",
    "object": {"@type": "residence", "name": "3 BHK Villa for Rent in Oragadam, Chennai"},
    "priceCurrency": "INR",
    "location": {"address": {"addressLocality": "Chennai", "streetAddress": "Oragadam", "name": "Hiranandani Parks Villa Plot"}},
    "price": "120000",
    "description": "A spacious 3-bedroom, 3-bathroom unfurnished villa is available for rent, reserved car parking included.",
    "url": "https://www.squareyards.com/rental-3-bhk-villa-in-hiranandani-parks/10419047",
    "image": "https://img.squareyards.com/rentaction.jpg",
}

APARTMENT_PROPERTY = {
    "@type": "Apartment",
    "address": {"addressCountry": "India", "streetAddress": "Egmore", "addressLocality": "Chennai"},
    "geo": {"@type": "GeoCoordinates", "latitude": 13.073668, "longitude": 80.25822},
    "name": "4 BHK Flat for Rent in Egmore, Chennai",
    "description": "Fully furnished 4 BHK apartment with car parking.",
    "numberOfRooms": "4",
    "numberOfBathroomsTotal": "5",
    "url": "https://www.squareyards.com/rental-4-bhk-apartment-in-egmore/10386170",
    "image": "https://img.squareyards.com/apartment.jpg",
}

MATCHED_RENT_ACTION = {
    **RENT_ACTION,
    "url": APARTMENT_PROPERTY["url"],
    "object": {"@type": "residence", "name": "4 BHK Flat for Rent in Egmore, Chennai"},
    "price": "40000",
}


def _html(blocks):
    scripts = "".join(f'<script type="application/ld+json">{json.dumps(b)}</script>' for b in blocks)
    return f"<html>{scripts}</html>"


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


def test_rent_action_only_listing_uses_text_parsing():
    source = SquareYardsSource()
    with patch("rentsearch.sources.squareyards.requests.get", return_value=FakeResponse(_html([RENT_ACTION]))):
        listings = source.fetch({})

    assert len(listings) == 1  # same fixture returned for all 3 category paths, deduped by id
    listing = listings[0]
    assert listing.source == "squareyards"
    assert listing.source_id == "10419047"
    assert listing.rent == 120000
    assert listing.bhk == 3
    assert listing.bathrooms == 3
    assert listing.property_type == "individual_house"
    assert listing.furnishing == "Unfurnished"
    assert listing.parking == "car"
    assert listing.locality == "Oragadam"
    assert listing.latitude is None
    assert "iid" not in listing.url


def test_matched_property_enriches_fields():
    source = SquareYardsSource()
    with patch(
        "rentsearch.sources.squareyards.requests.get",
        return_value=FakeResponse(_html([APARTMENT_PROPERTY, MATCHED_RENT_ACTION])),
    ):
        listings = source.fetch({})

    listing = listings[0]
    assert listing.source_id == "10386170"
    assert listing.rent == 40000
    assert listing.bhk == 4
    assert listing.bathrooms == 5
    assert listing.property_type == "apartment"
    assert listing.latitude == 13.073668
    assert listing.longitude == 80.25822
    assert listing.locality == "Egmore"
    assert listing.image_url == "https://img.squareyards.com/apartment.jpg"


def test_dedupes_across_category_paths():
    source = SquareYardsSource()
    with patch("rentsearch.sources.squareyards.requests.get", return_value=FakeResponse(_html([RENT_ACTION]))) as mock_get:
        listings = source.fetch({})
    assert mock_get.call_count == 3
    ids = [l.source_id for l in listings]
    assert len(ids) == len(set(ids))


def test_veg_only_detected():
    source = SquareYardsSource()
    item = {**RENT_ACTION, "description": "Only vegetarian family preferred. " + RENT_ACTION["description"]}
    with patch("rentsearch.sources.squareyards.requests.get", return_value=FakeResponse(_html([item]))):
        listings = source.fetch({})
    assert listings[0].non_veg_allowed is False


def test_block_without_trailing_id_is_skipped():
    source = SquareYardsSource()
    item = {**RENT_ACTION, "url": "https://www.squareyards.com/no-id-here"}
    with patch("rentsearch.sources.squareyards.requests.get", return_value=FakeResponse(_html([item]))):
        listings = source.fetch({})
    assert listings == []


def test_malformed_json_block_is_skipped():
    source = SquareYardsSource()
    html = '<html><script type="application/ld+json">{not valid json</script></html>'
    with patch("rentsearch.sources.squareyards.requests.get", return_value=FakeResponse(html)):
        listings = source.fetch({})
    assert listings == []
