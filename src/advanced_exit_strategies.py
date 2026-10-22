"""Season-by-season exit-rule backtests for Model C EV-filtered OU2.5 bets.

Run from repository root:
    python -m src.advanced_exit_strategies

Each eligible season gets a fresh 100-unit bankroll and 20% fractional staking.
For each season, Model C is trained only on earlier seasons (expanding-window
walk-forward); the target season is never used for fitting. Match features are
computed chronologically by calculate_elo_features().

Strategies:
  A: stop after settling the first bet that leaves bankroll >= 250.
  B: trailing stop activates only after bankroll has reached >= 200; then stop
     when bankroll is <= 75% of the best bankroll observed so far.
  C: stop at bankroll >= 250; otherwise stop if bankroll falls below 50.

This is a historical backtest, not a forecast or proof of a profitable edge.
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
    add_momentum,
    make_model,
)
from src.features import calculate_elo_features
from src.load_global import load_global_data


INITIAL_BANKROLL = 100.0
STAKE_FRACTION = 0.20
TAKE_PROFIT_TARGET = 250.0
TRAILING_ACTIVATION = 200.0
TRAILING_DRAWDOWN = 0.25
STOP_LOSS_FLOOR = 50.0
CONFIDENCE_EPS = 1e-7
EPS = 1e-9
OUTPUT_DIR = Path("data/csv")

MODEL_C_FEATURES = [
    "elo_h", "elo_a", "elo_diff",
    "form_h_pts_5", "form_h_gf_5", "form_h_ga_5",
    "form_a_pts_5", "form_a_gf_5", "form_a_ga_5",
    "form_h_pts_10", "form_h_gf_10", "form_h_ga_10",
    "form_a_pts_10", "form_a_gf_10", "form_a_ga_10",
    "form_h_home_pts", "form_h_home_gf", "form_h_home_ga",
    "form_a_away_pts", "form_a_away_gf", "form_a_away_ga",
] + REST_FEATURES + MOMENTUM_FEATURES

ODDS_COLUMNS = [
    "_odd_H", "_odd_D", "_odd_A",
    "_odd_under25", "_odd_over25",
]


def valid_odds(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values.notna() & np.isfinite(values) & values.gt(1.0)


def season_sort_key(season: str) -> tuple[int, int]:
    parts = str(season).split("/")
    try:
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return (9999, 9999)


def prepare_season_bets(season_frame: pd.DataFrame, p_over: np.ndarray) -> pd.DataFrame:
    """Apply the existing Model C EV > 0.05 selection rule to one season."""
    frame = season_frame.copy().reset_index(drop=True)
    p = np.clip(np.asarray(p_over, dtype=float), CONFIDENCE_EPS, 1.0 - CONFIDENCE_EPS)
    if len(p) != len(frame):
        raise ValueError("Tahmin sayısı ile sezon satırı sayısı eşleşmiyor.")

    odds_under = frame["_odd_under25"].to_numpy(dtype=float)
    odds_over = frame["_odd_over25"].to_numpy(dtype=float)
    y_over = frame["_y_ou25"].astype(int).to_numpy()

    ev_under = (1.0 - p) * odds_under - 1.0
    ev_over = p * odds_over - 1.0
    choose_over = ev_over > ev_under
    best_ev = np.maximum(ev_under, ev_over)
    take = best_ev > EV_THRESHOLD

    if not np.any(take):
        return pd.DataFrame(columns=[
            "_id", "_date", "_season", "Ev_Sahibi", "Deplasman",
            "selection", "selected_odds", "won", "estimated_best_ev",
        ])

    selected_odds = np.where(choose_over, odds_over, odds_under)
    selected_won = np.where(choose_over, y_over == 1, y_over == 0)
    bets = frame.loc[take].copy().reset_index(drop=True)
    bets["selection"] = np.where(choose_over[take], "OVER_2.5", "UNDER_2.5")
    bets["selected_odds"] = selected_odds[take]
    bets["won"] = selected_won[take].astype(bool)
    bets["estimated_best_ev"] = best_ev[take]
    return bets.sort_values(["_date", "_id"]).reset_index(drop=True)


def settle_bet(bankroll: float, odds: float, won: bool) -> tuple[float, float, float]:
    """Place 20% of pre-bet bankroll; return new bankroll, stake, and profit."""
    stake = bankroll * STAKE_FRACTION
    profit = stake * (odds - 1.0) if won else -stake
    return max(0.0, float(bankroll + profit)), float(stake), float(profit)


def simulate_strategy(
    bets: pd.DataFrame,
    season: str,
    strategy: str,
) -> tuple[dict, list[dict]]:
    bankroll = INITIAL_BANKROLL
    peak = INITIAL_BANKROLL
    peak_at_bet = 0
    peak_reached_200 = False
    placed = 0
    total_staked = 0.0
    total_profit = 0.0
    stopped = False
    stop_reason = "Sezondaki uygun bahisler tamamlandı."
    ledger: list[dict] = []

    for row in bets.itertuples(index=False):
        if bankroll <= EPS:
            bankroll = 0.0
            stopped = True
            stop_reason = "Kasa sıfırlandı."
            break

        before = bankroll
        odds = float(row.selected_odds)
        won = bool(row.won)
        bankroll, stake, profit = settle_bet(before, odds, won)
        placed += 1
        total_staked += stake
        total_profit += profit

        if bankroll > peak:
            peak = bankroll
            peak_at_bet = placed
        if bankroll >= TRAILING_ACTIVATION:
            peak_reached_200 = True

        ledger.append({
            "season": season,
            "strategy": strategy,
            "bet_number": placed,
            "_id": row._id,
            "_date": row._date,
            "Ev_Sahibi": row.Ev_Sahibi,
            "Deplasman": row.Deplasman,
            "selection": row.selection,
            "selected_odds": odds,
            "won": won,
            "estimated_best_ev": float(row.estimated_best_ev),
            "bankroll_before": before,
            "stake": stake,
            "stake_fraction_pct": STAKE_FRACTION * 100.0,
            "profit": profit,
            "bankroll_after": bankroll,
            "peak_bankroll_after": peak,
        })

        if strategy == "A_FIXED_TAKE_PROFIT":
            if bankroll >= TAKE_PROFIT_TARGET:
                stopped = True
                stop_reason = f"Kâr al hedefi {TAKE_PROFIT_TARGET:.0f} birime ulaşıldı."
                break

        elif strategy == "B_TRAILING_STOP":
            # The stop does not exist until the bankroll has reached 200.
            # Once activated, it follows the running peak, not the initial 100.
            if peak_reached_200 and bankroll <= peak * (1.0 - TRAILING_DRAWDOWN):
                stopped = True
                stop_reason = (
                    f"Zirve {peak:.2f} birimden "
                    f"%{TRAILING_DRAWDOWN * 100:.0f} geri çekilme."
                )
                break

        elif strategy == "C_TAKE_PROFIT_AND_STOP_LOSS":
            # If both conditions could be met after the same settlement, target
            # success takes priority; otherwise a sub-50 bankroll is a loss stop.
            if bankroll >= TAKE_PROFIT_TARGET:
                stopped = True
                stop_reason = f"Kâr al hedefi {TAKE_PROFIT_TARGET:.0f} birime ulaşıldı."
                break
            if bankroll < STOP_LOSS_FLOOR:
                stopped = True
                stop_reason = f"Kasa {STOP_LOSS_FLOOR:.0f} birimin altına düştü."
                break

        if bankroll <= EPS:
            bankroll = 0.0
            stopped = True
            stop_reason = "Kasa sıfırlandı."
            break

    net = bankroll - INITIAL_BANKROLL
    reached_target = bankroll >= TAKE_PROFIT_TARGET
    summary = {
        "season": season,
        "strategy": strategy,
        "initial_bankroll": INITIAL_BANKROLL,
        "stake_fraction_pct": STAKE_FRACTION * 100.0,
        "eligible_bets_in_season": int(len(bets)),
        "bets_placed": placed,
        "final_bankroll": bankroll,
        "net_profit": net,
        "peak_bankroll": peak,
        "peak_at_bet": peak_at_bet,
        "reached_200": peak_reached_200,
        "take_profit_target_reached": reached_target,
        "profitable_season": net > EPS,
        "losing_season": net < -EPS,
        "break_even_season": abs(net) <= EPS,
        "stopped_by_rule": stopped,
        "stop_reason": stop_reason,
        "roi_on_staked_pct": total_profit / total_staked * 100.0 if total_staked > 0 else np.nan,
        "ledger_exhausted": not stopped and placed >= len(bets),
    }
    return summary, ledger


def main() -> None:
    print("1. Tüm veri yükleniyor...")
    matches = load_global_data().copy()
    required = {
        "_id", "_date", "_season", "Lig/Sezon", "Ev_Sahibi", "Deplasman",
        "MSE", "MSD", "_y", "_y_ou25", *ODDS_COLUMNS,
    }
    missing = sorted(required - set(matches.columns))
    if missing:
        raise KeyError(f"Gerekli sütunlar eksik: {missing}")
    if matches["_id"].duplicated().any():
        raise ValueError("Veri kümesinde yinelenen _id var.")

    matches["_date"] = pd.to_datetime(matches["_date"], errors="coerce")
    matches["_season"] = matches["_season"].astype(str)
    matches["_y_ou25"] = pd.to_numeric(matches["_y_ou25"], errors="coerce")
    matches = matches.dropna(subset=["_date", "_season", "_y_ou25", "_y"]).copy()
    matches = matches.sort_values(["_date", "_id"]).reset_index(drop=True)

    seasons = sorted(matches["_season"].unique().tolist(), key=season_sort_key)
    if len(seasons) < 2:
        raise RuntimeError(f"Walk-forward test için yeterli sezon yok: {seasons}")

    print(f"   Veri aralığı: {matches['_date'].min().date()} – {matches['_date'].max().date()}")
    print(f"   Bulunan sezonlar: {len(seasons)} | {seasons[0]} – {seasons[-1]}")
    print("2. Kronolojik maç öncesi özellikler hesaplanıyor...")
    features = add_momentum(calculate_elo_features(matches))
    data = matches.merge(features, on="_id", how="inner", validate="one_to_one")
    data = data.sort_values(["_date", "_id"]).reset_index(drop=True)

    # Match the established cohort: every 1X2 and OU2.5 decimal odd must be > 1.
    common_mask = pd.Series(True, index=data.index)
    for column in ODDS_COLUMNS:
        common_mask &= valid_odds(data[column])
    common = data.loc[common_mask].copy().sort_values(["_date", "_id"]).reset_index(drop=True)

    summaries: list[dict] = []
    all_ledger: list[dict] = []
    skipped: list[dict] = []

    print("3. Sezon bazında genişleyen pencereyle eğitim ve çıkış stratejileri...")
    for index, season in enumerate(seasons):
        if index == 0:
            skipped.append({
                "season": season,
                "reason": "Önceki sezon olmadığı için sızıntısız eğitim/test yapılamaz.",
            })
            print(f"   {season}: ATLANDI — önceki sezon yok.")
            continue

        prior_seasons = set(seasons[:index])
        train = data.loc[data["_season"].isin(prior_seasons)].copy()
        train = train.dropna(subset=["_y_ou25"])
        train = train.loc[train["_y_ou25"].isin([0, 1])]
        test = common.loc[common["_season"].eq(season)].copy()
        if len(train) < MIN_TRAIN_ROWS:
            skipped.append({
                "season": season,
                "reason": f"Eğitim satırı yetersiz: {len(train)} < {MIN_TRAIN_ROWS}.",
            })
            print(f"   {season}: ATLANDI — eğitim satırı {len(train)}.")
            continue
        if train["_y_ou25"].astype(int).nunique() < 2:
            skipped.append({
                "season": season,
                "reason": "Eğitim verisinde ALT/ÜST iki sınıfı birden yok.",
            })
            print(f"   {season}: ATLANDI — tek sınıflı eğitim.")
            continue
        if test.empty:
            skipped.append({
                "season": season,
                "reason": "Bu sezonda ortak geçerli oran kümesinde maç yok.",
            })
            print(f"   {season}: ATLANDI — ortak geçerli oranlı maç yok.")
            continue

        X_train = train[MODEL_C_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
        X_test = test[MODEL_C_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
        model = make_model()
        model.fit(X_train, train["_y_ou25"].astype(int))
        p_over = model.predict_proba(X_test)[:, 1]
        bets = prepare_season_bets(test, p_over)

        print(
            f"   {season}: eğitim={len(train):,} | ortak test={len(test):,} "
            f"| EV>{EV_THRESHOLD:.2f} bahis={len(bets):,}"
        )

        for strategy in (
            "A_FIXED_TAKE_PROFIT",
            "B_TRAILING_STOP",
            "C_TAKE_PROFIT_AND_STOP_LOSS",
        ):
            summary, ledger = simulate_strategy(bets, season, strategy)
            summaries.append(summary)
            all_ledger.extend(ledger)

    if not summaries:
        raise RuntimeError("Simülasyona uygun hiçbir sezon bulunamadı.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_df = pd.DataFrame(summaries)
    ledger_df = pd.DataFrame(all_ledger)
    skipped_df = pd.DataFrame(skipped)

    season_path = OUTPUT_DIR / "advanced_exit_season_results.csv"
    aggregate_path = OUTPUT_DIR / "advanced_exit_strategy_summary.csv"
    ledger_path = OUTPUT_DIR / "advanced_exit_bet_ledger.csv"
    skipped_path = OUTPUT_DIR / "advanced_exit_skipped_seasons.csv"

    summary_df.to_csv(season_path, index=False, encoding="utf-8-sig")
    ledger_df.to_csv(ledger_path, index=False, encoding="utf-8-sig")
    skipped_df.to_csv(skipped_path, index=False, encoding="utf-8-sig")

    # Aggregate season outcomes. A target-hit rate is reported separately from
    # profitable-season rate; a season may finish profitable without reaching 250.
    aggregate_rows = []
    for strategy, group in summary_df.groupby("strategy", sort=False):
        n = len(group)
        wins = int(group["profitable_season"].sum())
        losses = int(group["losing_season"].sum())
        breaks = int(group["break_even_season"].sum())
        targets = int(group["take_profit_target_reached"].sum())
        aggregate_rows.append({
            "strategy": strategy,
            "seasons_tested": n,
            "profitable_seasons": wins,
            "losing_seasons": losses,
            "break_even_seasons": breaks,
            "take_profit_target_seasons": targets,
            "profitable_season_rate_pct": wins / n * 100.0 if n else np.nan,
            "take_profit_success_rate_pct": targets / n * 100.0 if n else np.nan,
            "mean_final_bankroll": float(group["final_bankroll"].mean()),
            "median_final_bankroll": float(group["final_bankroll"].median()),
            "sum_net_profit_across_independent_100_unit_seasons": float(group["net_profit"].sum()),
            "mean_net_profit_per_season": float(group["net_profit"].mean()),
        })
    aggregate_df = pd.DataFrame(aggregate_rows)
    aggregate_df.to_csv(aggregate_path, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 132)
    print("SEZON BAZINDA KÂR AL / ZİRVE KORUMA / ZARAR DURDUR")
    print("=" * 132)
    display_cols = [
        "season", "strategy", "eligible_bets_in_season", "bets_placed",
        "final_bankroll", "net_profit", "peak_bankroll",
        "take_profit_target_reached", "profitable_season", "losing_season",
        "stop_reason",
    ]
    print(summary_df[display_cols].to_string(
        index=False, float_format=lambda value: f"{value:,.2f}"
    ))

    print("\n" + "=" * 132)
    print("STRATEJİ ÖZETİ — SEZONLAR EŞİT AĞIRLIKLI")
    print("=" * 132)
    print(aggregate_df.to_string(
        index=False, float_format=lambda value: f"{value:,.2f}"
    ))

    print("\nYöntem notları:")
    print("- İlk sezon atlanır; eğitim için yalnızca daha eski sezonlar kullanılabilir.")
    print("- Her test sezonu 100 birimle ayrı başlar; sezonlar arasında kasa taşınmaz.")
    print("- B stratejisinin %25 trailing stop'u ancak kasa 200 birime ilk kez ulaştığında aktif olur.")
    print("- Kâr hedefi başarı oranı, 250 birime ulaşan sezon / test edilen sezon olarak hesaplanır.")
    print("- Kârlı sezon oranı ayrı metriktir; sezon sonunda 100 üzeri kasa hedefe ulaşmakla aynı değildir.")
    print("- Sonuçlar tarihsel backtesttir; 'kumahaneyi yenme' veya gelecekte kâr garantisi göstermez.")
    print(f"\nSezon sonuçları: {season_path}")
    print(f"Strateji özeti: {aggregate_path}")
    print(f"Bahis günlüğü: {ledger_path}")
    print(f"Atlanan sezonlar: {skipped_path}")


if __name__ == "__main__":
    main()
