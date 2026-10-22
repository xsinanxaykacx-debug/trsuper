"""Aggressive bankroll-growth simulations for Model C EV-filtered OU2.5 bets.

Training seasons: 2012/2013–2017/2018.
Test seasons: 2018/2019 and 2019/2020.
Selection: same common odds cohort and Model C EV > 0.05 rule as
src/theoretical_test.py / src/human_vs_ai_v2.py.

Strategies:
  ALL_IN:        stake 100% of current bankroll
  HALF_BANKROLL: stake 50% of current bankroll
  PCT_20:        stake 20% of current bankroll
  PCT_10:        stake 10% of current bankroll

Each strategy stops at the first of: reaching 10,000 units, bankroll becoming
effectively zero, or exhausting the historical test selections. This is a
historical simulation, not a forecast or evidence of a profitable edge.
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
TARGET_BANKROLL = 10_000.0
BANKROLL_EPSILON = 1e-12
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

STRATEGIES = [
    ("ALL_IN", 1.00),
    ("HALF_BANKROLL", 0.50),
    ("PCT_20", 0.20),
    ("PCT_10", 0.10),
]


def _valid_odds(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values.notna() & np.isfinite(values) & values.gt(1.0)


def _prepare_selections(common: pd.DataFrame, p_over: np.ndarray) -> pd.DataFrame:
    """Build the chronological EV-filtered bet ledger shared by all strategies."""
    p = np.clip(np.asarray(p_over, dtype=float), CONFIDENCE_EPS, 1.0 - CONFIDENCE_EPS)
    odds_under = common["_odd_under25"].to_numpy(dtype=float)
    odds_over = common["_odd_over25"].to_numpy(dtype=float)
    y_over = common["_y_ou25"].astype(int).to_numpy()

    ev_under = (1.0 - p) * odds_under - 1.0
    ev_over = p * odds_over - 1.0
    choose_over = ev_over > ev_under
    best_ev = np.maximum(ev_under, ev_over)
    take = best_ev > EV_THRESHOLD

    if not np.any(take):
        raise RuntimeError(f"EV > {EV_THRESHOLD:.2f} eşiğini geçen bahis bulunamadı.")

    selected_odds = np.where(choose_over, odds_over, odds_under)
    selected_won = np.where(choose_over, y_over == 1, y_over == 0)

    bets = common.loc[take].copy().reset_index(drop=True)
    bets["selection"] = np.where(choose_over[take], "OVER_2.5", "UNDER_2.5")
    bets["model_p_over"] = p[take]
    bets["estimated_best_ev"] = best_ev[take]
    bets["selected_odds"] = selected_odds[take]
    bets["won"] = selected_won[take].astype(bool)
    return bets.sort_values(["_date", "_id"]).reset_index(drop=True)


def _max_drawdown(bankroll_path: list[float]) -> tuple[float, float]:
    """Return maximum peak-to-trough drawdown in units and percent of peak."""
    values = np.asarray(bankroll_path, dtype=float)
    if values.size == 0:
        return 0.0, 0.0
    peaks = np.maximum.accumulate(values)
    drawdowns = peaks - values
    percentages = np.divide(
        drawdowns,
        peaks,
        out=np.zeros_like(drawdowns),
        where=peaks > BANKROLL_EPSILON,
    )
    return float(drawdowns.max()), float(percentages.max() * 100.0)


def _simulate_strategy(
    bets: pd.DataFrame,
    strategy: str,
    stake_fraction: float,
) -> tuple[dict, list[dict]]:
    bankroll = INITIAL_BANKROLL
    peak_bankroll = INITIAL_BANKROLL
    bankroll_path = [bankroll]
    ledger: list[dict] = []
    total_staked = 0.0
    total_profit = 0.0
    target_reached_at: int | None = None
    stop_reason = "Test dönemi bahisleri tamamlandı."
    bets_placed = 0

    for _, row in bets.iterrows():
        if bankroll >= TARGET_BANKROLL:
            target_reached_at = bets_placed
            stop_reason = "10.000 birim hedefi önceden karşılandı."
            break
        if bankroll <= BANKROLL_EPSILON:
            bankroll = 0.0
            stop_reason = "Kasa sıfırlandı; sonraki bahisler durduruldu."
            break

        bankroll_before = bankroll
        stake = bankroll_before * stake_fraction
        if stake <= BANKROLL_EPSILON:
            bankroll = 0.0
            stop_reason = "Kalan bahis tutarı sayısal olarak sıfıra indi."
            bankroll_path.append(bankroll)
            break

        odds = float(row["selected_odds"])
        won = bool(row["won"])
        profit = stake * (odds - 1.0) if won else -stake
        bankroll = bankroll_before + profit
        # Protect against tiny negative floating-point residue.
        bankroll = max(0.0, float(bankroll))
        bets_placed += 1
        total_staked += stake
        total_profit += profit
        peak_bankroll = max(peak_bankroll, bankroll)
        bankroll_path.append(bankroll)

        ledger.append({
            "strategy": strategy,
            "bet_number": bets_placed,
            "_id": row["_id"],
            "_date": row["_date"],
            "_season": row["_season"],
            "Ev_Sahibi": row["Ev_Sahibi"],
            "Deplasman": row["Deplasman"],
            "selection": row["selection"],
            "estimated_best_ev": float(row["estimated_best_ev"]),
            "selected_odds": odds,
            "won": won,
            "bankroll_before": bankroll_before,
            "stake_fraction": stake_fraction,
            "stake": stake,
            "profit": profit,
            "bankroll_after": bankroll,
            "peak_bankroll_after": peak_bankroll,
        })

        if bankroll >= TARGET_BANKROLL:
            target_reached_at = bets_placed
            stop_reason = "10.000 birim hedefi karşılandı."
            break
        if bankroll <= BANKROLL_EPSILON:
            bankroll = 0.0
            bankroll_path[-1] = bankroll
            stop_reason = "Kasa sıfırlandı; sonraki bahisler durduruldu."
            break

    max_dd_units, max_dd_pct = _max_drawdown(bankroll_path)
    summary = {
        "strategy": strategy,
        "stake_fraction_pct": stake_fraction * 100.0,
        "initial_bankroll": INITIAL_BANKROLL,
        "target_bankroll": TARGET_BANKROLL,
        "target_reached": target_reached_at is not None,
        "target_reached_at_bet": target_reached_at,
        "bets_placed": bets_placed,
        "eligible_bets_available": int(len(bets)),
        "final_bankroll": bankroll,
        "net_profit": bankroll - INITIAL_BANKROLL,
        "total_staked": total_staked,
        "realized_roi_pct": total_profit / total_staked * 100.0 if total_staked else np.nan,
        "max_drawdown_units": max_dd_units,
        "max_drawdown_pct": max_dd_pct,
        "stop_reason": stop_reason,
    }
    return summary, ledger


def main() -> None:
    print("1. Global veri ve Model C özellikleri yükleniyor...")
    matches = load_global_data().copy()
    required = {
        "_id", "_date", "_season", "Lig/Sezon", "Ev_Sahibi", "Deplasman",
        "MSE", "MSD", "_y", "_y_ou25", *ODDS_1X2, *ODDS_OU,
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

    # Keep the same common cohort used in theoretical_test.py and human_vs_ai_v2.py.
    valid_mask = pd.Series(True, index=test_raw.index)
    for col in ODDS_1X2 + ODDS_OU:
        valid_mask &= _valid_odds(test_raw[col])
    common = test_raw.loc[valid_mask].copy().sort_values(
        ["_date", "_id"]
    ).reset_index(drop=True)
    if common.empty:
        raise RuntimeError("Ortak test kümesinde geçerli oranlı maç bulunamadı.")

    print("\n3. Sabit veri kümeleri")
    print(f"   Eğitim sezonları: {TRAIN_SEASONS[0]}–{TRAIN_SEASONS[-1]}")
    print(f"   Eğitim maçı: {len(train):,}")
    print(f"   Ham test maçı: {len(test_raw):,}")
    print(f"   Ortak test kümesi: {len(common):,}")
    print(f"   Test sezonları: {', '.join(TEST_SEASONS)}")
    print(f"   Başlangıç kasası: {INITIAL_BANKROLL:,.2f}")
    print(f"   Hedef kasa: {TARGET_BANKROLL:,.2f}")
    print(f"   Seçim kuralı: en yüksek ALT/ÜST EV > {EV_THRESHOLD:.2f}")

    print("\n4. Model C bir kez eğitiliyor...")
    X_train = train[MODEL_C_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    X_common = common[MODEL_C_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    model = make_model()
    model.fit(X_train, train["_y_ou25"].astype(int))
    p_over = model.predict_proba(X_common)[:, 1]
    bets = _prepare_selections(common, p_over)
    print(f"   Model C tahmini: {len(common):,}")
    print(f"   EV > {EV_THRESHOLD:.2f} bahis: {len(bets):,}")

    print("\n5. Dört agresif kasa stratejisi simüle ediliyor...")
    summaries: list[dict] = []
    all_ledgers: list[dict] = []
    for strategy, fraction in STRATEGIES:
        summary, ledger = _simulate_strategy(bets, strategy, fraction)
        summaries.append(summary)
        all_ledgers.extend(ledger)

    summary_df = pd.DataFrame(summaries)
    ledger_df = pd.DataFrame(all_ledgers)
    output_dir = Path("data/csv")
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "aggressive_growth_results.csv"
    ledger_path = output_dir / "aggressive_growth_bet_ledger.csv"
    summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")
    ledger_df.to_csv(ledger_path, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 122)
    print("MODEL C — AGRESİF BİLEŞİK KASA BÜYÜMESİ | 100 → 10.000")
    print("=" * 122)
    display_cols = [
        "strategy", "stake_fraction_pct", "target_reached",
        "target_reached_at_bet", "bets_placed", "final_bankroll",
        "net_profit", "total_staked", "realized_roi_pct",
        "max_drawdown_units", "max_drawdown_pct",
    ]
    print(summary_df[display_cols].to_string(
        index=False, float_format=lambda value: f"{value:,.2f}"
    ))

    reached = summary_df[summary_df["target_reached"]]
    if not reached.empty:
        fastest = reached.sort_values("target_reached_at_bet").iloc[0]
        print(
            f"\nHEDEFE ULAŞAN: {fastest['strategy']} — "
            f"{int(fastest['target_reached_at_bet'])}. bahis."
        )
        print(
            "Hedefe ulaşan stratejiler için simülasyon, ilk kez 10.000 birime "
            "ulaşıldığı bahis sonrasında durdurulmuştur."
        )
    else:
        closest = summary_df.loc[summary_df["final_bankroll"].idxmax()]
        print("\nHEDEFE ULAŞAN STRATEJİ YOK.")
        print(
            f"100 birimden 10.000 birime en çok yaklaşan: {closest['strategy']} — "
            f"son kasa {closest['final_bankroll']:,.2f} birim "
            f"({closest['final_bankroll'] / TARGET_BANKROLL * 100.0:.2f}% hedef)."
        )

    print(f"\nÖzet CSV: {summary_path}")
    print(f"Bahis günlüğü CSV: {ledger_path}")
    print(
        "\nYorum: Bu stratejiler yalnızca bahis tutarını değiştirir; Model C'nin "
        "tahminlerini veya EV filtresini iyileştirmez. Agresif bileşik bahis, "
        "pozitif ve doğrulanmış bir edge yoksa kayıpları da hızlandırabilir. "
        "Sonuçlar geçmiş test dönemine aittir; gelecekteki kazancı garanti etmez."
    )


if __name__ == "__main__":
    main()
