"""Controlled ablation study for OU 2.5.

Fixed training seasons: 2012/2013–2017/2018.
Fixed test seasons: 2018/2019 and 2019/2020.
The test cohort is restricted to matches with both valid OU2.5 odds so every
model is evaluated on exactly the same rows. LogLoss is calculated on this
same odds-covered cohort; odds_coverage is reported against all raw test rows.

Model A: Elo + form.
Model B: Elo + form + rest days.
Model C: Elo + form + rest days + momentum.
Model D is intentionally omitted: the source data has no referee field and
does not expose a reliable league identifier. Adding a constant home-advantage
flag would add no information, so C remains the final model.

No calibration or test-season refitting is performed. Elo/form features are
chronological pre-match features; outcomes only update state for later dates.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import t
from sklearn.metrics import log_loss

from src.features import calculate_elo_features
from src.load_global import load_global_data


RANDOM_STATE = 42
EV_THRESHOLD = 0.05
MIN_TRAIN_ROWS = 300

TRAIN_SEASONS = [
    "2012/2013", "2013/2014", "2014/2015",
    "2015/2016", "2016/2017", "2017/2018",
]
TEST_SEASONS = ["2018/2019", "2019/2020"]

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

MODELS = [
    ("A", "Elo + Form", BASE_FEATURES),
    ("B", "Elo + Form + Rest", BASE_FEATURES + REST_FEATURES),
    ("C", "Elo + Form + Rest + Momentum",
     BASE_FEATURES + REST_FEATURES + MOMENTUM_FEATURES),
]


def add_momentum(features: pd.DataFrame) -> pd.DataFrame:
    out = features.copy()
    for side in ("h", "a"):
        for metric in ("pts", "gf", "ga"):
            out[f"momentum_{side}_{metric}"] = (
                out[f"form_{side}_{metric}_5"] - out[f"form_{side}_{metric}_10"]
            )
    return out


def roi_ci(profits: np.ndarray, confidence: float = 0.95) -> tuple[float, float]:
    """Student-t interval for mean unit-stake profit (approximate ROI CI)."""
    values = np.asarray(profits, dtype=float)
    if len(values) < 2:
        return np.nan, np.nan
    se = values.std(ddof=1) / np.sqrt(len(values))
    half = se * t.ppf((1.0 + confidence) / 2.0, len(values) - 1)
    return float(values.mean() - half), float(values.mean() + half)


def evaluate_predictions(frame: pd.DataFrame, p_over: np.ndarray) -> dict:
    y = frame["_y_ou25"].astype(int).to_numpy()
    p_over = np.clip(np.asarray(p_over, dtype=float), 1e-7, 1.0 - 1e-7)
    ll = float(log_loss(y, np.column_stack([1.0 - p_over, p_over]), labels=[0, 1]))

    odds_under = frame["_odd_under25"].to_numpy(dtype=float)
    odds_over = frame["_odd_over25"].to_numpy(dtype=float)
    ev_under = (1.0 - p_over) * odds_under - 1.0
    ev_over = p_over * odds_over - 1.0
    choose_over = ev_over > ev_under
    best_ev = np.maximum(ev_under, ev_over)
    take = best_ev > EV_THRESHOLD

    if not np.any(take):
        return {
            "logloss": ll, "bets": 0, "roi_pct": np.nan,
            "ci_low_pct": np.nan, "ci_high_pct": np.nan,
        }

    chosen_odds = np.where(choose_over, odds_over, odds_under)[take]
    chosen_side = choose_over[take].astype(int)
    actual = y[take]
    profits = np.where(actual == chosen_side, chosen_odds - 1.0, -1.0)
    lower, upper = roi_ci(profits)
    return {
        "logloss": ll,
        "bets": int(len(profits)),
        "roi_pct": float(profits.mean() * 100.0),
        "ci_low_pct": lower * 100.0,
        "ci_high_pct": upper * 100.0,
    }


def match_level_betting(frame: pd.DataFrame, p_over: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return per-match unit profit, bet indicator, and per-match log loss."""
    y = frame["_y_ou25"].astype(int).to_numpy()
    p = np.clip(np.asarray(p_over, dtype=float), 1e-7, 1.0 - 1e-7)
    odds_under = frame["_odd_under25"].to_numpy(dtype=float)
    odds_over = frame["_odd_over25"].to_numpy(dtype=float)

    ev_under = (1.0 - p) * odds_under - 1.0
    ev_over = p * odds_over - 1.0
    choose_over = ev_over > ev_under
    take = np.maximum(ev_under, ev_over) > EV_THRESHOLD

    chosen_odds = np.where(choose_over, odds_over, odds_under)
    chosen_side = choose_over.astype(int)
    profit = np.zeros(len(frame), dtype=float)
    profit[take] = np.where(
        y[take] == chosen_side[take],
        chosen_odds[take] - 1.0,
        -1.0,
    )
    logloss_each = -(y * np.log(p) + (1 - y) * np.log(1.0 - p))
    return profit, take.astype(bool), logloss_each


