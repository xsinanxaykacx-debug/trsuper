"""Compare Z-Kahin bankroll management methods on identical Model C predictions.

Fixed training seasons: 2012/2013–2017/2018.
Fixed test seasons: 2018/2019 and 2019/2020.

The model is trained once. Full Kelly, Quarter Kelly, and Flat Bet then use
the exact same predictions, EV > 0.05 selection rule, chronological test rows,
and starting bankroll. The common cohort deliberately matches human_vs_ai.py:
all 1X2 and OU2.5 odds must be valid (> 1.00).

This is a historical simulation, not evidence of a profitable betting edge.
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
KELLY_FRACTIONS = {
    "FULL_KELLY": 1.0,
    "QUARTER_KELLY": 0.25,
}
FLAT_PROFILE = "FLAT_BET"

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
    """Return peak-to-trough drawdown in units and as a percent of prior peak."""
    values = np.asarray(bankroll_path, dtype=float)
    peaks = np.maximum.accumulate(values)
    drawdowns = peaks - values
    drawdown_pct = np.divide(
        drawdowns,
        peaks,
        out=np.zeros_like(drawdowns),
        where=peaks > 0.0,
    )
    return (
        float(drawdowns.max(initial=0.0)),
        float(drawdown_pct.max(initial=0.0) * 100.0),
    )


def _settle(bankroll: float, stake: float, odds: float, won: bool) -> tuple[float, float]:
    """Settle a decimal-odds bet without allowing a negative bankroll."""
    if stake < 0.0 or stake > bankroll + 1e-9:
        raise ValueError(f"Geçersiz bahis/kasa: stake={stake}, bankroll={bankroll}")
    profit = stake * (odds - 1.0) if won else -stake
    new_bankroll = bankroll + profit
    # A losing stake equal to the bankroll can produce exactly zero; never negative.
    if new_bankroll < -1e-8:
        raise ArithmeticError(f"Kasa eksiye düştü: {new_bankroll}")
    return max(0.0, float(new_bankroll)), float(profit)


def _prepare_selections(
    frame: pd.DataFrame,
    p_over: np.ndarray,
) -> dict[str, np.ndarray]:
    """Calculate a single shared OU selection and its odds/probabilities."""
    p = np.clip(np.asarray(p_over, dtype=float), CONFIDENCE_EPS, 1.0 - CONFIDENCE_EPS)
    if len(p) != len(frame):
        raise ValueError("Tahmin sayısı ile test satırı sayısı eşleşmiyor.")

    odds_under = frame["_odd_under25"].to_numpy(dtype=float)
    odds_over = frame["_odd_over25"].to_numpy(dtype=float)
    ev_under = (1.0 - p) * odds_under - 1.0
    ev_over = p * odds_over - 1.0

    choose_over = ev_over > ev_under
    best_ev = np.maximum(ev_under, ev_over)
    take = best_ev > EV_THRESHOLD
    selected_odds = np.where(choose_over, odds_over, odds_under)
    selected_probability = np.where(choose_over, p, 1.0 - p)
    y_over = frame["_y_ou25"].astype(int).to_numpy()
    won = np.where(choose_over, y_over == 1, y_over == 0)

    return {
        "p_over": p,
        "choose_over": choose_over,
        "best_ev": best_ev,
        "take": take,
        "selected_odds": selected_odds,
        "selected_probability": selected_probability,
        "won": won.astype(bool),
    }


def _simulate_strategy(
    frame: pd.DataFrame,
    selection: dict[str, np.ndarray],
    profile: str,
    kelly_multiplier: float | None,
) -> tuple[dict, list[dict]]:
    """Simulate one bankroll policy over the same chronological predictions.

    kelly_multiplier=None means flat 1-unit betting; otherwise stake is the
    Kelly fraction multiplied by 1.0 (full) or 0.25 (quarter).
    If the bankroll cannot cover the next positive stake, stop before placing
    that bet and set stopped_early_insufficient_bankroll=True.
    """
    bankroll = float(INITIAL_BANKROLL)
    bankroll_path = [bankroll]
    bets = 0
    total_staked = 0.0
    total_profit = 0.0
    stopped_early = False
    stop_reason = ""
    ledger: list[dict] = []

    for i, (_, row) in enumerate(frame.iterrows()):
        take = bool(selection["take"][i])
        stake = 0.0
        profit = 0.0
        selected_side = "NO_BET"
        selected_odds = np.nan
        selected_probability = np.nan
        won = None
        ev = float(selection["best_ev"][i])

        if take:
            selected_odds = float(selection["selected_odds"][i])
            selected_probability = float(selection["selected_probability"][i])
            won = bool(selection["won"][i])
            selected_side = "OVER_2.5" if bool(selection["choose_over"][i]) else "UNDER_2.5"

            if kelly_multiplier is None:
                stake = FIXED_STAKE
            else:
                full_fraction = (
                    selected_probability * selected_odds - 1.0
                ) / (selected_odds - 1.0)
                full_fraction = float(np.clip(full_fraction, 0.0, 1.0))
                stake = bankroll * full_fraction * float(kelly_multiplier)

            # Do not place a bet if the available balance cannot cover it.
            if stake > bankroll + 1e-9:
                stopped_early = True
                stop_reason = (
                    f"Kasa bahis miktarını karşılamıyor (kasa={bankroll:.12g}, "
                    f"bahis={stake:.12g})."
                )
                break
            if stake <= 1e-12:
                # No meaningful stake; continue without counting it as a bet.
                stake = 0.0
                selected_side = "NO_BET_TINY_STAKE"
                won = None
                selected_odds = np.nan
                selected_probability = np.nan
            else:
                # Guard against harmless floating-point drift.
                stake = min(float(stake), bankroll)
                bankroll, profit = _settle(
                    bankroll, stake, selected_odds, bool(won)
                )
                bets += 1
                total_staked += stake
                total_profit += profit

        bankroll_path.append(bankroll)
        ledger.append({
            "profile": profile,
            "date": row["_date"],
            "season": row["_season"],
            "match_id": row["_id"],
            "home": row["Ev_Sahibi"],
            "away": row["Deplasman"],
            "selection": selected_side,
            "model_p_over": float(selection["p_over"][i]),
            "selected_side_probability": selected_probability,
            "estimated_best_ev": ev,
            "stake": stake,
            "stake_pct_of_bankroll": (
                stake / bankroll_path[-2] * 100.0 if bankroll_path[-2] > 0 else 0.0
            ),
            "odds": selected_odds,
            "won": won,
            "profit": profit,
            "bankroll_after": bankroll,
        })

        if bankroll <= 1e-12 and i < len(frame) - 1:
            # A zero bankroll cannot place any future positive stake.
            stopped_early = True
            stop_reason = "Kasa sıfırlandı; sonraki bahisler durduruldu."
            break

    max_dd_units, max_dd_pct = _max_drawdown(bankroll_path)
    summary = {
        "profile": profile,
        "initial_bankroll": INITIAL_BANKROLL,
        "final_bankroll": bankroll,
        "net_profit": total_profit,
        "bets": bets,
        "total_staked": total_staked,
        "roi_pct": (total_profit / total_staked * 100.0) if total_staked > 0 else np.nan,
        "max_drawdown_units": max_dd_units,
        "max_drawdown_pct": max_dd_pct,
        "stopped_early_insufficient_bankroll": stopped_early,
        "stop_reason": stop_reason,
        "test_matches_in_common_cohort": len(frame),
        "eligible_ev_matches": int(selection["take"].sum()),
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

    # Keep the same common cohort used by human_vs_ai.py for direct comparability.
    valid_mask = pd.Series(True, index=test_raw.index)
    for col in ODDS_1X2 + ODDS_OU:
        valid_mask &= _valid_odds(test_raw[col])
    common = test_raw.loc[valid_mask].copy().sort_values(
        ["_date", "_id"]
    ).reset_index(drop=True)
    if common.empty:
        raise RuntimeError("Ortak test kümesinde geçerli oranlı maç bulunamadı.")

    print("\n3. Sabit ortak test kümesi")
    print(f"   Eğitim sezonları: {TRAIN_SEASONS[0]}–{TRAIN_SEASONS[-1]}")
    print(f"   Eğitim maçı: {len(train):,}")
    print(f"   Ham test maçı: {len(test_raw):,}")
    print(f"   Ortak test maçı (1X2 + OU oranları geçerli): {len(common):,}")
    print(f"   Test sezonları: {', '.join(TEST_SEASONS)}")
    print(f"   Başlangıç kasası: {INITIAL_BANKROLL:.2f}")
    print(f"   Ortak seçim kuralı: en yüksek ALT/ÜST EV > {EV_THRESHOLD:.2f}")
    print("   Model bir kez eğitilecek; üç strateji aynı tahminleri kullanacak.")

    print("\n4. Model C bir kez eğitiliyor...")
    X_train = train[MODEL_C_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    X_common = common[MODEL_C_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    model = make_model()
    model.fit(X_train, train["_y_ou25"].astype(int))
    p_over = model.predict_proba(X_common)[:, 1]
    selections = _prepare_selections(common, p_over)

    print(f"   Model C tahmini: {len(p_over):,}")
    print(f"   EV eşiğini geçen maç: {int(selections['take'].sum()):,}")

    print("\n5. Üç kasa yönetimi aynı tahminlerle simüle ediliyor...")
    profiles = [
        ("FULL_KELLY", KELLY_FRACTIONS["FULL_KELLY"]),
        ("QUARTER_KELLY", KELLY_FRACTIONS["QUARTER_KELLY"]),
        (FLAT_PROFILE, None),
    ]
    summaries: list[dict] = []
    ledgers: list[dict] = []
    for profile, multiplier in profiles:
        summary, ledger = _simulate_strategy(common, selections, profile, multiplier)
        summaries.append(summary)
        ledgers.extend(ledger)

    summary_df = pd.DataFrame(summaries)
    ledger_df = pd.DataFrame(ledgers)
    output_dir = Path("data/csv")
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "human_vs_ai_v2_results.csv"
    ledger_path = output_dir / "human_vs_ai_v2_bet_ledger.csv"
    summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")
    ledger_df.to_csv(ledger_path, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 112)
    print("Z-KÂHİN — KASA YÖNETİMİ KARŞILAŞTIRMASI | 2018/19 + 2019/20")
    print("=" * 112)
    display_cols = [
        "profile", "initial_bankroll", "final_bankroll", "net_profit",
        "bets", "total_staked", "roi_pct", "max_drawdown_units",
        "max_drawdown_pct", "stopped_early_insufficient_bankroll",
    ]
    print(summary_df[display_cols].to_string(
        index=False, float_format=lambda value: f"{value:.2f}"
    ))
    print(f"\nÖzet CSV: {summary_path}")
    print(f"Bahis günlüğü CSV: {ledger_path}")

    print("\nYorumlama:")
    print(
        "Üç stratejinin seçimleri, olasılık tahminleri ve EV eşiği aynıdır; fark yalnızca "
        "kasa yönetimidir. Flat Bet, EV eşiğini geçen her maçta 1 birim yatırır. "
        "ROI = toplam net kâr / toplam yatırılan tutar. Maksimum düşüş, önceki kasa "
        "zirvesinden görülen en büyük mutlak ve yüzdesel gerilemedir."
    )
    print(
        "Bu test dönemi sonuçları geriye dönüktür. Kasa yönetimi sonuçları değiştirirken "
        "Model C'nin tahmin kalitesini değiştirmez; gerçek bir avantaj iddiası için "
        "ayrıca kalibrasyon ve dokunulmamış ileri dönem doğrulaması gerekir."
    )


if __name__ == "__main__":
    main()
