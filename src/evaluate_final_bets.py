import pandas as pd
import numpy as np
from scipy.stats import t
from src.load import load_data, load_v16_reference
from src.load_global import load_global_data
from src.features import calculate_elo_features
from src.models.xgboost_model import XGBoostModel

def calc_roi_ci(bet_profits, confidence=0.95):
    """%95 Güven Aralığı hesaplar."""
    n = len(bet_profits)
    if n < 2: return 0.0, 0.0
    mean = np.mean(bet_profits)
    se = np.std(bet_profits, ddof=1) / np.sqrt(n)
    h = se * t.ppf((1 + confidence) / 2., n-1)
    return mean - h, mean + h

def evaluate_bets(y_true, probs, odds, model_name, threshold=0.02):
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
        print(f"{model_name:20s} | Yeterli bahis bulunamadi.")
        return
        
    total_profit = sum(bet_profits)
    roi = (total_profit / len(bet_profits)) * 100
    ci_lower, ci_upper = calc_roi_ci(bet_profits)
    
    print(f"{model_name:20s} | Oynanan: {len(bet_profits):4d} | Kâr: {total_profit:+7.1f} | ROI: %{roi:+.1f} | %95 CI: [%{ci_lower*100:+.1f}, %{ci_upper*100:+.1f}]")

def main():
    print("1. Veriler Yukleniyor...")
    df_tr = load_data()
    df_global = load_global_data()
    ref = load_v16_reference()
    test_ids = set(ref["_id"])
    
    # VERI COGALMASI KONTROLU
    overlap = set(df_tr["_id"]).intersection(set(df_global["_id"]))
    if overlap:
        print(f"UYARI: {len(overlap)} adet ID cakismasi var! Temizleniyor...")
        df_global = df_global[~df_global["_id"].isin(overlap)]
    
    df_full = pd.concat([df_global, df_tr], ignore_index=True)
    print(f"   Toplam benzersiz mac: {len(df_full)}")
    
    print("2. Ozellikler Hesaplaniyor...")
    feats = calculate_elo_features(df_full)
    df_full = df_full.merge(feats, on="_id")
    
    test_df_temp = df_full[df_full["_id"].isin(test_ids)]
    test_start_date = test_df_temp["_date"].min()
    
    # KESIN ZAMAN AYRIMI
    train_mask = (df_full["_date"] < test_start_date) & (~df_full["_season"].isin(ref["season"].unique()))
    test_mask = df_full["_id"].isin(test_ids)
    
    train_df = df_full[train_mask].copy()
    test_df = df_full[test_mask].copy()
    
    print(f"   Train: {len(train_df)} mac (Max tarih: {train_df['_date'].max().date()})")
    print(f"   Test:  {len(test_df)} mac")
    
    print("3. Z-Kahin (Oranli) Egitiliyor...")
    xgb_with_odds = XGBoostModel().fit(train_df, train_df["_y"].values)
    p_with_odds = xgb_with_odds.predict_proba(test_df)
    
    print("4. Z-Kahin (Oransiz) Egitiliyor...")
    xgb_no_odds = XGBoostModel()
    xgb_no_odds.features = [f for f in xgb_no_odds.features if "_odd_" not in f]
    xgb_no_odds.fit(train_df, train_df["_y"].values)
    p_no_odds = xgb_no_odds.predict_proba(test_df)
    
    y_true = test_df["_y"].values
    odds = test_df[["_odd_H", "_odd_D", "_odd_A"]].values
    
    print("\n" + "="*80)
    print("VALUE BET SONUCLARI (EV > 0.02, Mac Basina Tek Bahis)")
    print("="*80)
    
    evaluate_bets(y_true, p_with_odds, odds, "Z-Kahin (Oranli)")
    evaluate_bets(y_true, p_no_odds, odds, "Z-Kahin (Oransiz)")

if __name__ == "__main__":
    main()