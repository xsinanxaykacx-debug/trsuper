"""Human vs AI bankroll simulation on the fixed 2018/19–2019/20 test period.

Profiles:
A) Home-only human: fixed 1-unit stake on the home win.
B) Favorite hunter: fixed 1-unit stake on the lowest-odds 1X2 outcome.
C) Z-Kahin: Model C from src.ablation_study, bet only when the best OU2.5 EV
   exceeds 0.05; stake uses full Kelly.

Fair-comparison rule: every profile is evaluated on the SAME test rows where
all three 1X2 odds and both OU2.5 odds are valid (> 1.00). This is a stricter
intersection than the 29,817-row OU-only cohort in the ablation report.
No claim of a profitable edge is implied by this historical simulation.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.ablation_study import (
    EV_THRESHOLD,
    MIN_TRAIN_ROWS,
    MOMENTUM_FEATURES,
    REST_FEATURES,
    TRAIN_SEASONS,
    TEST_SEASONS,
    add_momentum,
    make_model,
)
from src.features import calculate_elo_features
from src.load_global import load_global_data


INITIAL_BANKROLL = 100.0
FIXED_STAKE = 1.0
CONFIDENCE_EPS = 1e-7

MODEL_C_FEATURES = [
    "elo_h", "elo_a", "elo_diff",
    "form_h_pts_5", "form_h_gf_5", "form_h_ga_5",
    "form_a_pts_5", "form_a_gf_5", "form_a_ga_5",
    "form_h_pts_10", "form_h_gf_10", "form_h_ga_10",
    "form_a_pts_10", "form_a_gf_10", "form_a_ga_10",
    "form_h_home_pts", "form_h_home_gf", "form_h_home_ga",
    "form_a_away_pts", "form_a_away_gf", "form_a_away_ga",
] + REST_FEATURES + MOMENTUM_FEATURES

ODDS_1X2 = ["_odd_H", "_odd_D", "_odd_A"]
ODDS_OU = ["_odd_under25", "_odd_over25"]


def _valid_odds(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values.notna() & np.isfinite(values) & values.gt(1.0)


def _max_drawdown(bankroll_path: list[float]) -> tuple[float, float]:
    """Return maximum drawdown in units and as a percentage of prior peak."""
    values = np.asarray(bankroll_path, dtype=float)
    peaks = np.maximum.accumulate(values)
    drawdowns = peaks - values
    drawdown_pct = np.divide(
        drawdowns,
        peaks,
        out=np.zeros_like(drawdowns),
        where=peaks > 0.0,
    )
    return float(drawdowns.max(initial=0.0)), float(drawdown_pct.max(initial=0.0) * 100.0)


def _settle(bankroll: float, stake: float, odds: float, won: bool) -> tuple[float, float]:
    """Return updated bankroll and net profit for decimal odds."""
    profit = stake * (odds - 1.0) if won else -stake
    return max(0.0, bankroll + profit), profit


def _simulate_fixed_stake(
    frame: pd.DataFrame,
    profile: str,
    selection: np.ndarray,
    odds: np.ndarray,
    won: np.ndarray,
) -> tuple[dict, list[dict]]:
    bankroll = INITIAL_BANKROLL
    path = [bankroll]
    bets = 0
    total_staked = 0.0
    total_profit = 0.0
    stopped_early = False
    ledger: list[dict] = []

    for i, (_, row) in enumerate(frame.iterrows()):
        stake = FIXED_STAKE if bool(selection[i]) else 0.0
        if stake > 0 and bankroll + 1e-12 < stake:
            stopped_early = True
            break

        profit = 0.0
        if stake > 0:
            bankroll, profit = _settle(bankroll, stake, float(odds[i]), bool(won[i]))
            bets += 1
            total_staked += stake
            total_profit += profit

        path.append(bankroll)
        ledger.append({
            "profile": profile,
            "date": row["_date"],
            "season": row["_season"],
            "match_id": row["_id"],
            "home": row["Ev_Sahibi"],
            "away": row["Deplasman"],
            "selection": (
                "HOME" if profile == "A_HOME_ONLY"
                else str(row["_favorite_label"])
            ) if stake > 0 else "NO_BET_AFTER_STOP",
            "stake": stake,
            "odds": float(odds[i]) if stake > 0 else np.nan,
            "won": bool(won[i]) if stake > 0 else None,
            "profit": profit,
            "bankroll_after": bankroll,
        })

    max_dd_units, max_dd_pct = _max_drawdown(path)
    summary = {
        "profile": profile,
        "initial_bankroll": INITIAL_BANKROLL,
        "final_bankroll": bankroll,
        "net_profit": total_profit,
        "bets": bets,
        "total_staked": total_staked,
        "roi_pct": (total_profit / total_staked * 100.0) if total_staked else np.nan,
        "max_drawdown_units": max_dd_units,
        "max_drawdown_pct": max_dd_pct,
        "stopped_early_insufficient_bankroll": stopped_early,
        "test_matches_in_common_cohort": len(frame),
    }
    return summary, ledger


def _simulate_kelly(
    frame: pd.DataFrame,
    p_over: np.ndarray,
) -> tuple[dict, list[dict]]:
    bankroll = INITIAL_BANKROLL
    path = [bankroll]
    bets = 0
    total_staked = 0.0
    total_profit = 0.0
    ledger: list[dict] = []

    y_over = frame["_y_ou25"].astype(int).to_numpy()
    odds_under = frame["_odd_under25"].to_numpy(dtype=float)
    odds_over = frame["_odd_over25"].to_numpy(dtype=float)
    p = np.clip(np.asarray(p_over, dtype=float), CONFIDENCE_EPS, 1.0 - CONFIDENCE_EPS)

    ev_under = (1.0 - p) * odds_under - 1.0
    ev_over = p * odds_over - 1.0
    choose_over = ev_over > ev_under
    best_ev = np.maximum(ev_under, ev_over)
    take = best_ev > EV_THRESHOLD

    for i, (_, row) in enumerate(frame.iterrows()):
        stake = 0.0
        selected_side = "NO_BET"
        selected_odds = np.nan
        won = None
        profit = 0.0
        p_selected = np.nan
        ev_selected = float(best_ev[i])

        if take[i] and bankroll > 0.0:
            selected_odds = float(odds_over[i] if choose_over[i] else odds_under[i])
            p_selected = float(p[i] if choose_over[i] else 1.0 - p[i])
            # Full Kelly: f* = (p*b - q) / b = (p*odds - 1)/(odds - 1).
            fraction = (p_selected * selected_odds - 1.0) / (selected_odds - 1.0)
            fraction = float(np.clip(fraction, 0.0, 1.0))
            stake = bankroll * fraction
            # Avoid meaningless near-zero wagers due to floating-point noise.
            if stake > 1e-10:
                selected_side = "OVER_2.5" if choose_over[i] else "UNDER_2.5"
                won = bool((y_over[i] == 1) if choose_over[i] else (y_over[i] == 0))
                bankroll, profit = _settle(bankroll, stake, selected_odds, won)
                bets += 1
                total_staked += stake
                total_profit += profit
            else:
                stake = 0.0

        path.append(bankroll)
        ledger.append({
            "profile": "C_Z_KAHIN_FULL_KELLY",
            "date": row["_date"],
            "season": row["_season"],
            "match_id": row["_id"],
            "home": row["Ev_Sahibi"],
            "away": row["Deplasman"],
            "selection": selected_side,
            "model_p_over": float(p[i]),
            "selected_side_probability": p_selected,
            "estimated_best_ev": ev_selected,
            "stake": stake,
            "stake_pct_of_bankroll": (stake / path[-2] * 100.0) if path[-2] > 0 else 0.0,
            "odds": selected_odds,
            "won": won,
            "profit": profit,
            "bankroll_after": bankroll,
        })

    max_dd_units, max_dd_pct = _max_drawdown(path)
    summary = {
        "profile": "C_Z_KAHIN_FULL_KELLY",
        "initial_bankroll": INITIAL_BANKROLL,
        "final_bankroll": bankroll,
        "net_profit": total_profit,
        "bets": bets,
        "total_staked": total_staked,
        "roi_pct": (total_profit / total_staked * 100.0) if total_staked else np.nan,
        "max_drawdown_units": max_dd_units,
        "max_drawdown_pct": max_dd_pct,
        "stopped_early_insufficient_bankroll": False,
        "test_matches_in_common_cohort": len(frame),
    }
    return summary, ledger


def main() -> None:
    print("1. Global veri ve Model C'nin aynı özellikleri yükleniyor...")
    matches = load_global_data().copy()
    required = {
        "_id", "_date", "_season", "Lig/Sezon", "Ev_Sahibi", "Deplasman",
        "MSE", "MSD", "_y", "_y_ou25",
        *ODDS_1X2, *ODDS_OU,
    }
    missing = required.difference(matches.columns)
    if missing:
        raise KeyError(f"Gerekli sütunlar eksik: {sorted(missing)}")
    if matches["_id"].duplicated().any():
        raise ValueError("Global veri setinde yinelenen _id var.")

    matches["_date"] = pd.to_datetime(matches["_date"], errors="coerce")
    matches["_season"] = matches["_season"].astype(str)
    matches["_y_ou25"] = pd.to_numeric(matches["_y_ou25"], errors="coerce")
    matches = matches.dropna(subset=["_date", "_season", "_y", "_y_ou25"]).copy()

    missing_train = sorted(set(TRAIN_SEASONS) - set(matches["_season"].unique()))
    missing_test = sorted(set(TEST_SEASONS) - set(matches["_season"].unique()))
    if missing_train or missing_test:
        raise ValueError(f"Sezon eksik. Eğitim={missing_train}; test={missing_test}")

    print("2. Kronolojik maç öncesi özellikler hesaplanıyor...")
    features = add_momentum(calculate_elo_features(matches))
    data = matches.merge(features, on="_id", how="inner", validate="one_to_one")
    data = data.sort_values(["_date", "_id"]).reset_index(drop=True)

    train = data[data["_season"].isin(TRAIN_SEASONS)].copy()
    test_raw = data[data["_season"].isin(TEST_SEASONS)].copy()
    train = train.dropna(subset=["_y_ou25"]).copy()
    if len(train) < MIN_TRAIN_ROWS:
        raise RuntimeError(f"Eğitim örneği yetersiz: {len(train)}")
    if train["_y_ou25"].astype(int).nunique() != 2:
        raise RuntimeError("Eğitim verisinde ALT/ÜST hedefinin iki sınıfı da yok.")

    valid_mask = pd.Series(True, index=test_raw.index)
    for col in ODDS_1X2 + ODDS_OU:
        valid_mask &= _valid_odds(test_raw[col])
    common = test_raw.loc[valid_mask].copy().sort_values(["_date", "_id"]).reset_index(drop=True)
    if common.empty:
        raise RuntimeError("Ortak test kümesinde tüm 1X2 ve OU oranları geçerli olan maç yok.")

    print("\n3. Ortak test kümesi")
    print(f"   Ham test maçı: {len(test_raw):,}")
    print(f"   Tüm 1X2 ve OU oranları geçerli ortak test maçı: {len(common):,}")
    print(f"   Sezonlar: {', '.join(TEST_SEASONS)}")
    print("   Üç profil aynı maç satırlarında, kronolojik sırayla karşılaştırılır.")
    print("   Profil C: Model C, EV > 0.05, tam Kelly; A/B: sabit 1 birim.")

    print("\n4. Model C eğitiliyor (eğitim: 2012/13–2017/18; test dönemine yeniden uyum yok)...")
    X_train = train[MODEL_C_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    X_common = common[MODEL_C_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    model = make_model()
    model.fit(X_train, train["_y_ou25"].astype(int))
    p_over = model.predict_proba(X_common)[:, 1]

    # Profile A: home-win, fixed 1 unit.
    home_odds = common["_odd_H"].to_numpy(dtype=float)
    home_won = common["_y"].eq("H").to_numpy()
    all_bets = np.ones(len(common), dtype=bool)
    summary_a, ledger_a = _simulate_fixed_stake(
        common, "A_HOME_ONLY", all_bets, home_odds, home_won
    )

    # Profile B: lowest decimal odds among home/draw/away (ties follow H, D, A order).
    odds_1x2 = common[ODDS_1X2].to_numpy(dtype=float)
    favorite_idx = np.argmin(odds_1x2, axis=1)
    favorite_odds = odds_1x2[np.arange(len(common)), favorite_idx]
    labels = np.array(["HOME", "DRAW", "AWAY"], dtype=object)
    favorite_label = labels[favorite_idx]
    common["_favorite_label"] = favorite_label
    outcomes = common["_y"].to_numpy()
    favorite_won = np.array([
        (outcome == ("H" if label == "HOME" else "D" if label == "DRAW" else "A"))
        for outcome, label in zip(outcomes, favorite_label)
    ], dtype=bool)
    summary_b, ledger_b = _simulate_fixed_stake(
        common, "B_FAVORITE_HUNTER", all_bets, favorite_odds, favorite_won
    )

    # Profile C: OU2.5, EV filter and full Kelly.
    summary_c, ledger_c = _simulate_kelly(common, p_over)

    summaries = pd.DataFrame([summary_a, summary_b, summary_c])
    ledger = pd.DataFrame(ledger_a + ledger_b + ledger_c)

    output_dir = Path("data/csv")
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "human_vs_ai_results.csv"
    ledger_path = output_dir / "human_vs_ai_bet_ledger.csv"
    summaries.to_csv(summary_path, index=False, encoding="utf-8-sig")
    ledger.to_csv(ledger_path, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 110)
    print("İNSAN PROFİLLERİ vs Z-KÂHİN — 2018/19 + 2019/20")
    print("=" * 110)
    display_cols = [
        "profile", "initial_bankroll", "final_bankroll", "net_profit",
        "bets", "total_staked", "roi_pct", "max_drawdown_units",
        "max_drawdown_pct", "stopped_early_insufficient_bankroll",
    ]
    print(summaries[display_cols].to_string(
        index=False, float_format=lambda value: f"{value:.2f}"
    ))
    print(f"\nÖzet CSV: {summary_path}")
    print(f"Bahis günlüğü CSV: {ledger_path}")
    print(
        "\nYorumlama sınırı: Bu, aynı tarihsel maç kümesindeki geriye dönük bir simülasyondur. "
        "Tam Kelly, model olasılıklarının doğru kalibre edildiğini varsayar ve hatalı/iyimser "
        "olasılıklarda kasayı sert biçimde oynatabilir. Sonuç tek başına gerçek parayla "
        "oynanabilir bir avantaj veya insanlardan genel olarak üstünlük kanıtı değildir."
    )


if __name__ == "__main__":
    main()
