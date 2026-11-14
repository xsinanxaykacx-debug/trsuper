from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any

import joblib
import src.telegram_bot as bot

FIXTURE_DATE = date(2026, 11, 16)
ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "zkahin_bot_model.pkl"
OUTPUT_DIR = ROOT / "data" / "prediction_tests"
OUTPUT_CSV = OUTPUT_DIR / "2026-11-16-fixtures.csv"
AUDIT_CSV = OUTPUT_DIR / "2026-11-16-team-resolution.csv"

# Turkish fixture labels mapped to likely source-data spellings.
TEAM_ALIASES = {
    "Letonya": ["Latvia", "Letonya"],
    "Ermenistan": ["Armenia", "Ermenistan"],
    "G. Kıbrıs": ["Cyprus", "Güney Kıbrıs", "G. Kıbrıs", "Cyprus (Republic)"],
    "Karadağ": ["Montenegro", "Karadağ"],
    "Belarus": ["Belarus"],
    "Arnavutluk": ["Albania", "Arnavutluk"],
    "Finlandiya": ["Finland", "Finlandiya"],
    "San Marino": ["San Marino"],
    "Hırvatistan": ["Croatia", "Hırvatistan"],
    "Çekya": ["Czechia", "Czech Republic", "Çekya"],
    "İspanya": ["Spain", "İspanya"],
    "İngiltere": ["England", "İngiltere"],
    "Fransa": ["France", "Fransa"],
    "Türkiye": ["Turkey", "Türkiye"],
    "Belçika": ["Belgium", "Belçika"],
    "İtalya": ["Italy", "İtalya"],
    "Kazakistan": ["Kazakhstan", "Kazakistan"],
    "Slovakya": ["Slovakia", "Slovakya"],
    "Faroe Adaları": ["Faroe Islands", "Faroe Adaları"],
    "Moldova": ["Moldova"],
    "Litvanya": ["Lithuania", "Litvanya"],
    "Lihtenştayn": ["Liechtenstein", "Lihtenştayn"],
    "İzlanda": ["Iceland", "İzlanda"],
    "Lüksemburg": ["Luxembourg", "Lüksemburg"],
    "Estonya": ["Estonia", "Estonya"],
    "Bulgaristan": ["Bulgaria", "Bulgaristan"],
    "Yunanistan": ["Greece", "Yunanistan"],
    "Sırbistan": ["Serbia", "Sırbistan"],
    "Almanya": ["Germany", "Almanya"],
    "Hollanda": ["Netherlands", "Holland", "Hollanda"],
    "Kuzey Makedonya": ["North Macedonia", "Macedonia", "FYR Macedonia", "Kuzey Makedonya"],
    "Slovenya": ["Slovenia", "Slovenya"],
    "İsviçre": ["Switzerland", "İsviçre"],
    "İskoçya": ["Scotland", "İskoçya"],
    "Cebelitarık": ["Gibraltar", "Cebelitarık"],
    "Malta": ["Malta"],
}

FIXTURES = [
    ("F01", "17:00", "Letonya", "Ermenistan", "Turnuva belirtilmedi"),
    ("F02", "17:00", "G. Kıbrıs", "Karadağ", "Turnuva belirtilmedi"),
    ("F03", "20:00", "Belarus", "Arnavutluk", "Turnuva belirtilmedi"),
    ("F04", "20:00", "Finlandiya", "San Marino", "Turnuva belirtilmedi"),
    ("F05", "22:45", "Hırvatistan", "Çekya", "Turnuva belirtilmedi"),
    ("F06", "22:45", "İspanya", "İngiltere", "Turnuva belirtilmedi"),
    ("F07", "22:45", "Fransa", "Türkiye", "Turnuva belirtilmedi"),
    ("F08", "22:45", "Belçika", "İtalya", "Turnuva belirtilmedi"),
    ("N01", "18:00", "Kazakistan", "Slovakya", "UEFA Uluslar Ligi"),
    ("N02", "18:00", "Faroe Adaları", "Moldova", "UEFA Uluslar Ligi"),
    ("N03", "20:00", "Litvanya", "Lihtenştayn", "UEFA Uluslar Ligi"),
    ("N04", "20:00", "İzlanda", "Lüksemburg", "UEFA Uluslar Ligi"),
    ("N05", "20:00", "Estonya", "Bulgaristan", "UEFA Uluslar Ligi"),
    ("N06", "22:45", "Yunanistan", "Sırbistan", "UEFA Uluslar Ligi"),
    ("N07", "22:45", "Almanya", "Hollanda", "UEFA Uluslar Ligi"),
    ("N08", "22:45", "Kuzey Makedonya", "Slovenya", "UEFA Uluslar Ligi"),
    ("N09", "22:45", "İsviçre", "İskoçya", "UEFA Uluslar Ligi"),
    ("N10", "22:45", "Cebelitarık", "Malta", "UEFA Uluslar Ligi"),
]

