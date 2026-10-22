import os
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

CACHE_VERSION = 3
PICKLE_PATH = Path("data/csv/180k.pkl")
XLSX_PATH = Path("data/csv/180k.xlsx")


def _clean_odds(series: pd.Series) -> pd.Series:
    """Virgüllü veya noktalı ondalık oranları sayısala dönüştürür."""
    return pd.to_numeric(
        series.astype(str).str.replace(",", ".", regex=False).str.strip(),
        errors="coerce",
    )


def _build_global_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """180k ham verisinden modelleme için standartlaştırılmış tablo üretir."""
    required = ["TARİH", "EV", "DEP", "MSE", "MSD"]
    missing = [column for column in required if column not in raw.columns]
    if missing:
        raise KeyError(f"180k verisinde gerekli sütunlar eksik: {missing}")

    # Hakem alanı varsa standartlaştır; kaynak dosyalarda sütun adı değişebiliyor.
    referee_candidates = ["HAKEM", "Hakem", "HAKEM_ADI", "Hakem Adı", "REFEREE", "Referee"]
    referee_source = next((name for name in referee_candidates if name in raw.columns), None)

    df = raw.rename(
        columns={
            "TARİH": "Tarih",
            "EV": "Ev_Sahibi",
            "DEP": "Deplasman",
            "MS1": "_odd_H",
            "MSX": "_odd_D",
            "MS2": "_odd_A",
            "25A": "_odd_under25",
            "25Ü": "_odd_over25",
        }
    ).copy()
    if referee_source is not None:
        df["_referee"] = df[referee_source].astype("string").str.strip()
    else:
        df["_referee"] = pd.Series(pd.NA, index=df.index, dtype="string")

    df["_date"] = pd.to_datetime(df["Tarih"], dayfirst=True, errors="coerce")
    df["_season"] = np.where(
        df["_date"].dt.month >= 7,
        df["_date"].dt.year.astype("Int64").astype(str)
        + "/"
        + (df["_date"].dt.year + 1).astype("Int64").astype(str),
        (df["_date"].dt.year - 1).astype("Int64").astype(str)
        + "/"
        + df["_date"].dt.year.astype("Int64").astype(str),
    )
    df.loc[df["_date"].isna(), "_season"] = None
    df["Lig/Sezon"] = "Dunya " + df["_season"].astype(str)

    df["MSE"] = pd.to_numeric(df["MSE"], errors="coerce")
    df["MSD"] = pd.to_numeric(df["MSD"], errors="coerce")

    # Mevcut 1X2 hedefi Elo/form özelliklerinin hesaplanması için korunur.
    home_goals = df["MSE"]
    away_goals = df["MSD"]
    df["_y"] = np.select(
        [home_goals > away_goals, home_goals == away_goals, home_goals < away_goals],
        ["H", "D", "A"],
        default=None,
    )

    # İkili ALT/ÜST 2.5 hedefi: 1 = ÜST, 0 = ALT.
    total_goals = home_goals + away_goals
    df["_y_ou25"] = np.where(
        total_goals.notna(),
        (total_goals > 2.5).astype("int8"),
        np.nan,
    )

    for column in (
        "_odd_H",
        "_odd_D",
        "_odd_A",
        "_odd_under25",
        "_odd_over25",
    ):
        if column not in df.columns:
            df[column] = np.nan
        df[column] = _clean_odds(df[column])

    # 180k satırlarına özel sentetik kimlik; gerçek maç ID'si olarak kullanılmamalı.
    df["_id"] = np.arange(20_000_000, 20_000_000 + len(df), dtype=np.int64)

    columns = [
        "_id",
        "_date",
        "_season",
        "Lig/Sezon",
        "Ev_Sahibi",
        "Deplasman",
        "MSE",
        "MSD",
        "_y",
        "_y_ou25",
        "_odd_H",
        "_odd_D",
        "_odd_A",
        "_odd_under25",
        "_odd_over25",
        "_referee",
    ]
    df = df.dropna(subset=["_date", "_season", "_y", "_y_ou25"])
    return df[columns].reset_index(drop=True)


def load_global_data(force_rebuild: bool = False) -> pd.DataFrame:
    """
    180k verisini yükler. Cache sürümü ve gerekli ALT/ÜST sütunları kontrol edilir;
    eski PKL dosyası varsa Excel'den yeniden üretilir.
    """
    if not force_rebuild and PICKLE_PATH.exists():
        try:
            with PICKLE_PATH.open("rb") as handle:
                cached = pickle.load(handle)
            required_cache_columns = {
                "_odd_under25",
                "_odd_over25",
                "_y_ou25",
                "_referee",
                "_id",
                "_date",
            }
            if (
                isinstance(cached, pd.DataFrame)
                and required_cache_columns.issubset(cached.columns)
                and cached.attrs.get("cache_version") == CACHE_VERSION
            ):
                print("Hizli formattan (pkl) okunuyor...")
                return cached
            print("Eski/eksik PKL tespit edildi; Excel'den yeniden olusturulacak.")
        except (EOFError, pickle.UnpicklingError, OSError, AttributeError):
            print("PKL okunamadi; Excel'den yeniden olusturulacak.")

    if not XLSX_PATH.exists():
        raise FileNotFoundError(
            f"{XLSX_PATH} bulunamadi. ALT/UST oranlarini eklemek icin kaynak Excel gerekli."
        )

    print("Excel okunuyor (gerekirse PKL yeniden olusturulacak)...")
    raw = pd.read_excel(XLSX_PATH)
    df = _build_global_frame(raw)
    df.attrs["cache_version"] = CACHE_VERSION

    PICKLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = PICKLE_PATH.with_suffix(".pkl.tmp")
    with temp_path.open("wb") as handle:
        pickle.dump(df, handle, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(temp_path, PICKLE_PATH)

    print(f"Basarili: {len(df)} mac yuklendi.")
    print(f"ALT oran dolulugu: {df['_odd_under25'].notna().sum()} mac")
    print(f"UST oran dolulugu: {df['_odd_over25'].notna().sum()} mac")
    print("Gelecek testler icin guncel PKL kaydedildi.")
    return df


if __name__ == "__main__":
    data = load_global_data()
    print(data[["_odd_under25", "_odd_over25", "_y_ou25"]].head())
