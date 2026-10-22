import pandas as pd
import numpy as np
from src.load import load_data, load_v16_reference
from src.load_global import load_global_data
from src.features import calculate_elo_features
from src.models.xgboost_model import XGBoostModel

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
    
    test_seasons = ref["season"].unique()
    train_mask = ~df_full["_season"].isin(test_seasons) & (df_full["_season"] != "2015/2016")
    test_mask = df_full["_id"].isin(test_ids)
    
    train_df = df_full[train_mask].copy()
    test_df = df_full[test_mask].copy()
    
    print("3. Z-Kahin (180k) Egitiliyor...")
    xgb_model = XGBoostModel().fit(train_df, train_df["_y"].values)
    
    print("4. Tahminler Aliniyor ve Value Bet Araniyor...")
    p_xgb = xgb_model.predict_proba(test_df)
    
    eval_df = test_df[["_id", "_odd_H", "_odd_D", "_odd_A", "_y"]].copy()
    eval_df["p_H"] = p_xgb[:, 0]
    eval_df["p_D"] = p_xgb[:, 1]
    eval_df["p_A"] = p_xgb[:, 2]
    
    thresholds = [0.0, 0.02, 0.05, 0.10]
    
    print("\n" + "="*70)
    print("Z-KAHIN (180k) 1X2 VALUE BET SONUCLARI")
    print("="*70)
    
    for th in thresholds:
        all_bets = []
        for _, row in eval_df.iterrows():
            actual_y = row["_y"]
            
            if (row["p_H"] * row["_odd_H"]) - 1.0 > th:
                kazandi = (actual_y == "H")
                all_bets.append((row["_odd_H"] - 1.0) if kazandi else -1.0)
                
            if (row["p_D"] * row["_odd_D"]) - 1.0 > th:
                kazandi = (actual_y == "D")
                all_bets.append((row["_odd_D"] - 1.0) if kazandi else -1.0)
                
            if (row["p_A"] * row["_odd_A"]) - 1.0 > th:
                kazandi = (actual_y == "A")
                all_bets.append((row["_odd_A"] - 1.0) if kazandi else -1.0)
                
        if not all_bets:
            print(f"EV Esigi > {th:.2f} | Yeterli bahis bulunamadi.")
            continue
            
        profit = sum(all_bets)
        roi = (profit / len(all_bets)) * 100
        
        print(f"EV Esigi > {th:.2f} | Oynanan: {len(all_bets):4d} | Kâr: {profit:+7.1f} Birim | ROI: %{roi:+.1f}")

if __name__ == "__main__":
    main()