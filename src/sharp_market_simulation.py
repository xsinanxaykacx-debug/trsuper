"""Synthetic low-margin market simulation for Model C.

Run from repository root:
    python -m src.sharp_market_simulation

Important interpretation:
- Model C is trained on 2012/2013–2017/2018 and tested chronologically on
  2018/2019–2019/2020, matching src/ablation_study.py.
- Bets are selected with the Turkish odds and EV > 0.05, exactly as in the
  existing Model C evaluation.
- Synthetic sharp odds are defined as (1 / model probability) * 0.98.
  They are NOT historical Pinnacle/Betfair prices and are not independent
  market observations. At the model's own probabilities, their theoretical
  expected return is exactly -2% per unit staked. This experiment therefore
  cannot prove that the model beats a real low-margin market.
- The 20% bankroll strategy stakes 20% of the current bankroll per bet. This
  is a bankroll fraction, not a true Kelly fraction derived from edge.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t

from src.ablation_study import (
    EV_THRESHOLD,
    MIN_TRAIN_ROWS,
    MOMENTUM_FEATURES,
    REST_FEATURES,
    TEST_SEASONS,
    TRAIN_SEASONS,
    add_momentum,
    make_model,
)
from src.features import calculate_elo_features
from src.load_global import load_global_data


SHARP_MARGIN = 0.02
SHARP_PRICE_FACTOR = 1.0 - SHARP_MARGIN
INITIAL_BANKROLL = 100.0
BANKROLL_STAKE_FRACTION = 0.20
FLAT_STAKE = 1.0
EPS = 1e-9
OUTPUT_DIR = Path("data/csv")
LEDGER_PATH = OUTPUT_DIR / "sharp_market_simulation_bet_ledger.csv"
SUMMARY_PATH = OUTPUT_DIR / "sharp_market_simulation_summary.csv"

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
    "_y_ou25", "_odd_under25", "_odd_over25",
}


def valid_decimal_odds(series: pd.Series) -> pd.Series:
    """True for finite decimal odds strictly greater than 1.00."""
    values = pd.to_numeric(series, errors="coerce")
    return values.notna() & np.isfinite(values) & values.gt(1.0)


def roi_confidence_interval(profits: np.ndarray, confidence: float = 0.95) -> tuple[float, float]:
    """Approximate Student-t CI for mean profit per unit stake."""
    values = np.asarray(profits, dtype=float)
    if len(values) < 2:
        return np.nan, np.nan
    standard_error = values.std(ddof=1) / np.sqrt(len(values))
    half_width = standard_error * t.ppf((1.0 + confidence) / 2.0, len(values) - 1)
    return float(values.mean() - half_width), float(values.mean() + half_width)


def select_model_c_bets(test: pd.DataFrame, p_over: np.ndarray) -> pd.DataFrame:
    """Select bets by highest Turkish-odds EV, requiring EV > 0.05."""
    out = test.copy().reset_index(drop=True)
    p = np.clip(np.asarray(p_over, dtype=float), 1e-7, 1.0 - 1e-7)
    if len(p) != len(out):
        raise ValueError("Tahmin sayısı ile test satırı sayısı eşleşmiyor.")

    odds_under = out["_odd_under25"].to_numpy(dtype=float)
    odds_over = out["_odd_over25"].to_numpy(dtype=float)
    actual_over = out["_y_ou25"].astype(int).to_numpy()

    p_under = 1.0 - p
    ev_under_tr = p_under * odds_under - 1.0
    ev_over_tr = p * odds_over - 1.0
    choose_over = ev_over_tr > ev_under_tr
    best_ev_tr = np.maximum(ev_under_tr, ev_over_tr)
    take = best_ev_tr > EV_THRESHOLD

    out["p_over_model"] = p
    out["p_under_model"] = p_under
    out["ev_under_turkey"] = ev_under_tr
    out["ev_over_turkey"] = ev_over_tr
    out["best_ev_turkey"] = best_ev_tr
    out["selected_side"] = np.where(choose_over, "UST", "ALT")
    out["selected_model_probability"] = np.where(choose_over, p, p_under)
    out["actual_side"] = np.where(actual_over == 1, "UST", "ALT")
    out["is_win"] = (out["selected_side"].to_numpy() == out["actual_side"].to_numpy())
    out["selected_turkey_odds"] = np.where(choose_over, odds_over, odds_under)

    # Fair odds and synthetic 2% margin odds for both outcomes.
    out["fair_odds_under"] = 1.0 / p_under
    out["fair_odds_over"] = 1.0 / p
    out["sharp_odds_under"] = out["fair_odds_under"] * SHARP_PRICE_FACTOR
    out["sharp_odds_over"] = out["fair_odds_over"] * SHARP_PRICE_FACTOR
    out["selected_sharp_odds"] = np.where(
        choose_over, out["sharp_odds_over"], out["sharp_odds_under"]
    )
    out["selected_sharp_model_ev"] = (
        out["selected_model_probability"] * out["selected_sharp_odds"] - 1.0
    )

    bets = out.loc[take].copy().reset_index(drop=True)
    if bets.empty:
        return bets

    wins = bets["is_win"].to_numpy(dtype=bool)
    turkey_odds = bets["selected_turkey_odds"].to_numpy(dtype=float)
    sharp_odds = bets["selected_sharp_odds"].to_numpy(dtype=float)
    bets["profit_turkey_flat_1u"] = np.where(wins, turkey_odds - 1.0, -1.0)
    bets["profit_sharp_flat_1u"] = np.where(wins, sharp_odds - 1.0, -1.0)
    return bets


def simulate_bankroll(
    bets: pd.DataFrame,
    odds_column: str,
    initial_bankroll: float = INITIAL_BANKROLL,
    stake_fraction: float = BANKROLL_STAKE_FRACTION,
) -> tuple[dict, pd.DataFrame]:
    """Chronological compounding simulation staking a fraction of current bankroll."""
    bankroll = float(initial_bankroll)
    total_staked = 0.0
    total_profit = 0.0
    rows = []

    for row in bets.itertuples(index=False):
        odds = float(getattr(row, odds_column))
        won = bool(row.is_win)
        stake = bankroll * stake_fraction
        if stake <= 0.0 or not np.isfinite(stake):
            raise RuntimeError("Geçersiz kasa/bahis tutarı; simülasyon durduruldu.")

        profit = stake * (odds - 1.0) if won else -stake
        bankroll_before = bankroll
        bankroll += profit
        total_staked += stake
        total_profit += profit
        rows.append({
            "_id": getattr(row, "_id"),
            "_date": getattr(row, "_date"),
            "selected_side": getattr(row, "selected_side"),
            "is_win": won,
            "odds_used": odds,
            "bankroll_before": bankroll_before,
            "stake_20pct": stake,
            "profit": profit,
            "bankroll_after": bankroll,
        })

    roi_pct = (total_profit / total_staked * 100.0) if total_staked > EPS else np.nan
    bankroll_roi_pct = (bankroll / initial_bankroll - 1.0) * 100.0
    summary = {
        "strategy": "20pct_current_bankroll",
        "odds_source": "turkey" if odds_column == "selected_turkey_odds" else "synthetic_sharp_2pct",
        "bets": int(len(bets)),
        "initial_bankroll": initial_bankroll,
        "total_staked": total_staked,
        "total_profit": total_profit,
        "roi_pct_profit_over_total_staked": roi_pct,
        "final_bankroll": bankroll,
        "bankroll_return_pct_vs_initial": bankroll_roi_pct,
    }
    return summary, pd.DataFrame(rows)


def flat_bet_summary(bets: pd.DataFrame, profit_column: str, odds_source: str) -> dict:
    profits = bets[profit_column].to_numpy(dtype=float) if len(bets) else np.array([], dtype=float)
    count = int(len(profits))
    total_staked = count * FLAT_STAKE
    total_profit = float(profits.sum()) if count else 0.0
    roi_pct = total_profit / total_staked * 100.0 if total_staked else np.nan
    ci_low, ci_high = roi_confidence_interval(profits)
    return {
        "strategy": "flat_1_unit",
        "odds_source": odds_source,
        "bets": count,
        "initial_bankroll": np.nan,
        "total_staked": total_staked,
        "total_profit": total_profit,
        "roi_pct_profit_over_total_staked": roi_pct,
        "roi_ci95_low_pct_approx": ci_low * 100.0 if np.isfinite(ci_low) else np.nan,
        "roi_ci95_high_pct_approx": ci_high * 100.0 if np.isfinite(ci_high) else np.nan,
        "final_bankroll": np.nan,
        "bankroll_return_pct_vs_initial": np.nan,
    }


def main() -> None:
    print("=" * 90)
    print("MODEL C — TÜRKİYE ORANI / SENTETİK %2 MARJLI ORAN KARŞILAŞTIRMASI")
    print("=" * 90)
    print("1. Global veri yükleniyor...")
    matches = load_global_data().copy()
    missing = REQUIRED_COLUMNS.difference(matches.columns)
    if missing:
        raise KeyError(f"Gerekli sütunlar eksik: {sorted(missing)}")
    if matches["_id"].duplicated().any():
        raise ValueError("Global veri setinde yinelenen _id var.")

    matches["_date"] = pd.to_datetime(matches["_date"], errors="coerce")
    matches["_season"] = matches["_season"].astype(str)
    matches["_y_ou25"] = pd.to_numeric(matches["_y_ou25"], errors="coerce")
    matches["_odd_under25"] = pd.to_numeric(matches["_odd_under25"], errors="coerce")
    matches["_odd_over25"] = pd.to_numeric(matches["_odd_over25"], errors="coerce")
    matches = matches.dropna(subset=["_date", "_season", "_y_ou25"]).copy()
    matches["_y_ou25"] = matches["_y_ou25"].astype(int)
    if not matches["_y_ou25"].isin([0, 1]).all():
        raise ValueError("_y_ou25 yalnızca 0/1 değerlerini içermeli.")

    missing_train = sorted(set(TRAIN_SEASONS) - set(matches["_season"].unique()))
    missing_test = sorted(set(TEST_SEASONS) - set(matches["_season"].unique()))
    if missing_train or missing_test:
        raise ValueError(f"Sezon eksik. Eğitim: {missing_train}; test: {missing_test}")

    print("2. Kronolojik Elo/Form/Rest/Momentum özellikleri hesaplanıyor...")
    features = add_momentum(calculate_elo_features(matches))
    data = matches.merge(features, on="_id", how="inner", validate="one_to_one")
    data = data.sort_values(["_date", "_id"]).reset_index(drop=True)

    train = data[data["_season"].isin(TRAIN_SEASONS)].copy()
    test_raw = data[data["_season"].isin(TEST_SEASONS)].copy()
    train = train.dropna(subset=["_y_ou25"]).copy()

    odds_valid = (
        valid_decimal_odds(test_raw["_odd_under25"])
        & valid_decimal_odds(test_raw["_odd_over25"])
    )
    test = test_raw.loc[odds_valid].copy().reset_index(drop=True)
    if len(train) < MIN_TRAIN_ROWS:
        raise RuntimeError(f"Eğitim örneği yetersiz: {len(train)}")
    if train["_y_ou25"].nunique() != 2:
        raise RuntimeError("Eğitim verisinde ALT/ÜST hedefinin iki sınıfı da yok.")
    if test.empty:
        raise RuntimeError("Test sezonlarında iki geçerli Türkiye oranına sahip maç bulunamadı.")

    absent_features = [name for name in MODEL_C_FEATURES if name not in data.columns]
    if absent_features:
        raise KeyError(f"Model C özellikleri eksik: {absent_features}")

    X_train = train[MODEL_C_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    X_test = test[MODEL_C_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)

    print(f"   Eğitim maçları: {len(train):,}")
    print(f"   Ham test maçları: {len(test_raw):,}")
    print(f"   Oranları geçerli test maçları: {len(test):,}")
    print(f"   Eğitim sezonları: {', '.join(TRAIN_SEASONS)}")
    print(f"   Test sezonları: {', '.join(TEST_SEASONS)}")
    print(f"   EV eşiği: > {EV_THRESHOLD:.2f}")

    print("3. Model C eğitiliyor (mevcut sabit model ayarları)...")
    model = make_model()
    model.fit(X_train, train["_y_ou25"].astype(int))
    p_over = model.predict_proba(X_test)[:, 1]

    print("4. Türkiye oranlarına göre EV > 0.05 bahisleri seçiliyor...")
    bets = select_model_c_bets(test, p_over)
    if bets.empty:
        raise RuntimeError(
            "EV > 0.05 koşulunu geçen bahis bulunmadı; ROI karşılaştırması yapılamıyor."
        )

    # Both odds systems settle exactly the same selected bets and actual outcomes.
    flat_turkey = flat_bet_summary(bets, "profit_turkey_flat_1u", "turkey_odds")
    flat_sharp = flat_bet_summary(bets, "profit_sharp_flat_1u", "synthetic_sharp_2pct")
    bankroll_turkey, ledger_turkey = simulate_bankroll(bets, "selected_turkey_odds")
    bankroll_sharp, ledger_sharp = simulate_bankroll(bets, "selected_sharp_odds")

    summary = pd.DataFrame([
        flat_turkey,
        flat_sharp,
        bankroll_turkey,
        bankroll_sharp,
    ])
    summary["test_matches_with_valid_turkey_odds"] = len(test)
    summary["ev_threshold_for_selection"] = EV_THRESHOLD
    summary["synthetic_sharp_margin"] = SHARP_MARGIN
    summary["selection_basis"] = "Turkish odds; max(EV_under, EV_over) > 0.05"
    summary["sharp_odds_are_independent_market_data"] = False
    summary["sharp_model_expected_roi_pct_by_construction"] = -SHARP_MARGIN * 100.0

    # Join stake paths into the selected-bet ledger for side-by-side inspection.
    turkey_ledger = ledger_turkey.rename(columns={
        "odds_used": "turkey_odds_used",
        "bankroll_before": "turkey_bankroll_before",
        "stake_20pct": "turkey_stake_20pct",
        "profit": "turkey_profit_20pct",
        "bankroll_after": "turkey_bankroll_after",
    })
    sharp_ledger = ledger_sharp.rename(columns={
        "odds_used": "sharp_odds_used",
        "bankroll_before": "sharp_bankroll_before",
        "stake_20pct": "sharp_stake_20pct",
        "profit": "sharp_profit_20pct",
        "bankroll_after": "sharp_bankroll_after",
    })
    drop_columns = ["selected_side", "is_win"]
    ledger = bets.merge(
        turkey_ledger.drop(columns=drop_columns, errors="ignore"),
        on=["_id", "_date"], how="left", validate="one_to_one",
    ).merge(
        sharp_ledger.drop(columns=drop_columns, errors="ignore"),
        on=["_id", "_date"], how="left", validate="one_to_one",
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ledger.to_csv(LEDGER_PATH, index=False, encoding="utf-8-sig")
    summary.to_csv(SUMMARY_PATH, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 90)
    print("SONUÇLAR")
    print("=" * 90)
    print(f"Test maçları (geçerli Türkiye oranı): {len(test):,}")
    print(f"Model C EV > 0.05 bahis sayısı: {len(bets):,}")
    print(
        f"Seçilen bahislerde gerçekleşen kazanma oranı: "
        f"%{100.0 * bets['is_win'].mean():.2f}"
    )
    print(
        f"Sharp fiyatlarda modelin teorik EV'si: "
        f"%{100.0 * bets['selected_sharp_model_ev'].mean():.2f} "
        "(formül gereği yaklaşık -2%)"
    )
    print("\n" + summary.to_string(index=False, float_format=lambda value: f"{value:.4f}"))
    print(f"\nBahis detayları: {LEDGER_PATH}")
    print(f"Özet rapor: {SUMMARY_PATH}")
    print(
        "\nYORUM SINIRI: Sharp oranları modelin kendi olasılıklarından türetildi; "
        "Pinnacle/Betfair geçmiş oranları değildir. Bu sonuç, gerçek düşük marjlı "
        "piyasayı yenebildiğimizi tek başına göstermez. Gerçek piyasa testi için "
        "maç başlangıcına ait bağımsız sharp oranları gerekir."
    )


if __name__ == "__main__":
    main()
