"""Peak-tracking trailing-stop backtest for Model C (EV > 0.05).

Run from repository root:
    python -m src.peak_exit_strategy

The 2018/2019 and 2019/2020 test matches are processed as one continuous,
chronological stream. Every session starts with 100 units and each bet stakes
20% of the current bankroll. Once bankroll has risen above 100, the session
closes when bankroll falls to or below 75% of its historical session peak.
If the bankroll never rises above 100 and falls below 50, it closes by
stop-loss. After any closure, the next eligible bet starts a fresh 100-unit
session.

This is a historical simulation, not evidence of a reliable future betting edge.
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
TRAILING_DRAWDOWN = 0.25
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
    """Select the higher-EV side only when estimated EV is strictly above 0.05."""
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
            "selection", "selected_odds", "won", "estimated_best_ev",
        ])

    selected_rows = out.loc[selected].copy()
    selected_rows["selection"] = np.where(
        choose_over[selected], "OVER_2.5", "UNDER_2.5"
    )
    selected_rows["selected_odds"] = np.where(
        choose_over[selected], odds_over[selected], odds_under[selected]
    )
    selected_rows["won"] = np.where(
        choose_over[selected],
        actual_over[selected] == 1,
        actual_over[selected] == 0,
    ).astype(bool)
    selected_rows["estimated_best_ev"] = best_ev[selected]
    return selected_rows.sort_values(["_date", "_id"]).reset_index(drop=True)


def simulate_sessions(bets: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run one continuous chronological stream, resetting to 100 after each exit."""
    session_rows: list[dict] = []
    ledger_rows: list[dict] = []

    session_number = 1
    session_start_bankroll = INITIAL_BANKROLL
    bankroll = INITIAL_BANKROLL
    peak_bankroll = INITIAL_BANKROLL
    peak_date = pd.NaT
    session_start_date = pd.NaT
    session_start_match_id = None
    session_bets = 0
    session_staked = 0.0
    session_profit = 0.0
    session_peak_ever = INITIAL_BANKROLL
    closed_sessions = 0
    trailing_exit_count = 0
    stop_loss_count = 0
    total_withdrawn_profit = 0.0
    total_closed_session_pnl = 0.0

    for row in bets.sort_values(["_date", "_id"]).to_dict("records"):
        if session_start_date is pd.NaT or pd.isna(session_start_date):
            session_start_date = row["_date"]
            session_start_match_id = row["_id"]

        bankroll_before = bankroll
        stake = bankroll_before * STAKE_FRACTION
        odds = float(row["selected_odds"])
        won = bool(row["won"])
        profit = stake * (odds - 1.0) if won else -stake
        bankroll = max(0.0, float(bankroll_before + profit))
        session_bets += 1
        session_staked += stake
        session_profit += profit

        if bankroll > peak_bankroll:
            peak_bankroll = bankroll
            peak_date = row["_date"]
        session_peak_ever = max(session_peak_ever, peak_bankroll)

        trailing_level = peak_bankroll * (1.0 - TRAILING_DRAWDOWN)
        trailing_triggered = (
            peak_bankroll > INITIAL_BANKROLL + EPS
            and bankroll <= trailing_level + EPS
        )
        stop_loss_triggered = (
            peak_bankroll <= INITIAL_BANKROLL + EPS
            and bankroll < STOP_LOSS_FLOOR - EPS
        )

        exit_reason = None
        if trailing_triggered:
            exit_reason = "ZIRVEDEN_%25_DUSUS"
        elif stop_loss_triggered:
            exit_reason = "50_BIRIM_ALTI"

        ledger_rows.append({
            "session": session_number,
            "_id": row["_id"],
            "_date": row["_date"],
            "_season": row["_season"],
            "Ev_Sahibi": row["Ev_Sahibi"],
            "Deplasman": row["Deplasman"],
            "selection": row["selection"],
            "selected_odds": odds,
            "won": won,
            "estimated_best_ev": float(row["estimated_best_ev"]),
            "bankroll_before": bankroll_before,
            "stake": stake,
            "profit": profit,
            "bankroll_after": bankroll,
            "session_peak_after": peak_bankroll,
            "trailing_stop_level": trailing_level,
            "drawdown_from_peak_pct": (
                (peak_bankroll - bankroll) / peak_bankroll * 100.0
                if peak_bankroll > 0 else np.nan
            ),
            "exit_reason": exit_reason or "",
        })

        if exit_reason is None:
            continue

        session_net = bankroll - session_start_bankroll
        if exit_reason == "ZIRVEDEN_%25_DUSUS":
            trailing_exit_count += 1
            # All positive net results at a trailing-stop closure are withdrawn.
            withdrawn_profit = max(0.0, session_net)
            total_withdrawn_profit += withdrawn_profit
        else:
            stop_loss_count += 1
            withdrawn_profit = 0.0

        closed_sessions += 1
        total_closed_session_pnl += session_net
        session_rows.append({
            "session": session_number,
            "start_date": session_start_date,
            "end_date": row["_date"],
            "start_match_id": session_start_match_id,
            "end_match_id": row["_id"],
            "bets_placed": session_bets,
            "initial_bankroll": session_start_bankroll,
            "final_bankroll": bankroll,
            "peak_bankroll": peak_bankroll,
            "peak_date": peak_date,
            "trailing_stop_level_at_peak": peak_bankroll * (1.0 - TRAILING_DRAWDOWN),
            "net_profit_loss": session_net,
            "withdrawn_profit": withdrawn_profit,
            "total_staked": session_staked,
            "profit_on_staked_pct": (
                session_profit / session_staked * 100.0
                if session_staked > 0 else np.nan
            ),
            "exit_reason": exit_reason,
            "is_closed": True,
        })

        # Start a new independent 100-unit session at the next eligible bet.
        session_number += 1
        bankroll = INITIAL_BANKROLL
        session_start_bankroll = INITIAL_BANKROLL
        peak_bankroll = INITIAL_BANKROLL
        peak_date = pd.NaT
        session_start_date = pd.NaT
        session_start_match_id = None
        session_bets = 0
        session_staked = 0.0
        session_profit = 0.0
        session_peak_ever = INITIAL_BANKROLL

    # The final session may remain active at the end of the test stream.
    active_session = session_bets > 0
    if active_session:
        active_net = bankroll - session_start_bankroll
        session_rows.append({
            "session": session_number,
            "start_date": session_start_date,
            "end_date": bets.sort_values(["_date", "_id"]).iloc[-1]["_date"],
            "start_match_id": session_start_match_id,
            "end_match_id": bets.sort_values(["_date", "_id"]).iloc[-1]["_id"],
            "bets_placed": session_bets,
            "initial_bankroll": session_start_bankroll,
            "final_bankroll": bankroll,
            "peak_bankroll": peak_bankroll,
            "peak_date": peak_date,
            "trailing_stop_level_at_peak": peak_bankroll * (1.0 - TRAILING_DRAWDOWN),
            "net_profit_loss": active_net,
            "withdrawn_profit": 0.0,
            "total_staked": session_staked,
            "profit_on_staked_pct": (
                session_profit / session_staked * 100.0
                if session_staked > 0 else np.nan
            ),
            "exit_reason": "AKTIF_SEANS_TEST_SONU",
            "is_closed": False,
        })

    sessions = pd.DataFrame(session_rows)
    ledger = pd.DataFrame(ledger_rows)

    # Reconcile the strategy's result against all 100-unit session allocations.
    # Each completed session's P/L is counted once; the active session contributes
    # its current bankroll minus its own initial 100 units. This avoids treating
    # every reset as free capital.
    if not sessions.empty:
        closed_pnl = float(sessions.loc[sessions["is_closed"], "net_profit_loss"].sum())
        active_pnl = float(sessions.loc[~sessions["is_closed"], "net_profit_loss"].sum())
        total_strategy_net = closed_pnl + active_pnl
        if not np.isclose(total_strategy_net, total_closed_session_pnl + active_pnl, atol=1e-6):
            raise RuntimeError("Seans kâr/zarar mutabakatı başarısız.")

    return sessions, ledger


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

    if selected_bets.empty:
        raise RuntimeError("Model C için EV > 0.05 koşulunu sağlayan test bahsi bulunamadı.")

    print("\n4. Test sezonları tek kronolojik akış olarak simüle ediliyor...")
    print(f"   Eğitim sezonları: {', '.join(TRAIN_SEASONS)}")
    print(f"   Test sezonları: {', '.join(TEST_SEASONS)}")
    print(f"   Ham test maçı: {len(test_raw):,}")
    print(f"   Geçerli oranlı test maçı: {len(test):,}")
    print(f"   Model C bahis adedi (EV > {EV_THRESHOLD:.2f}): {len(selected_bets):,}")
    print(f"   Başlangıç seansı: {INITIAL_BANKROLL:.2f} birim")
    print(f"   Bahis: kasanın %{STAKE_FRACTION * 100:.0f}'si")
    print(f"   Zirve düşüş eşiği: %{TRAILING_DRAWDOWN * 100:.0f}")
    print(f"   İlk zirve oluşmadan zarar durdur: kasa < {STOP_LOSS_FLOOR:.0f}")

    sessions_df, ledger_df = simulate_sessions(selected_bets)
    if sessions_df.empty:
        raise RuntimeError("Simülasyon hiçbir seans sonucu üretmedi.")

    closed = sessions_df.loc[sessions_df["is_closed"]].copy()
    active = sessions_df.loc[~sessions_df["is_closed"]].copy()
    trailing = closed.loc[closed["exit_reason"].eq("ZIRVEDEN_%25_DUSUS")]
    stop_loss = closed.loc[closed["exit_reason"].eq("50_BIRIM_ALTI")]

    total_sessions_opened = int(len(sessions_df))
    trailing_count = int(len(trailing))
    stop_count = int(len(stop_loss))
    active_count = int(len(active))
    highest_peak = float(sessions_df["peak_bankroll"].max())
    pocketed_profit = float(trailing["withdrawn_profit"].sum())
    closed_session_pnl = float(closed["net_profit_loss"].sum())
    active_bankroll = float(active.iloc[-1]["final_bankroll"]) if active_count else 0.0
    active_net = float(active.iloc[-1]["net_profit_loss"]) if active_count else 0.0
    total_strategy_net = closed_session_pnl + active_net
    total_allocated = total_sessions_opened * INITIAL_BANKROLL
    effective_final_value = total_allocated + total_strategy_net
    total_bets = int(sessions_df["bets_placed"].sum())

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sessions_path = OUTPUT_DIR / "peak_exit_strategy_sessions.csv"
    ledger_path = OUTPUT_DIR / "peak_exit_strategy_bet_ledger.csv"
    summary_path = OUTPUT_DIR / "peak_exit_strategy_summary.csv"

    sessions_df.to_csv(sessions_path, index=False, encoding="utf-8-sig")
    ledger_df.to_csv(ledger_path, index=False, encoding="utf-8-sig")
    summary_df = pd.DataFrame([{
        "training_seasons": ", ".join(TRAIN_SEASONS),
        "test_seasons": ", ".join(TEST_SEASONS),
        "eligible_bets": len(selected_bets),
        "bets_placed": total_bets,
        "sessions_opened": total_sessions_opened,
        "sessions_closed_by_trailing_25pct": trailing_count,
        "sessions_closed_by_below_50_stop_loss": stop_count,
        "active_sessions_at_test_end": active_count,
        "highest_bankroll_peak": highest_peak,
        "total_pocketed_profit": pocketed_profit,
        "closed_sessions_net_pnl": closed_session_pnl,
        "active_bankroll_at_test_end": active_bankroll,
        "active_session_net_pnl": active_net,
        "total_strategy_net_profit_loss": total_strategy_net,
        "total_100_unit_allocations": total_allocated,
        "effective_final_value_including_allocations": effective_final_value,
        "net_vs_one_initial_100_unit_bankroll": total_strategy_net,
        "stake_fraction_pct": STAKE_FRACTION * 100.0,
        "trailing_drawdown_pct": TRAILING_DRAWDOWN * 100.0,
        "stop_loss_floor": STOP_LOSS_FLOOR,
    }])
    summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 104)
    print("ZİRVEYİ TAKİP ET — DYNAMIC TRAILING STOP | MODEL C")
    print("=" * 104)
    print(f"Test akışı: {', '.join(TEST_SEASONS)} (tek kronolojik simülasyon)")
    print(f"Toplam açılan seans: {total_sessions_opened}")
    print(f"Zirveden %25 düşüş ile kapanan: {trailing_count}")
    print(f"50 birimin altı stop-loss ile kapanan: {stop_count}")
    print(f"Test sonunda aktif kalan seans: {active_count}")
    print(f"Görülen en yüksek kasa zirvesi: {highest_peak:.2f} birim")
    print(f"Cebe atılan toplam kâr (yalnız zirve çıkışları): {pocketed_profit:+.2f} birim")
    print(f"Kapanan seansların net kâr/zararı: {closed_session_pnl:+.2f} birim")
    print(f"Test sonundaki aktif kasa: {active_bankroll:.2f} birim")
    print(f"Aktif seansın net sonucu: {active_net:+.2f} birim")
    print(f"TOPLAM NET KÂR/ZARAR: {total_strategy_net:+.2f} birim")
    print(f"Her seans için 100 birimlik toplam tahsis: {total_allocated:.2f} birim")
    print(f"Tahsisler dahil simüle edilmiş toplam değer: {effective_final_value:.2f} birim")
    print(
        "Not: Toplam net, kapanan her seansın (son kasa - 100) sonucu ile "
        "aktif seansın (aktif kasa - 100) toplamıdır; her sıfırlama bedava sermaye sayılmaz."
    )

    display_cols = [
        "session", "start_date", "end_date", "bets_placed", "peak_bankroll",
        "final_bankroll", "net_profit_loss", "withdrawn_profit", "exit_reason", "is_closed",
    ]
    print("\nSeans sonuçları:")
    print(sessions_df[display_cols].to_string(
        index=False, float_format=lambda value: f"{value:,.2f}"
    ))
    print("\nÇıktılar:")
    print(f"Seans sonuçları: {sessions_path}")
    print(f"Bahis günlüğü: {ledger_path}")
    print(f"Genel özet: {summary_path}")
    print("\nYöntem notları:")
    print("- Model C, sabit 2012/2013–2017/2018 eğitim sezonlarıyla yalnızca bir kez eğitilir.")
    print("- Test bahisleri 2018/2019 ve 2019/2020 boyunca tarih + maç ID ile sıralanır.")
    print("- Her bahis öncesi kasa tutarının %20'si yatırılır; sonuçtan sonra zirve güncellenir.")
    print("- Zirve 100'ü aştıktan sonra kasa zirvenin %75'ine veya altına inerse seans kapanır.")
    print("- Zirve 100'ü aşmadıysa kasa 50'nin ALTINA indiğinde stop-loss uygulanır.")
    print("- Kapanan seansın tüm net sonucu, strateji toplamına dahil edilir; pozitif trailing çıkışı ayrıca cebe atılan kâr olarak raporlanır.")
    print("- Seans sıfırlaması yeni 100 birim tahsis varsayar; bu ek tahsisler toplam netten düşülür.")


if __name__ == "__main__":
    main()
