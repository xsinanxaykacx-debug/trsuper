"""Chronological OU 2.5 stacking evaluation against the legacy XGBoost baseline.

Protocol:
- Model training cohort: 2012/2013 through 2016/2017.
- 2017/2018 is not used for fitting or evaluation; its results may inform
  historical pre-match features for later matches.
- Fixed out-of-sample test: 2018/2019 and 2019/2020.
- Every model uses the same test matches with valid Under and Over odds.
- Target: _y_ou25 = 1 for OVER 2.5, 0 for UNDER 2.5.
- At most one 1-unit bet per match: choose the side with higher EV if EV > 0.05.
- Stacking meta-features are generated with expanding chronological folds.
  Test data is never used for fitting, calibration, threshold selection, or tuning.

Run from repository root:
    python -m src.stacking_value_bet

Required packages:
    pip install xgboost lightgbm catboost scikit-learn scipy pandas numpy
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from scipy.stats import t
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
from xgboost import XGBClassifier

from src.ablation_study import EV_THRESHOLD, MIN_TRAIN_ROWS, add_momentum, make_model
from src.features import calculate_elo_features
from src.load_global import load_global_data

RANDOM_STATE = 42
TRAIN_SEASONS = [
    "2012/2013",
    "2013/2014",
    "2014/2015",
    "2015/2016",
    "2016/2017",
]
TEST_SEASONS = ["2018/2019", "2019/2020"]
EPS = 1e-7
N_BOOTSTRAP = 1000

BASE_FEATURES = [
    "elo_h", "elo_a", "elo_diff",
    "form_h_pts_5", "form_h_gf_5", "form_h_ga_5",
    "form_a_pts_5", "form_a_gf_5", "form_a_ga_5",
    "form_h_pts_10", "form_h_gf_10", "form_h_ga_10",
    "form_a_pts_10", "form_a_gf_10", "form_a_ga_10",
    "form_h_home_pts", "form_h_home_gf", "form_h_home_ga",
    "form_a_away_pts", "form_a_away_gf", "form_a_away_ga",
]
REST_FEATURES = ["rest_h", "rest_a"]
MOMENTUM_FEATURES = [
    "momentum_h_pts", "momentum_h_gf", "momentum_h_ga",
    "momentum_a_pts", "momentum_a_gf", "momentum_a_ga",
]
FEATURES = BASE_FEATURES + REST_FEATURES + MOMENTUM_FEATURES

OUTPUT_DIR = Path("data/csv")
SUMMARY_PATH = OUTPUT_DIR / "stacking_value_bet_summary.csv"
BETS_PATH = OUTPUT_DIR / "stacking_value_bet_ledger.csv"
PREDICTIONS_PATH = OUTPUT_DIR / "stacking_value_bet_predictions.csv"
COMPARISON_PATH = OUTPUT_DIR / "stacking_value_bet_paired_bootstrap.csv"


def valid_decimal_odds(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values.notna() & np.isfinite(values) & values.gt(1.0)


def make_base_models() -> dict[str, Any]:
    """Return freshly initialized base models; no fitted artifacts are assumed."""
    return {
        "xgb": make_model(),
        "lightgbm": LGBMClassifier(
            objective="binary",
            n_estimators=350,
            learning_rate=0.04,
            num_leaves=15,
            max_depth=4,
            min_child_samples=30,
            subsample=0.8,
            subsample_freq=1,
            colsample_bytree=0.8,
            reg_lambda=1.0,
            random_state=RANDOM_STATE,
            n_jobs=-1,
            verbosity=-1,
        ),
        "catboost": CatBoostClassifier(
            loss_function="Logloss",
            iterations=350,
            depth=4,
            learning_rate=0.04,
            l2_leaf_reg=3.0,
            random_seed=RANDOM_STATE,
            verbose=False,
            allow_writing_files=False,
            thread_count=-1,
        ),
    }


def make_feature_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in FEATURES if column not in frame.columns]
    if missing:
        raise KeyError(f"Model özellikleri eksik: {missing}")
    return (
        frame.loc[:, FEATURES]
        .replace([np.inf, -np.inf], np.nan)
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0.0)
        .astype(np.float32)
    )


def chronological_oof_predictions(
    X: pd.DataFrame,
    y: np.ndarray,
    dates: pd.Series,
    n_validation_blocks: int = 4,
) -> tuple[np.ndarray, np.ndarray]:
    """Expanding-window OOF probabilities, with all same-day matches kept together.

    The earliest block(s) are used only as initial training history. Later blocks
    receive predictions from models fitted strictly on earlier dates.
    """
    unique_dates = np.array(sorted(pd.to_datetime(dates).dropna().unique()))
    if len(unique_dates) < n_validation_blocks + 2:
        raise RuntimeError(
            f"OOF için tarih sayısı yetersiz: {len(unique_dates)} "
            f"(en az {n_validation_blocks + 2} gerekli)."
        )

    blocks = [block for block in np.array_split(unique_dates, n_validation_blocks + 1) if len(block)]
    oof = np.full((len(X), 3), np.nan, dtype=float)
    assigned = np.zeros(len(X), dtype=bool)
    date_values = pd.to_datetime(dates).to_numpy()

    # First two date blocks are the initial historical training window.
    for block_index in range(2, len(blocks)):
        validation_dates = blocks[block_index]
        validation_start = validation_dates[0]
        train_mask = date_values < validation_start
        validation_mask = np.isin(date_values, validation_dates)

        if int(train_mask.sum()) < MIN_TRAIN_ROWS or not validation_mask.any():
            continue
        if np.unique(y[train_mask]).size != 2:
            continue

        models = make_base_models()
        for column_index, model_name in enumerate(("xgb", "lightgbm", "catboost")):
            model = models[model_name]
            model.fit(X.loc[train_mask], y[train_mask])
            oof[validation_mask, column_index] = model.predict_proba(
                X.loc[validation_mask]
            )[:, 1]
        assigned[validation_mask] = True

    usable = assigned & np.isfinite(oof).all(axis=1)
    if int(usable.sum()) < 1000:
        raise RuntimeError(
            f"Stacking meta-modeli için yeterli kronolojik OOF tahmini yok: {int(usable.sum())}"
        )
    if np.unique(y[usable]).size != 2:
        raise RuntimeError("OOF kümesinde hedefin iki sınıfı da bulunmalı.")
    return oof, usable


def roi_confidence_interval(profits: np.ndarray) -> tuple[float, float]:
    """Approximate 95% Student-t interval for mean profit per bet (ROI)."""
    values = np.asarray(profits, dtype=float)
    if len(values) < 2:
        return np.nan, np.nan
    standard_error = values.std(ddof=1) / np.sqrt(len(values))
    half_width = standard_error * t.ppf(0.975, len(values) - 1)
    return float(values.mean() - half_width), float(values.mean() + half_width)


def evaluate_strategy(
    frame: pd.DataFrame,
    p_over: np.ndarray,
    model_name: str,
) -> tuple[dict[str, Any], pd.DataFrame, np.ndarray, np.ndarray]:
    y = frame["_y_ou25"].astype(int).to_numpy()
    p = np.clip(np.asarray(p_over, dtype=float), EPS, 1.0 - EPS)
    if len(p) != len(frame):
        raise ValueError(f"{model_name}: tahmin sayısı test satırlarıyla eşleşmiyor.")

    odds_under = frame["_odd_under25"].to_numpy(dtype=float)
    odds_over = frame["_odd_over25"].to_numpy(dtype=float)
    ev_under = (1.0 - p) * odds_under - 1.0
    ev_over = p * odds_over - 1.0
    choose_over = ev_over > ev_under
    best_ev = np.maximum(ev_under, ev_over)
    take = best_ev > EV_THRESHOLD
    chosen_odds = np.where(choose_over, odds_over, odds_under)
    chosen_side = choose_over.astype(np.int8)  # 0 = ALT, 1 = ÜST

    # Profit is zero for a match with no qualifying bet; this supports paired
    # comparisons on the exact same out-of-sample match cohort.
    per_match_profit = np.zeros(len(frame), dtype=float)
    per_match_profit[take] = np.where(
        y[take] == chosen_side[take],
        chosen_odds[take] - 1.0,
        -1.0,
    )
    bet_profits = per_match_profit[take]
    ci_low, ci_high = roi_confidence_interval(bet_profits)
    bet_count = int(take.sum())
    total_profit = float(per_match_profit.sum())
    roi = float(bet_profits.mean() * 100.0) if bet_count else np.nan
    brier = float(brier_score_loss(y, p))
    ll = float(log_loss(y, np.column_stack([1.0 - p, p]), labels=[0, 1]))

    summary = {
        "model": model_name,
        "train_seasons": f"{TRAIN_SEASONS[0]}–{TRAIN_SEASONS[-1]}",
        "test_seasons": ",".join(TEST_SEASONS),
        "test_matches": int(len(frame)),
        "log_loss": ll,
        "brier_score": brier,
        "ev_threshold": EV_THRESHOLD,
        "bets": bet_count,
        "bet_coverage_pct": float(bet_count / len(frame) * 100.0),
        "wins": int(np.sum(bet_profits > 0.0)),
        "losses": int(np.sum(bet_profits < 0.0)),
        "total_profit_1u": total_profit,
        "roi_pct": roi,
        "roi_ci95_low_pct": ci_low * 100.0 if np.isfinite(ci_low) else np.nan,
        "roi_ci95_high_pct": ci_high * 100.0 if np.isfinite(ci_high) else np.nan,
        "roi_ci95_includes_zero": (
            bool(ci_low <= 0.0 <= ci_high)
            if np.isfinite(ci_low) and np.isfinite(ci_high)
            else None
        ),
    }

    ledger = frame[
        ["_id", "_date", "_season", "Ev_Sahibi", "Deplasman", "_y_ou25",
         "_odd_under25", "_odd_over25"]
    ].copy()
    ledger["model"] = model_name
    ledger["p_over25"] = p
    ledger["p_under25"] = 1.0 - p
    ledger["ev_under25"] = ev_under
    ledger["ev_over25"] = ev_over
    ledger["best_ev"] = best_ev
    ledger["bet_taken"] = take
    ledger["selected_market"] = np.where(choose_over, "UST", "ALT")
    ledger["selected_odds"] = chosen_odds
    ledger["bet_won"] = np.where(take, y == chosen_side, False)
    ledger["profit_1u"] = per_match_profit
    return summary, ledger, per_match_profit, take


def paired_bootstrap_comparison(
    frame: pd.DataFrame,
    profits_by_model: dict[str, np.ndarray],
    bets_by_model: dict[str, np.ndarray],
    n_bootstrap: int = N_BOOTSTRAP,
) -> pd.DataFrame:
    """Paired match-level bootstrap for total-profit and ROI differences."""
    if len(frame) < 2:
        raise ValueError("Bootstrap için en az iki test maçı gerekli.")
    if "STACKING" not in profits_by_model or "XGBOOST_BASELINE" not in profits_by_model:
        raise KeyError("STACKING ve XGBOOST_BASELINE sonuçları gerekli.")

    stack_profit = profits_by_model["STACKING"]
    xgb_profit = profits_by_model["XGBOOST_BASELINE"]
    stack_bets = bets_by_model["STACKING"]
    xgb_bets = bets_by_model["XGBOOST_BASELINE"]
    n = len(frame)
    rng = np.random.default_rng(RANDOM_STATE)
    profit_difference_per_match = stack_profit - xgb_profit
    bootstrap_total_profit_diff = np.empty(n_bootstrap, dtype=float)
    bootstrap_roi_diff = np.full(n_bootstrap, np.nan, dtype=float)

    for replicate in range(n_bootstrap):
        indices = rng.integers(0, n, size=n)
        bootstrap_total_profit_diff[replicate] = profit_difference_per_match[indices].sum()

        stack_count = int(stack_bets[indices].sum())
        xgb_count = int(xgb_bets[indices].sum())
        if stack_count and xgb_count:
            stack_roi = stack_profit[indices].sum() / stack_count
            xgb_roi = xgb_profit[indices].sum() / xgb_count
            bootstrap_roi_diff[replicate] = (stack_roi - xgb_roi) * 100.0

    total_low, total_high = np.percentile(bootstrap_total_profit_diff, [2.5, 97.5])
    valid_roi_diff = bootstrap_roi_diff[np.isfinite(bootstrap_roi_diff)]
    if len(valid_roi_diff) >= int(0.95 * n_bootstrap):
        roi_low, roi_high = np.percentile(valid_roi_diff, [2.5, 97.5])
    else:
        roi_low, roi_high = np.nan, np.nan

    observed_profit_diff = float(stack_profit.sum() - xgb_profit.sum())
    stack_count = int(stack_bets.sum())
    xgb_count = int(xgb_bets.sum())
    stack_roi = stack_profit.sum() / stack_count * 100.0 if stack_count else np.nan
    xgb_roi = xgb_profit.sum() / xgb_count * 100.0 if xgb_count else np.nan

    return pd.DataFrame([{
        "comparison": "STACKING_minus_XGBOOST_BASELINE",
        "test_matches": n,
        "bootstrap_replicates": n_bootstrap,
        "stacking_bets": stack_count,
        "xgboost_bets": xgb_count,
        "stacking_total_profit_1u": float(stack_profit.sum()),
        "xgboost_total_profit_1u": float(xgb_profit.sum()),
        "total_profit_difference_1u": observed_profit_diff,
        "total_profit_difference_ci95_low_1u": float(total_low),
        "total_profit_difference_ci95_high_1u": float(total_high),
        "total_profit_difference_ci95_includes_zero": bool(total_low <= 0.0 <= total_high),
        "stacking_roi_pct": float(stack_roi),
        "xgboost_roi_pct": float(xgb_roi),
        "roi_difference_pp_stacking_minus_xgboost": float(stack_roi - xgb_roi),
        "roi_difference_ci95_low_pp": float(roi_low) if np.isfinite(roi_low) else np.nan,
        "roi_difference_ci95_high_pp": float(roi_high) if np.isfinite(roi_high) else np.nan,
        "roi_difference_ci95_includes_zero": (
            bool(roi_low <= 0.0 <= roi_high) if np.isfinite(roi_low) else None
        ),
        "higher_total_profit": (
            "STACKING" if observed_profit_diff > 0.0
            else "XGBOOST_BASELINE" if observed_profit_diff < 0.0
            else "TIE"
        ),
    }])


def main() -> None:
    print("1. 180k veri seti yükleniyor...")
    matches = load_global_data().copy()
    required = {
        "_id", "_date", "_season", "Ev_Sahibi", "Deplasman",
        "MSE", "MSD", "_y", "_y_ou25", "_odd_under25", "_odd_over25",
    }
    missing = sorted(required - set(matches.columns))
    if missing:
        raise KeyError(f"Global veri setinde gerekli sütunlar eksik: {missing}")
    if matches["_id"].duplicated().any():
        raise ValueError("Veri setinde yinelenen _id var.")

    matches["_date"] = pd.to_datetime(matches["_date"], errors="coerce")
    matches["_season"] = matches["_season"].astype(str).str.strip()
    matches["_y_ou25"] = pd.to_numeric(matches["_y_ou25"], errors="coerce")
    matches = matches.dropna(subset=["_date", "_season", "_y_ou25"]).copy()
    matches["_y_ou25"] = matches["_y_ou25"].astype(int)
    if not matches["_y_ou25"].isin([0, 1]).all():
        raise ValueError("_y_ou25 yalnızca 0 (ALT) ve 1 (ÜST) olabilir.")

    missing_train = sorted(set(TRAIN_SEASONS) - set(matches["_season"].unique()))
    missing_test = sorted(set(TEST_SEASONS) - set(matches["_season"].unique()))
    if missing_train or missing_test:
        raise ValueError(
            f"Sezon eksik. Eğitimde bulunmayan: {missing_train}; "
            f"testte bulunmayan: {missing_test}"
        )

    print("2. Maç öncesi özellikler hesaplanıyor...")
    features = add_momentum(calculate_elo_features(matches))
    data = matches.merge(features, on="_id", how="inner", validate="one_to_one")
    data = data.sort_values(["_date", "_id"], kind="stable").reset_index(drop=True)

    train = data[data["_season"].isin(TRAIN_SEASONS)].copy().reset_index(drop=True)
    test_raw = data[data["_season"].isin(TEST_SEASONS)].copy()
    valid_odds = (
        valid_decimal_odds(test_raw["_odd_under25"])
        & valid_decimal_odds(test_raw["_odd_over25"])
    )
    test = test_raw.loc[valid_odds].copy().reset_index(drop=True)

    if len(train) < MIN_TRAIN_ROWS:
        raise RuntimeError(f"Eğitim maçı yetersiz: {len(train)}")
    if train["_y_ou25"].nunique() != 2:
        raise RuntimeError("Eğitim kümesinde ALT ve ÜST sınıflarının ikisi de bulunmalı.")
    if test.empty:
        raise RuntimeError("Test sezonlarında iki tarafı da geçerli oranlı maç yok.")

    print(f"   Eğitim: {TRAIN_SEASONS[0]}–{TRAIN_SEASONS[-1]} | {len(train):,} maç")
    print(f"   Test: {', '.join(TEST_SEASONS)} | ham={len(test_raw):,} | geçerli oran={len(test):,}")
    print(f"   Sabit bahis eşiği: EV > {EV_THRESHOLD:.2f} | 1 birim | maç başına en fazla bir bahis")

    X_train = make_feature_matrix(train)
    X_test = make_feature_matrix(test)
    y_train = train["_y_ou25"].astype(int).to_numpy()
    y_test = test["_y_ou25"].astype(int).to_numpy()

    print("\n3. Eski XGBoost baseline eğitiliyor...")
    xgb_baseline = make_model()
    xgb_baseline.fit(X_train, y_train)
    p_xgb = np.clip(xgb_baseline.predict_proba(X_test)[:, 1], EPS, 1.0 - EPS)

    print("\n4. Stacking için kronolojik OOF tahminleri oluşturuluyor...")
    oof_predictions, usable_oof = chronological_oof_predictions(
        X_train,
        y_train,
        train["_date"],
    )
    meta_model = LogisticRegression(
        C=1.0,
        solver="lbfgs",
        max_iter=2000,
        random_state=RANDOM_STATE,
    )
    meta_model.fit(oof_predictions[usable_oof], y_train[usable_oof])

    print("5. XGBoost + LightGBM + CatBoost tam eğitim kümesinde yeniden eğitiliyor...")
    full_base_models = make_base_models()
    base_test_probabilities = np.zeros((len(test), 3), dtype=float)
    for index, model_name in enumerate(("xgb", "lightgbm", "catboost")):
        model = full_base_models[model_name]
        model.fit(X_train, y_train)
        base_test_probabilities[:, index] = model.predict_proba(X_test)[:, 1]
        print(f"   {model_name}: tamamlandı")

    p_stacking = np.clip(
        meta_model.predict_proba(base_test_probabilities)[:, 1],
        EPS,
        1.0 - EPS,
    )

    print("\n6. Aynı test maçlarında bahis sonuçları hesaplanıyor...")
    model_predictions = {
        "XGBOOST_BASELINE": p_xgb,
        "STACKING": p_stacking,
    }
    summaries: list[dict[str, Any]] = []
    ledgers: list[pd.DataFrame] = []
    profits_by_model: dict[str, np.ndarray] = {}
    bets_by_model: dict[str, np.ndarray] = {}
    prediction_rows = test[
        ["_id", "_date", "_season", "Ev_Sahibi", "Deplasman", "_y_ou25",
         "_odd_under25", "_odd_over25"]
    ].copy()

    for model_name, probabilities in model_predictions.items():
        summary, ledger, profits, bet_mask = evaluate_strategy(test, probabilities, model_name)
        summaries.append(summary)
        ledgers.append(ledger)
        profits_by_model[model_name] = profits
        bets_by_model[model_name] = bet_mask
        prediction_rows[f"{model_name.lower()}_p_over25"] = probabilities
        print(
            f"   {model_name:<18} | LogLoss={summary['log_loss']:.5f} "
            f"| bahis={summary['bets']:,} | kâr={summary['total_profit_1u']:+.2f} "
            f"| ROI=%{summary['roi_pct']:+.2f} "
            f"| %95 GA=[%{summary['roi_ci95_low_pct']:+.2f}, "
            f"%{summary['roi_ci95_high_pct']:+.2f}]"
        )

    print("\n7. Stacking ile XGBoost farkı için eşleştirilmiş bootstrap...")
    comparison = paired_bootstrap_comparison(
        test,
        profits_by_model,
        bets_by_model,
        n_bootstrap=N_BOOTSTRAP,
    )
    row = comparison.iloc[0]
    print(
        f"   Toplam kâr farkı (Stacking - XGBoost): "
        f"{row['total_profit_difference_1u']:+.2f} birim "
        f"| %95 GA=[{row['total_profit_difference_ci95_low_1u']:+.2f}, "
        f"{row['total_profit_difference_ci95_high_1u']:+.2f}]"
    )
    print(
        f"   ROI farkı: {row['roi_difference_pp_stacking_minus_xgboost']:+.2f} yüzde puan "
        f"| %95 bootstrap GA=[{row['roi_difference_ci95_low_pp']:+.2f}, "
        f"{row['roi_difference_ci95_high_pp']:+.2f}]"
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(summaries).to_csv(SUMMARY_PATH, index=False, encoding="utf-8-sig")
    pd.concat(ledgers, ignore_index=True).to_csv(BETS_PATH, index=False, encoding="utf-8-sig")
    prediction_rows.to_csv(PREDICTIONS_PATH, index=False, encoding="utf-8-sig")
    comparison.to_csv(COMPARISON_PATH, index=False, encoding="utf-8-sig")

    print("\n=== FİNAL RAPOR DOSYALARI ===")
    print(f"Özet: {SUMMARY_PATH}")
    print(f"Bahis defteri: {BETS_PATH}")
    print(f"Tahminler: {PREDICTIONS_PATH}")
    print(f"Eşleştirilmiş bootstrap: {COMPARISON_PATH}")
    print("\nNot: 0.68472 önceki çalışmanın bildirilen skorudur; bu betik skoru sabit kabul etmez.")
    print("Stacking LogLoss ve kârlılığı bu sabit eğitim/test protokolünde yeniden hesaplanır.")


if __name__ == "__main__":
    main()
