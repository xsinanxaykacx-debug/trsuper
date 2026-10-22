"""ALT/ÜST 2.5 Value Bet deneyi.

Test referansı: archive_v16/v16_per_match_predictions.csv (5.854 maç).
ALT/ÜST oranı bulunmayan test maçları tahmin kapsamına dahil olabilir ancak
ROI hesabına alınamaz; oran kapsamı ayrıca raporlanır.
"""
import re
import unicodedata

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import t
from sklearn.calibration import CalibratedClassifierCV

try:
    from sklearn.frozen import FrozenEstimator
except ImportError:
    FrozenEstimator = None

from src.features import calculate_elo_features
from src.load import load_data, load_v16_reference
from src.load_global import load_global_data


RANDOM_STATE = 42
EV_THRESHOLDS = (0.05, 0.10, 0.15)
CALIBRATION_FRACTION = 0.20

FEATURES = [
    "elo_h", "elo_a", "elo_diff",
    "form_h_pts_5", "form_h_gf_5", "form_h_ga_5",
    "form_a_pts_5", "form_a_gf_5", "form_a_ga_5",
    "form_h_pts_10", "form_h_gf_10", "form_h_ga_10",
    "form_a_pts_10", "form_a_gf_10", "form_a_ga_10",
    "form_h_home_pts", "form_h_home_gf", "form_h_home_ga",
    "form_a_away_pts", "form_a_away_gf", "form_a_away_ga",
    "rest_h", "rest_a", "h2h_home_win_share",
]


