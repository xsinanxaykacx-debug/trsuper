"""Out-of-sample comparison of alternative OU 2.5 betting rules.

Fixed protocol:
- Train: seasons 2012/2013 through 2016/2017.
- Test: seasons 2018/2019 and 2019/2020, unchanged.
- Model: the existing XGBoost baseline from src.ablation_study.make_model().
- Target: _y_ou25 = 1 (OVER 2.5), 0 (UNDER 2.5).
- All rules use the same test matches with valid decimal odds on both sides.
- Fixed stake: 1 unit; no retraining, threshold fitting, or calibration on test data.

Rules:
A. Highest side EV > 0.15.
B. Highest side EV > 0.20.
C. Under-only and Over-only, each requiring side-specific EV > 0.05.
D. Odds bands for the highest-EV side, intersected with EV > 0.05.

Run from the repository root:
    python -m src.alternative_betting_rules
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import t
from sklearn.metrics import brier_score_loss, log_loss

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
OUTPUT_DIR = Path("data/csv")
SUMMARY_PATH = OUTPUT_DIR / "alternative_betting_rules_summary.csv"
LEDGER_PATH = OUTPUT_DIR / "alternative_betting_rules_ledger.csv"
PREDICTIONS_PATH = OUTPUT_DIR / "alternative_betting_rules_predictions.csv"

# Intervals are evaluated on the selected side's offered decimal odds.
# Each odds-band rule additionally requires the baseline EV > 0.05.
ODDS_BANDS = [
    ("ODDS_1.50_1.80", 1.50, 1.80),
    ("ODDS_1.80_2.20", 1.80, 2.20),
    ("ODDS_2.20_3.00", 2.20, 3.00),
    ("ODDS_3.00_PLUS", 3.00, np.inf),
]

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


def valid_decimal_odds(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values.notna() & np.isfinite(values) & values.gt(1.0)


def make_feature_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [name for name in FEATURES if name not in frame.columns]
    if missing:
        raise KeyError(f"Model özellikleri eksik: {missing}")
    return (
        frame.loc[:, FEATURES]
        .replace([np.inf, -np.inf], np.nan)
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0.0)
        .astype(np.float32)
    )


def roi_confidence_interval(profits: np.ndarray) -> tuple[float, float]:
    """Approximate Student-t 95% CI for mean profit per bet (ROI)."""
    values = np.asarray(profits, dtype=float)
    if len(values) < 2:
        return np.nan, np.nan
    standard_error = values.std(ddof=1) / np.sqrt(len(values))
    half_width = standard_error * t.ppf(0.975, len(values) - 1)
    return float(values.mean() - half_width), float(values.mean() + half_width)


def build_candidate_sides(
    frame: pd.DataFrame,
    p_over: np.ndarray,
) -> pd.DataFrame:
    """Create side-level EVs and the highest-EV side for every test match."""
    p = np.clip(np.asarray(p_over, dtype=float), EPS, 1.0 - EPS)
    if len(p) != len(frame):
        raise ValueError("Tahmin sayısı test satırlarıyla eşleşmiyor.")

    odds_under = pd.to_numeric(frame["_odd_under25"], errors="coerce").to_numpy(float)
    odds_over = pd.to_numeric(frame["_odd_over25"], errors="coerce").to_numpy(float)
    ev_under = (1.0 - p) * odds_under - 1.0
    ev_over = p * odds_over - 1.0

    choose_over = ev_over > ev_under
    chosen_odds = np.where(choose_over, odds_over, odds_under)
    chosen_ev = np.maximum(ev_under, ev_over)
    y = frame["_y_ou25"].astype(int).to_numpy()
    chosen_side = choose_over.astype(np.int8)  # 0 = ALT, 1 = ÜST
    chosen_profit_if_bet = np.where(
        y == chosen_side,
        chosen_odds - 1.0,
        -1.0,
    )

    return pd.DataFrame({
        "p_over25": p,
        "p_under25": 1.0 - p,
        "ev_under25": ev_under,
        "ev_over25": ev_over,
        "best_ev": chosen_ev,
        "best_side": np.where(choose_over, "UST", "ALT"),
        "best_odds": chosen_odds,
        "best_side_profit_if_bet": chosen_profit_if_bet,
        "under_profit_if_bet": np.where(y == 0, odds_under - 1.0, -1.0),
        "over_profit_if_bet": np.where(y == 1, odds_over - 1.0, -1.0),
    })


def summarize_rule(
    rule_name: str,
    description: str,
    candidate: pd.DataFrame,
    take: np.ndarray,
    y: np.ndarray,
    p_over: np.ndarray,
    total_test_matches: int,
) -> tuple[dict[str, Any], pd.DataFrame]:
    take = np.asarray(take, dtype=bool)
    if len(take) != len(candidate):
        raise ValueError(f"{rule_name}: seçim maskesi uzunluğu uyuşmuyor.")

    selected = candidate.loc[take].copy()
    profits = selected["profit_1u"].to_numpy(float)
    count = int(take.sum())
    total_profit = float(profits.sum()) if count else 0.0
    roi = float(profits.mean() * 100.0) if count else np.nan
    ci_low, ci_high = roi_confidence_interval(profits)
    wins = int((profits > 0).sum())
    losses = int((profits < 0).sum())
    pushes = int((profits == 0).sum())

    summary = {
        "strategy": rule_name,
        "description": description,
        "train_seasons": f"{TRAIN_SEASONS[0]}–{TRAIN_SEASONS[-1]}",
        "test_seasons": ",".join(TEST_SEASONS),
        "test_matches_with_valid_odds": int(total_test_matches),
        "bets": count,
        "coverage_pct": float(count / total_test_matches * 100.0) if total_test_matches else np.nan,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "total_profit_1u": total_profit,
        "roi_pct": roi,
        "roi_ci95_low_pct": ci_low * 100.0 if np.isfinite(ci_low) else np.nan,
        "roi_ci95_high_pct": ci_high * 100.0 if np.isfinite(ci_high) else np.nan,
        "roi_ci95_includes_zero": (
            bool(ci_low <= 0.0 <= ci_high)
            if np.isfinite(ci_low) and np.isfinite(ci_high)
            else None
        ),
        "roi_ci_method": "Approximate Student-t interval on per-bet 1-unit profit",
    }

    return summary, selected


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

    absent_train = sorted(set(TRAIN_SEASONS) - set(matches["_season"].unique()))
    absent_test = sorted(set(TEST_SEASONS) - set(matches["_season"].unique()))
    if absent_train or absent_test:
        raise ValueError(
            f"Sezon eksik. Eğitimde bulunmayan: {absent_train}; "
            f"testte bulunmayan: {absent_test}"
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
    print(
        f"   Test: {', '.join(TEST_SEASONS)} | ham={len(test_raw):,} "
        f"| geçerli oran={len(test):,}"
    )
    print("   Model: mevcut XGBoost baseline; eğitim/test protokolü değişmedi.")

    X_train = make_feature_matrix(train)
    X_test = make_feature_matrix(test)
    y_train = train["_y_ou25"].astype(int).to_numpy()
    y_test = test["_y_ou25"].astype(int).to_numpy()

    print("\n3. XGBoost Baseline eğitiliyor...")
    model = make_model()
    model.fit(X_train, y_train)
    p_over = np.clip(model.predict_proba(X_test)[:, 1], EPS, 1.0 - EPS)
    ll = float(log_loss(y_test, np.column_stack([1.0 - p_over, p_over]), labels=[0, 1]))
    brier = float(brier_score_loss(y_test, p_over))
    candidate = build_candidate_sides(test, p_over)

    # Attach the fixed test outcomes and a side-specific profit for every rule.
    candidate["match_id"] = test["_id"].to_numpy()
    candidate["date"] = test["_date"].to_numpy()
    candidate["season"] = test["_season"].to_numpy()
    candidate["home_team"] = test["Ev_Sahibi"].to_numpy()
    candidate["away_team"] = test["Deplasman"].to_numpy()
    candidate["actual_total_goals_over25"] = y_test
    candidate["under_odds"] = test["_odd_under25"].to_numpy(float)
    candidate["over_odds"] = test["_odd_over25"].to_numpy(float)
    candidate["profit_1u"] = candidate["best_side_profit_if_bet"]

    print(f"   Test LogLoss={ll:.5f} | Brier={brier:.5f}")
    print("\n4. Alternatif kurallar aynı test maçlarında değerlendiriliyor...")

    rules: list[tuple[str, str, np.ndarray, str]] = []
    best_ev = candidate["best_ev"].to_numpy(float)
    best_side = candidate["best_side"].to_numpy(str)
    best_odds = candidate["best_odds"].to_numpy(float)
    ev_under = candidate["ev_under25"].to_numpy(float)
    ev_over = candidate["ev_over25"].to_numpy(float)

    # Baseline is included as the reference point.
    rules.append((
        "BASELINE_EV_005",
        "En yüksek taraf EV > 0.05",
        best_ev > EV_THRESHOLD,
        "BEST",
    ))
    rules.append((
        "A_HIGH_EV_015",
        "En yüksek taraf EV > 0.15",
        best_ev > 0.15,
        "BEST",
    ))
    rules.append((
        "B_VERY_HIGH_EV_020",
        "En yüksek taraf EV > 0.20",
        best_ev > 0.20,
        "BEST",
    ))
    rules.append((
        "C_UNDER_ONLY_EV_005",
        "Yalnız ALT; ALT EV > 0.05",
        ev_under > EV_THRESHOLD,
        "UNDER",
    ))
    rules.append((
        "C_OVER_ONLY_EV_005",
        "Yalnız ÜST; ÜST EV > 0.05",
        ev_over > EV_THRESHOLD,
        "OVER",
    ))

    for band_name, lower, upper in ODDS_BANDS:
        upper_inclusive = np.isinf(upper)
        odds_mask = (best_odds >= lower) & (
            (best_odds <= upper) if upper_inclusive else (best_odds < upper)
        )
        rules.append((
            f"D_{band_name}_EV_005",
            f"En yüksek EV tarafı, oran {lower:.2f}–{'+' if upper_inclusive else f'{upper:.2f}'} ve EV > 0.05",
            (best_ev > EV_THRESHOLD) & odds_mask,
            "BEST",
        ))

    summaries: list[dict[str, Any]] = []
    ledgers: list[pd.DataFrame] = []

    for rule_name, description, take, side_mode in rules:
        if side_mode == "UNDER":
            rule_candidate = candidate.copy()
            rule_candidate["selected_side"] = "ALT"
            rule_candidate["selected_odds"] = rule_candidate["under_odds"]
            rule_candidate["selected_ev"] = rule_candidate["ev_under25"]
            rule_candidate["profit_1u"] = rule_candidate["under_profit_if_bet"]
        elif side_mode == "OVER":
            rule_candidate = candidate.copy()
            rule_candidate["selected_side"] = "UST"
            rule_candidate["selected_odds"] = rule_candidate["over_odds"]
            rule_candidate["selected_ev"] = rule_candidate["ev_over25"]
            rule_candidate["profit_1u"] = rule_candidate["over_profit_if_bet"]
        else:
            rule_candidate = candidate.copy()
            rule_candidate["selected_side"] = rule_candidate["best_side"]
            rule_candidate["selected_odds"] = rule_candidate["best_odds"]
            rule_candidate["selected_ev"] = rule_candidate["best_ev"]
            rule_candidate["profit_1u"] = rule_candidate["best_side_profit_if_bet"]

        summary, selected = summarize_rule(
            rule_name,
            description,
            rule_candidate,
            take,
            y_test,
            p_over,
            len(test),
        )
        summary["test_log_loss"] = ll
        summary["test_brier_score"] = brier
        summaries.append(summary)

        # Keep a full decision ledger, including no-bet rows, for auditability.
        ledger = rule_candidate[[
            "match_id", "date", "season", "home_team", "away_team",
            "actual_total_goals_over25", "under_odds", "over_odds",
            "p_under25", "p_over25", "ev_under25", "ev_over25",
            "selected_side", "selected_odds", "selected_ev", "profit_1u",
        ]].copy()
        ledger["strategy"] = rule_name
        ledger["bet_taken"] = np.asarray(take, dtype=bool)
        ledger.loc[~ledger["bet_taken"], "profit_1u"] = 0.0
        ledgers.append(ledger)

        print(
            f"   {rule_name:<26} | bahis={summary['bets']:>5,} "
            f"| kâr={summary['total_profit_1u']:+.2f} "
            f"| ROI=%{summary['roi_pct']:+.2f} "
            f"| %95 GA=[%{summary['roi_ci95_low_pct']:+.2f}, "
            f"%{summary['roi_ci95_high_pct']:+.2f}]"
            if summary["bets"] >= 2
            else (
                f"   {rule_name:<26} | bahis={summary['bets']:>5,} "
                f"| kâr={summary['total_profit_1u']:+.2f} | ROI hesaplanamadı "
                f"| %95 GA hesaplanamadı"
            )
        )

    summary_df = pd.DataFrame(summaries)
    summary_df["profit_rank"] = summary_df["total_profit_1u"].rank(
        ascending=False, method="min"
    ).astype(int)
    summary_df["roi_rank"] = summary_df["roi_pct"].rank(
        ascending=False, method="min"
    ).astype("Int64")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(SUMMARY_PATH, index=False, encoding="utf-8-sig")
    pd.concat(ledgers, ignore_index=True).to_csv(LEDGER_PATH, index=False, encoding="utf-8-sig")
    candidate.to_csv(PREDICTIONS_PATH, index=False, encoding="utf-8-sig")

    print("\n=== KARŞILAŞTIRMA ÖZETİ ===")
    columns = [
        "strategy", "bets", "total_profit_1u", "roi_pct",
        "roi_ci95_low_pct", "roi_ci95_high_pct", "profit_rank",
    ]
    print(summary_df[columns].sort_values(
        ["total_profit_1u", "roi_pct"], ascending=[False, False]
    ).to_string(index=False, float_format=lambda value: f"{value:.2f}"))

    baseline_row = summary_df.loc[summary_df["strategy"].eq("BASELINE_EV_005")].iloc[0]
    eligible = summary_df[summary_df["bets"] >= 30].copy()
    if not eligible.empty:
        best_profit_row = eligible.sort_values(
            ["total_profit_1u", "roi_pct"], ascending=[False, False]
        ).iloc[0]
        best_roi_row = eligible.sort_values(
            ["roi_pct", "total_profit_1u"], ascending=[False, False]
        ).iloc[0]
        print("\n=== YORUM ===")
        print(
            f"Baseline EV > {EV_THRESHOLD:.2f}: {int(baseline_row['bets']):,} bahis, "
            f"kâr={baseline_row['total_profit_1u']:+.2f}, ROI=%{baseline_row['roi_pct']:+.2f}."
        )
        print(
            f"En yüksek toplam kâr (en az 30 bahis): {best_profit_row['strategy']} "
            f"| kâr={best_profit_row['total_profit_1u']:+.2f} "
            f"| ROI=%{best_profit_row['roi_pct']:+.2f}."
        )
        print(
            f"En yüksek ROI (en az 30 bahis): {best_roi_row['strategy']} "
            f"| ROI=%{best_roi_row['roi_pct']:+.2f} "
            f"| bahis={int(best_roi_row['bets']):,}."
        )
        profitable = eligible[eligible["roi_pct"] > 0.0]
        if profitable.empty:
            print("Bu testte en az 30 bahis yapan kurallar arasında pozitif ROI yok.")
        else:
            print(
                "Pozitif nokta tahmini ROI veren kurallar: "
                + ", ".join(
                    f"{row.strategy} (ROI=%{row.roi_pct:+.2f}, bahis={int(row.bets)})"
                    for row in profitable.itertuples()
                )
            )
        print(
            "ÖNEMLİ: Bu çoklu kural karşılaştırması test sonuçlarını inceleyerek seçim yapar. "
            "En iyi görünen kural keşifsel sonuçtur; doğrulamak için yeni, dokunulmamış bir "
            "sezon/test dönemi gerekir. ROI güven aralıkları yaklaşık Student-t aralıklarıdır."
        )

    print("\n=== RAPOR DOSYALARI ===")
    print(f"Özet: {SUMMARY_PATH}")
    print(f"Karar defteri: {LEDGER_PATH}")
    print(f"Model tahminleri: {PREDICTIONS_PATH}")


if __name__ == "__main__":
    main()
