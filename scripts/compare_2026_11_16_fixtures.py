from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "prediction_tests" / "2026-11-16-fixtures.csv"

def main() -> int:
    if not CSV_PATH.exists():
        raise FileNotFoundError(CSV_PATH)

    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    required = {"actual_home_goals", "actual_away_goals", "actual_1x2", "actual_ou25", "hit_1x2", "hit_ou25"}
    if not required.issubset(fieldnames):
        raise RuntimeError(f"CSV columns missing: {sorted(required - set(fieldnames))}")

    for row in rows:
        home_goals = str(row.get("actual_home_goals", "")).strip()
        away_goals = str(row.get("actual_away_goals", "")).strip()
        if not home_goals or not away_goals:
            continue
        hg, ag = int(home_goals), int(away_goals)
        actual_1x2 = "H" if hg > ag else "D" if hg == ag else "A"
        actual_ou25 = "Over" if hg + ag >= 3 else "Under"
        row["actual_1x2"] = actual_1x2
        row["actual_ou25"] = actual_ou25
        row["hit_1x2"] = str(row["predicted_1x2"] == actual_1x2)
        row["hit_ou25"] = str(row["predicted_ou25"] == actual_ou25)

    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    completed = [r for r in rows if r.get("actual_1x2")]
    print(f"Completed matches: {len(completed)}/{len(rows)}")
    if completed:
        hit_1x2 = sum(r["hit_1x2"] == "True" for r in completed)
        hit_ou = sum(r["hit_ou25"] == "True" for r in completed)
        print(f"1X2 accuracy: {hit_1x2}/{len(completed)} ({hit_1x2/len(completed):.1%})")
        print(f"OU2.5 accuracy: {hit_ou}/{len(completed)} ({hit_ou/len(completed):.1%})")
    else:
        print("No actual scores entered yet. Fill actual_home_goals and actual_away_goals, then rerun.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
