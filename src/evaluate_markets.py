import pandas as pd
import numpy as np
from src.load import load_data, load_v16_reference
from src.features import calculate_elo_features
from src.models.poisson import PoissonModel

def to_num(s):
    return pd.to_numeric(s.astype(str).str.replace(",", ".", regex=False).str.strip(), errors="coerce")

def main():
    print("1. Veri yukleniyor...")
    df = load_data()
    ref = load_v16_reference()
    test_ids = set(ref["_id"])
    
    # AU 2.5 oranlarini temizle
    df["_odd_over"] = to_num(df["AÜ_2,5_Gol_|_Üst"])
    df["_odd_under"] = to_num(df["AÜ_2,5_Gol_|_Alt"])
    
    print("2. Ozellikler hesaplaniyor...")
    feats = calculate_elo_features(df)
    df_full = df.merge(feats, on="_id")
    
    test_seasons = ref["season"].unique()
    train_mask = ~df_full["_season"].isin(test_seasons)
    test_mask = df_full["_id"].isin(test_ids)
    
    train_df = df_full[train_mask].copy()
    test_df = df_full[test_mask].copy()
    
    print("3. Poisson modeli egitiliyor...")
    poisson_model = PoissonModel().fit(train_df)
    
    print("4. Test seti icin Alt/Ust tahminleri yapiliyor...")
    markets = poisson_model.predict_markets(test_df)
    
    # Sonuclari birlestir
    eval_df = test_df[["_id", "MSE", "MSD", "_odd_over", "_odd_under"]].copy()
    eval_df["p_over"] = markets["p_over25"].values
    eval_df["p_under"] = markets["p_under25"].values
    
    # Gercek sonuclari hesapla (Alt/Ust)
    eval_df["total_goals"] = pd.to_numeric(eval_df["MSE"], errors="coerce") + pd.to_numeric(eval_df["MSD"], errors="coerce")
    eval_df["actual_over"] = eval_df["total_goals"] > 2.5
    
    # Sadece 2.5 oranlari gecerli olanlari al
    valid_bets = eval_df.dropna(subset=["_odd_over", "_odd_under", "p_over", "p_under"]).copy()
    print(f"   Gecerli AU 2.5 oranina sahip mac sayisi: {len(valid_bets)} / {len(test_df)}")
    
    if len(valid_bets) == 0:
        print("HATA: Test setinde AU 2.5 orani bulunamadi!")
        return

    # Beklenen Deger (EV) hesapla
    valid_bets["ev_over"] = (valid_bets["p_over"] * valid_bets["_odd_over"]) - 1.0
    valid_bets["ev_under"] = (valid_bets["p_under"] * valid_bets["_odd_under"]) - 1.0
    
    print("\n" + "="*60)
    print("VALUE BET (DEGER BAHSI) SIMULASYONU - AU 2.5")
    print("="*60)
    
    # Farkli EV esikleri deneyelim (Sadece belirli bir kâr marji ustundekilere oynayacagiz)
    thresholds = [0.0, 0.02, 0.05, 0.10]
    
    for th in thresholds:
        # Sadece EV'si esik degerinden buyuk olanlara bahis oyna
        bets_over = valid_bets[valid_bets["ev_over"] > th]
        bets_under = valid_bets[valid_bets["ev_under"] > th]
        
        all_bets = []
        
        # Ust bahisleri
        for _, row in bets_over.iterrows():
            kazandi = row["actual_over"]
            kar = (row["_odd_over"] - 1.0) if kazandi else -1.0
            all_bets.append({"type": "Over", "profit": kar, "win": kazandi})
            
        # Alt bahisleri
        for _, row in bets_under.iterrows():
            kazandi = not row["actual_over"]
            kar = (row["_odd_under"] - 1.0) if kazandi else -1.0
            all_bets.append({"type": "Under", "profit": kar, "win": kazandi})
            
        if len(all_bets) == 0:
            continue
            
        bets_df = pd.DataFrame(all_bets)
        total_staked = len(bets_df)
        total_profit = bets_df["profit"].sum()
        roi = (total_profit / total_staked) * 100
        win_rate = bets_df["win"].mean() * 100
        
        print(f"EV Esigi > {th:.2f} | Oynanan: {total_staked:3d} | Kazanma: %{win_rate:.1f} | Kâr: {total_profit:+.1f} Birim | ROI: %{roi:+.1f}")

if __name__ == "__main__":
    main()