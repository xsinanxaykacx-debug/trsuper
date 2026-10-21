# -*- coding: utf-8 -*-
"""Keşif (in-sample) dönemi oran bandı taraması.

Bu betik aday keşfi içindir; tek başına kârlılık kanıtı üretmez.
DATA.csv ham verisi değiştirilmez.
"""
from pathlib import Path
import re

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests


# --- AYARLAR ---
CSV_PATH = Path("data/csv/DATA.csv")
OUT_PATH = Path("docs/discovery_results.csv")
SURVIVORS_PATH = Path("docs/discovery_survivors.csv")
STRONG_PATH = Path("docs/discovery_strong_candidates.csv")

MIN_SAMPLE_SIZE = 100
ALPHA = 0.05
BOOTSTRAP_ITERATIONS = 2000
RANDOM_SEED = 42

MARKET_COLS = [
    "Maç_Sonucu_|_1",
    "Maç_Sonucu_|_X",
    "Maç_Sonucu_|_2",
    "Karşılıklı_Gol_|_Var",
    "Karşılıklı_Gol_|_Yok",
    "2,5_Alt/Üst_|_Alt",
    "2,5_Alt/Üst_|_Üst",
    "1,5_Alt/Üst_|_Alt",
    "1,5_Alt/Üst_|_Üst",
]
INSAMPLE_SEASONS = {"2014/2015", "2015/2016", "2016/2017", "2017/2018"}


def to_float(value):
    """Türkçe ondalık virgülü destekleyerek sayıya çevir."""
    if pd.isna(value):
        return np.nan
    try:
        parsed = float(str(value).strip().replace(",", "."))
        return parsed if np.isfinite(parsed) else np.nan
    except (TypeError, ValueError):
        return np.nan


def parse_score(score_series):
    """Skorları güvenli biçimde Ev_Gol ve Dep_Gol sütunlarına ayır."""
    split_scores = score_series.astype("string").str.extract(
        r"^\s*(\d+)\s*[-:]\s*(\d+)\s*$"
    )
    home_goals = pd.to_numeric(split_scores[0], errors="coerce")
    away_goals = pd.to_numeric(split_scores[1], errors="coerce")
    return home_goals, away_goals


def create_bins(odds_series):
    """1.00 üzerindeki oranları boşluksuz ve kapsayıcı aralıklara ayır.

    2.80-4.00 aralığı bilerek geniş tutulur; 10.00 ve üzeri tek açık uçlu banttır.
    """
    edges = np.round(np.arange(1.0, 3.0, 0.2), 10).tolist()
    edges.extend([4.0, 5.0, 7.5, 10.0, np.inf])
    labels = []
    for left, right in zip(edges[:-1], edges[1:]):
        if np.isinf(right):
            labels.append(f"{left:.2f}+")
        else:
            labels.append(f"{left:.2f}-{right:.2f}")
    return pd.cut(odds_series, bins=edges, labels=labels, right=False, include_lowest=True)


def bootstrap_ci(returns, rng, n_boot=BOOTSTRAP_ITERATIONS, alpha=ALPHA):
    """ROI ortalaması için yüzde yöntemiyle nominal bootstrap GA."""
    values = np.asarray(returns, dtype=float)
    if values.size == 0 or not np.isfinite(values).all():
        return np.nan, np.nan
    boot_means = np.empty(n_boot, dtype=float)
    for index in range(n_boot):
        boot_means[index] = rng.choice(values, size=values.size, replace=True).mean()
    lower = np.quantile(boot_means, alpha / 2)
    upper = np.quantile(boot_means, 1 - alpha / 2)
    return float(lower), float(upper)


def get_win_condition(frame, market_col):
    """Her market için sonuç etiketini skordan üret."""
    home = frame["Ev_Gol"]
    away = frame["Dep_Gol"]

    if market_col == "Maç_Sonucu_|_1":
        return home > away
    if market_col == "Maç_Sonucu_|_X":
        return home == away
    if market_col == "Maç_Sonucu_|_2":
        return home < away
    if market_col == "Karşılıklı_Gol_|_Var":
        return (home > 0) & (away > 0)
    if market_col == "Karşılıklı_Gol_|_Yok":
        return (home == 0) | (away == 0)
    if market_col.endswith("_|_Üst") or market_col.endswith("_|_Alt"):
        try:
            goal_line = float(market_col.split("_", 1)[0].replace(",", "."))
        except ValueError:
            raise ValueError(f"Market adı içinden gol çizgisi okunamadı: {market_col}")
        total_goals = home + away
        if market_col.endswith("_|_Üst"):
            return total_goals > goal_line
        return total_goals < goal_line
    raise ValueError(f"Desteklenmeyen market: {market_col}")


