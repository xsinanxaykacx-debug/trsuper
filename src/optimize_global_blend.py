import pandas as pd
import numpy as np
from scipy.optimize import minimize
from src.load import load_data, load_v16_reference
from src.load_global import load_global_data
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
    print("1. Veriler Yukleniyor (Devasa Boyut)...")
    df_tr = load_data()
    df_global = load_global_data()
    ref = load_v16_reference()
    test_ids = set(ref["_id"])
    
    df_full = pd.concat([df_global, df_tr], ignore_index=True)
    
    print("2. Ozellikler Hesaplaniyor...")
    feats = calculate_elo_features(df_full)
    df_full = df_full.merge(feats, on="_id")
    
    test_seasons = ref["season"].unique()
    # Train: 2015/2016'dan onceki tum dunya verisi
    train_mask = ~df_full["_season"].isin(test_seasons) & (df_full["_season"] != "2015/2016")
    # Validation: 2015/2016 sezonu (Dunya verisi de dahil)
    val_mask = df_full["_season"] == "2015/2016"
    # Test: 5854 mac
    test_mask = df_full["_id"].isin(test_ids)
    
    train_df = df_full[train_mask].copy()
    val_df = df_full[val_mask].copy()
    test_df = df_full[test_mask].copy()
    
    print(f"   Train: {len(train_df)} mac | Val: {len(val_df)} mac | Test: {len(test_df)} mac")
    
    print("3. Modeller Egitiliyor (71k mac)...")
    elo_model = EloModel().fit(train_df, train_df["_y"].values)
    poisson_model = PoissonModel().fit(train_df)
    xgb_model = XGBoostModel().fit(train_df, train_df["_y"].values)
    market_model = MarketModel()
    
    print("4. Validation setinde tahminler aliniyor...")
    p_elo_val = elo_model.predict_proba(val_df)
    p_poisson_val = poisson_model.predict_proba(val_df)
    p_market_val = market_model.predict_proba(val_df)
    p_xgb_val = xgb_model.predict_proba(val_df)
    
    print("5. En iyi agirliklar hesaplaniyor...")
    best_w = optimize_weights(val_df["_y"].values, p_elo_val, p_poisson_val, p_market_val, p_xgb_val)
    print(f"   -> Elo: {best_w[0]:.3f} | Poisson: {best_w[1]:.3f} | Market: {best_w[2]:.3f} | Z-Kahin (XGB): {best_w[3]:.3f}")
    
    print("\n6. Test setinde nihai tahminler yapiliyor...")
    p_elo_te = elo_model.predict_proba(test_df)
    p_poisson_te = poisson_model.predict_proba(test_df)
    p_market_te = market_model.predict_proba(test_df)
    p_xgb_te = xgb_model.predict_proba(test_df)
    
    p_ultimate = (best_w[0] * p_elo_te) + (best_w[1] * p_poisson_te) + (best_w[2] * p_market_te) + (best_w[3] * p_xgb_te)
    p_ultimate = p_ultimate / p_ultimate.sum(axis=1, keepdims=True)
    
    y_true = test_df["_y"].values
    print("\n" + "="*50)
    print("GLOBAL ULTIMATE BLEND SONUCLARI (5854 TEST MACI)")
    print("="*50)
    
    m_market = calc_metrics(y_true, p_market_te)
    m_ultimate = calc_metrics(y_true, p_ultimate)
    
    print(f"Market (Hedef) | LogLoss: {m_market['log_loss']:.4f} | Brier: {m_market['brier']:.4f} | Acc: %{m_market['accuracy']*100:.2f}")
    print(f"Ultimate Blend | LogLoss: {m_ultimate['log_loss']:.4f} | Brier: {m_ultimate['brier']:.4f} | Acc: %{m_ultimate['accuracy']*100:.2f}")
    
    if m_ultimate['log_loss'] < m_market['log_loss']:
        print("\nMÜKEMMEL! PIYASAYI (MARKET) GECTIK!")
    else:
        print("\nPiyasayi henuz gecemedik ama cok yaklastik.")

if __name__ == "__main__":
    main()