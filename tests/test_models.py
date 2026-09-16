from rentsearch.models import PropertyListing


def _listing(**overrides):
    defaults = dict(
        source="nobroker",
        url="https://www.nobroker.in/property/1",
        title="2 BHK Flat for Rent in Guindy",
        locality="Guindy",
        address="Some Street, Guindy, Chennai",
        rent=20000,
        description_raw="2 BHK Flat for Rent in Guindy",
    )
    defaults.update(overrides)
    return PropertyListing(**defaults)


def test_description_hash_is_stable_and_whitespace_insensitive():
    a = _listing(description_raw="2 BHK Flat  for Rent")
    b = _listing(description_raw="2 bhk flat for rent")
    assert a.description_hash() == b.description_hash()


def test_description_hash_changes_with_content():
    a = _listing(description_raw="2 BHK Flat for Rent")
    b = _listing(description_raw="3 BHK Flat for Rent")
    assert a.description_hash() != b.description_hash()


def test_description_fingerprint_truncates():
    long_text = "x" * 1000
    a = _listing(description_raw=long_text)
    b = _listing(description_raw="x" * 500)
    assert a.description_fingerprint(length=500) == b.description_fingerprint(length=500)