def paired_market_column(market_col):
    """Alt/Üst ve Var/Yok marketlerinde karşı tarafın sütun adını döndür."""
    replacements = (
        ("_|_Alt", "_|_Üst"),
        ("_|_Üst", "_|_Alt"),
        ("_|_Var", "_|_Yok"),
        ("_|_Yok", "_|_Var"),
    )
    for source, target in replacements:
        if market_col.endswith(source):
            return market_col[:-len(source)] + target
    return None


def load_and_clean_data():
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"CSV bulunamadı: {CSV_PATH}. Betiği depo kök dizininden çalıştırın."
        )

    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig", sep=",", dtype=str)
    required = {"Skor", "Lig/Sezon"}
    missing_required = required - set(df.columns)
    if missing_required:
        raise ValueError(f"CSV'de gerekli sütun(lar) eksik: {sorted(missing_required)}")

    df["Ev_Gol"], df["Dep_Gol"] = parse_score(df["Skor"])
    df["Sezon"] = (
        df["Lig/Sezon"]
        .astype("string")
        .str.extract(r"(\d{4}\s*/\s*\d{4})", expand=False)
        .str.replace(r"\s+", "", regex=True)
    )

    present_markets = [col for col in MARKET_COLS if col in df.columns]
    absent_markets = [col for col in MARKET_COLS if col not in df.columns]
    for col in present_markets:
        df[col] = df[col].map(to_float)

    return df, present_markets, absent_markets


