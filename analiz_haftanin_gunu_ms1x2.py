from __future__ import annotations

import math
import re
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

# Yeni ve bağımsız araştırma betiği. Mevcut analiz betiklerine dokunmaz.
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "csv" / "DATA.csv"
OUT_DIR = BASE_DIR / "data" / "pattern_discovery_ms1x2"

MIN_N = 30
MIN_CANDIDATE_N = 60
MIN_ODDS = 1.00
MAX_ODDS = 5.00  # 5.00 dahil değildir.
BAND_WIDTH = 0.10
ALPHA = 0.05
Z95 = 1.959963984540054

ODDS_COLUMNS = {
    "MS1": "Maç_Sonucu_|_1",
    "MSX": "Maç_Sonucu_|_X",
    "MS2": "Maç_Sonucu_|_2",
}
DAY_NAMES = {
    0: "Pazartesi", 1: "Salı", 2: "Çarşamba", 3: "Perşembe",
    4: "Cuma", 5: "Cumartesi", 6: "Pazar",
}


def parse_numeric(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip().str.replace(",", ".", regex=False)
    text = text.replace({"": pd.NA, "-": pd.NA, "—": pd.NA, "nan": pd.NA,
                         "None": pd.NA, "NA": pd.NA, "N/A": pd.NA})
    return pd.to_numeric(text, errors="coerce")


def parse_score(value):
    match = re.fullmatch(r"\s*(\d+)\s*[-–:]\s*(\d+)\s*", str(value))
    if not match:
        return (np.nan, np.nan)
    return (int(match.group(1)), int(match.group(2)))


def normalize_league(value) -> str:
    text = str(value).strip()
    # Sezon eki kaldırılır; farklı sezonlar aynı lig ailesinde birleşir.
    text = re.sub(r"\s+\d{4}\s*/\s*\d{4}\s*$", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text if text and text.lower() not in {"nan", "none"} else "LİG_BİLİNMİYOR"


def odds_band(value):
    if not np.isfinite(value) or value < MIN_ODDS or value >= MAX_ODDS:
        return None
    low = math.floor((float(value) + 1e-10) / BAND_WIDTH) * BAND_WIDTH
    low = round(low, 2)
    return f"{low:.2f}-{round(low + BAND_WIDTH, 2):.2f}"


def bh_fdr(p_values):
    p = np.asarray(p_values, dtype=float)
    q = np.full(p.shape, np.nan, dtype=float)
    valid = np.flatnonzero(np.isfinite(p))
    if not len(valid):
        return q
    order_local = np.argsort(p[valid])
    sorted_p = p[valid][order_local]
    m = len(sorted_p)
    sorted_q = sorted_p * m / np.arange(1, m + 1)
    sorted_q = np.minimum.accumulate(sorted_q[::-1])[::-1]
    sorted_q = np.clip(sorted_q, 0, 1)
    restored = np.empty(m, dtype=float)
    restored[order_local] = sorted_q
    q[valid] = restored
    return q


def summarize(group: pd.DataFrame) -> dict:
    n = len(group)
    wins = int(group["Kazandi"].sum())
    returns = np.where(group["Kazandi"].to_numpy(dtype=bool),
                       group["Oran"].to_numpy(dtype=float) - 1.0, -1.0)
    roi = float(np.mean(returns)) if n else np.nan
    se = float(np.std(returns, ddof=1) / math.sqrt(n)) if n > 1 else np.nan
    low = roi - Z95 * se if np.isfinite(se) else np.nan
    high = roi + Z95 * se if np.isfinite(se) else np.nan
    if np.isfinite(se) and se > 0:
        p_value = NormalDist().cdf(-roi / se)  # H1: ROI > 0
    else:
        p_value = 0.0 if n > 0 and roi > 0 else (1.0 if n > 0 else np.nan)

    return {
        "Mac_Sayisi": n,
        "Kazanan_Sayisi": wins,
        "Kazanma_Yuzdesi": 100 * wins / n if n else np.nan,
        "Ortalama_Oran": float(group["Oran"].mean()) if n else np.nan,
        "Net_Birim_Kar": float(returns.sum()) if n else np.nan,
        "ROI_Yuzde": 100 * roi if n else np.nan,
        "ROI_GA95_Alt_Yuzde": 100 * low if np.isfinite(low) else np.nan,
        "ROI_GA95_Ust_Yuzde": 100 * high if np.isfinite(high) else np.nan,
        "P_Tek_Yonlu": p_value,
    }


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Veri dosyası bulunamadı: {DATA_PATH}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"CSV okunuyor: {DATA_PATH}")
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig", low_memory=False)

    required = ["Tarih", "Lig/Sezon", "Skor", *ODDS_COLUMNS.values()]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError("Eksik sütun(lar): " + repr(missing))

    dates = pd.to_datetime(df["Tarih"].astype("string").str.strip(),
                           errors="coerce", dayfirst=True)
    score_pairs = df["Skor"].map(parse_score)
    home_goals = pd.Series([x[0] for x in score_pairs], index=df.index, dtype="float64")
    away_goals = pd.Series([x[1] for x in score_pairs], index=df.index, dtype="float64")
    valid_score = dates.notna() & home_goals.notna() & away_goals.notna()

    work_base = pd.DataFrame({
        "Tarih": dates,
        "Lig": df["Lig/Sezon"].map(normalize_league),
        "Sezon": df["Lig/Sezon"].astype("string").str.extract(r"(\d{4}\s*/\s*\d{4})\s*$", expand=False),
        "Gun": dates.dt.dayofweek.map(DAY_NAMES),
        "Ev_Gol": home_goals,
        "Dep_Gol": away_goals,
        "Skor_Gecerli": valid_score,
    })
    work_base["Sezon"] = work_base["Sezon"].fillna("SEZON_BULUNAMADI")
    work_base["Yil"] = dates.dt.year
    work_base["Sonuc_MS1"] = home_goals > away_goals
    work_base["Sonuc_MSX"] = home_goals == away_goals
    work_base["Sonuc_MS2"] = home_goals < away_goals

    all_patterns = []
    coverage = []
    day_market_summary = []
    season_rows = []

    for market, odds_col in ODDS_COLUMNS.items():
        odds = parse_numeric(df[odds_col])
        result_col = f"Sonuc_{market}"
        valid = (
            work_base["Skor_Gecerli"]
            & work_base["Gun"].notna()
            & odds.notna()
            & (odds >= MIN_ODDS)
            & (odds < MAX_ODDS)
        )
        tmp = work_base.loc[valid, ["Tarih", "Lig", "Sezon", "Gun", "Yil", result_col]].copy()
        tmp["Oran"] = odds.loc[valid].astype(float)
        tmp["Kazandi"] = tmp[result_col].astype(bool)
        tmp["Market"] = market
        tmp["Oran_Araligi"] = tmp["Oran"].map(odds_band)
        tmp = tmp[tmp["Oran_Araligi"].notna()].copy()

        coverage.append({
            "Market": market,
            "Oran_Sutunu": odds_col,
            "CSV_Satiri": len(df),
            "Gecerli_Tarih_ve_Skor": int(valid_score.sum()),
            "Gecerli_Oranli_Mac_1_00_5_00": len(tmp),
            "Kazanan_Bahis": int(tmp["Kazandi"].sum()),
            "Tarih_Ilk": tmp["Tarih"].min().date().isoformat() if len(tmp) else "",
            "Tarih_Son": tmp["Tarih"].max().date().isoformat() if len(tmp) else "",
        })

        for day in DAY_NAMES.values():
            day_group = tmp[tmp["Gun"] == day]
            if len(day_group):
                day_market_summary.append({
                    "Market": market, "Gun": day, **summarize(day_group)
                })

        keys = ["Lig", "Gun", "Market", "Oran_Araligi"]
        for key, group in tmp.groupby(keys, sort=False, dropna=False):
            if len(group) < MIN_N:
                continue
            row = dict(zip(keys, key))
            row.update(summarize(group))
            row["Erken_Donem_N"] = int(group["Yil"].between(2014, 2019).sum())
            row["Erken_Donem_ROI_Yuzde"] = summarize(
                group[group["Yil"].between(2014, 2019)]
            )["ROI_Yuzde"] if row["Erken_Donem_N"] else np.nan
            row["Gec_Donem_N"] = int(group["Yil"].between(2020, 2025).sum())
            row["Gec_Donem_ROI_Yuzde"] = summarize(
                group[group["Yil"].between(2020, 2025)]
            )["ROI_Yuzde"] if row["Gec_Donem_N"] else np.nan
            all_patterns.append(row)

        # Sezon ayrıntısı: sezonlar bağımsız doğrulama sayılmaz; tanısal rapordur.
        season_keys = ["Lig", "Sezon", "Gun", "Market", "Oran_Araligi"]
        for key, group in tmp.groupby(season_keys, sort=False, dropna=False):
            row = dict(zip(season_keys, key))
            row.update(summarize(group))
            season_rows.append(row)

    patterns = pd.DataFrame(all_patterns)
    if not patterns.empty:
        patterns["FDR_Q"] = bh_fdr(patterns["P_Tek_Yonlu"].to_numpy())
        patterns["FDR_Gecti"] = patterns["FDR_Q"] < ALPHA
        patterns["Aday_Kosullarini_Saglar"] = (
            (patterns["Mac_Sayisi"] >= MIN_CANDIDATE_N)
            & (patterns["ROI_Yuzde"] > 0)
            & (patterns["ROI_GA95_Alt_Yuzde"] > 0)
            & (patterns["FDR_Q"] < ALPHA)
            & (patterns["Erken_Donem_N"] >= 20)
            & (patterns["Gec_Donem_N"] >= 20)
            & (patterns["Erken_Donem_ROI_Yuzde"] > 0)
            & (patterns["Gec_Donem_ROI_Yuzde"] > 0)
        )
        patterns = patterns.sort_values(
            ["Aday_Kosullarini_Saglar", "FDR_Q", "ROI_Yuzde", "Mac_Sayisi"],
            ascending=[False, True, False, False],
        )
        tests = patterns[patterns["Mac_Sayisi"] >= MIN_N].copy()
        candidates = patterns[patterns["Aday_Kosullarini_Saglar"]].copy()
    else:
        tests = pd.DataFrame()
        candidates = pd.DataFrame()

    files = {
        "ms1x2_market_kapsami.csv": pd.DataFrame(coverage),
        "ms1x2_haftanin_gunu_genel.csv": pd.DataFrame(day_market_summary),
        "ms1x2_test_edilen_oruntuler.csv": tests,
        "ms1x2_adaylar.csv": candidates,
        "ms1x2_sezon_detayi.csv": pd.DataFrame(season_rows),
    }
    for name, table in files.items():
        table.to_csv(OUT_DIR / name, index=False, encoding="utf-8-sig")

    print("\n=== MS1 / MSX / MS2 HAFTANIN GÜNÜ ANALİZİ ===")
    print("CSV satırı:", len(df))
    print("Geçerli tarih ve skor:", int(valid_score.sum()))
    print("Market başına geçerli oran aralığı: 1.00 dahil, 5.00 hariç")
    print("Oran bandı genişliği:", BAND_WIDTH)
    print("Minimum örneklem:", MIN_N)
    print("Test edilen lig-gün-market-oran örüntüsü:", len(tests))
    print("FDR q < 0.05:", int(tests["FDR_Gecti"].sum()) if not tests.empty else 0)
    print("Bütün katı aday koşullarını sağlayan:", len(candidates))
    if not pd.DataFrame(coverage).empty:
        print("\n--- MARKET KAPSAMI ---")
        print(pd.DataFrame(coverage).to_string(index=False))
    if not candidates.empty:
        print("\n--- ADAYLAR ---")
        print(candidates.head(20).round(3).to_string(index=False))
    else:
        print("\nKatı aday koşullarının tamamını sağlayan örüntü bulunmadı.")
    print("\nÇıktı klasörü:", OUT_DIR)
    for name in files:
        print(" -", OUT_DIR / name)
    print(
        "\nMETODOLOJİ UYARISI: Bu bir keşif analizidir. FDR, test edilen örüntüler "
        "üzerinde uygulanır; dönem karşılaştırması tek başına bağımsız doğrulama "
        "değildir. 2020-2025 dönemi daha önceki keşiflerde incelendiğinden gerçek "
        "out-of-sample doğrulama olarak sunulmaz. ROI güven aralığı normal yaklaşımıdır."
    )


if __name__ == "__main__":
    main()
