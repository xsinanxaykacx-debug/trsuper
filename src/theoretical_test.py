"""Theoretical flat-stake test of Model C's EV-filtered OU2.5 selections.

Fixed training seasons: 2012/2013–2017/2018.
Fixed test seasons: 2018/2019 and 2019/2020.
Common cohort matches human_vs_ai.py / human_vs_ai_v2.py: all 1X2 and OU2.5
odds must be valid (> 1.00). Model C is trained once; all eligible EV > 0.05
selections receive a theoretical 1-unit stake, with NO bankroll constraint.

Odds bands use the selected side's decimal odds:
  LOW:    1.00 <= odds < 1.50
  MEDIUM: 1.50 <= odds <= 3.00
  HIGH:   odds > 3.00

A negative result is evidence that this particular model/selection rule did not
show an edge on this historical test period; it does not prove markets are
universally unbeatable. The confidence intervals are descriptive and do not
replace a truly untouched forward test.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as student_t

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


FIXED_STAKE = 1.0
CONFIDENCE_EPS = 1e-7
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 42

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


def _mean_ci_t(profits: np.ndarray) -> tuple[float, float]:
    """Two-sided 95% Student-t confidence interval for mean profit per bet."""
    values = np.asarray(profits, dtype=float)
    if len(values) < 2:
        return np.nan, np.nan
    standard_error = values.std(ddof=1) / np.sqrt(len(values))
    half_width = standard_error * student_t.ppf(0.975, len(values) - 1)
    return float(values.mean() - half_width), float(values.mean() + half_width)


def _bootstrap_ci(profits: np.ndarray) -> tuple[float, float]:
    """Percentile bootstrap 95% CI for mean profit per bet, in ROI percentage points."""
    values = np.asarray(profits, dtype=float)
    if len(values) < 2:
        return np.nan, np.nan
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    means = np.empty(BOOTSTRAP_REPLICATES, dtype=float)
    # Batch resampling avoids allocating a 10,000 x N index matrix at once.
    batch_size = 250
    for start in range(0, BOOTSTRAP_REPLICATES, batch_size):
        size = min(batch_size, BOOTSTRAP_REPLICATES - start)
        indices = rng.integers(0, len(values), size=(size, len(values)))
        means[start:start + size] = values[indices].mean(axis=1) * 100.0
    low, high = np.percentile(means, [2.5, 97.5])
    return float(low), float(high)


def _summarize(profits: np.ndarray, label: str) -> dict:
    values = np.asarray(profits, dtype=float)
    n_bets = int(len(values))
    total_staked = n_bets * FIXED_STAKE
    total_profit = float(values.sum())
    roi_pct = total_profit / total_staked * 100.0 if total_staked else np.nan
    ci_low, ci_high = _mean_ci_t(values)
    boot_low, boot_high = _bootstrap_ci(values)
    wins = int(np.count_nonzero(values > 0.0))
    losses = int(np.count_nonzero(values < 0.0))
    pushes = int(np.count_nonzero(values == 0.0))
    return {
        "group": label,
        "bets": n_bets,
        "total_staked": total_staked,
        "total_profit": total_profit,
        "roi_pct": roi_pct,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "win_rate_pct": wins / n_bets * 100.0 if n_bets else np.nan,
        "roi_ci95_t_low_pct": ci_low * 100.0 if np.isfinite(ci_low) else np.nan,
        "roi_ci95_t_high_pct": ci_high * 100.0 if np.isfinite(ci_high) else np.nan,
        "roi_ci95_bootstrap_low_pct": boot_low,
        "roi_ci95_bootstrap_high_pct": boot_high,
    }


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

    # Match the exact common cohort used in the previous human-vs-AI experiment.
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
    print(f"   Seçim kuralı: en yüksek ALT/ÜST EV > {EV_THRESHOLD:.2f}")
    print("   Kasa sınırı YOK; uygun her seçime sabit 1 birim yatırılacak.")

    print("\n4. Model C bir kez eğitiliyor...")
    X_train = train[MODEL_C_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    X_common = common[MODEL_C_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    model = make_model()
    model.fit(X_train, train["_y_ou25"].astype(int))
    p_over = np.clip(
        model.predict_proba(X_common)[:, 1],
        CONFIDENCE_EPS,
        1.0 - CONFIDENCE_EPS,
    )

    odds_under = common["_odd_under25"].to_numpy(dtype=float)
    odds_over = common["_odd_over25"].to_numpy(dtype=float)
    y_over = common["_y_ou25"].astype(int).to_numpy()

    ev_under = (1.0 - p_over) * odds_under - 1.0
    ev_over = p_over * odds_over - 1.0
    choose_over = ev_over > ev_under
    best_ev = np.maximum(ev_under, ev_over)
    take = best_ev > EV_THRESHOLD

    selected_odds = np.where(choose_over, odds_over, odds_under)
    selected_probability = np.where(choose_over, p_over, 1.0 - p_over)
    selected_won = np.where(choose_over, y_over == 1, y_over == 0).astype(bool)

    eligible_idx = np.flatnonzero(take)
    if len(eligible_idx) == 0:
        raise RuntimeError("EV eşiğini geçen bahis bulunamadı.")

    bet_frame = common.iloc[eligible_idx].copy().reset_index(drop=True)
    bet_frame["selection"] = np.where(choose_over[take], "OVER_2.5", "UNDER_2.5")
    bet_frame["model_p_over"] = p_over[take]
    bet_frame["selected_side_probability"] = selected_probability[take]
    bet_frame["estimated_best_ev"] = best_ev[take]
    bet_frame["selected_odds"] = selected_odds[take]
    bet_frame["won"] = selected_won[take]
    bet_frame["stake"] = FIXED_STAKE
    bet_frame["profit"] = np.where(
        bet_frame["won"].to_numpy(),
        (bet_frame["selected_odds"].to_numpy(dtype=float) - 1.0) * FIXED_STAKE,
        -FIXED_STAKE,
    )
    bet_frame["roi_contribution_pct"] = bet_frame["profit"] / FIXED_STAKE * 100.0

    odds = bet_frame["selected_odds"].to_numpy(dtype=float)
    bet_frame["odds_band"] = np.select(
        [odds < 1.50, odds <= 3.00],
        ["LOW_1.00_TO_1.50", "MEDIUM_1.50_TO_3.00"],
        default="HIGH_OVER_3.00",
    )

    print(f"   Model C tahmini: {len(p_over):,}")
    print(f"   EV > {EV_THRESHOLD:.2f} bahis: {len(bet_frame):,}")
    print(f"   Sonuçlar: {int(bet_frame['won'].sum()):,} kazanç; "
          f"{int((~bet_frame['won']).sum()):,} kayıp")
    print("   ROI güven aralığı: Student-t %95 + bootstrap yüzdebirlik %95 (10.000 tekrar).")

    summaries = [_summarize(bet_frame["profit"].to_numpy(dtype=float), "ALL_ELIGIBLE_BETS")]
    for band in ["LOW_1.00_TO_1.50", "MEDIUM_1.50_TO_3.00", "HIGH_OVER_3.00"]:
        values = bet_frame.loc[bet_frame["odds_band"].eq(band), "profit"].to_numpy(dtype=float)
        summaries.append(_summarize(values, band))
    summary_df = pd.DataFrame(summaries)

    output_dir = Path("data/csv")
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "theoretical_test_results.csv"
    ledger_path = output_dir / "theoretical_test_bet_ledger.csv"
    summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")
    bet_frame.to_csv(ledger_path, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 130)
    print("SAF SEÇİM KALİTESİ — MODEL C | SABİT 1 BİRİM | KASA SINIRI YOK")
    print("=" * 130)
    display_cols = [
        "group", "bets", "total_staked", "total_profit", "roi_pct",
        "wins", "losses", "roi_ci95_t_low_pct", "roi_ci95_t_high_pct",
        "roi_ci95_bootstrap_low_pct", "roi_ci95_bootstrap_high_pct",
    ]
    print(summary_df[display_cols].to_string(
        index=False, float_format=lambda value: f"{value:.3f}"
    ))

    overall = summary_df.iloc[0]
    print("\nSONUÇ:")
    if overall["roi_pct"] < 0.0:
        print(
            "Bu model ve EV filtresi, bu tarihsel test döneminde negatif ham ROI verdi. "
            "Bu kurulumda doğrulanmış bir edge yok; bu, tüm bahis piyasalarının evrensel "
            "olarak yenilmez olduğunu kanıtlamaz."
        )
    elif overall["roi_ci95_t_low_pct"] > 0.0:
        print(
            "Ham ROI pozitif ve Student-t %95 güven aralığının alt sınırı da sıfırın üstünde. "
            "Bu, bu tarihsel testte umut verici bir işarettir; bağımsız ileri dönem doğrulaması "
            "olmadan güvenilir veya tekrarlanabilir edge ilan edilmemelidir."
        )
    else:
        print(
            "Ham ROI pozitif olsa da Student-t %95 güven aralığının alt sınırı sıfırın üstünde değil. "
            "İstatistiksel olarak doğrulanmış edge sonucu çıkarılamaz."
        )

    print(f"\nÖzet CSV: {summary_path}")
    print(f"Bahis günlüğü CSV: {ledger_path}")
    print(
        "\nNot: Güven aralıkları seçilmiş bahis kârlarını yaklaşık bağımsız gözlemler olarak ele alır; "
        "aynı sezon içindeki bağımlılık ve test döneminin geçmişte seçilmiş olması belirsizliği artırabilir. "
        "Oran grupları keşif amaçlıdır; gruplar sonuca bakılarak seçildiği için ileri dönem testi gerekir."
    )


if __name__ == "__main__":
    main()
