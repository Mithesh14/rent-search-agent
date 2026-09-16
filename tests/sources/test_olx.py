import json

from rentsearch.sources.olx import OlxSource

FIXTURE_STAGED = [
    {
        "id": "999",
        "title": "2BHK for rent in Adyar",
        "url": "https://www.olx.in/item/2bhk-for-rent-in-adyar-iid-999",
        "location": "Adyar, Chennai",
        "raw_price": 22000,
        "description": "Spacious 2BHK, car parking available, semi-furnished.",
        "created_at": "2026-09-01T00:00:00Z",
        "bhk": 2,
        "property_type": "apartment",
        "parking": "car",
        "age_years": 4,
    }
]


def test_fetch_returns_empty_when_staging_file_missing(tmp_path):
    source = OlxSource()
    missing_path = str(tmp_path / "does_not_exist.json")
    assert source.fetch({}, staging_path=missing_path) == []


def test_fetch_maps_staged_fields(tmp_path):
    staging_path = tmp_path / "olx_staging.json"
    staging_path.write_text(json.dumps(FIXTURE_STAGED))

    source = OlxSource()
    listings = source.fetch({}, staging_path=str(staging_path))

    assert len(listings) == 1
    listing = listings[0]
    assert listing.source == "olx"
    assert listing.source_id == "999"
    assert listing.rent == 22000
    assert listing.bhk == 2
    assert listing.property_type == "apartment"
    assert listing.parking == "car"
    assert listing.age_years == 4
    assert "Adyar" in listing.address
