import pandas as pd
import numpy as np
from scipy.optimize import minimize
from src.load import load_data, load_v16_reference
from src.features import calculate_elo_features
from src.models.elo import EloModel
from src.models.poisson import PoissonModel
from src.models.market import MarketModel
from src.models.xgboost_model import XGBoostModel
from src.evaluate import calc_metrics

def optimize_weights(y_true, p_elo, p_poisson, p_market, p_xgb):
    def loss_func(weights):
        w_e, w_p, w_m, w_x = weights
        p_blend = (w_e * p_elo) + (w_p * p_poisson) + (w_m * p_market) + (w_x * p_xgb)
        p_blend = p_blend / p_blend.sum(axis=1, keepdims=True)
        
        labels = {"H": 0, "D": 1, "A": 2}
        y_idx = np.array([labels[y] for y in y_true])
        chosen = p_blend[np.arange(len(y_idx)), y_idx]
        return -np.mean(np.log(np.clip(chosen, 1e-15, 1.0)))

    init_weights = [0.25, 0.25, 0.25, 0.25]
    constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})
    bounds = ((0, 1), (0, 1), (0, 1), (0, 1))
    
    res = minimize(loss_func, init_weights, method='SLSQP', bounds=bounds, constraints=constraints)
    return res.x

def main():
    print("1. Veri yukleniyor...")
    df = load_data()
    ref = load_v16_reference()
    test_ids = set(ref["_id"])
    
    print("2. Ozellikler hesaplaniyor...")
    feats = calculate_elo_features(df)
    df_full = df.merge(feats, on="_id")
    
    # 3'lu Kronolojik Bolme
    test_seasons = ref["season"].unique()
    
    # Train: 2013-2014 (Test sezonlarinda ve 2015'te olmayanlar)
    train_mask = ~df_full["_season"].isin(test_seasons) & (df_full["_season"] != "2015/2016")
    # Validation: 2015-2016
    val_mask = df_full["_season"] == "2015/2016"
    # Test: 2016-2025
    test_mask = df_full["_id"].isin(test_ids)
    
    train_df = df_full[train_mask].copy()
    val_df = df_full[val_mask].copy()
    test_df = df_full[test_mask].copy()
    
    print(f"   Train: {len(train_df)} mac | Validation: {len(val_df)} mac | Test: {len(test_df)} mac")
    
    print("3. Tum modeller Train setinde egitiliyor...")
    elo_model = EloModel().fit(train_df, train_df["_y"].values)
    poisson_model = PoissonModel().fit(train_df)
    xgb_model = XGBoostModel().fit(train_df, train_df["_y"].values)
    
    print("4. Validation setinde tahminler aliniyor (Agirlik optimizasyonu icin)...")
    p_elo_val = elo_model.predict_proba(val_df)
    p_poisson_val = poisson_model.predict_proba(val_df)
    p_market_val = MarketModel().predict_proba(val_df)
    p_xgb_val = xgb_model.predict_proba(val_df)
    
    print("5. En iyi agirliklar Validation setinde hesaplaniyor...")
    best_w = optimize_weights(val_df["_y"].values, p_elo_val, p_poisson_val, p_market_val, p_xgb_val)
    print(f"   -> Elo: {best_w[0]:.3f} | Poisson: {best_w[1]:.3f} | Market: {best_w[2]:.3f} | Z-Kahin (XGB): {best_w[3]:.3f}")
    
    print("\n6. Test setinde nihai tahminler yapiliyor...")
    p_elo_te = elo_model.predict_proba(test_df)
    p_poisson_te = poisson_model.predict_proba(test_df)
    p_market_te = MarketModel().predict_proba(test_df)
    p_xgb_te = xgb_model.predict_proba(test_df)
    
    p_ultimate = (best_w[0] * p_elo_te) + (best_w[1] * p_poisson_te) + (best_w[2] * p_market_te) + (best_w[3] * p_xgb_te)
    p_ultimate = p_ultimate / p_ultimate.sum(axis=1, keepdims=True)
    
    y_true = test_df["_y"].values
    print("\n" + "="*50)
    print("ULTIMATE BLEND SONUCLARI (Duzeltilmis)")
    print("="*50)
    
    m_market = calc_metrics(y_true, p_market_te)
    m_ultimate = calc_metrics(y_true, p_ultimate)
    
    print(f"Market (Hedef) | LogLoss: {m_market['log_loss']:.4f} | Brier: {m_market['brier']:.4f} | Acc: %{m_market['accuracy']*100:.2f}")
    print(f"Ultimate Blend | LogLoss: {m_ultimate['log_loss']:.4f} | Brier: {m_ultimate['brier']:.4f} | Acc: %{m_ultimate['accuracy']*100:.2f}")
    
    if m_ultimate['log_loss'] < m_market['log_loss']:
        print("\nMÜKEMMEL! Piyasayi (Market) gectik!")
    else:
        print("\nPiyasayi henuz gecemedik ama Z-Kahin artik ezber yapamiyor.")

if __name__ == "__main__":
    main()