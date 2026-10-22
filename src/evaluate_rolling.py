"""Expanding-window ALT/ÜST 2.5 evaluation by season.

Each season is predicted only by matches from earlier seasons. Feature groups
are introduced progressively by walk-forward step:
1 Elo + form; 2 add rest days; 3 add momentum; 4+ add referee historical stats
when referee identifiers exist in the loaded source data.

Target: 1 when MSE + MSD > 2.5, else 0.
ROI: one max-EV bet per match using valid under/over odds; thresholds are fixed.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.special import expit
from scipy.stats import t
from sklearn.metrics import log_loss

from src.features import calculate_elo_features
from src.load_global import load_global_data


RANDOM_STATE = 42
EV_THRESHOLD = 0.05
MIN_TRAIN_ROWS = 300

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
REFEREE_FEATURES = ["ref_ou_rate", "ref_match_count"]


def season_sort_key(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d{4})/(\d{4})", str(value))
    if not match:
        return (9999, 9999)
    return int(match.group(1)), int(match.group(2))


def _normalise_text(value) -> str:
    value = unicodedata.normalize("NFKD", str(value))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.casefold().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _add_momentum(features: pd.DataFrame) -> pd.DataFrame:
    out = features.copy()
    # Momentum is a pre-match proxy: recent-five form minus recent-ten form.
    for side in ("h", "a"):
        for metric in ("pts", "gf", "ga"):
            recent = f"form_{side}_{metric}_5"
            long = f"form_{side}_{metric}_10"
            out[f"momentum_{side}_{metric}"] = out[recent] - out[long]
    return out


def _add_referee_history(matches: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    """Leakage-safe referee historical over-rate, using only strictly prior dates."""
    out = features.copy()
    if "_referee" not in matches.columns:
        out["ref_ou_rate"] = np.nan
        out["ref_match_count"] = 0.0
        return out

    work = matches[["_id", "_date", "_referee", "_y_ou25"]].copy()
    work["_ref_key"] = work["_referee"].map(_normalise_text)
    work.loc[work["_ref_key"].isin(["", "nan", "none", "unknown"]), "_ref_key"] = np.nan
    work = work.sort_values(["_date", "_id"])
    rates = {}
    count = {}
    rows = []

    # Same-day matches do not inform each other's referee feature.
    for date, day in work.groupby("_date", sort=True):
        # iterrows avoids pandas itertuples renaming columns that start with "_".
        for _, row in day.iterrows():
            key = row["_ref_key"]
            n = count.get(key, 0) if pd.notna(key) else 0
            total = rates.get(key, 0.0) if pd.notna(key) else 0.0
            rows.append({
                "_id": row["_id"],
                "ref_ou_rate": (total / n) if n else np.nan,
                "ref_match_count": float(n),
            })
        for _, row in day.iterrows():
            key = row["_ref_key"]
            target = row["_y_ou25"]
            if pd.notna(key) and pd.notna(target):
                count[key] = count.get(key, 0) + 1
                rates[key] = rates.get(key, 0.0) + float(target)

    ref_features = pd.DataFrame(rows)
    return out.merge(ref_features, on="_id", how="left", validate="one_to_one")


def _roi_ci(profits, confidence=0.95):
    values = np.asarray(profits, dtype=float)
    if len(values) < 2:
        return np.nan, np.nan
    mean = values.mean()
    se = values.std(ddof=1) / np.sqrt(len(values))
    half = se * t.ppf((1 + confidence) / 2, len(values) - 1)
    return float(mean - half), float(mean + half)


def _evaluate_roi(test: pd.DataFrame, p_over: np.ndarray):
    required = ["_odd_under25", "_odd_over25"]
    eligible_mask = (
        test[required].notna().all(axis=1)
        & test["_odd_under25"].gt(1.0)
        & test["_odd_over25"].gt(1.0)
    )
    eligible = test.loc[eligible_mask].copy()
    if eligible.empty:
        return 0, np.nan, np.nan, np.nan, 0.0

    test_positions = np.flatnonzero(eligible_mask.to_numpy())
    p_over_valid = p_over[test_positions]
    p_under_valid = 1.0 - p_over_valid
    odds_under = eligible["_odd_under25"].to_numpy(dtype=float)
    odds_over = eligible["_odd_over25"].to_numpy(dtype=float)

    ev_under = p_under_valid * odds_under - 1.0
    ev_over = p_over_valid * odds_over - 1.0
    choose_over = ev_over > ev_under
    best_ev = np.maximum(ev_under, ev_over)
    take = best_ev > EV_THRESHOLD
    if not np.any(take):
        return 0, np.nan, np.nan, np.nan, float(eligible_mask.mean())

    chosen_odds = np.where(choose_over, odds_over, odds_under)[take]
    chosen_side = choose_over[take].astype(int)  # 1=Over, 0=Under
    actual = eligible["_y_ou25"].to_numpy(dtype=int)[take]
    profits = np.where(actual == chosen_side, chosen_odds - 1.0, -1.0)
    roi = float(profits.mean())
    lower, upper = _roi_ci(profits)
    return len(profits), roi, lower, upper, float(eligible_mask.mean())


def _feature_list(step_number: int, referee_available: bool) -> list[str]:
    features = list(BASE_FEATURES)
    if step_number >= 2:
        features += REST_FEATURES
    if step_number >= 3:
        features += MOMENTUM_FEATURES
    if step_number >= 4:
        if referee_available:
            features += REFEREE_FEATURES
        else:
            print(
                "   UYARI: Hakem sütunu kaynak veride yok; "
                "4. adımda hakem istatistikleri eklenemiyor."
            )
    return features


def _season_label(df: pd.DataFrame) -> pd.Series:
    if "_season" in df.columns:
        return df["_season"].astype(str)
    dates = pd.to_datetime(df["_date"], errors="coerce")
    year = dates.dt.year
    return np.where(
        dates.dt.month >= 7,
        year.astype("Int64").astype(str) + "/" + (year + 1).astype("Int64").astype(str),
        (year - 1).astype("Int64").astype(str) + "/" + year.astype("Int64").astype(str),
    )


def main():
    print("1. Global veri yükleniyor...")
    matches = load_global_data().copy()
    required = {
        "_id", "_date", "_season", "Ev_Sahibi", "Deplasman",
        "MSE", "MSD", "_y", "_y_ou25",
        "_odd_under25", "_odd_over25",
    }
    missing = required.difference(matches.columns)
    if missing:
        raise KeyError(f"Global veri setinde gerekli sütunlar eksik: {sorted(missing)}")
    if matches["_id"].duplicated().any():
        raise ValueError("Global veri setinde yinelenen _id var.")

    matches["_date"] = pd.to_datetime(matches["_date"], errors="coerce")
    matches["_y_ou25"] = pd.to_numeric(matches["_y_ou25"], errors="coerce")
    matches = matches.dropna(subset=["_date", "_season", "_y_ou25"]).copy()
    matches["_season"] = _season_label(matches)
    seasons = sorted(matches["_season"].dropna().unique(), key=season_sort_key)
    seasons = [s for s in seasons if season_sort_key(s)[0] != 9999]

    if len(seasons) < 2:
        raise ValueError(f"Expanding window için en az iki sezon gerekli; bulunan: {seasons}")

    print(f"   Sezonlar: {', '.join(seasons)}")
    print("2. Maç öncesi Elo/form özellikleri hesaplanıyor...")
    base_features = calculate_elo_features(matches)
    all_features = _add_momentum(base_features)
    all_features = _add_referee_history(matches, all_features)

    # Özellikleri tekil ID üzerinden birleştir; aynı maçın satırı çoğalamaz.
    data = matches.merge(all_features, on="_id", how="inner", validate="one_to_one")
    data = data.sort_values(["_date", "_id"]).reset_index(drop=True)
    data["_season"] = _season_label(data)

    referee_available = (
        "_referee" in matches.columns
        and matches["_referee"].notna().any()
    )
    print("\n3. Expanding-window değerlendirmesi başlıyor...")
    print("   Hedef: ALT=0 / ÜST=1 | EV eşiği: {:.2f}".format(EV_THRESHOLD))
    print("   Her sezon yalnızca kendisinden önceki sezonlarla tahmin edilir.")
    print("   Kalibrasyon uygulanmıyor: her sezonun tahmininde yalnızca geçmiş veriye")
    print("   dayalı temel XGBoost kullanılır; böylece sezon içi test kalibrasyona girmez.")
    print()

    results = []
    for index in range(1, len(seasons)):
        test_season = seasons[index]
        prior_seasons = seasons[:index]
        step_number = min(index, 4)
        train = data[data["_season"].isin(prior_seasons)].copy()
        test = data[data["_season"].eq(test_season)].copy()

        train = train.dropna(subset=["_y_ou25"])
        test = test.dropna(subset=["_y_ou25"])
        features = _feature_list(step_number, referee_available)

        # Doğrudan önceki sezonlara göre genişleyen eğitim penceresi.
        if len(train) < MIN_TRAIN_ROWS:
            print(
                f"Sezon {test_season}: ATLANDI — eğitim örneği {len(train)} "
                f"(minimum {MIN_TRAIN_ROWS})."
            )
            continue
        if test.empty:
            print(f"Sezon {test_season}: ATLANDI — test maçı yok.")
            continue
        if train["_y_ou25"].nunique() != 2:
            print(f"Sezon {test_season}: ATLANDI — eğitimde iki hedef sınıfı yok.")
            continue

        X_train = train[features].replace([np.inf, -np.inf], np.nan).fillna(0)
        X_test = test[features].replace([np.inf, -np.inf], np.nan).fillna(0)
        model = xgb.XGBClassifier(
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
        model.fit(X_train, train["_y_ou25"].astype(int))
        p_over = np.clip(model.predict_proba(X_test)[:, 1], 1e-7, 1 - 1e-7)
        y_test = test["_y_ou25"].astype(int).to_numpy()
        ll = float(log_loss(y_test, np.column_stack([1 - p_over, p_over]), labels=[0, 1]))
        n_bets, roi, ci_low, ci_high, odds_coverage = _evaluate_roi(test.reset_index(drop=True), p_over)

        result = {
            "step": step_number,
            "train_seasons": f"{prior_seasons[0]}–{prior_seasons[-1]}",
            "test_season": test_season,
            "features": len(features),
            "train_n": len(train),
            "test_n": len(test),
            "logloss": ll,
            "odds_coverage": odds_coverage,
            "bets": n_bets,
            "roi_pct": roi * 100 if pd.notna(roi) else np.nan,
            "ci_low_pct": ci_low * 100 if pd.notna(ci_low) else np.nan,
            "ci_high_pct": ci_high * 100 if pd.notna(ci_high) else np.nan,
        }
        results.append(result)
        roi_text = (
            f"%{result['roi_pct']:+.2f} "
            f"[%{result['ci_low_pct']:+.2f}, %{result['ci_high_pct']:+.2f}]"
            if pd.notna(result["roi_pct"])
            else "hesaplanamadi"
        )
        print(
            f"Adım {index} | Test {test_season} | Eğitim {len(train):6d} | "
            f"Test {len(test):5d} | Özellik {len(features):2d} | "
            f"LogLoss {ll:.5f} | Bahis {n_bets:4d} | ROI {roi_text} | "
            f"oran kapsamı %{odds_coverage * 100:.1f}"
        )

    if not results:
        raise RuntimeError("Hiçbir sezon değerlendirilemedi.")

    out_path = Path("data/csv/rolling_over_under_results.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result_df = pd.DataFrame(results)
    result_df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print("\n" + "=" * 110)
    print("EXPANDING WINDOW SONUÇ ÖZETİ")
    print("=" * 110)
    print(result_df.to_string(index=False, float_format=lambda value: f"{value:.4f}"))
    print(f"\nSonuç dosyası: {out_path}")
    print(
        "\nYorum: Farklı adımlarda hem sezon hem eğitim örneklemi değiştiği için "
        "LogLoss/ROI farkı tek başına yeni özelliğin nedensel katkısını kanıtlamaz. "
        "Özellik katkısı için aynı test sezonlarında iç içe özellik setlerini karşılaştırmak gerekir."
    )


if __name__ == "__main__":
    main()
