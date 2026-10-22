import pandas as pd
import numpy as np
from src.load import load_data, load_v16_reference
from src.features import calculate_elo_features
from src.models.elo import EloModel
from src.models.poisson import PoissonModel
from src.models.market import MarketModel
from src.blend import BlendModel
from src.evaluate import calc_metrics

def main():
    print("1. Veri yukleniyor...")
    df = load_data()
    ref = load_v16_reference()
    
    # v1.6'nın test ettigi 5854 macin ID'lerini al
    test_ids = set(ref["_id"])
    
    print("2. Ozellikler hesaplaniyor (bu islem biraz surebilir)...")
    feats = calculate_elo_features(df)
    
    # Veriyi birlestir
    df_full = df.merge(feats, on="_id")
    
    # Kronolojik Split (WARMUP=3: 2013-2015 egitim, 2016+ test)
    test_seasons = ref["season"].unique()
    train_mask = ~df_full["_season"].isin(test_seasons)
    test_mask = df_full["_id"].isin(test_ids)
    
    train_df = df_full[train_mask].copy()
    test_df = df_full[test_mask].copy()
    
    print(f"   Egitim seti: {len(train_df)} mac")
    print(f"   Test seti: {len(test_df)} mac (v1.6 ile birebir ayni)")
    
    # Modelleri egit
    print("3. Modeller egitiliyor...")
    elo_model = EloModel().fit(train_df, train_df["_y"].values)
    poisson_model = PoissonModel().fit(train_df)
    
    # Test setinde tahmin yap
    print("4. Test seti tahminleri yapiliyor...")
    p_elo = elo_model.predict_proba(test_df)
    p_poisson = poisson_model.predict_proba(test_df)
    p_market = MarketModel().predict_proba(test_df)
    
    blend_model = BlendModel()
    p_blend = blend_model.predict_proba(p_elo, p_poisson, p_market)
    
    # v1.6 RF referansi (test_df uzerinden)
    test_df_ref = test_df.merge(ref[["_id", "p_rf_H", "p_rf_D", "p_rf_A"]], on="_id")
    p_rf = test_df_ref[["p_rf_H", "p_rf_D", "p_rf_A"]].values
    
    # Metrikleri hesapla
    y_true = test_df["_y"].values
    
    print("\n" + "="*50)
    print("MVP FAZ 1 SONUCLARI (5854 TEST MACI)")
    print("="*50)
    
    models = {
        "v1.6 RF": p_rf,
        "Market": p_market,
        "Elo": p_elo,
        "Poisson": p_poisson,
        "Blend": p_blend
    }
    
    for name, probs in models.items():
        m = calc_metrics(y_true, probs)
        print(f"{name:10s} | LogLoss: {m['log_loss']:.4f} | Brier: {m['brier']:.4f} | Acc: %{m['accuracy']*100:.2f}")

if __name__ == "__main__":
    main()