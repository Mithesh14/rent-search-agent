from rentsearch.textsignals import detect_veg_only


def test_detects_only_vegetarian_phrase():
    assert detect_veg_only("Flat For Rent 2BHK Only Vegetarian Family-") is False


def test_detects_veg_only_variant():
    assert detect_veg_only("2bhk flat, veg only, near metro") is False


def test_detects_non_veg_not_allowed_phrase():
    assert detect_veg_only("Note: non-veg not allowed in this building") is False


def test_silent_listing_is_unknown():
    assert detect_veg_only("2 BHK Flat for Rent in Guindy") is None


def test_checks_multiple_text_fields():
    assert detect_veg_only("2BHK for rent", "Strictly vegetarian tenants preferred") is False


def test_ignores_none_texts():
    assert detect_veg_only(None, "2 BHK Flat") is None
