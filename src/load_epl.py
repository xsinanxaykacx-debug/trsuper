"""EPL CSV loader: converts raw English Premier League results to project schema.

Expected common source columns: Date, HomeTeam, AwayTeam, FTHG, FTAG,
B365H, B365D, B365A. Column matching is case-insensitive and ignores
surrounding whitespace.

EPL Maç_ID/_id values use a negative namespace so they do not collide with
the existing positive Maçkolik IDs. Callers may pass existing_ids to protect
against collisions with any additional ID namespace.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


# Canonical team names for common historical football-data.co.uk EPL aliases.
# Keys are matched case-insensitively; unknown names are preserved unchanged.
EPL_TEAM_NAME_MAPPING = {
    "man united": "Manchester United",
    "man utd": "Manchester United",
    "manchester utd": "Manchester United",
    "man city": "Manchester City",
    "nott'm forest": "Nottingham Forest",
    "nott forest": "Nottingham Forest",
    "notts forest": "Nottingham Forest",
    "spurs": "Tottenham Hotspur",
    "tottenham": "Tottenham Hotspur",
    "wolves": "Wolverhampton Wanderers",
    "west brom": "West Bromwich Albion",
    "west bromwich": "West Bromwich Albion",
    "newcastle": "Newcastle United",
    "sheffield united": "Sheffield United",
    "sheff utd": "Sheffield United",
    "sheffield wed": "Sheffield Wednesday",
    "sheff wed": "Sheffield Wednesday",
    "brighton": "Brighton and Hove Albion",
    "brighton & hove albion": "Brighton and Hove Albion",
    "qpr": "Queens Park Rangers",
    "west ham": "West Ham United",
    "leeds": "Leeds United",
    "leicester": "Leicester City",
    "norwich": "Norwich City",
    "cardiff": "Cardiff City",
    "hull": "Hull City",
    "stoke": "Stoke City",
    "swansea": "Swansea City",
    "birmingham": "Birmingham City",
    "blackburn": "Blackburn Rovers",
    "bolton": "Bolton Wanderers",
    "blackpool": "Blackpool",
    "luton": "Luton Town",
    "bournemouth": "AFC Bournemouth",
}


def normalize_epl_team_name(value: object) -> object:
    """Map a known EPL team alias to its canonical name; preserve unknowns."""
    if pd.isna(value):
        return value
    cleaned = str(value).strip()
    return EPL_TEAM_NAME_MAPPING.get(cleaned.casefold(), cleaned)


COLUMN_ALIASES = {
    "date": ("date", "matchdate", "tarih"),
    "home_team": ("hometeam", "home_team", "ev_sahibi"),
    "away_team": ("awayteam", "away_team", "deplasman"),
    "home_goals": ("fthg", "homegoals", "home_goals", "mse"),
    "away_goals": ("ftag", "awaygoals", "away_goals", "msd"),
    "odd_h": ("b365h", "odd_h", "homeodds"),
    "odd_d": ("b365d", "odd_d", "drawodds"),
    "odd_a": ("b365a", "odd_a", "awayodds"),
}


def to_numeric_comma(series: pd.Series) -> pd.Series:
    """Convert decimal-comma or decimal-point odds to numeric floats."""
    cleaned = (
        series.astype("string")
        .str.strip()
        .str.replace(",", ".", regex=False)
        .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    )
    return pd.to_numeric(cleaned, errors="coerce")


def _resolve_columns(df: pd.DataFrame) -> dict[str, str]:
    """Resolve source columns without depending on their capitalization."""
    normalized = {str(column).strip().casefold(): column for column in df.columns}
    resolved: dict[str, str] = {}
    missing: list[str] = []

    for target, aliases in COLUMN_ALIASES.items():
        source = next(
            (normalized[alias.casefold()] for alias in aliases if alias.casefold() in normalized),
            None,
        )
        if source is None:
            missing.append(f"{target} ({', '.join(aliases)})")
        else:
            resolved[target] = source

    if missing:
        raise ValueError(
            "EPL CSV dosyasinda gerekli sutunlar bulunamadi: " + "; ".join(missing)
        )

    return resolved


def _allocate_epl_ids(
    count: int,
    existing_ids: Iterable[int] | None = None,
) -> list[int]:
    """Allocate unique negative IDs, skipping IDs already in use."""
    used: set[int] = set()
    if existing_ids is not None:
        for value in existing_ids:
            if pd.isna(value):
                continue
            used.add(int(value))

    allocated: list[int] = []
    candidate = -1
    while len(allocated) < count:
        if candidate not in used:
            allocated.append(candidate)
            used.add(candidate)
        candidate -= 1

    return allocated


def load_epl_data(
    csv_path: str | Path,
    existing_ids: Iterable[int] | None = None,
) -> pd.DataFrame:
    """Load a raw EPL CSV and return columns compatible with the project.

    Invalid dates, missing team names, and missing/non-numeric final scores
    are excluded because a completed-match target (_y) cannot be created for
    those rows. Missing or invalid odds are retained as NaN.
    """
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"EPL CSV dosyasi bulunamadi: {path}")

    raw = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")
    columns = _resolve_columns(raw)

    df = pd.DataFrame(index=raw.index)
    parsed_dates = pd.to_datetime(
        raw[columns["date"]].astype("string").str.strip(),
        errors="coerce",
        dayfirst=True,
    )
    df["_date"] = parsed_dates
    df["Ev_Sahibi"] = raw[columns["home_team"]].map(normalize_epl_team_name).astype("string").str.strip()
    df["Deplasman"] = raw[columns["away_team"]].map(normalize_epl_team_name).astype("string").str.strip()
    df["MSE"] = pd.to_numeric(raw[columns["home_goals"]], errors="coerce")
    df["MSD"] = pd.to_numeric(raw[columns["away_goals"]], errors="coerce")

    df["_odd_H"] = to_numeric_comma(raw[columns["odd_h"]])
    df["_odd_D"] = to_numeric_comma(raw[columns["odd_d"]])
    df["_odd_A"] = to_numeric_comma(raw[columns["odd_a"]])

    valid = (
        df["_date"].notna()
        & df["Ev_Sahibi"].notna()
        & df["Deplasman"].notna()
        & df["Ev_Sahibi"].ne("")
        & df["Deplasman"].ne("")
        & df["MSE"].notna()
        & df["MSD"].notna()
        & df["MSE"].ge(0)
        & df["MSD"].ge(0)
        & df["MSE"].mod(1).eq(0)
        & df["MSD"].mod(1).eq(0)
    )
    df = df.loc[valid].copy()

    if df.empty:
        raise ValueError(
            "EPL CSV dosyasinda tarih, takim ve skor bilgileri gecerli tamamlanmis mac bulunamadi."
        )

    df["MSE"] = df["MSE"].astype("int64")
    df["MSD"] = df["MSD"].astype("int64")

    df["_y"] = "D"
    df.loc[df["MSE"] > df["MSD"], "_y"] = "H"
    df.loc[df["MSE"] < df["MSD"], "_y"] = "A"

    season_start = df["_date"].dt.year - (df["_date"].dt.month < 8).astype("int64")
    season_end = season_start + 1
    df["_season"] = (
        season_start.astype("string") + "/" + season_end.astype("string")
    )
    df["Lig/Sezon"] = "EPL " + df["_season"]
    df["Tarih"] = df["_date"].dt.strftime("%d-%m-%Y")

    # Odds <= 1.00 are not usable decimal odds; keep them as missing.
    for odds_column in ("_odd_H", "_odd_D", "_odd_A"):
        df.loc[df[odds_column] <= 1.0, odds_column] = float("nan")

    df["Maç_ID"] = _allocate_epl_ids(len(df), existing_ids=existing_ids)
    df["_id"] = df["Maç_ID"]

    output_columns = [
        "Maç_ID",
        "Tarih",
        "Lig/Sezon",
        "Ev_Sahibi",
        "Deplasman",
        "MSE",
        "MSD",
        "_y",
        "_date",
        "_season",
        "_odd_H",
        "_odd_D",
        "_odd_A",
        "_id",
    ]
    return df[output_columns].reset_index(drop=True)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Ham EPL CSV dosyasini model veri formatina donusturur."
    )
    parser.add_argument("csv_path", help="Ham EPL CSV dosyasinin yolu")
    args = parser.parse_args()

    epl = load_epl_data(args.csv_path)
    print(f"Yuklenen tamamlanmis EPL maci: {len(epl)}")
    print(f"Tarih araligi: {epl['_date'].min().date()} - {epl['_date'].max().date()}")
    print(f"Hedef dagilimi:\n{epl['_y'].value_counts().to_string()}")
    print(f"1X2 oran dolulugu: {epl[['_odd_H', '_odd_D', '_odd_A']].notna().all(axis=1).mean() * 100:.2f}%")
