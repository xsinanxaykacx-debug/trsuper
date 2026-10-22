"""Leakage-aware comparison of raw, isotonic and Platt-scaled Model C probabilities.

Run from repository root:
    python -m src.calibrated_model_evaluation_v2

Chronological protocol:
- Base model fit: 2012/2013–2016/2017.
- Both calibrators fit only on 2017/2018 predictions from the frozen base model.
- Final test: 2018/2019 and 2019/2020; never used for fitting or calibration.

The test cohort is restricted to matches with valid decimal odds for both OU2.5 sides,
so LogLoss/Brier and the existing EV betting simulation are comparable across methods.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
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
EPS = 1e-7
TARGET_LOG_LOSS = 0.66
OUTPUT_DIR = Path("data/csv")
SUMMARY_PATH = OUTPUT_DIR / "calibrated_model_evaluation_v2_summary.csv"
CALIBRATION_PATH = OUTPUT_DIR / "calibrated_model_evaluation_v2_bins.csv"
BETS_PATH = OUTPUT_DIR / "calibrated_model_evaluation_v2_bets.csv"

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


def fit_platt_calibrator(model, x_cal: pd.DataFrame, y_cal: np.ndarray):
    """Fit sigmoid calibration on the dedicated season without refitting Model C."""
    try:
        from sklearn.frozen import FrozenEstimator
        calibrated = CalibratedClassifierCV(
            estimator=FrozenEstimator(model),
            method="sigmoid",
        )
    except ImportError:
        # Compatibility with sklearn releases predating FrozenEstimator.
        try:
            calibrated = CalibratedClassifierCV(
                estimator=model,
                method="sigmoid",
                cv="prefit",
            )
        except TypeError:
            calibrated = CalibratedClassifierCV(
                base_estimator=model,
                method="sigmoid",
                cv="prefit",
            )
    calibrated.fit(x_cal, y_cal)
    return calibrated


def evaluate_model(
    frame: pd.DataFrame,
    probabilities_over: np.ndarray,
    model_label: str,
) -> tuple[dict, pd.DataFrame]:
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
        "log_loss_target": TARGET_LOG_LOSS,
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
    x_train = make_feature_matrix(train)
    y_train = train["_y_ou25"].astype(int).to_numpy()
    x_cal = make_feature_matrix(calibration)
    y_cal = calibration["_y_ou25"].astype(int).to_numpy()
    x_test = make_feature_matrix(test)
    model.fit(x_train, y_train)

    print("4. Aynı ayrılmış kalibrasyon sezonunda Isotonic ve Platt fit ediliyor...")
    p_calibration_raw = model.predict_proba(x_cal)[:, 1]
    isotonic = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
    isotonic.fit(p_calibration_raw, y_cal)
    platt = fit_platt_calibrator(model, x_cal, y_cal)

    print("5. Test tahminleri ve metrikler hesaplanıyor...")
    p_test_raw = model.predict_proba(x_test)[:, 1]
    p_test_isotonic = np.clip(isotonic.predict(p_test_raw), EPS, 1.0 - EPS)
    p_test_platt = np.clip(platt.predict_proba(x_test)[:, 1], EPS, 1.0 - EPS)
    prediction_map = {
        "RAW": p_test_raw,
        "ISOTONIC": p_test_isotonic,
        "PLATT_SIGMOID": p_test_platt,
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
            season_summary, _ = evaluate_model(
                test.loc[mask].reset_index(drop=True),
                probabilities[mask],
                model_label,
            )
            season_summary["test_season"] = season
            summaries.append(season_summary)

    summary_df = pd.DataFrame(summaries)
    pooled = summary_df.loc[summary_df["test_season"].eq("POOLED")].set_index("model")
    bins_df = calibration_bins(test, prediction_map)
    bets_df = pd.concat(ledgers, ignore_index=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(SUMMARY_PATH, index=False, encoding="utf-8-sig")
    bins_df.to_csv(CALIBRATION_PATH, index=False, encoding="utf-8-sig")
    bets_df.to_csv(BETS_PATH, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 120)
    print("RAW vs ISOTONIC vs PLATT SIGMOID — ORAN KAPSAMLI TEST")
    print("=" * 120)
    print(summary_df.to_string(index=False, float_format=lambda value: f"{value:.5f}"))
    print("\nTEST KALİBRASYON TABLOSU (tahmin aralığına göre)")
    print(bins_df.to_string(index=False, float_format=lambda value: f"{value:.3f}"))

    raw_ll = float(pooled.loc["RAW", "log_loss"])
    isotonic_ll = float(pooled.loc["ISOTONIC", "log_loss"])
    platt_ll = float(pooled.loc["PLATT_SIGMOID", "log_loss"])
    raw_brier = float(pooled.loc["RAW", "brier_score"])
    isotonic_brier = float(pooled.loc["ISOTONIC", "brier_score"])
    platt_brier = float(pooled.loc["PLATT_SIGMOID", "brier_score"])
    print("\nKARAR RAPORU")
    print(f"Hedef LogLoss: {TARGET_LOG_LOSS:.2f}")
    print(f"RAW LogLoss:          {raw_ll:.5f}")
    print(f"ISOTONIC LogLoss:     {isotonic_ll:.5f} (RAW farkı {isotonic_ll - raw_ll:+.5f})")
    print(f"PLATT SIGMOID LogLoss:{platt_ll:.5f} (RAW farkı {platt_ll - raw_ll:+.5f})")
    print(f"LogLoss hedefi 0.66: {'ULAŞILDI' if platt_ll <= TARGET_LOG_LOSS else 'ULAŞILAMADI'}")
    print(f"Brier RAW / ISOTONIC / PLATT: {raw_brier:.5f} / {isotonic_brier:.5f} / {platt_brier:.5f}")
    print(
        "Platt, Isotonic'e göre LogLoss'u "
        + ("iyileştirdi." if platt_ll < isotonic_ll else "iyileştirmedi.")
    )
    print(
        "Platt, ham modele göre LogLoss'u "
        + ("düşürdü." if platt_ll < raw_ll else "düşürmedi.")
    )
    print(
        "ROI RAW / ISOTONIC / PLATT: "
        f"%{pooled.loc['RAW', 'roi_pct']:+.2f} / "
        f"%{pooled.loc['ISOTONIC', 'roi_pct']:+.2f} / "
        f"%{pooled.loc['PLATT_SIGMOID', 'roi_pct']:+.2f}"
    )
    if platt_ll >= raw_ll:
        print(
            "\nSONUÇ: Kalibrasyon defterini kapatıyoruz, sorun modelin tahmin gücünde. "
            "Platt Scaling ham modelin LogLoss'unu düşürmedi; kalibrasyon bu protokolde "
            "genelleme performansını iyileştirmedi."
        )
    elif platt_ll > TARGET_LOG_LOSS:
        print(
            "\nSONUÇ: Platt ham LogLoss'u düşürdü ancak 0.66 hedefini karşılamadı. "
            "Kalibrasyon küçük bir iyileşme sağlamış olabilir; hedeflenen tahmin gücüne ulaşılamadı."
        )
    else:
        print(
            "\nSONUÇ: Platt ham LogLoss'u düşürdü ve 0.66 hedefini karşıladı. "
            "Bu sonuç tek başına bahis kârlılığını veya istatistiksel üstünlüğü kanıtlamaz."
        )

    print("\nÇıktılar:")
    print(f"  Özet: {SUMMARY_PATH}")
    print(f"  Kalibrasyon bantları: {CALIBRATION_PATH}")
    print(f"  Maç/bahis ayrıntıları: {BETS_PATH}")
    print(
        "\nYöntem notu: Model C sadece eğitim sezonlarında fit edildi. Isotonic ve "
        "CalibratedClassifierCV(method='sigmoid') yalnızca 2017/2018 kalibrasyon sezonunu "
        "kullandı. 2018/2019–2019/2020 test sezonları hiçbir fit/ayar adımında kullanılmadı. "
        "ROI sabit 1 birim bahis başına hesaplandı; pozitif ROI tek başına güvenilir avantaj kanıtı değildir."
    )


if __name__ == "__main__":
    main()
