from pathlib import Path
import re
import unicodedata
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "csv" / "DATA.csv"
PRED_PATH = ROOT / "archive_v16" / "v16_per_match_predictions.csv"
SCHEDULE_PATH = ROOT / "archive_v16" / "walkforward_v16_exact.csv"

def _norm(value):
    text = unicodedata.normalize("NFKD", str(value))
    return "".join(ch for ch in text if not unicodedata.combining(ch)).lower().replace(" ", "").replace("_", "").replace("-", "")

def find_column(df, aliases, required=True):
    lookup = {_norm(c): c for c in df.columns}
    for alias in aliases:
        key = _norm(alias)
        if key in lookup:
            return lookup[key]
    if required:
        raise ValueError(f"Gerekli sütun bulunamadı: {aliases}; mevcut={list(df.columns)}")
    return None

def to_numeric(series):
    return pd.to_numeric(series.astype(str).str.strip().str.replace(",", ".", regex=False), errors="coerce")

def season_normalize(value):
    if pd.isna(value):
        return None
    text = str(value)
    match = re.search(r"(20\d{2})\s*[/\-]\s*(?:(20)?(\d{2}))", text)
    if match:
        start = int(match.group(1))
        tail = match.group(3)
        end = int(("20" + tail) if len(tail) == 2 else tail)
        return f"{start}/{end}"
    match = re.search(r"(20\d{2})", text)
    if match:
        start = int(match.group(1))
        return f"{start}/{start + 1}"
    return text.strip()

def load_data(path=DATA_PATH):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"DATA.csv bulunamadı: {path}")
    df = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig", low_memory=False)
    aliases = {
        "date": ["Tarih", "Date", "Mac Tarihi"],
        "season_raw": ["Lig/Sezon", "Sezon", "Season", "Lig Sezon"],
        "league_raw": ["Lig", "League", "Lig Adı"],
        "home": ["Ev_Sahibi", "Ev Sahibi", "EvSahibi", "Home", "Home Team"],
        "away": ["Deplasman", "Deplasman Takımı", "Away", "Away Team"],
        "home_goals": ["MSE", "MS Ev", "Ev Gol", "Home Goals"],
        "away_goals": ["MSD", "MS Dep", "Dep Gol", "Away Goals"],
        "id": ["Maç_ID", "Mac_ID", "match_id", "ID"],
        "odd_H": ["Maç_Sonucu_|_1", "MS 1", "MS1", "1"],
        "odd_D": ["Maç_Sonucu_|_X", "MS X", "MSX", "X"],
        "odd_A": ["Maç_Sonucu_|_2", "MS 2", "MS2", "2"],
    }
    cols = {key: find_column(df, names, required=key not in ("league_raw", "id", "odd_H", "odd_D", "odd_A")) for key, names in aliases.items()}
    out = pd.DataFrame(index=df.index)
    out["match_id"] = df[cols["id"]].astype(str).str.strip() if cols["id"] else df.index.astype(str)
    dates = df[cols["date"]].astype(str).str.strip()
    out["date"] = pd.to_datetime(dates, format="%d-%m-%Y", errors="coerce")
    fallback = out["date"].isna()
    if fallback.any():
        out.loc[fallback, "date"] = pd.to_datetime(dates[fallback], errors="coerce", dayfirst=True)
    season_source = df[cols["season_raw"]]
    out["season"] = season_source.map(season_normalize)
    if cols["league_raw"]:
        league = df[cols["league_raw"]].astype(str)
    else:
        league = season_source.astype(str)
    out["league"] = np.where(league.str.contains("1\\.?\\s*Lig|Birinci", case=False, regex=True), "1. Lig", "Süper Lig")
    out["home"] = df[cols["home"]].astype(str).str.strip()
    out["away"] = df[cols["away"]].astype(str).str.strip()
    out["home_goals"] = to_numeric(df[cols["home_goals"]])
    out["away_goals"] = to_numeric(df[cols["away_goals"]])
    for key in ("odd_H", "odd_D", "odd_A"):
        out[key] = to_numeric(df[cols[key]]) if cols[key] else np.nan
    out["y"] = np.select(
        [out["home_goals"] > out["away_goals"], out["home_goals"] == out["away_goals"], out["home_goals"] < out["away_goals"]],
        ["H", "D", "A"], default=""
    )
    out = out[out["date"].notna() & out["season"].notna() & out["home"].ne("nan") & out["away"].ne("nan")].copy()
    out = out.sort_values(["date", "match_id"], kind="stable").reset_index(drop=True)
    if out["match_id"].duplicated().any():
        raise ValueError("DATA içinde match_id tekrarı var.")
    return out

def load_reference(pred_path=PRED_PATH, schedule_path=SCHEDULE_PATH):
    pred_path, schedule_path = Path(pred_path), Path(schedule_path)
    if not pred_path.exists():
        raise FileNotFoundError(f"Sabit v1.6 test kümesi bulunamadı: {pred_path}")
    if not schedule_path.exists():
        raise FileNotFoundError(f"Sezon takvimi bulunamadı: {schedule_path}")
    pred = pd.read_csv(pred_path, encoding="utf-8-sig", low_memory=False)
    schedule = pd.read_csv(schedule_path, encoding="utf-8-sig", low_memory=False)
    required = {"match_id", "season", "date", "y", "odd_H", "odd_D", "odd_A"}
    missing = required - set(pred.columns)
    if missing:
        raise ValueError(f"Referans tahmin dosyasında eksik sütunlar: {sorted(missing)}")
    if pred["match_id"].astype(str).duplicated().any():
        raise ValueError("Referans test kümesinde yinelenen match_id var.")
    if len(pred) != 5854:
        raise ValueError(f"Sabit test kümesi 5854 maç olmalı; bulunan={len(pred)}")
    return pred, schedule