def resolve_from_aliases(predictor: Any, label: str) -> str | None:
    for candidate in TEAM_ALIASES.get(label, [label]):
        resolved = predictor.resolve_team(candidate)
        if resolved:
            return resolved
        choices = predictor.team_names.get(bot.normalize_team_name(candidate), [])
        if len(choices) == 1:
            return choices[0]
    return None

def main() -> int:
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"Model artifact not found: {MODEL_PATH}")

    model_sha256 = hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()
    payload = joblib.load(MODEL_PATH)
    predictor = payload.get("predictor") if isinstance(payload, dict) else None
    if predictor is None:
        raise RuntimeError("Model artifact does not contain predictor.")
    required = ("model_1x2", "model_1x2_odds", "model_ou25", "predict", "resolve_team", "team_names")
    missing = [name for name in required if not hasattr(predictor, name)]
    if missing or any(getattr(predictor, name, None) is None for name in required[:3]):
        raise RuntimeError(f"Predictor artifact is incomplete: {missing}")

    # The bot normally builds rest-day features using today's date.
    # Freeze that feature clock to the scheduled fixture date for a fair pre-match snapshot.
    class FixtureClock:
        @staticmethod
        def now(tz=None):
            return datetime.combine(FIXTURE_DATE, time(12, 0), tzinfo=tz)

    bot.datetime = FixtureClock
    created_at = datetime.now(timezone.utc).isoformat()

    resolution_rows = []
    resolved_fixtures = []
    for fixture_id, kickoff, home_label, away_label, competition in FIXTURES:
        home = resolve_from_aliases(predictor, home_label)
        away = resolve_from_aliases(predictor, away_label)
        resolution_rows.extend([
            {"fixture_id": fixture_id, "input_team": home_label, "resolved_team": home or "", "status": "ok" if home else "UNRESOLVED"},
            {"fixture_id": fixture_id, "input_team": away_label, "resolved_team": away or "", "status": "ok" if away else "UNRESOLVED"},
        ])
        if home and away:
            resolved_fixtures.append((fixture_id, kickoff, home_label, away_label, competition, home, away))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with AUDIT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["fixture_id", "input_team", "resolved_team", "status"])
        writer.writeheader()
        writer.writerows(resolution_rows)

    unresolved = [r for r in resolution_rows if r["status"] != "ok"]
    if unresolved:
        print(f"TEAM_RESOLUTION_FAILED: {len(unresolved)} team labels unresolved.")
        for row in unresolved:
            print(f'{row["fixture_id"]}: {row["input_team"]}')
        return 2

    rows = []
    for fixture_id, kickoff, home_label, away_label, competition, home, away in resolved_fixtures:
        result = predictor.predict(home, away)
        probs = {
            "H": float(result["p_home_win"]),
            "D": float(result["p_draw"]),
            "A": float(result["p_away_win"]),
        }
        predicted_1x2 = max(probs, key=probs.get)
        ou_probs = {
            "Under": float(result["p_under25"]),
            "Over": float(result["p_over25"]),
        }
        predicted_ou25 = max(ou_probs, key=ou_probs.get)
        rows.append({
            "fixture_id": fixture_id,
            "match_date": FIXTURE_DATE.isoformat(),
            "kickoff_tr": kickoff,
            "competition": competition,
            "home_input": home_label,
            "away_input": away_label,
            "home_resolved": home,
            "away_resolved": away,
            "p_home_win": round(probs["H"], 8),
            "p_draw": round(probs["D"], 8),
            "p_away_win": round(probs["A"], 8),
            "p_under25": round(ou_probs["Under"], 8),
            "p_over25": round(ou_probs["Over"], 8),
            "predicted_1x2": predicted_1x2,
            "predicted_ou25": predicted_ou25,
            "actual_home_goals": "",
            "actual_away_goals": "",
            "actual_1x2": "",
            "actual_ou25": "",
            "hit_1x2": "",
            "hit_ou25": "",
            "prediction_created_at_utc": created_at,
            "model_sha256": model_sha256,
        })

    fields = list(rows[0].keys())
    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"PREDICTIONS_WRITTEN: {len(rows)}")
    print(f"OUTPUT: {OUTPUT_CSV.relative_to(ROOT)}")
    print(f"TEAM_AUDIT: {AUDIT_CSV.relative_to(ROOT)}")
    for row in rows:
        print(
            f'{row["fixture_id"]} {row["kickoff_tr"]} '
            f'{row["home_input"]} - {row["away_input"]}: '
            f'1={row["p_home_win"]:.3f} X={row["p_draw"]:.3f} '
            f'2={row["p_away_win"]:.3f}; '
            f'Alt={row["p_under25"]:.3f} Üst={row["p_over25"]:.3f}'
        )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
