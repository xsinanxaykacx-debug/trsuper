import pandas as pd
import numpy as np
from src.load import load_data, load_v16_reference
from src.features import calculate_elo_features
from src.models.xgboost_model import XGBoostModel
from src.models.market import MarketModel
from src.models.elo import EloModel
from src.models.poisson import PoissonModel
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
    xgb_model = XGBoostModel().fit(train_df, train_df["_y"].values)
    market_model = MarketModel()
    elo_model = EloModel().fit(train_df, train_df["_y"].values)
    poisson_model = PoissonModel().fit(train_df)
    
    print("4. Test seti tahminleri yapiliyor...")
    p_xgb = xgb_model.predict_proba(test_df)
    p_market = market_model.predict_proba(test_df)
    
    # Optimize edilmis Blend'i de karsilastirmak icin hazirlayalim
    p_elo = elo_model.predict_proba(test_df)
    p_poisson = poisson_model.predict_proba(test_df)
    # En iyi agirliklar (Elo: 0.088, Poisson: 0.031, Market: 0.881)
    best_w = [0.088, 0.031, 0.881]
    p_blend = (best_w[0] * p_elo) + (best_w[1] * p_poisson) + (best_w[2] * p_market)
    p_blend = p_blend / p_blend.sum(axis=1, keepdims=True)
    
    y_true = test_df["_y"].values
    
    print("\n" + "="*50)
    print("XGBOOST vs PIYASA (5854 TEST MACI)")
    print("="*50)
    
    models = {
        "Market": p_market,
        "Opt. Blend": p_blend,
        "XGBoost": p_xgb
    }
    
    for name, probs in models.items():
        m = calc_metrics(y_true, probs)
        print(f"{name:12s} | LogLoss: {m['log_loss']:.4f} | Brier: {m['brier']:.4f} | Acc: %{m['accuracy']*100:.2f}")

if __name__ == "__main__":
    main()