def paired_bootstrap(
    frame: pd.DataFrame,
    predictions: dict[str, np.ndarray],
    n_bootstrap: int = 1000,
    seed: int = RANDOM_STATE,
) -> pd.DataFrame:
    """Paired match-level bootstrap; ROI is profit per bet, matching evaluate_predictions."""
    rng = np.random.default_rng(seed)
    n = len(frame)
    if n < 2:
        raise ValueError("Bootstrap için en az iki test maçı gerekli.")

    metrics = {
        model_id: match_level_betting(frame, predictions[model_id])
        for model_id, _, _ in MODELS
    }
    comparisons = [("A", "B"), ("B", "C")]
    rows = []

    for old_id, new_id in comparisons:
        old_profit, old_bet, old_loss = metrics[old_id]
        new_profit, new_bet, new_loss = metrics[new_id]
        roi_diffs = np.empty(n_bootstrap, dtype=float)
        ll_diffs = np.empty(n_bootstrap, dtype=float)

        for b in range(n_bootstrap):
            idx = rng.integers(0, n, size=n)
            old_n_bets = int(old_bet[idx].sum())
            new_n_bets = int(new_bet[idx].sum())

            old_roi = (
                old_profit[idx].sum() / old_n_bets
                if old_n_bets else np.nan
            )
            new_roi = (
                new_profit[idx].sum() / new_n_bets
                if new_n_bets else np.nan
            )
            roi_diffs[b] = (new_roi - old_roi) * 100.0
            ll_diffs[b] = float(np.mean(new_loss[idx] - old_loss[idx]))

        roi_diffs = roi_diffs[np.isfinite(roi_diffs)]
        ll_diffs = ll_diffs[np.isfinite(ll_diffs)]
        if len(roi_diffs) < int(n_bootstrap * 0.95):
            raise RuntimeError(
                f"{old_id}-{new_id}: geçerli ROI bootstrap örneği yetersiz "
                f"({len(roi_diffs)}/{n_bootstrap})."
            )

        roi_low, roi_high = np.percentile(roi_diffs, [2.5, 97.5])
        ll_low, ll_high = np.percentile(ll_diffs, [2.5, 97.5])
        roi_point = (
            new_profit.sum() / new_bet.sum()
            - old_profit.sum() / old_bet.sum()
        ) * 100.0
        ll_point = float(np.mean(new_loss - old_loss))

        rows.append({
            "comparison": f"{new_id}-{old_id}",
            "old_model": old_id,
            "new_model": new_id,
            "bootstrap_replicates": n_bootstrap,
            "test_matches": n,
            "old_bets": int(old_bet.sum()),
            "new_bets": int(new_bet.sum()),
            "roi_difference_pp_new_minus_old": roi_point,
            "roi_ci95_low_pp": float(roi_low),
            "roi_ci95_high_pp": float(roi_high),
            "roi_ci_includes_zero": bool(roi_low <= 0.0 <= roi_high),
            "roi_conclusion": (
                "Yeni özellikler istatistiksel olarak anlamlı bir fark yaratmadı"
                if roi_low <= 0.0 <= roi_high
                else (
                    "Yeni özellikler gerçekten işe yarıyor"
                    if roi_low > 0.0
                    else "Yeni özellikler ROI'yi istatistiksel olarak anlamlı biçimde düşürdü"
                )
            ),
            "logloss_difference_new_minus_old": ll_point,
            "logloss_ci95_low": float(ll_low),
            "logloss_ci95_high": float(ll_high),
            "logloss_ci_includes_zero": bool(ll_low <= 0.0 <= ll_high),
        })

    return pd.DataFrame(rows)


