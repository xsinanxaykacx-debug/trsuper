"""Leakage-aware raw vs isotonic-calibrated evaluation for Model C (OU 2.5).

Run from repository root:
    python -m src.calibrated_model_evaluation

Chronological protocol:
- Base model fit: 2012/2013–2016/2017.
- Calibration only: 2017/2018 (out-of-sample predictions from the earlier model).
- Final test: 2018/2019 and 2019/2020; never used to fit the model or calibrator.

The dedicated calibration season is intentionally not used to refit the base model
after calibration. This avoids applying an isotonic map learned from one model's
probability distribution to a refitted model with a different distribution.
Metrics and ROI are computed on the same test matches with both valid OU2.5 odds,
matching the existing ablation evaluation. Calibration curves therefore describe
that odds-covered test cohort, not every match in the raw dataset.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss, log_loss

from src.ablation_study import (
    EV_THRESHOLD,
    MIN_TRAIN_ROWS,
    MOMENTUM_FEATURES,
    REST_FEATURES,
    add_momentum,
    make_model,
)
from src.features import calculate_elo_features
from src.load_global import load_global_data


TRAIN_SEASONS = [
    "2012/2013", "2013/2014", "2014/2015",
    "2015/2016", "2016/2017",
]
CALIBRATION_SEASON = "2017/2018"
TEST_SEASONS = ["2018/2019", "2019/2020"]
RANDOM_STATE = 42
EPS = 1e-7
OUTPUT_DIR = Path("data/csv")
SUMMARY_PATH = OUTPUT_DIR / "calibrated_model_evaluation_summary.csv"
CALIBRATION_PATH = OUTPUT_DIR / "calibrated_model_evaluation_bins.csv"
BETS_PATH = OUTPUT_DIR / "calibrated_model_evaluation_bets.csv"

MODEL_C_FEATURES = [
    "elo_h", "elo_a", "elo_diff",
    "form_h_pts_5", "form_h_gf_5", "form_h_ga_5",
    "form_a_pts_5", "form_a_gf_5", "form_a_ga_5",
    "form_h_pts_10", "form_h_gf_10", "form_h_ga_10",
    "form_a_pts_10", "form_a_gf_10", "form_a_ga_10",
    "form_h_home_pts", "form_h_home_gf", "form_h_home_ga",
    "form_a_away_pts", "form_a_away_gf", "form_a_away_ga",
] + REST_FEATURES + MOMENTUM_FEATURES

REQUIRED_COLUMNS = {
    "_id", "_date", "_season", "Ev_Sahibi", "Deplasman",
    "MSE", "MSD", "_y", "_y_ou25", "_odd_under25", "_odd_over25",
}


def valid_decimal_odds(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values.notna() & np.isfinite(values) & values.gt(1.0)


def make_feature_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [name for name in MODEL_C_FEATURES if name not in frame.columns]
    if missing:
        raise KeyError(f"Model C özellikleri eksik: {missing}")
    return (
        frame[MODEL_C_FEATURES]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0.0)
        .astype(float)
    )


def evaluate_model(
    frame: pd.DataFrame,
    probabilities_over: np.ndarray,
    model_label: str,
) -> tuple[dict, pd.DataFrame]:
    """Score predictions and simulate the existing highest-EV Turkish-odds rule."""
    y = frame["_y_ou25"].astype(int).to_numpy()
    p_over = np.clip(np.asarray(probabilities_over, dtype=float), EPS, 1.0 - EPS)
    if len(p_over) != len(frame):
        raise ValueError(f"{model_label}: tahmin ve test satırı sayısı eşleşmiyor.")

    brier = float(brier_score_loss(y, p_over))
    ll = float(log_loss(y, np.column_stack([1.0 - p_over, p_over]), labels=[0, 1]))

    odds_under = frame["_odd_under25"].to_numpy(dtype=float)
    odds_over = frame["_odd_over25"].to_numpy(dtype=float)
    ev_under = (1.0 - p_over) * odds_under - 1.0
    ev_over = p_over * odds_over - 1.0
    choose_over = ev_over > ev_under
    best_ev = np.maximum(ev_under, ev_over)
    take = best_ev > EV_THRESHOLD

    chosen_odds = np.where(choose_over, odds_over, odds_under)
    chosen_side = np.where(choose_over, "UST", "ALT")
    actual_over = y == 1
    won = np.where(choose_over, actual_over, ~actual_over)
    profits = np.where(won[take], chosen_odds[take] - 1.0, -1.0)
    bet_count = int(take.sum())
    total_profit = float(profits.sum()) if bet_count else 0.0
    roi_pct = float(profits.mean() * 100.0) if bet_count else np.nan

    summary = {
        "model": model_label,
        "test_matches": int(len(frame)),
        "mean_predicted_over_pct": float(p_over.mean() * 100.0),
        "actual_over_rate_pct": float(y.mean() * 100.0),
        "brier_score": brier,
        "log_loss": ll,
        "ev_threshold": EV_THRESHOLD,
        "bets": bet_count,
        "bet_coverage_pct": float(take.mean() * 100.0),
        "wins": int(won[take].sum()) if bet_count else 0,
        "losses": int(bet_count - won[take].sum()) if bet_count else 0,
        "total_profit_1u": total_profit,
        "roi_pct": roi_pct,
    }

    ledger = frame[[
        "_id", "_date", "_season", "Ev_Sahibi", "Deplasman", "_y_ou25",
        "_odd_under25", "_odd_over25",
    ]].copy()
    ledger["model"] = model_label
    ledger["p_over"] = p_over
    ledger["p_under"] = 1.0 - p_over
    ledger["ev_under"] = ev_under
    ledger["ev_over"] = ev_over
    ledger["best_ev"] = best_ev
    ledger["selected_side"] = chosen_side
    ledger["selected_odds"] = chosen_odds
    ledger["bet_taken"] = take
    ledger["bet_won"] = np.where(take, won, False)
    ledger["profit_1u"] = np.where(take, np.where(won, chosen_odds - 1.0, -1.0), 0.0)
    return summary, ledger


def calibration_bins(
    frame: pd.DataFrame,
    probabilities: dict[str, np.ndarray],
) -> pd.DataFrame:
    """Reliability table; actual rate is compared with mean predicted probability."""
    y = frame["_y_ou25"].astype(int).to_numpy()
    edges = [0.0, 0.50, 0.55, 0.60, 0.65, 0.70, 1.000000001]
    labels = ["<50%", "50–55%", "55–60%", "60–65%", "65–70%", "70%+"]
    rows: list[dict] = []

    for model_label, values in probabilities.items():
        p = np.clip(np.asarray(values, dtype=float), 0.0, 1.0)
        bins = pd.cut(p, bins=edges, labels=labels, right=False, include_lowest=True)
        for label in labels:
            mask = np.asarray(bins == label)
            n = int(mask.sum())
            rows.append({
                "model": model_label,
                "probability_band": label,
                "matches": n,
                "mean_predicted_pct": float(p[mask].mean() * 100.0) if n else np.nan,
                "actual_over_rate_pct": float(y[mask].mean() * 100.0) if n else np.nan,
                "actual_minus_predicted_pp": (
                    float((y[mask].mean() - p[mask].mean()) * 100.0) if n else np.nan
                ),
                "brier_score_in_band": (
                    float(np.mean((p[mask] - y[mask]) ** 2)) if n else np.nan
                ),
            })
    return pd.DataFrame(rows)


def main() -> None:
    print("1. Global veri yükleniyor...")
    matches = load_global_data().copy()
    missing = sorted(REQUIRED_COLUMNS - set(matches.columns))
    if missing:
        raise KeyError(f"Global veri setinde gerekli sütunlar eksik: {missing}")
    if matches["_id"].duplicated().any():
        raise ValueError("Global veri setinde yinelenen _id var.")

    matches["_date"] = pd.to_datetime(matches["_date"], errors="coerce")
    matches["_y_ou25"] = pd.to_numeric(matches["_y_ou25"], errors="coerce")
    matches["_season"] = matches["_season"].astype(str).str.strip()
    matches = matches.dropna(subset=["_date", "_season", "_y_ou25", "_y"]).copy()
    matches["_y_ou25"] = matches["_y_ou25"].astype(int)
    if not matches["_y_ou25"].isin([0, 1]).all():
        raise ValueError("_y_ou25 yalnızca 0 (ALT) ve 1 (ÜST) olmalı.")

    required_seasons = set(TRAIN_SEASONS + [CALIBRATION_SEASON] + TEST_SEASONS)
    absent = sorted(required_seasons - set(matches["_season"].unique()))
    if absent:
        raise ValueError(f"Veride gerekli sezonlar bulunamadı: {absent}")

    print("2. Kronolojik maç öncesi özellikleri hesaplanıyor...")
    features = add_momentum(calculate_elo_features(matches))
    data = matches.merge(features, on="_id", how="inner", validate="one_to_one")
    data = data.sort_values(["_date", "_id"], kind="stable").reset_index(drop=True)

    train = data[data["_season"].isin(TRAIN_SEASONS)].copy()
    calibration = data[data["_season"].eq(CALIBRATION_SEASON)].copy()
    test_raw = data[data["_season"].isin(TEST_SEASONS)].copy()
    valid_test_odds = (
        valid_decimal_odds(test_raw["_odd_under25"])
        & valid_decimal_odds(test_raw["_odd_over25"])
    )
    test = test_raw.loc[valid_test_odds].copy().reset_index(drop=True)

    if len(train) < MIN_TRAIN_ROWS:
        raise RuntimeError(f"Eğitim örneği yetersiz: {len(train)}")
    if train["_y_ou25"].nunique() != 2 or calibration["_y_ou25"].nunique() != 2:
        raise RuntimeError("Eğitim ve kalibrasyon kümelerinde ALT/ÜST iki sınıfı da bulunmalı.")
    if len(calibration) < 100:
        raise RuntimeError(f"Kalibrasyon sezonu örneği yetersiz: {len(calibration)}")
    if test.empty:
        raise RuntimeError("Test sezonlarında geçerli ALT ve ÜST oranları olan maç yok.")

    print(f"   Eğitim: {TRAIN_SEASONS[0]}–{TRAIN_SEASONS[-1]} | {len(train):,} maç")
    print(f"   Kalibrasyon: {CALIBRATION_SEASON} | {len(calibration):,} maç")
    print(f"   Ham test: {len(test_raw):,} maç")
    print(f"   Oranları geçerli test: {len(test):,} maç")
    print(f"   Test sezonları: {', '.join(TEST_SEASONS)}")

    print("\n3. Model C yalnızca eğitim sezonlarında eğitiliyor...")
    model = make_model()
    model.fit(make_feature_matrix(train), train["_y_ou25"].astype(int).to_numpy())

    print("4. Ayrı kalibrasyon sezonundan izotonik eşleyici öğreniliyor...")
    p_calibration_raw = model.predict_proba(make_feature_matrix(calibration))[:, 1]
    calibrator = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
    calibrator.fit(p_calibration_raw, calibration["_y_ou25"].astype(int).to_numpy())

    print("5. Test sezonlarında ham ve kalibre edilmiş olasılıklar ölçülüyor...")
    p_test_raw = model.predict_proba(make_feature_matrix(test))[:, 1]
    p_test_calibrated = np.clip(calibrator.predict(p_test_raw), EPS, 1.0 - EPS)
    prediction_map = {
        "RAW": p_test_raw,
        "ISOTONIC": p_test_calibrated,
    }

    summaries: list[dict] = []
    ledgers: list[pd.DataFrame] = []
    for model_label, probabilities in prediction_map.items():
        summary, ledger = evaluate_model(test, probabilities, model_label)
        summary["test_season"] = "POOLED"
        summaries.append(summary)
        ledgers.append(ledger)

        for season in TEST_SEASONS:
            mask = test["_season"].eq(season).to_numpy()
            season_frame = test.loc[mask].reset_index(drop=True)
            season_summary, season_ledger = evaluate_model(
                season_frame, probabilities[mask], model_label
            )
            season_summary["test_season"] = season
            summaries.append(season_summary)

    summary_df = pd.DataFrame(summaries)
    pooled = summary_df.loc[summary_df["test_season"].eq("POOLED")].set_index("model")
    raw_ll = float(pooled.loc["RAW", "log_loss"])
    calibrated_ll = float(pooled.loc["ISOTONIC", "log_loss"])
    raw_brier = float(pooled.loc["RAW", "brier_score"])
    calibrated_brier = float(pooled.loc["ISOTONIC", "brier_score"])

    bins_df = calibration_bins(test, prediction_map)
    bets_df = pd.concat(ledgers, ignore_index=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(SUMMARY_PATH, index=False, encoding="utf-8-sig")
    bins_df.to_csv(CALIBRATION_PATH, index=False, encoding="utf-8-sig")
    bets_df.to_csv(BETS_PATH, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 112)
    print("HAM MODEL vs ISOTONIC KALİBRASYON — ORAN KAPSAMLI TEST")
    print("=" * 112)
    print(summary_df.to_string(index=False, float_format=lambda value: f"{value:.5f}"))

    print("\nTEST KALİBRASYON TABLOSU (tahmin aralığına göre)")
    print(bins_df.to_string(index=False, float_format=lambda value: f"{value:.3f}"))

    target_band = bins_df[
        bins_df["model"].eq("ISOTONIC")
        & bins_df["probability_band"].eq("60–65%")
    ]
    if not target_band.empty and int(target_band.iloc[0]["matches"]) > 0:
        row = target_band.iloc[0]
        print(
            "\n%60 civarı tahmin kontrolü (kalibre modelin 60–65% bandı): "
            f"n={int(row['matches']):,}, ortalama tahmin=%{row['mean_predicted_pct']:.2f}, "
            f"gerçekleşen ÜST=%{row['actual_over_rate_pct']:.2f}, "
            f"fark={row['actual_minus_predicted_pp']:+.2f} yüzde puan."
        )
    else:
        print("\n%60–65 bandında test maçı yok; bu bant için sonuç çıkarılamaz.")

    print("\nKISA KARAR")
    print(f"LogLoss: ham={raw_ll:.5f}, isotonic={calibrated_ll:.5f}, fark={calibrated_ll - raw_ll:+.5f}")
    print(f"Brier:   ham={raw_brier:.5f}, isotonic={calibrated_brier:.5f}, fark={calibrated_brier - raw_brier:+.5f}")
    raw_roi = pooled.loc["RAW", "roi_pct"]
    calibrated_roi = pooled.loc["ISOTONIC", "roi_pct"]
    print(f"Türkiye oranı ROI: ham=%{raw_roi:+.2f}, isotonic=%{calibrated_roi:+.2f}")
    if pd.notna(calibrated_roi) and calibrated_roi > 0.0:
        print("ROI yorumu: kalibre modelin nokta tahmini artıda; bu tek başına güvenilir bahis avantajı kanıtı değildir.")
    elif pd.notna(calibrated_roi):
        print("ROI yorumu: kalibre modelin nokta tahmini hâlâ ekside.")
    else:
        print("ROI yorumu: kalibre model için seçilen bahis bulunmadı.")
    print("\nÇıktılar:")
    print(f"  Özet: {SUMMARY_PATH}")
    print(f"  Kalibrasyon bantları: {CALIBRATION_PATH}")
    print(f"  Maç/bahis ayrıntıları: {BETS_PATH}")
    print(
        "\nYöntem notu: isotonic eşleyici yalnızca 2017/2018 kalibrasyon sezonunda fit edildi. "
        "2018/2019–2019/2020 test sezonları fit veya ayar için kullanılmadı. "
        "ROI sabit 1 birim bahis başına kârdır; ROI'nin pozitif çıkması tek başına "
        "istatistiksel olarak güvenilir avantaj göstermez. LogLoss için 0.68→0.66 hedefi "
        "önceden garanti edilemez; gerçek sonuç yukarıdaki ölçümlerden okunmalıdır."
    )


if __name__ == "__main__":
    main()
