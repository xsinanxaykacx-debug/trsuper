"""Run the MVP with combined Turkish and EPL training data.

Run from any working directory:
    python -m src.run_mvp_with_epl

The v1.6 reference IDs remain the only test set. Training and validation are
restricted to combined-data matches dated before the earliest reference-test
match to avoid training on future outcomes.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.evaluate import calc_metrics
from src.features import calculate_elo_features
from src.load import load_data, load_v16_reference
from src.load_epl import load_epl_data
from src.models.elo import EloModel
from src.models.market import MarketModel
from src.models.poisson import PoissonModel
from src.models.xgboost_model import XGBoostModel


ROOT = Path(__file__).resolve().parents[1]
EPL_CSV = ROOT / "data" / "csv" / "EPL.csv"
EXPECTED_TEST_MATCHES = 5854
ODDS_COLUMNS = ["_odd_H", "_odd_D", "_odd_A"]


def _valid_market_rows(df: pd.DataFrame) -> np.ndarray:
    """Rows with three usable decimal odds."""
    odds = df[ODDS_COLUMNS].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
    return np.isfinite(odds).all(axis=1) & (odds > 1.0).all(axis=1)


def _metrics_line(name: str, y_true: np.ndarray, probabilities: np.ndarray) -> str:
    metrics = calc_metrics(y_true, probabilities)
    return (
        f"{name:24s} | LogLoss: {metrics['log_loss']:.4f} "
        f"| Brier: {metrics['brier']:.4f} "
        f"| Accuracy: %{metrics['accuracy'] * 100:.2f} "
        f"| N={metrics['n_matches']}"
    )


def _predict_market(model: MarketModel, df: pd.DataFrame) -> np.ndarray:
    """Predict only where all three market odds are present and usable."""
    probabilities = np.full((len(df), 3), np.nan, dtype=float)
    valid = _valid_market_rows(df)
    if valid.any():
        probabilities[valid] = model.predict_proba(df.loc[valid])
    return probabilities


def _assert_probabilities(name: str, probabilities: np.ndarray) -> None:
    finite_rows = np.isfinite(probabilities).all(axis=1)
    if finite_rows.any():
        rows = probabilities[finite_rows]
        assert (rows >= 0.0).all(), f"{name}: negative probabilities detected"
        assert np.allclose(rows.sum(axis=1), 1.0, atol=1e-6), (
            f"{name}: probability rows do not sum to 1"
        )


def main() -> None:
    print("1. Loading Turkish data, fixed v1.6 reference, and EPL data...")
    turkiye_df = load_data(root_path=ROOT)
    reference_df = load_v16_reference(root_path=ROOT)

    if not EPL_CSV.is_file():
        raise FileNotFoundError(
            f"EPL CSV not found: {EPL_CSV}\n"
            "Finish the download and place the completed file at data/csv/EPL.csv."
        )

    required_reference_columns = {"_id", "season", "p_rf_H", "p_rf_D", "p_rf_A"}
    missing_reference = required_reference_columns.difference(reference_df.columns)
    if missing_reference:
        raise ValueError(
            "v1.6 reference is missing required columns: "
            + ", ".join(sorted(missing_reference))
        )
    assert not reference_df["_id"].duplicated().any(), "Duplicate IDs in v1.6 reference"
    assert len(reference_df) == EXPECTED_TEST_MATCHES, (
        f"Expected {EXPECTED_TEST_MATCHES} fixed v1.6 test rows, "
        f"found {len(reference_df)}. Do not regenerate or silently alter the benchmark."
    )

    reference_ids = set(pd.to_numeric(reference_df["_id"], errors="raise").astype("int64"))
    turkiye_ids = set(pd.to_numeric(turkiye_df["_id"], errors="raise").astype("int64"))
    missing_test_ids = reference_ids.difference(turkiye_ids)
    if missing_test_ids:
        raise ValueError(
            f"{len(missing_test_ids)} v1.6 reference IDs are missing from Turkish DATA.csv."
        )

    epl_df = load_epl_data(EPL_CSV, existing_ids=turkiye_df["_id"].tolist())
    print(f"   Türkiye: {len(turkiye_df):,} rows | EPL valid completed matches: {len(epl_df):,}")

    print("2. Concatenating datasets and validating IDs/schema...")
    combined_df = pd.concat([turkiye_df, epl_df], ignore_index=True, sort=False)
    assert combined_df["_id"].notna().all(), "Missing _id after concatenation"
    assert not combined_df["_id"].duplicated().any(), "Duplicate _id after concatenation"
    assert set(epl_df["_id"]).isdisjoint(turkiye_ids), "EPL IDs collide with Turkish IDs"
    assert {"_date", "_season", "_y", "Ev_Sahibi", "Deplasman", "MSE", "MSD"}.issubset(
        combined_df.columns
    ), "Combined data is missing required feature/model columns"

    combined_df["_date"] = pd.to_datetime(combined_df["_date"], errors="coerce")
    combined_df = combined_df.dropna(
        subset=["_date", "_season", "_y", "Ev_Sahibi", "Deplasman", "MSE", "MSD"]
    ).copy()
    combined_df["_id"] = pd.to_numeric(combined_df["_id"], errors="raise").astype("int64")
    combined_df["_y"] = combined_df["_y"].astype(str)
    combined_df = combined_df[combined_df["_y"].isin(["H", "D", "A"])].copy()
    if combined_df["_id"].duplicated().any():
        raise AssertionError("Duplicate _id introduced while cleaning combined data")

    print(f"   Combined valid rows: {len(combined_df):,}")
    print(
        f"   Combined date span: {combined_df['_date'].min().date()} "
        f"to {combined_df['_date'].max().date()}"
    )

    print("3. Computing pre-match Elo/form/H2H features across the combined history...")
    # PR #4's feature implementation uses (league, team) keys. Season suffixes
    # are stripped by the feature helper so each league's team history continues
    # across seasons without mixing EPL and Turkish teams.
    features = calculate_elo_features(combined_df)
    assert not features["_id"].duplicated().any(), "Feature output contains duplicate IDs"
    full_df = combined_df.merge(features, on="_id", how="left", validate="one_to_one")
    if len(full_df) != len(combined_df):
        raise AssertionError("Feature merge changed the number of matches")

    print("4. Creating chronological Train / Validation splits and fixed v1.6 Test...")
    reference_ids = set(reference_df["_id"].astype("int64"))
    test_df = full_df[full_df["_id"].isin(reference_ids)].copy()
    test_df = test_df.merge(
        reference_df[["_id", "season", "p_rf_H", "p_rf_D", "p_rf_A"]],
        on="_id",
        how="left",
        validate="one_to_one",
        suffixes=("", "_reference"),
    )
    assert len(test_df) == EXPECTED_TEST_MATCHES, (
        f"Fixed test set should contain {EXPECTED_TEST_MATCHES} matches, found {len(test_df)}"
    )
    assert set(test_df["_id"]) == reference_ids, "Test IDs differ from the fixed v1.6 IDs"
    assert test_df["Lig/Sezon"].astype(str).str.contains("EPL", case=False).sum() == 0, (
        "The fixed v1.6 test set must contain Turkish matches only"
    )

    earliest_test_date = test_df["_date"].min()
    pretest_df = full_df[
        (full_df["_date"] < earliest_test_date)
        & (~full_df["_id"].isin(reference_ids))
    ].copy()
    if pretest_df.empty:
        raise ValueError("No combined-data matches exist before the fixed test period.")

    # Validation is the latest season entirely before the test begins.
    season_end_dates = pretest_df.groupby("_season")["_date"].max().sort_values()
    validation_season = season_end_dates.index[-1]
    validation_start = pretest_df.loc[
        pretest_df["_season"] == validation_season, "_date"
    ].min()
    val_df = pretest_df[pretest_df["_season"] == validation_season].copy()
    train_df = pretest_df[pretest_df["_date"] < validation_start].copy()

    if train_df.empty or val_df.empty:
        raise ValueError(
            "Chronological split produced an empty Train or Validation set. "
            "Check the date range and season labels in both datasets."
        )
    assert train_df["_date"].max() < val_df["_date"].min(), "Train/Validation time leakage"
    assert val_df["_date"].max() < test_df["_date"].min(), "Validation/Test time leakage"
    assert not set(train_df["_id"]) & reference_ids, "Test IDs leaked into Train"
    assert not set(val_df["_id"]) & reference_ids, "Test IDs leaked into Validation"

    print(f"   Train: {len(train_df):,} | Validation: {len(val_df):,} ({validation_season})")
    print(f"   Fixed Turkish test: {len(test_df):,} | earliest date: {earliest_test_date.date()}")

    print("5. Fitting Elo, Poisson, and Z-Kahin (XGBoost) on combined Train data...")
    elo_model = EloModel().fit(train_df, train_df["_y"].to_numpy())
    poisson_model = PoissonModel().fit(train_df)
    xgb_model = XGBoostModel().fit(train_df, train_df["_y"].to_numpy())

    # Diagnostic companion: same XGBoost architecture without market odds.
    # The repository's default XGBoost feature list includes odds, so reporting
    # this variant avoids mistaking market information for an independent edge.
    xgb_no_odds = XGBoostModel()
    xgb_no_odds.features = [column for column in xgb_no_odds.features if column not in ODDS_COLUMNS]
    xgb_no_odds.fit(train_df, train_df["_y"].to_numpy())

    print("6. Evaluating Validation predictions (no test fitting/tuning)...")
    validation_predictions = {
        "Elo": elo_model.predict_proba(val_df),
        "Poisson": poisson_model.predict_proba(val_df),
        "Market": _predict_market(MarketModel(), val_df),
        "Z-Kahin (odds included)": xgb_model.predict_proba(val_df),
        "Z-Kahin (no odds)": xgb_no_odds.predict_proba(val_df),
    }
    validation_y = val_df["_y"].to_numpy()
    validation_common = np.isfinite(validation_y.astype(str)) & np.isin(validation_y, ["H", "D", "A"])
    for probabilities in validation_predictions.values():
        validation_common &= np.isfinite(probabilities).all(axis=1)
    if validation_common.any():
        print(f"   Common validation rows: {validation_common.sum():,} / {len(val_df):,}")
        for name, probabilities in validation_predictions.items():
            print("   " + _metrics_line(name, validation_y[validation_common], probabilities[validation_common]))
    else:
        print("   No common rows with valid predictions across every model; per-model test metrics will still be reported.")

    print("7. Scoring every model on the unchanged 5,854-match Turkish test reference...")
    market_model = MarketModel()
    predictions = {
        "v1.6 Random Forest": test_df[["p_rf_H", "p_rf_D", "p_rf_A"]].to_numpy(dtype=float),
        "Market": _predict_market(market_model, test_df),
        "Elo": elo_model.predict_proba(test_df),
        "Poisson": poisson_model.predict_proba(test_df),
        "Z-Kahin (odds included)": xgb_model.predict_proba(test_df),
        "Z-Kahin (no odds)": xgb_no_odds.predict_proba(test_df),
    }
    for name, probabilities in predictions.items():
        _assert_probabilities(name, probabilities)

    y_test = test_df["_y"].to_numpy()
    print("\n" + "=" * 94)
    print("FIXED v1.6 TURKISH TEST — PER-MODEL AVAILABLE ROWS")
    print("=" * 94)
    for name, probabilities in predictions.items():
        valid = np.isin(y_test, ["H", "D", "A"]) & np.isfinite(probabilities).all(axis=1)
        if not valid.any():
            print(f"{name:24s} | No valid predictions")
            continue
        print(_metrics_line(name, y_test[valid], probabilities[valid]))

    common_mask = np.isin(y_test, ["H", "D", "A"])
    for probabilities in predictions.values():
        common_mask &= np.isfinite(probabilities).all(axis=1)
    print("\n" + "=" * 94)
    print(f"FAIR COMPARISON — SAME TEST ROWS FOR EVERY MODEL: {common_mask.sum():,}/{len(test_df):,}")
    print("=" * 94)
    if common_mask.any():
        for name, probabilities in predictions.items():
            print(" " + _metrics_line(name, y_test[common_mask], probabilities[common_mask]))
    else:
        print("No common rows have valid predictions for all models; inspect missing market odds/reference probabilities.")

    print("\nNote: Z-Kahin with odds uses market odds as input features; the no-odds variant is the cleaner test of independent signal.")
    print("No claim that any model beats the market is made unless the metrics support it.")


if __name__ == "__main__":
    main()
