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
    test_ids = set(ref["_id"])
    
    print("2. Ozellikler hesaplaniyor...")
    feats = calculate_elo_features(df)
    df_full = df.merge(feats, on="_id")
    
    test_seasons = ref["season"].unique()
    train_mask = ~df_full["_season"].isin(test_seasons)
    test_mask = df_full["_id"].isin(test_ids)
    
    train_df = df_full[train_mask].copy()
    test_df = df_full[test_mask].copy()
    
    print("3. Modeller egitiliyor...")
    elo_model = EloModel().fit(train_df, train_df["_y"].values)
    poisson_model = PoissonModel().fit(train_df)
    
    print("4. Tahminler aliniyor...")
    p_elo = elo_model.predict_proba(test_df)
    p_poisson = poisson_model.predict_proba(test_df)
    p_market = MarketModel().predict_proba(test_df)
    
    blend_model = BlendModel()
    p_blend = blend_model.predict_proba(p_elo, p_poisson, p_market)
    
    test_df_ref = test_df.merge(ref[["_id", "p_rf_H", "p_rf_D", "p_rf_A"]], on="_id")
    p_rf = test_df_ref[["p_rf_H", "p_rf_D", "p_rf_A"]].values
    
    y_true = test_df["_y"].values
    
    # --- ADALETLI ORNEKLEM DUZELTMESI (Intersection Mask) ---
    # Tum modellerin gecerli (NaN olmayan) tahmin urettigi satirlari bulalim
    valid_mask = (
        np.isfinite(p_rf).all(axis=1) & 
        np.isfinite(p_market).all(axis=1) & 
        np.isfinite(p_blend).all(axis=1)
    )
    
    y_true_valid = y_true[valid_mask]
    p_rf_valid = p_rf[valid_mask]
    p_market_valid = p_market[valid_mask]
    p_blend_valid = p_blend[valid_mask]
    p_elo_valid = p_elo[valid_mask]
    p_poisson_valid = p_poisson[valid_mask]
    
    print(f"   Adaletli Karsilastirma Icin Gecerli Mac Sayisi: {valid_mask.sum()} / {len(test_df)}")
    
    print("\n" + "="*50)
    print("MVP FAZ 1 SONUCLARI (Ayni Orneklem Uzerinde)")
    print("="*50)
    
    models = {
        "v1.6 RF": p_rf_valid,
        "Market": p_market_valid,
        "Elo": p_elo_valid,
        "Poisson": p_poisson_valid,
        "Blend": p_blend_valid
    }
    
    for name, probs in models.items():
        m = calc_metrics(y_true_valid, probs)
        print(f"{name:10s} | LogLoss: {m['log_loss']:.4f} | Brier: {m['brier']:.4f} | Acc: %{m['accuracy']*100:.2f} | N={m['n_matches']}")

if __name__ == "__main__":
    main()