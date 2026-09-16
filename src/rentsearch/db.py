import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    listing_id TEXT PRIMARY KEY,
    dedupe_key TEXT UNIQUE NOT NULL,
    source TEXT NOT NULL,
    source_id TEXT,
    url TEXT,
    title TEXT,
    locality TEXT,
    address TEXT,
    latitude REAL,
    longitude REAL,
    rent INTEGER,
    deposit INTEGER,
    maintenance INTEGER,
    bhk INTEGER,
    property_type TEXT,
    age_years INTEGER,
    parking TEXT,
    furnishing TEXT,
    bathrooms INTEGER,
    posting_date TEXT,
    date_discovered TEXT NOT NULL,
    description_raw TEXT,
    description_hash TEXT,
    metro_distance_km REAL,
    nearest_metro_station TEXT,
    flood_notes TEXT,
    match_score INTEGER,
    decision TEXT,
    hard_constraints_json TEXT,
    reasoning_json TEXT,
    status TEXT NOT NULL DEFAULT 'DISCOVERED',
    rejection_reason TEXT,
    notes TEXT,
    last_analyzed_at TEXT
);
"""


@contextmanager
def connect(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as conn:
        conn.execute(SCHEMA)


def upsert_listing(conn, listing_id: str, dedupe_key: str, listing, description_hash: str, geo_info: dict, date_discovered: str) -> str:
    existing = conn.execute(
        "SELECT listing_id, description_hash FROM listings WHERE dedupe_key = ?", (dedupe_key,)
    ).fetchone()
    if existing is None:
        conn.execute(
            """INSERT INTO listings (
                listing_id, dedupe_key, source, source_id, url, title, locality, address,
                latitude, longitude, rent, deposit, maintenance, bhk, property_type, age_years,
                parking, furnishing, bathrooms, posting_date, date_discovered, description_raw,
                description_hash, metro_distance_km, nearest_metro_station, flood_notes, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DISCOVERED')""",
            (
                listing_id, dedupe_key, listing.source, listing.source_id, listing.url,
                listing.title, listing.locality, listing.address, listing.latitude,
                listing.longitude, listing.rent, listing.deposit, listing.maintenance,
                listing.bhk, listing.property_type, listing.age_years, listing.parking,
                listing.furnishing, listing.bathrooms, listing.posting_date, date_discovered,
                listing.description_raw, description_hash, geo_info.get("metro_distance_km"),
                geo_info.get("nearest_metro_station"), geo_info.get("flood_notes"),
            ),
        )
        return "inserted"
    if existing["description_hash"] != description_hash:
        conn.execute(
            """UPDATE listings SET description_raw = ?, description_hash = ?, rent = ?,
               metro_distance_km = ?, nearest_metro_station = ?, flood_notes = ?,
               match_score = NULL, decision = NULL, hard_constraints_json = NULL,
               reasoning_json = NULL, status = 'DISCOVERED', last_analyzed_at = NULL
               WHERE dedupe_key = ?""",
            (
                listing.description_raw, description_hash, listing.rent,
                geo_info.get("metro_distance_km"), geo_info.get("nearest_metro_station"),
                geo_info.get("flood_notes"), dedupe_key,
            ),
        )
        return "updated"
    return "unchanged"


def get_unscored_discovered(conn):
    return conn.execute(
        "SELECT * FROM listings WHERE status = 'DISCOVERED' AND match_score IS NULL"
    ).fetchall()


def mark_rejected(conn, listing_id: str, reason: str) -> None:
    conn.execute(
        "UPDATE listings SET status = 'REJECTED', rejection_reason = ? WHERE listing_id = ?",
        (reason, listing_id),
    )


def record_score(conn, listing_id: str, match_score: int, decision: str, hard_constraints: dict, reasoning: dict, analyzed_at: str) -> None:
    conn.execute(
        """UPDATE listings SET match_score = ?, decision = ?, hard_constraints_json = ?,
           reasoning_json = ?, status = 'REVIEWED', last_analyzed_at = ?
           WHERE listing_id = ?""",
        (match_score, decision, json.dumps(hard_constraints), json.dumps(reasoning), analyzed_at, listing_id),
    )


def get_listing(conn, listing_id: str):
    return conn.execute("SELECT * FROM listings WHERE listing_id = ?", (listing_id,)).fetchone()