def _normalise_team(value):
    value = unicodedata.normalize("NFKD", str(value))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.casefold().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _match_key(frame):
    result = frame.copy()
    result["_key_date"] = pd.to_datetime(result["_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    result["_key_home"] = result["Ev_Sahibi"].map(_normalise_team)
    result["_key_away"] = result["Deplasman"].map(_normalise_team)
    return result


def _roi_ci(profits, confidence=0.95):
    """Bir birimlik bahis başına ortalama kâr için yaklaşık t güven aralığı."""
    values = np.asarray(profits, dtype=float)
    if len(values) < 2:
        return np.nan, np.nan
    mean_profit = float(values.mean())
    standard_error = float(values.std(ddof=1) / np.sqrt(len(values)))
    half_width = standard_error * float(t.ppf((1 + confidence) / 2.0, len(values) - 1))
    return mean_profit - half_width, mean_profit + half_width


def _make_calibrated_model(train_df):
    """En yeni eğitim dönemini yalnızca kalibrasyon için ayırır."""
    train_df = train_df.sort_values("_date").reset_index(drop=True)
    if len(train_df) < 500:
        raise ValueError(f"Model eğitimi için yeterli geçmiş maç yok: {len(train_df)}")

    cal_n = max(100, int(len(train_df) * CALIBRATION_FRACTION))
    if cal_n >= len(train_df) - 100:
        cal_n = max(1, int(len(train_df) * CALIBRATION_FRACTION))
    pure_train = train_df.iloc[:-cal_n].copy()
    cal_df = train_df.iloc[-cal_n:].copy()

    if pure_train["_y_ou25"].nunique() != 2:
        raise ValueError("Saf eğitim bölümünde ALT ve ÜST sınıflarının ikisi de bulunmalı.")
    if cal_df["_y_ou25"].nunique() != 2:
        raise ValueError("Kalibrasyon bölümünde ALT ve ÜST sınıflarının ikisi de bulunmalı.")

    model = xgb.XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        n_estimators=400,
        max_depth=4,
        learning_rate=0.04,
        subsample=0.80,
        colsample_bytree=0.80,
        min_child_weight=5,
        reg_lambda=1.0,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    X_train = pure_train[FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    model.fit(X_train, pure_train["_y_ou25"].astype(int))

    X_cal = cal_df[FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    y_cal = cal_df["_y_ou25"].astype(int)

    if FrozenEstimator is not None:
        calibrator = CalibratedClassifierCV(FrozenEstimator(model), method="isotonic")
    else:
        calibrator = CalibratedClassifierCV(model, method="isotonic", cv="prefit")
    calibrator.fit(X_cal, y_cal)
    return calibrator, len(pure_train), len(cal_df)


def _evaluate_bets(test_df, p_over, threshold):
    """Maç başına en yüksek EV'li tek bahis; eşit EV durumunda ALT önceliklidir."""
    profits = []
    selected_sides = []
    eligible = test_df[
        test_df["_odd_under25"].gt(1.0)
        & test_df["_odd_over25"].gt(1.0)
        & test_df["_odd_under25"].notna()
        & test_df["_odd_over25"].notna()
        & test_df["_y_ou25"].notna()
    ].copy()

    for row_index, row in eligible.iterrows():
        p_over_i = float(p_over[test_df.index.get_loc(row_index)])
        p_under_i = 1.0 - p_over_i
        odds_under = float(row["_odd_under25"])
        odds_over = float(row["_odd_over25"])
        ev_under = p_under_i * odds_under - 1.0
        ev_over = p_over_i * odds_over - 1.0

        if ev_under >= ev_over:
            side, ev, odds = 0, ev_under, odds_under
        else:
            side, ev, odds = 1, ev_over, odds_over

        if ev <= threshold:
            continue

        won = int(row["_y_ou25"]) == side
        profits.append(odds - 1.0 if won else -1.0)
        selected_sides.append("UST" if side == 1 else "ALT")

    if not profits:
        print(f"EV > {threshold:.2f} | Bahis: 0 | ROI: hesaplanamadi | %95 GA: hesaplanamadi")
        return

    profit = float(np.sum(profits))
    roi = profit / len(profits)
    lower, upper = _roi_ci(profits)
    print(
        f"EV > {threshold:.2f} | Bahis: {len(profits):4d} | "
        f"ALT: {selected_sides.count('ALT'):4d} | UST: {selected_sides.count('UST'):4d} | "
        f"Kâr: {profit:+8.2f} | ROI: %{roi * 100:+.2f} | "
        f"%95 GA: [%{lower * 100:+.2f}, %{upper * 100:+.2f}]"
    )


def main():
    print("1. Veriler yukleniyor...")
    df_tr = load_data()
    global_df = load_global_data()
    reference = load_v16_reference()

    required_ref = {"_id", "season", "date", "home", "away"}
    missing_ref = required_ref.difference(reference.columns)
    if missing_ref:
        raise KeyError(f"V1.6 test referansinda eksik sütunlar: {sorted(missing_ref)}")

    if df_tr["_id"].duplicated().any():
        raise ValueError("DATA.csv içinde yinelenen _id var; test kimlikleri benzersiz olmalı.")
    if reference["_id"].duplicated().any():
        raise ValueError("V1.6 referansında yinelenen maç kimliği var.")

    # Test hedefi gerçek skorla hesaplanır; 1X2 etiketi kullanılmaz.
    df_tr["_y_ou25"] = np.where(
        df_tr["MSE"].notna() & df_tr["MSD"].notna(),
        ((pd.to_numeric(df_tr["MSE"], errors="coerce")
          + pd.to_numeric(df_tr["MSD"], errors="coerce")) > 2.5).astype("int8"),
        np.nan,
    )

    # 180k'daki OU oranlarını tarih + normalize ev/deplasman takımlarıyla eşleştir.
    global_keyed = _match_key(global_df)
    if global_keyed.duplicated(["_key_date", "_key_home", "_key_away"]).any():
        duplicate_count = int(global_keyed.duplicated(
            ["_key_date", "_key_home", "_key_away"], keep=False
        ).sum())
        raise ValueError(
            f"180k verisinde maç anahtarı tekil değil ({duplicate_count} satır). "
            "Belirsiz oran eşleşmeleriyle teste devam edilmiyor."
        )

    tr_keyed = _match_key(df_tr)
    odds_lookup = global_keyed[
        ["_key_date", "_key_home", "_key_away", "_odd_under25", "_odd_over25"]
    ]
    tr_keyed = tr_keyed.merge(
        odds_lookup,
        on=["_key_date", "_key_home", "_key_away"],
        how="left",
        validate="many_to_one",
        suffixes=("", "_global"),
    )

    # Sabit 5.854 test ID'si DATA.csv'den alınır. Global oran eşleşmesi olmayan
    # maçlar sessizce yok sayılmaz; kapsama oranı raporlanır.
    test_ids = set(reference["_id"].astype("int64"))
    test_df = tr_keyed[tr_keyed["_id"].isin(test_ids)].copy()
    missing_test_ids = test_ids.difference(set(test_df["_id"].astype("int64")))
    if missing_test_ids:
        raise ValueError(
            f"DATA.csv içinde {len(missing_test_ids)} referans test ID'si bulunamadı. "
            "5854 maçlık sabit test kümesi doğrulanamadı."
        )
    if len(test_df) != len(test_ids):
        raise ValueError("Test ID'leri bire bir eşleşmedi; çoğalmış satırlar olabilir.")

    odds_ok = (
        test_df["_odd_under25"].gt(1.0)
        & test_df["_odd_over25"].gt(1.0)
        & test_df["_odd_under25"].notna()
        & test_df["_odd_over25"].notna()
    )
    print(f"   Referans test maçı: {len(reference)}")
    print(f"   DATA.csv ile eşleşen test maçı: {len(test_df)}")
    print(f"   İki geçerli ALT/ÜST oranı bulunan test maçı: {int(odds_ok.sum())}")
    print(f"   ALT/ÜST oran kapsamı: %{odds_ok.mean() * 100:.2f}")

    # Özellik geçmişinde aynı maç iki kere kullanılmasın. Global satırların OU
    # oranları önce DATA.csv'ye taşındı; aynı anahtardaki global kopyalar çıkarılır.
    tr_keys = set(zip(tr_keyed["_key_date"], tr_keyed["_key_home"], tr_keyed["_key_away"]))
    global_only = global_keyed[
        ~global_keyed.apply(
            lambda row: (row["_key_date"], row["_key_home"], row["_key_away"]) in tr_keys,
            axis=1,
        )
    ].copy()

    common_columns = [
        "_id", "_date", "_season", "Lig/Sezon", "Ev_Sahibi", "Deplasman",
        "MSE", "MSD", "_y", "_y_ou25", "_odd_H", "_odd_D", "_odd_A",
        "_odd_under25", "_odd_over25",
    ]
    for column in common_columns:
        if column not in tr_keyed.columns:
            tr_keyed[column] = np.nan
        if column not in global_only.columns:
            global_only[column] = np.nan

    all_df = pd.concat(
        [global_only[common_columns], tr_keyed[common_columns]],
        ignore_index=True,
    )
    all_df = all_df.dropna(subset=["_date", "_season", "_y", "_y_ou25"])
    if all_df["_id"].duplicated().any():
        raise ValueError("Birleşik veri kümesinde yinelenen _id var.")

    print("2. Maç öncesi özellikler hesaplaniyor...")
    features = calculate_elo_features(all_df)
    all_df = all_df.merge(features, on="_id", how="inner", validate="one_to_one")

    test_start = pd.to_datetime(reference["date"], errors="coerce").min()
    if pd.isna(test_start):
        raise ValueError("Test referansının başlangıç tarihi okunamadı.")

    train_df = all_df[
        (all_df["_date"] < test_start) & all_df["_y_ou25"].notna()
    ].copy()
    test_feature_df = all_df[all_df["_id"].isin(test_ids)].copy()

    # Özellikler global ve DATA kaynakları birleştirilerek hesaplandığı için test
    # maçlarının ID'leri aynı olmalı; test seti tarih sınırından sonra kalmalı.
    if len(test_feature_df) != len(test_ids):
        raise ValueError(
            f"Özellikler sonrası test sayısı {len(test_feature_df)}; "
            f"beklenen {len(test_ids)}. ID eşleşmesi kayboldu."
        )
    if (test_feature_df["_date"] < test_start).any():
        raise ValueError("Test kümesinde test başlangıcından önce tarih bulundu.")

    train_df = train_df.sort_values("_date")
    print(f"   Eğitim için kullanılabilir maç: {len(train_df)}")
    print(f"   Test tahmini: {len(test_feature_df)} maç")

    print("3. Binary:logistic model + zaman sıralı isotonic kalibrasyon...")
    calibrated_model, n_fit, n_cal = _make_calibrated_model(train_df)
    print(f"   Model eğitim maçı: {n_fit} | Kalibrasyon maçı: {n_cal}")

    X_test = test_feature_df[FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    p_over = calibrated_model.predict_proba(X_test)[:, 1]

    # Test sırasını ve oranları tahmin satırlarıyla bire bir hizala.
    pred_frame = test_feature_df[["_id", "_y_ou25"]].copy()
    pred_frame["_p_over"] = p_over
    eval_df = tr_keyed[tr_keyed["_id"].isin(test_ids)].merge(
        pred_frame[["_id", "_p_over"]],
        on="_id",
        how="left",
        validate="one_to_one",
    )
    eval_df = eval_df.sort_values("_id").reset_index(drop=True)
    eval_p_over = eval_df["_p_over"].to_numpy()

    print("\n" + "=" * 84)
    print("KALİBRE EDİLMİŞ Z-KÂHİN | ALT/ÜST 2.5 VALUE BET")
    print("=" * 84)
    print("Hedef: toplam gol > 2.5 => ÜST (1), aksi => ALT (0)")
    print("Bahis: maç başına en yüksek EV; birim bahis; kapanış oranları")
    print("Not: ROI yalnızca iki geçerli ALT/ÜST oranı bulunan test maçlarından hesaplanır.")
    for threshold in EV_THRESHOLDS:
        _evaluate_bets(eval_df, eval_p_over, threshold)


if __name__ == "__main__":
    main()
