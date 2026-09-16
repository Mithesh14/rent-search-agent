from rentsearch.dedupe import compute_dedupe_key, compute_listing_id
from rentsearch.models import PropertyListing


def _listing(**overrides):
    defaults = dict(
        source="nobroker",
        source_id=None,
        url="",
        title="2 BHK Flat for Rent in Guindy",
        locality="Guindy",
        address="Some Street, Guindy, Chennai",
        rent=20000,
        bhk=2,
        description_raw="2 BHK Flat for Rent in Guindy",
    )
    defaults.update(overrides)
    return PropertyListing(**defaults)


def test_prefers_source_id():
    listing = _listing(source_id="abc123", url="https://example.com/x")
    assert compute_dedupe_key(listing) == "nobroker:abc123"


def test_falls_back_to_url_when_no_source_id():
    listing = _listing(source_id=None, url="https://example.com/x")
    assert compute_dedupe_key(listing) == "url:https://example.com/x"


def test_falls_back_to_fingerprint_when_no_id_or_url():
    listing = _listing(source_id=None, url="")
    key = compute_dedupe_key(listing)
    assert key.startswith("fallback:")


def test_same_fallback_inputs_produce_same_key():
    a = _listing(source_id=None, url="")
    b = _listing(source_id=None, url="")
    assert compute_dedupe_key(a) == compute_dedupe_key(b)


def test_listing_id_is_short_and_stable():
    key = "url:https://example.com/x"
    assert compute_listing_id(key) == compute_listing_id(key)
    assert len(compute_listing_id(key)) == 16