def main():
    print("Veri yükleniyor...")
    df, market_cols, absent_markets = load_and_clean_data()
    if absent_markets:
        print("CSV'de bulunmayan market sütunları (atlanacak):")
        for col in absent_markets:
            print(f"  - {col}")

    df_insample = df.loc[df["Sezon"].isin(INSAMPLE_SEASONS)].copy()
    total_rows = len(df_insample)
    invalid_score_mask = df_insample["Ev_Gol"].isna() | df_insample["Dep_Gol"].isna()
    invalid_score_count = int(invalid_score_mask.sum())
    df_valid_score = df_insample.loc[~invalid_score_mask].copy()

    print(f"Keşif dönemi satır sayısı: {total_rows}")
    print(f"Eksik/bozuk skor nedeniyle dışlanan satır: {invalid_score_count}")
    print(f"Geçerli skorlu satır: {len(df_valid_score)}")

    results = []
    rng = np.random.default_rng(RANDOM_SEED)

    for col in market_cols:
        counterpart = paired_market_column(col)
        if counterpart and counterpart not in df_valid_score.columns:
            print(f"\nAtlandı; karşı market sütunu yok: {col} -> {counterpart}")
            continue

        required_cols = [col] + ([counterpart] if counterpart else [])
        eligible = df_valid_score.dropna(subset=required_cols).copy()

        # Oranlar > 1.00 olmalı; sıfır/negatif, 1.00 ve sonsuz oranlar bahis olarak geçersizdir.
        valid_odds_mask = np.isfinite(eligible[col]) & (eligible[col] > 1.0)
        eligible = eligible.loc[valid_odds_mask].copy()
        if counterpart:
            valid_pair_mask = np.isfinite(eligible[counterpart]) & (eligible[counterpart] > 1.0)
            eligible = eligible.loc[valid_pair_mask].copy()

        excluded_count = len(df_valid_score) - len(eligible)
        print(
            f"\nTaranıyor: {col} | kullanılabilir maç: {len(eligible)} "
            f"| skor geçerliyken oran/karşı oran nedeniyle dışlanan: {excluded_count}"
        )
        if eligible.empty:
            continue

        eligible["bin"] = create_bins(eligible[col])
        eligible = eligible.dropna(subset=["bin"]).copy()
        if eligible.empty:
            print("  - Tanımlı oran bantlarına giren maç yok.")
            continue

        eligible["win"] = get_win_condition(eligible, col).astype(bool)
        eligible["net_return"] = np.where(
            eligible["win"].to_numpy(),
            eligible[col].to_numpy() - 1.0,
            -1.0,
        )

        for bin_name, group in eligible.groupby("bin", observed=True, sort=True):
            returns = group["net_return"].to_numpy(dtype=float)
            n = len(returns)
            if n < MIN_SAMPLE_SIZE:
                continue

            roi = float(returns.mean())
            # Tek yönlü asimptotik t-testi: H0: ortalama net getiri <= 0.
            # Yüksek oranlarda çarpıklık olabileceği için bu p-değeri tek başına kanıt değildir.
            test = stats.ttest_1samp(returns, popmean=0.0, alternative="greater")
            p_value = float(test.pvalue) if np.isfinite(test.pvalue) else np.nan
            roi_lower, roi_upper = bootstrap_ci(returns, rng=rng)

            results.append({
                "Market": col,
                "Oran_Bandi": str(bin_name),
                "Gecerli_Mac_Sayisi": int(n),
                "Kazanma_Orani": float(group["win"].mean()),
                "Ortalama_Oran": float(group[col].mean()),
                "ROI": roi,
                "ROI_Alt_GA_95_Nominal": roi_lower,
                "ROI_Ust_GA_95_Nominal": roi_upper,
                "Ham_P_Degeri_TTest": p_value,
            })

    Path("docs").mkdir(parents=True, exist_ok=True)
    result_columns = [
        "Market", "Oran_Bandi", "Gecerli_Mac_Sayisi", "Kazanma_Orani",
        "Ortalama_Oran", "ROI", "ROI_Alt_GA_95_Nominal",
        "ROI_Ust_GA_95_Nominal", "Ham_P_Degeri_TTest",
    ]
    results_df = pd.DataFrame(results, columns=result_columns)
    if not results_df.empty:
        valid_p = results_df["Ham_P_Degeri_TTest"].notna()
        results_df["Duzeltilmis_P_BH"] = np.nan
        results_df["FDR_Anlamli_Mi"] = False
        if valid_p.any():
            rejected, adjusted, _, _ = multipletests(
                results_df.loc[valid_p, "Ham_P_Degeri_TTest"].to_numpy(),
                alpha=ALPHA,
                method="fdr_bh",
            )
            results_df.loc[valid_p, "Duzeltilmis_P_BH"] = adjusted
            results_df.loc[valid_p, "FDR_Anlamli_Mi"] = rejected

        survivors = results_df.loc[results_df["FDR_Anlamli_Mi"]].copy()
        strong_candidates = survivors.loc[
            survivors["ROI_Alt_GA_95_Nominal"] > 0
        ].copy()
        survivors = survivors.sort_values(
            ["Duzeltilmis_P_BH", "ROI"], ascending=[True, False]
        )
        strong_candidates = strong_candidates.sort_values(
            ["Duzeltilmis_P_BH", "ROI"], ascending=[True, False]
        )
    else:
        results_df["Duzeltilmis_P_BH"] = pd.Series(dtype=float)
        results_df["FDR_Anlamli_Mi"] = pd.Series(dtype=bool)
        survivors = results_df.copy()
        strong_candidates = results_df.copy()

    results_df.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    survivors.to_csv(SURVIVORS_PATH, index=False, encoding="utf-8-sig")
    strong_candidates.to_csv(STRONG_PATH, index=False, encoding="utf-8-sig")

    print("\nTarama tamamlandı.")
    print(f"Test edilen bant sayısı: {len(results_df)}")
    print(f"FDR sonrası aday sayısı: {len(survivors)}")
    print(f"FDR + nominal bootstrap alt GA > 0 aday sayısı: {len(strong_candidates)}")
    print(f"Sonuç: {OUT_PATH}")
    print(f"FDR adayları: {SURVIVORS_PATH}")
    print(f"Güçlü aday listesi: {STRONG_PATH}")
    print(
        "\nUYARI: Bootstrap güven aralıkları nominaldir ve çoklu test için "
        "eşzamanlı güven aralığı değildir. T-testi p-değerleri de özellikle "
        "çarpık getirilerde sınırlıdır. Adaylar bağımsız doğrulama döneminde "
        "değiştirilmeden test edilmeden kârlılık sonucu ilan etmeyin."
    )


if __name__ == "__main__":
    main()
