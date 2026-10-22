import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import LabelEncoder
from src.load import load_data, load_v16_reference
from src.load_global import load_global_data
from src.features import calculate_elo_features
from src.models.xgboost_model import XGBoostModel
from src.evaluate_final_bets import calc_roi_ci

# Yeni sklearn surumleri icin FrozenEstimator
try:
    from sklearn.frozen import FrozenEstimator
    HAS_FROZEN = True
except ImportError:
    HAS_FROZEN = False

def evaluate_bets_calibrated(y_true, probs, odds, threshold=0.10):
    bet_profits = []
    labels = ["H", "D", "A"]
    
    for i in range(len(y_true)):
        o_h, o_d, o_a = odds[i]
        if pd.isna(o_h) or pd.isna(o_d) or pd.isna(o_a): continue
        if o_h <= 1.0 or o_d <= 1.0 or o_a <= 1.0: continue
        
        p_h, p_d, p_a = probs[i]
        evs = [(p_h * o_h) - 1.0, (p_d * o_d) - 1.0, (p_a * o_a) - 1.0]
        
        max_idx = np.argmax(evs)
        max_ev = evs[max_idx]
        
        if max_ev > threshold:
            secilen_oran = [o_h, o_d, o_a][max_idx]
            secilen_tahmin = labels[max_idx]
            
            if y_true[i] == secilen_tahmin:
                bet_profits.append(secilen_oran - 1.0)
            else:
                bet_profits.append(-1.0)
                
    if len(bet_profits) == 0:
        print(f"EV > {threshold} | Yeterli bahis bulunamadi.")
        return
        
    total_profit = sum(bet_profits)
    roi = (total_profit / len(bet_profits)) * 100
    ci_lower, ci_upper = calc_roi_ci(bet_profits)
    
    print(f"EV > {threshold} | Oynanan: {len(bet_profits):4d} | Kâr: {total_profit:+7.1f} | ROI: %{roi:+.1f} | %95 CI: [%{ci_lower*100:+.1f}, %{ci_upper*100:+.1f}]")

def main():
    print("1. Veriler Yukleniyor...")
    df_tr = load_data()
    df_global = load_global_data()
    ref = load_v16_reference()
    test_ids = set(ref["_id"])
    
    df_full = pd.concat([df_global, df_tr], ignore_index=True)
    
    print("2. Ozellikler Hesaplaniyor...")
    feats = calculate_elo_features(df_full)
    df_full = df_full.merge(feats, on="_id")
    
    test_df_temp = df_full[df_full["_id"].isin(test_ids)]
    test_start_date = test_df_temp["_date"].min()
    
    train_mask = (df_full["_date"] < test_start_date) & (~df_full["_season"].isin(ref["season"].unique()))
    test_mask = df_full["_id"].isin(test_ids)
    
    train_df = df_full[train_mask].copy()
    test_df = df_full[test_mask].copy()
    
    print(f"   Train: {len(train_df)} mac | Test: {len(test_df)} mac")
    
    # Veriyi Validation ve Train olarak ikiye böl (Kalibrasyon için)
    cal_size = int(len(train_df) * 0.2)
    cal_df = train_df.sample(n=cal_size, random_state=42)
    pure_train_df = train_df.drop(cal_df.index)
    
    print("3. Z-Kahin (Ham) Egitiliyor...")
    model = XGBoostModel()
    model.fit(pure_train_df, pure_train_df["_y"].values)
    
    print("4. Kalibrasyon (Isotonic) Uygulaniyor...")
    X_cal = cal_df[model.features].fillna(0)
    le = LabelEncoder()
    y_cal = le.fit_transform(cal_df["_y"].values)
    
    base_model = model.model
    
    # Sürüm uyumluluğu kontrolü
    if HAS_FROZEN:
        frozen_model = FrozenEstimator(base_model)
        calibrated_clf = CalibratedClassifierCV(frozen_model, method='isotonic')
    else:
        calibrated_clf = CalibratedClassifierCV(base_model, method='isotonic', cv='prefit')
        
    calibrated_clf.fit(X_cal, y_cal)
    
    print("5. Test Seti Tahminleri Aliniyor...")
    X_test = test_df[model.features].fillna(0)
    p_calibrated = calibrated_clf.predict_proba(X_test)
    
    # Sınıf sırasını H, D, A yap
    probs_reordered = np.zeros_like(p_calibrated)
    for i, label in enumerate(calibrated_clf.classes_):
        if label == le.transform(["H"])[0]: probs_reordered[:, 0] = p_calibrated[:, i]
        elif label == le.transform(["D"])[0]: probs_reordered[:, 1] = p_calibrated[:, i]
        elif label == le.transform(["A"])[0]: probs_reordered[:, 2] = p_calibrated[:, i]
    
    y_true = test_df["_y"].values
    odds = test_df[["_odd_H", "_odd_D", "_odd_A"]].values
    
    print("\n" + "="*80)
    print("KALIBRE EDILMIS Z-KAHIN VALUE BET SONUCLARI")
    print("="*80)
    
    evaluate_bets_calibrated(y_true, probs_reordered, odds, threshold=0.05)
    evaluate_bets_calibrated(y_true, probs_reordered, odds, threshold=0.10)
    evaluate_bets_calibrated(y_true, probs_reordered, odds, threshold=0.15)

if __name__ == "__main__":
    main()