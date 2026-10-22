import pandas as pd
import numpy as np
from src.load import load_data, load_v16_reference
from src.load_global import load_global_data
from src.features import calculate_elo_features
from src.models.market import MarketModel
from src.models.xgboost_model import XGBoostModel
from src.models.elo import EloModel
from src.models.poisson import PoissonModel
from src.evaluate import calc_metrics

def main():
    print("1. Veriler Yukleniyor (Bu islem birkac dakika surebilir)...")
    df_tr = load_data() # Test setimiz (5854 mac)
    df_global = load_global_data() # 180k dev veri
    ref = load_v16_reference()
    test_ids = set(ref["_id"])
    
    # Dev veri ile Turkiye verisini birlestir
    print("2. Veriler Birlestiriliyor...")
    df_full = pd.concat([df_global, df_tr], ignore_index=True)
    assert df_full["_id"].duplicated().sum() == 0, "ID cakismasi var!"
    
    print(f"Toplam veri boyutu: {len(df_full)} mac")
    
    print("3. Ozellikler Hesaplaniyor (180k mac icin Elo, Form vs.)...")
    feats = calculate_elo_features(df_full)
    df_full = df_full.merge(feats, on="_id")
    
    test_seasons = ref["season"].unique()
    # Egitim: Test sezonlari (2016+) disindaki tum dunya verisi
    train_mask = ~df_full["_season"].isin(test_seasons)
    # Test: v1.6'nin sabit 5854 maci
    test_mask = df_full["_id"].isin(test_ids)
    
    train_df = df_full[train_mask].copy()
    test_df = df_full[test_mask].copy()
    
    print(f"   Egitim (Train) seti: {len(train_df)} mac")
    print(f"   Test seti: {len(test_df)} mac")
    
    print("4. Modeller Egitiliyor...")
    xgb_model = XGBoostModel().fit(train_df, train_df["_y"].values)
    market_model = MarketModel()
    
    print("5. Test Seti Tahminleri Aliniyor...")
    p_xgb = xgb_model.predict_proba(test_df)
    p_market = market_model.predict_proba(test_df)
    
    y_true = test_df["_y"].values
    
    print("\n" + "="*50)
    print("Z-KAHIN (180k Mac Egitimi) vs PIYASA")
    print("="*50)
    
    m_market = calc_metrics(y_true, p_market)
    m_xgb = calc_metrics(y_true, p_xgb)
    
    print(f"Market  | LogLoss: {m_market['log_loss']:.4f} | Brier: {m_market['brier']:.4f} | Acc: %{m_market['accuracy']*100:.2f}")
    print(f"Z-Kahin | LogLoss: {m_xgb['log_loss']:.4f} | Brier: {m_xgb['brier']:.4f} | Acc: %{m_xgb['accuracy']*100:.2f}")

    if m_xgb['log_loss'] < m_market['log_loss']:
        print("\nMÜKEMMEL! Z-KAHIN PIYASAYI (MARKET) GECTI!")
    else:
        print("\nPiyasa hala onde ama aradaki fark kapandi.")

if __name__ == "__main__":
    main()