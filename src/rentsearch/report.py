import json
import sys
from datetime import date
from pathlib import Path

from rentsearch import db

DB_PATH = "data/rentals.db"
REPORTS_DIR = "reports"


def _format_reviewed_line(row) -> str:
    emoji = "🏠" if row["decision"] == "SHORTLIST" else "🟡"
    lines = [
        f"{emoji} {row['match_score']} — {row['title']} — ₹{row['rent']}/mo",
        f"Locality: {row['locality']} | {row['bhk']}BHK | {row['property_type']} | Age: {row['age_years']} | Parking: {row['parking']}",
    ]
    if row["nearest_metro_station"]:
        lines.append(f"Metro: {row['nearest_metro_station']} ({row['metro_distance_km']} km)")
    reasoning = json.loads(row["reasoning_json"] or "{}")
    if reasoning.get("strong_points"):
        lines.append(f"Why: {reasoning['strong_points']}")
    constraints = json.loads(row["hard_constraints_json"] or "{}")
    unknowns = [k for k, v in constraints.items() if v == "UNKNOWN"]
    if unknowns:
        lines.append(f"Unknown: {', '.join(unknowns)}")
    if reasoning.get("concerns"):
        lines.append(f"Concern: {reasoning['concerns']}")
    lines.append(f"Source: {row['source']} — {row['url']}")
    return "\n".join(lines)


def _format_skip_line(row) -> str:
    constraints = json.loads(row["hard_constraints_json"] or "{}")
    failed = [k for k, v in constraints.items() if v == "FAIL"]
    reason = f"failed hard constraint: {', '.join(failed)}" if failed else f"low fit score ({row['match_score']})"
    return f"❌ {row['match_score']} — {row['title']} — ₹{row['rent']}/mo — {reason}"


def generate_report(db_path: str = DB_PATH, report_date: str = None) -> str:
    report_date = report_date or date.today().isoformat()
    with db.connect(db_path) as conn:
        reviewed = conn.execute(
            "SELECT * FROM listings WHERE status = 'REVIEWED' AND date(last_analyzed_at) = ?", (report_date,)
        ).fetchall()
        rejected = conn.execute(
            "SELECT * FROM listings WHERE status = 'REJECTED' AND date(date_discovered) = ?", (report_date,)
        ).fetchall()

    shortlist = sorted((r for r in reviewed if r["decision"] == "SHORTLIST"), key=lambda r: -r["match_score"])
    consider = sorted((r for r in reviewed if r["decision"] == "CONSIDER"), key=lambda r: -r["match_score"])
    skip = [r for r in reviewed if r["decision"] == "SKIP"]

    sections = [f"# Rent Search Report — {report_date}\n"]
    sections.append(f"## Shortlist ({len(shortlist)})\n")
    sections.extend(_format_reviewed_line(r) + "\n" for r in shortlist)
    sections.append(f"## Consider ({len(consider)})\n")
    sections.extend(_format_reviewed_line(r) + "\n" for r in consider)
    sections.append(f"## Skip ({len(skip)})\n")
    sections.extend(_format_skip_line(r) + "\n" for r in skip)
    if rejected:
        sections.append(f"## Filtered out before analysis ({len(rejected)})\n")
        sections.extend(f"- {r['title']} — ₹{r['rent']}/mo ({r['rejection_reason']})\n" for r in rejected)

    return "\n".join(sections)


def save_report(content: str, report_date: str = None) -> str:
    report_date = report_date or date.today().isoformat()
    Path(REPORTS_DIR).mkdir(exist_ok=True)
    path = Path(REPORTS_DIR) / f"{report_date}.md"
    path.write_text(content)
    return str(path)


if __name__ == "__main__":
    content = generate_report()
    output_path = save_report(content)
    print(content)
    print(f"\nSaved to {output_path}", file=sys.stderr)