def make_model() -> xgb.XGBClassifier:
    return xgb.XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        n_estimators=350,
        max_depth=4,
        learning_rate=0.04,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=5,
        reg_lambda=1.0,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )


def main() -> None:
    print("1. Global veri yükleniyor...")
    matches = load_global_data().copy()
    required = {
        "_id", "_date", "_season", "Ev_Sahibi", "Deplasman",
        "MSE", "MSD", "_y", "_y_ou25", "_odd_under25", "_odd_over25",
    }
    missing = required.difference(matches.columns)
    if missing:
        raise KeyError(f"Gerekli sütunlar eksik: {sorted(missing)}")
    if matches["_id"].duplicated().any():
        raise ValueError("Global veri setinde yinelenen _id var.")

    matches["_date"] = pd.to_datetime(matches["_date"], errors="coerce")
    matches["_y_ou25"] = pd.to_numeric(matches["_y_ou25"], errors="coerce")
    matches = matches.dropna(subset=["_date", "_season", "_y_ou25"]).copy()
    matches["_season"] = matches["_season"].astype(str)

    absent_train = sorted(set(TRAIN_SEASONS) - set(matches["_season"].unique()))
    absent_test = sorted(set(TEST_SEASONS) - set(matches["_season"].unique()))
    if absent_train or absent_test:
        raise ValueError(
            f"Sezon eksik. Eğitim: {absent_train}; test: {absent_test}"
        )

    print("2. Kronolojik maç öncesi özellikleri hesaplanıyor...")
    features = add_momentum(calculate_elo_features(matches))
    data = matches.merge(features, on="_id", how="inner", validate="one_to_one")
    data = data.sort_values(["_date", "_id"]).reset_index(drop=True)

    train = data[data["_season"].isin(TRAIN_SEASONS)].copy()
    test_raw = data[data["_season"].isin(TEST_SEASONS)].copy()
    train = train.dropna(subset=["_y_ou25"]).copy()

    odds_valid = (
        test_raw["_odd_under25"].notna()
        & test_raw["_odd_over25"].notna()
        & test_raw["_odd_under25"].gt(1.0)
        & test_raw["_odd_over25"].gt(1.0)
    )
    test = test_raw.loc[odds_valid].copy().reset_index(drop=True)
    if len(train) < MIN_TRAIN_ROWS:
        raise RuntimeError(f"Eğitim örneği yetersiz: {len(train)}")
    if train["_y_ou25"].nunique() != 2:
        raise RuntimeError("Eğitim verisinde ALT/ÜST hedefinin iki sınıfı da yok.")
    if test.empty:
        raise RuntimeError("Sabit test sezonlarında geçerli ALT/ÜST oranlı maç bulunamadı.")

    print("\n3. Sabit veri kümeleri")
    print(f"   Eğitim sezonları: {TRAIN_SEASONS[0]}–{TRAIN_SEASONS[-1]}")
    print(f"   Eğitim maçı: {len(train):,}")
    print(f"   Test sezonları: {', '.join(TEST_SEASONS)}")
    print(f"   Ham test maçı: {len(test_raw):,}")
    print(f"   Geçerli iki oranı bulunan test maçı: {len(test):,}")
    print(f"   Test oran kapsamı: %{100.0 * len(test) / max(1, len(test_raw)):.1f}")
    print(f"   Test filtresi: iki oran da sayısal ve > 1.00; EV eşiği: {EV_THRESHOLD:.2f}")
    print("   Tüm modeller aynı eğitim ve aynı oran-kapsamlı test satırlarını kullanır.")

    X_train_by_model = {}
    X_test_by_model = {}
    for model_id, model_name, feature_names in MODELS:
        absent = [name for name in feature_names if name not in data.columns]
        if absent:
            raise KeyError(f"{model_id} modelinde eksik özellikler: {absent}")
        X_train_by_model[model_id] = (
            train[feature_names].replace([np.inf, -np.inf], np.nan).fillna(0)
        )
        X_test_by_model[model_id] = (
            test[feature_names].replace([np.inf, -np.inf], np.nan).fillna(0)
        )

    results = []
    predictions: dict[str, np.ndarray] = {}
    y_train = train["_y_ou25"].astype(int)

    print("\n4. Ablation modelleri eğitiliyor...")
    for model_id, model_name, feature_names in MODELS:
        model = make_model()
        model.fit(X_train_by_model[model_id], y_train)
        p_over = model.predict_proba(X_test_by_model[model_id])[:, 1]
        predictions[model_id] = p_over

        pooled = evaluate_predictions(test, p_over)
        results.append({
            "model": model_id,
            "model_name": model_name,
            "features": len(feature_names),
            "test_season": "POOLED",
            "test_n": len(test),
            **pooled,
        })

        for season in TEST_SEASONS:
            mask = test["_season"].eq(season).to_numpy()
            season_result = evaluate_predictions(test.loc[mask].reset_index(drop=True), p_over[mask])
            results.append({
                "model": model_id,
                "model_name": model_name,
                "features": len(feature_names),
                "test_season": season,
                "test_n": int(mask.sum()),
                **season_result,
            })

        roi_text = (
            f"%{pooled['roi_pct']:+.2f} "
            f"[{pooled['ci_low_pct']:+.2f}, {pooled['ci_high_pct']:+.2f}]"
            if pd.notna(pooled["roi_pct"]) else "hesaplanamadı"
        )
        print(
            f"Model {model_id} | {model_name:<30} | özellik={len(feature_names):2d} "
            f"| LogLoss={pooled['logloss']:.5f} | bahis={pooled['bets']:4d} "
            f"| ROI={roi_text}"
        )

    print("\\n5. Eşleştirilmiş bootstrap testi (1.000 tekrar)...")
    bootstrap_df = paired_bootstrap(test, predictions, n_bootstrap=1000, seed=RANDOM_STATE)
    bootstrap_path = Path("data/csv/bootstrap_ablation_results.csv")
    bootstrap_path.parent.mkdir(parents=True, exist_ok=True)
    bootstrap_df.to_csv(bootstrap_path, index=False, encoding="utf-8-sig")
    print(bootstrap_df.to_string(index=False, float_format=lambda value: f"{value:.5f}"))
    print(f"Bootstrap sonuç dosyası: {bootstrap_path}")

    result_df = pd.DataFrame(results)
    output_path = Path("data/csv/ablation_study_results.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    pooled = result_df[result_df["test_season"].eq("POOLED")].set_index("model")
    comparison_rows = []
    for model_id, model_name, feature_names in MODELS:
        row = pooled.loc[model_id]
        comparison_rows.append({
            "model": model_id,
            "model_name": model_name,
            "features": len(feature_names),
            "logloss": row["logloss"],
            "bets": row["bets"],
            "roi_pct": row["roi_pct"],
            "ci_low_pct": row["ci_low_pct"],
            "ci_high_pct": row["ci_high_pct"],
        })
    comparison = pd.DataFrame(comparison_rows)
    comparison["delta_logloss_vs_previous"] = comparison["logloss"].diff()
    comparison["delta_roi_pp_vs_previous"] = comparison["roi_pct"].diff()

    print("\n" + "=" * 112)
    print("KONTROLLÜ ABLATION SONUÇLARI — POOLED TEST")
    print("=" * 112)
    print(comparison.to_string(index=False, float_format=lambda value: f"{value:.4f}"))
    print("\nSEZON BAZLI SONUÇLAR")
    print(result_df[result_df["test_season"].ne("POOLED")].to_string(
        index=False, float_format=lambda value: f"{value:.4f}"
    ))
    print(f"\nSonuç dosyası: {output_path}")
    print(
        "\nNot: D modeli eklenmedi. Kaynakta hakem ve güvenilir lig kimliği yok; "
        "sabit bir ev-sahibi bayrağı tüm maçlarda aynı olacağı için modele bilgi katmaz. "
        "ROI güven aralığı birim bahis kârlarının Student-t aralığıdır; yaklaşık bir aralıktır. "
        "Özellik etkisi aynı test satırlarında karşılaştırılır, ancak test sezonları model "
        "seçimi/ayarları için kullanılmamalıdır."
    )


if __name__ == "__main__":
    main()
