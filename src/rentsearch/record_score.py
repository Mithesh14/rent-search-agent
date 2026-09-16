import argparse
import json
from datetime import datetime, timezone

from rentsearch import db

DB_PATH = "data/rentals.db"
VALID_DECISIONS = {"SHORTLIST", "CONSIDER", "SKIP"}
VALID_CONSTRAINT_VALUES = {"PASS", "FAIL", "UNKNOWN"}
REQUIRED_CONSTRAINT_KEYS = {"metro_proximity", "flood_risk", "ambience", "value_for_money"}
REQUIRED_REASONING_KEYS = {"strong_points", "concerns", "flood_context", "why_not_shortlist"}


def validate(match_score: int, decision: str, hard_constraints: dict, reasoning: dict) -> None:
    if not (0 <= match_score <= 100):
        raise ValueError(f"match_score must be 0-100, got {match_score}")
    if decision not in VALID_DECISIONS:
        raise ValueError(f"decision must be one of {VALID_DECISIONS}, got {decision}")

    missing_keys = REQUIRED_CONSTRAINT_KEYS - hard_constraints.keys()
    if missing_keys:
        raise ValueError(f"hard_constraints missing keys: {missing_keys}")
    bad_values = {v for v in hard_constraints.values() if v not in VALID_CONSTRAINT_VALUES}
    if bad_values:
        raise ValueError(f"hard_constraints has invalid values: {bad_values}")

    missing_reasoning = REQUIRED_REASONING_KEYS - reasoning.keys()
    if missing_reasoning:
        raise ValueError(f"reasoning missing keys: {missing_reasoning}")

    if any(v == "FAIL" for v in hard_constraints.values()) and decision != "SKIP":
        raise ValueError("a FAILed hard constraint requires decision=SKIP")


def record(listing_id: str, match_score: int, decision: str, hard_constraints: dict, reasoning: dict, db_path: str = DB_PATH) -> None:
    validate(match_score, decision, hard_constraints, reasoning)
    now = datetime.now(timezone.utc).isoformat()
    db.init_db(db_path)
    with db.connect(db_path) as conn:
        db.record_score(conn, listing_id, match_score, decision, hard_constraints, reasoning, now)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--listing-id", required=True)
    parser.add_argument("--match-score", type=int, required=True)
    parser.add_argument("--decision", required=True)
    parser.add_argument("--hard-constraints-json", required=True)
    parser.add_argument("--reasoning-json", required=True)
    parser.add_argument("--db-path", default=DB_PATH)
    args = parser.parse_args()

    record(
        args.listing_id, args.match_score, args.decision,
        json.loads(args.hard_constraints_json), json.loads(args.reasoning_json),
        db_path=args.db_path,
    )
    print(f"Recorded {args.listing_id}: {args.decision} ({args.match_score})")


if __name__ == "__main__":
    main()
