import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.preprocessing import LabelEncoder
from src.load import load_data, load_v16_reference
from src.load_global import load_global_data
from src.features import calculate_elo_features
from src.models.xgboost_model import XGBoostModel

def evaluate_bets(y_true, probs, odds, model_name, threshold=0.02):
    """Sadece maç başına en yüksek EV'li tek bahsi oynar."""
    total_bets = 0
    profit = 0.0
    wins = 0
    
    labels = ["H", "D", "A"]
    
    for i in range(len(y_true)):
        # Oranların geçerliliğini kontrol et
        o_h, o_d, o_a = odds[i]
        if pd.isna(o_h) or pd.isna(o_d) or pd.isna(o_a): continue
        if o_h <= 1.0 or o_d <= 1.0 or o_a <= 1.0: continue
        
        p_h, p_d, p_a = probs[i]
        
        evs = [
            (p_h * o_h) - 1.0,
            (p_d * o_d) - 1.0,
            (p_a * o_a) - 1.0
        ]
        
        # En yüksek EV'yi bul
        max_idx = np.argmax(evs)
        max_ev = evs[max_idx]
        
        # Eğer eşiği geçiyorsa bahis oyna
        if max_ev > threshold:
            total_bets += 1
            secilen_oran = [o_h, o_d, o_a][max_idx]
            secilen_tahmin = labels[max_idx]
            
            if y_true[i] == secilen_tahmin:
                profit += (secilen_oran - 1.0)
                wins += 1
            else:
                profit -= 1.0
                
    if total_bets == 0:
        return 0, 0.0, 0.0
        
    roi = (profit / total_bets) * 100
    win_rate = (wins / total_bets) * 100
    print(f"{model_name:20s} | Oynanan: {total_bets:4d} | Kazanma: %{win_rate:.1f} | Kâr: {profit:+7.1f} | ROI: %{roi:+.1f}")

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
    
    # ZAMAN SIZINTISI DUZELTMESI: Test baslangic tarihini bul
    test_df_temp = df_full[df_full["_id"].isin(test_ids)]
    test_start_date = test_df_temp["_date"].min()
    
    # Egitim: Test baslangic tarihinden KESINLIKLE once olan tum dunya verisi
    train_mask = (df_full["_date"] < test_start_date) & (~df_full["_season"].isin(ref["season"].unique()))
    test_mask = df_full["_id"].isin(test_ids)
    
    train_df = df_full[train_mask].copy()
    test_df = df_full[test_mask].copy()
    
    print(f"   Train: {len(train_df)} mac (Kesin tarih: {train_df['_date'].max().date()})")
    print(f"   Test:  {len(test_df)} mac")
    
    # 1. ORANLI MODEL (Z-Kahin)
    print("\n3. Z-Kahin (Oranli) Egitiliyor...")
    xgb_with_odds = XGBoostModel().fit(train_df, train_df["_y"].values)
    p_with_odds = xgb_with_odds.predict_proba(test_df)
    
    # 2. ORANSIZ MODEL (Sadece Elo ve Form)
    print("4. Z-Kahin (Oransiz) Egitiliyor...")
    xgb_no_odds = XGBoostModel()
    # Oranlari ozellik listesinden cikar
    xgb_no_odds.features = [f for f in xgb_no_odds.features if "_odd_" not in f]
    xgb_no_odds.fit(train_df, train_df["_y"].values)
    p_no_odds = xgb_no_odds.predict_proba(test_df)
    
    y_true = test_df["_y"].values
    odds = test_df[["_odd_H", "_odd_D", "_odd_A"]].values
    
    print("\n" + "="*70)
    print("VALUE BET SONUCLARI (EV > 0.02, Mac Basina Tek Bahis)")
    print("="*70)
    
    evaluate_bets(y_true, p_with_odds, odds, "Z-Kahin (Oranli)")
    evaluate_bets(y_true, p_no_odds, odds, "Z-Kahin (Oransiz)")

if __name__ == "__main__":
    main()