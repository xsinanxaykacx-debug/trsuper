"""Weekly take-profit backtest for Model C (EV > 0.05).

Run from repository root:
    python -m src.weekly_take_profit

Fixed training seasons and test seasons match src.ablation_study. Each ISO
calendar week within each test season is an independent session starting at
100 units. Model C selections are placed chronologically with 20% fractional
staking; a session stops after settlement when bankroll reaches >= 200 or
falls to <= 50. Weeks with no selected bets are retained with a 100-unit close.

This is a historical backtest, not evidence of a reliable future betting edge.
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
    TEST_SEASONS,
    TRAIN_SEASONS,
    add_momentum,
    make_model,
)
from src.features import calculate_elo_features
from src.load_global import load_global_data


INITIAL_BANKROLL = 100.0
STAKE_FRACTION = 0.20
TAKE_PROFIT_TARGET = 200.0
STOP_LOSS_FLOOR = 50.0
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

REQUIRED_COLUMNS = {
    "_id", "_date", "_season", "Ev_Sahibi", "Deplasman",
    "_y_ou25", "_odd_under25", "_odd_over25",
}


def valid_decimal_odds(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values.notna() & np.isfinite(values) & values.gt(1.0)


def prepare_model_c_bets(frame: pd.DataFrame, p_over: np.ndarray) -> pd.DataFrame:
    """Select the better of Under/Over only when its estimated EV exceeds 0.05."""
    out = frame.copy().reset_index(drop=True)
    p = np.clip(np.asarray(p_over, dtype=float), 1e-7, 1.0 - 1e-7)
    if len(p) != len(out):
        raise ValueError("Tahmin sayısı ile test satırı sayısı eşleşmiyor.")

    odds_under = out["_odd_under25"].to_numpy(dtype=float)
    odds_over = out["_odd_over25"].to_numpy(dtype=float)
    actual_over = out["_y_ou25"].astype(int).to_numpy()

    ev_under = (1.0 - p) * odds_under - 1.0
    ev_over = p * odds_over - 1.0
    choose_over = ev_over > ev_under
    best_ev = np.maximum(ev_under, ev_over)
    selected = best_ev > EV_THRESHOLD

    if not np.any(selected):
        return pd.DataFrame(columns=[
            "_id", "_date", "_season", "Ev_Sahibi", "Deplasman",
            "_iso_year", "_iso_week", "selection", "selected_odds",
            "won", "estimated_best_ev",
        ])

    selected_rows = out.loc[selected].copy()
    selected_rows["selection"] = np.where(choose_over[selected], "OVER_2.5", "UNDER_2.5")
    selected_rows["selected_odds"] = np.where(
        choose_over[selected], odds_over[selected], odds_under[selected]
    )
    selected_rows["won"] = np.where(
        choose_over[selected], actual_over[selected] == 1, actual_over[selected] == 0
    ).astype(bool)
    selected_rows["estimated_best_ev"] = best_ev[selected]
    return selected_rows.sort_values(["_date", "_id"]).reset_index(drop=True)


def simulate_week(week: pd.DataFrame, season: str, iso_year: int, iso_week: int,
                  total_matches: int, valid_odds_matches: int) -> tuple[dict, list[dict]]:
    bankroll = INITIAL_BANKROLL
    placed = 0
    total_staked = 0.0
    total_profit = 0.0
    ledger: list[dict] = []
    stop_reason = "Hafta sonuna kadar hedef veya zarar durdur tetiklenmedi."
    outcome = "HAFTA_SONU_ARALIKTA"

    for row in week.sort_values(["_date", "_id"]).to_dict("records"):
        if bankroll <= EPS:
            bankroll = 0.0
            outcome = "ZARAR_DURDUR"
            stop_reason = "Kasa sıfırlandı."
            break

        before = bankroll
        stake = before * STAKE_FRACTION
        odds = float(row["selected_odds"])
        won = bool(row["won"])
        profit = stake * (odds - 1.0) if won else -stake
        bankroll = max(0.0, float(before + profit))
        placed += 1
        total_staked += stake
        total_profit += profit

        ledger.append({
            "season": season,
            "iso_year": iso_year,
            "iso_week": iso_week,
            "week_id": f"{iso_year}-W{iso_week:02d}",
            "bet_number": placed,
            "_id": row["_id"],
            "_date": row["_date"],
            "Ev_Sahibi": row["Ev_Sahibi"],
            "Deplasman": row["Deplasman"],
            "selection": row["selection"],
            "selected_odds": odds,
            "won": won,
            "estimated_best_ev": float(row["estimated_best_ev"]),
            "bankroll_before": before,
            "stake": stake,
            "profit": profit,
            "bankroll_after": bankroll,
        })

        # Check the take-profit rule first after each settled bet.
        if bankroll >= TAKE_PROFIT_TARGET:
            outcome = "KAR_HEDEFI"
            stop_reason = f"Kasa {TAKE_PROFIT_TARGET:.0f} birime ulaştı/aştı."
            break
        if bankroll <= STOP_LOSS_FLOOR:
            outcome = "ZARAR_DURDUR"
            stop_reason = f"Kasa {STOP_LOSS_FLOOR:.0f} birime düştü/aştı."
            break

    if not week.empty and placed == 0:
        outcome = "HAFTA_SONU_ARALIKTA"
    elif placed == 0:
        outcome = "HAFTA_SONU_ARALIKTA"
        stop_reason = "Bu haftada EV > 0.05 koşulunu sağlayan bahis yok."

    net_profit = bankroll - INITIAL_BANKROLL
    summary = {
        "season": season,
        "iso_year": int(iso_year),
        "iso_week": int(iso_week),
        "week_id": f"{iso_year}-W{iso_week:02d}",
        "week_start": pd.Timestamp.fromisocalendar(int(iso_year), int(iso_week), 1).date(),
        "week_end": pd.Timestamp.fromisocalendar(int(iso_year), int(iso_week), 7).date(),
        "matches_in_week": int(total_matches),
        "matches_with_valid_odds": int(valid_odds_matches),
        "eligible_model_c_bets": int(len(week)),
        "bets_placed": int(placed),
        "initial_bankroll": INITIAL_BANKROLL,
        "final_bankroll": float(bankroll),
        "net_profit": float(net_profit),
        "outcome": outcome,
        "take_profit_hit": outcome == "KAR_HEDEFI",
        "stop_loss_hit": outcome == "ZARAR_DURDUR",
        "week_ended_between_limits": outcome == "HAFTA_SONU_ARALIKTA",
        "total_staked": float(total_staked),
        "profit_on_staked_pct": total_profit / total_staked * 100.0 if total_staked > 0 else np.nan,
        "stop_reason": stop_reason,
    }
    return summary, ledger


def main() -> None:
    print("1. Global veri yükleniyor...")
    matches = load_global_data().copy()
    missing = sorted(REQUIRED_COLUMNS - set(matches.columns))
    if missing:
        raise KeyError(f"Gerekli sütunlar eksik: {missing}")
    if matches["_id"].duplicated().any():
        raise ValueError("Global veri kümesinde yinelenen _id var.")

    matches["_date"] = pd.to_datetime(matches["_date"], errors="coerce")
    matches["_season"] = matches["_season"].astype(str)
    matches["_y_ou25"] = pd.to_numeric(matches["_y_ou25"], errors="coerce")
    matches = matches.dropna(subset=["_date", "_season", "_y_ou25"]).copy()
    matches = matches.loc[matches["_y_ou25"].isin([0, 1])].copy()
    matches = matches.sort_values(["_date", "_id"]).reset_index(drop=True)

    absent_train = sorted(set(TRAIN_SEASONS) - set(matches["_season"].unique()))
    absent_test = sorted(set(TEST_SEASONS) - set(matches["_season"].unique()))
    if absent_train or absent_test:
        raise ValueError(f"Sezon eksik. Eğitim: {absent_train}; test: {absent_test}")

    print("2. Kronolojik maç öncesi özellikleri hesaplanıyor...")
    features = add_momentum(calculate_elo_features(matches))
    data = matches.merge(features, on="_id", how="inner", validate="one_to_one")
    data = data.sort_values(["_date", "_id"]).reset_index(drop=True)

    train = data.loc[data["_season"].isin(TRAIN_SEASONS)].copy()
    train = train.dropna(subset=["_y_ou25"])
    train = train.loc[train["_y_ou25"].isin([0, 1])].copy()
    test_raw = data.loc[data["_season"].isin(TEST_SEASONS)].copy()

    if len(train) < MIN_TRAIN_ROWS:
        raise RuntimeError(f"Eğitim örneği yetersiz: {len(train)} < {MIN_TRAIN_ROWS}")
    if train["_y_ou25"].astype(int).nunique() != 2:
        raise RuntimeError("Eğitim verisinde ALT/ÜST hedefinin iki sınıfı da yok.")
    if test_raw.empty:
        raise RuntimeError("Sabit test sezonlarında maç bulunamadı.")

    # Define weekly sessions from all dated test matches, not only matches with
    # odds. Thus a calendar week with no usable odds or no Model C bet is retained.
    iso = test_raw["_date"].dt.isocalendar()
    test_raw["_iso_year"] = iso["year"].astype(int)
    test_raw["_iso_week"] = iso["week"].astype(int)

    odds_valid = (
        valid_decimal_odds(test_raw["_odd_under25"])
        & valid_decimal_odds(test_raw["_odd_over25"])
    )
    test = test_raw.loc[odds_valid].copy().sort_values(["_date", "_id"]).reset_index(drop=True)
    if test.empty:
        raise RuntimeError("Test sezonlarında geçerli ALT ve ÜST oranı olan maç yok.")

    print("3. Model C sabit eğitim kümesiyle bir kez eğitiliyor...")
    X_train = train[MODEL_C_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    X_test = test[MODEL_C_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    model = make_model()
    model.fit(X_train, train["_y_ou25"].astype(int))
    p_over = model.predict_proba(X_test)[:, 1]
    selected_bets = prepare_model_c_bets(test, p_over)

    # Keep every season × ISO-week session represented by at least one match.
    all_weeks = (
        test_raw.groupby(["_season", "_iso_year", "_iso_week"], sort=True)
        .agg(
            matches_in_week=("_id", "size"),
            week_start_date=("_date", "min"),
        )
        .reset_index()
    )
    valid_counts = (
        test.groupby(["_season", "_iso_year", "_iso_week"], sort=True)
        .size().rename("matches_with_valid_odds").reset_index()
    )
    all_weeks = all_weeks.merge(
        valid_counts, on=["_season", "_iso_year", "_iso_week"], how="left"
    )
    all_weeks["matches_with_valid_odds"] = (
        all_weeks["matches_with_valid_odds"].fillna(0).astype(int)
    )

    weekly_rows: list[dict] = []
    all_ledger: list[dict] = []
    for key in all_weeks[["_season", "_iso_year", "_iso_week"]].itertuples(
        index=False, name=None
    ):
        season, iso_year, iso_week = key
        week_bets = selected_bets.loc[
            selected_bets["_season"].eq(season)
            & selected_bets["_iso_year"].eq(iso_year)
            & selected_bets["_iso_week"].eq(iso_week)
        ].copy()
        week_meta = all_weeks.loc[
            all_weeks["_season"].eq(season)
            & all_weeks["_iso_year"].eq(iso_year)
            & all_weeks["_iso_week"].eq(iso_week)
        ].iloc[0]
        summary, ledger = simulate_week(
            week_bets,
            str(season),
            int(iso_year),
            int(iso_week),
            int(week_meta["matches_in_week"]),
            int(week_meta["matches_with_valid_odds"]),
        )
        weekly_rows.append(summary)
        all_ledger.extend(ledger)

    weekly_df = pd.DataFrame(weekly_rows).sort_values(
        ["season", "iso_year", "iso_week"]
    ).reset_index(drop=True)
    if weekly_df.empty:
        raise RuntimeError("Haftalık sonuç üretilemedi.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    weekly_path = OUTPUT_DIR / "weekly_take_profit_results.csv"
    ledger_path = OUTPUT_DIR / "weekly_take_profit_bet_ledger.csv"
    summary_path = OUTPUT_DIR / "weekly_take_profit_summary.csv"

    ledger_df = pd.DataFrame(all_ledger)
    weekly_df.to_csv(weekly_path, index=False, encoding="utf-8-sig")
    ledger_df.to_csv(ledger_path, index=False, encoding="utf-8-sig")

    n_weeks = int(len(weekly_df))
    target_weeks = int(weekly_df["take_profit_hit"].sum())
    loss_weeks = int(weekly_df["stop_loss_hit"].sum())
    neutral_weeks = int(weekly_df["week_ended_between_limits"].sum())
    total_net = float(weekly_df["net_profit"].sum())
    successful_week_withdrawals = float(
        weekly_df.loc[weekly_df["take_profit_hit"], "net_profit"].sum()
    )
    summary_df = pd.DataFrame([{
        "test_seasons": ", ".join(TEST_SEASONS),
        "training_seasons": ", ".join(TRAIN_SEASONS),
        "weeks_tested": n_weeks,
        "take_profit_weeks": target_weeks,
        "take_profit_success_rate_pct": target_weeks / n_weeks * 100.0,
        "stop_loss_weeks": loss_weeks,
        "week_end_between_limits": neutral_weeks,
        "weeks_with_no_eligible_bets": int((weekly_df["eligible_model_c_bets"] == 0).sum()),
        "initial_bankroll_per_week": INITIAL_BANKROLL,
        "stake_fraction_pct": STAKE_FRACTION * 100.0,
        "take_profit_target": TAKE_PROFIT_TARGET,
        "stop_loss_floor": STOP_LOSS_FLOOR,
        "successful_week_profit_withdrawn": successful_week_withdrawals,
        "total_net_profit_all_independent_weeks": total_net,
        "mean_net_profit_per_week": float(weekly_df["net_profit"].mean()),
        "median_net_profit_per_week": float(weekly_df["net_profit"].median()),
        "total_bets_placed": int(weekly_df["bets_placed"].sum()),
        "total_model_c_eligible_bets": int(weekly_df["eligible_model_c_bets"].sum()),
    }])
    summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 100)
    print("HAFTALIK KÂR AL — MODEL C (EV > 0.05)")
    print("=" * 100)
    print(f"Test sezonları: {', '.join(TEST_SEASONS)}")
    print(f"Test edilen hafta: {n_weeks}")
    print(f"200 birim kâr hedefi: {target_weeks} hafta (%{target_weeks / n_weeks * 100.0:.2f})")
    print(f"50 birim zarar durdur: {loss_weeks} hafta")
    print(f"Hafta sonu iki sınıra da ulaşmayan: {neutral_weeks} hafta")
    print(f"Betsiz hafta: {int((weekly_df['eligible_model_c_bets'] == 0).sum())}")
    print(f"Başarılı haftalarda çekilen net kâr: {successful_week_withdrawals:+.2f} birim")
    print(f"Tüm haftaların toplam net kâr/zararı: {total_net:+.2f} birim")
    print(f"Hafta başına ortalama net sonuç: {weekly_df['net_profit'].mean():+.2f} birim")

    display_cols = [
        "season", "week_id", "matches_in_week", "eligible_model_c_bets",
        "bets_placed", "final_bankroll", "net_profit", "outcome",
    ]
    print("\nHafta bazında sonuçlar:")
    print(weekly_df[display_cols].to_string(
        index=False, float_format=lambda value: f"{value:,.2f}"
    ))
    print("\nÇıktılar:")
    print(f"Haftalık sonuçlar: {weekly_path}")
    print(f"Bahis günlüğü: {ledger_path}")
    print(f"Genel özet: {summary_path}")
    print("\nYöntem notları:")
    print("- Her sezonun her ISO takvim haftası, o hafta içinde en az bir maç varsa ayrı oturumdur.")
    print("- Her hafta 100 birimle başlar; bahis tutarı her maç öncesi kasanın %20'sidir.")
    print("- Eşikler bahis sonuçlandıktan sonra kontrol edilir; kasa 200'ü aşabilir veya 50'nin altına inebilir.")
    print("- Başarılı haftalardaki çekilen kâr, başarılı haftaların son kasası eksi 100 toplamıdır.")
    print("- Tüm haftaların toplam net sonucu, her bağımsız haftanın son kasası eksi 100 toplamıdır.")
    print("- Haftalık oturumlar aynı maçları kullanarak bir kâr garantisi veya bağımsız kanıt sağlamaz.")


if __name__ == "__main__":
    main()
