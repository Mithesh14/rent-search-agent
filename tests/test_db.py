from rentsearch import db
from rentsearch.models import PropertyListing


def _listing(**overrides):
    defaults = dict(
        source="nobroker",
        source_id="123",
        url="https://example.com/1",
        title="2 BHK Flat",
        locality="Guindy",
        address="Guindy, Chennai",
        rent=20000,
        bhk=2,
        property_type="apartment",
        age_years=3,
        parking="car",
        description_raw="2 BHK Flat",
    )
    defaults.update(overrides)
    return PropertyListing(**defaults)


GEO_INFO = {"metro_distance_km": 1.2, "nearest_metro_station": "Guindy", "flood_notes": "note"}


def test_insert_then_unchanged(tmp_path):
    db_path = str(tmp_path / "rentals.db")
    db.init_db(db_path)
    listing = _listing()
    with db.connect(db_path) as conn:
        result1 = db.upsert_listing(conn, "id1", "dedupe1", listing, listing.description_hash(), GEO_INFO, "2026-01-01")
        result2 = db.upsert_listing(conn, "id1", "dedupe1", listing, listing.description_hash(), GEO_INFO, "2026-01-01")
    assert result1 == "inserted"
    assert result2 == "unchanged"


def test_update_on_description_change(tmp_path):
    db_path = str(tmp_path / "rentals.db")
    db.init_db(db_path)
    original = _listing()
    with db.connect(db_path) as conn:
        db.upsert_listing(conn, "id1", "dedupe1", original, original.description_hash(), GEO_INFO, "2026-01-01")
        changed = _listing(description_raw="Now with a pool", rent=21000)
        result = db.upsert_listing(conn, "id1", "dedupe1", changed, changed.description_hash(), GEO_INFO, "2026-01-01")
        row = db.get_listing(conn, "id1")
    assert result == "updated"
    assert row["rent"] == 21000
    assert row["status"] == "DISCOVERED"


def test_mark_rejected(tmp_path):
    db_path = str(tmp_path / "rentals.db")
    db.init_db(db_path)
    listing = _listing()
    with db.connect(db_path) as conn:
        db.upsert_listing(conn, "id1", "dedupe1", listing, listing.description_hash(), GEO_INFO, "2026-01-01")
        db.mark_rejected(conn, "id1", "filtered: rent-over-25000")
        row = db.get_listing(conn, "id1")
    assert row["status"] == "REJECTED"
    assert row["rejection_reason"] == "filtered: rent-over-25000"


def test_record_score_and_get_unscored(tmp_path):
    db_path = str(tmp_path / "rentals.db")
    db.init_db(db_path)
    listing = _listing()
    with db.connect(db_path) as conn:
        db.upsert_listing(conn, "id1", "dedupe1", listing, listing.description_hash(), GEO_INFO, "2026-01-01")
        unscored_before = db.get_unscored_discovered(conn)
        db.record_score(
            conn, "id1", 85, "SHORTLIST",
            {"metro_proximity": "PASS", "flood_risk": "PASS", "ambience": "PASS", "value_for_money": "PASS"},
            {"strong_points": "great", "concerns": "", "flood_context": "", "why_not_shortlist": ""},
            "2026-01-02",
        )
        unscored_after = db.get_unscored_discovered(conn)
        row = db.get_listing(conn, "id1")
    assert len(unscored_before) == 1
    assert len(unscored_after) == 0
    assert row["status"] == "REVIEWED"
    assert row["match_score"] == 85
    assert row["decision"] == "SHORTLIST"
