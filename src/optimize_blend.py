import pandas as pd
import numpy as np
from scipy.optimize import minimize
from src.load import load_data, load_v16_reference
from src.features import calculate_elo_features
from src.models.elo import EloModel
from src.models.poisson import PoissonModel
from src.models.market import MarketModel
from src.evaluate import calc_metrics

def optimize_weights(y_true, p_elo, p_poisson, p_market):
    """Eğitim setinde log loss'u minimize edecek ağırlıkları bulur."""
    
    def loss_func(weights):
        w_e, w_p, w_m = weights
        p_blend = (w_e * p_elo) + (w_p * p_poisson) + (w_m * p_market)
        p_blend = p_blend / p_blend.sum(axis=1, keepdims=True)
        
        labels = {"H": 0, "D": 1, "A": 2}
        y_idx = np.array([labels[y] for y in y_true])
        chosen = p_blend[np.arange(len(y_idx)), y_idx]
        return -np.mean(np.log(np.clip(chosen, 1e-15, 1.0)))

    init_weights = [0.2, 0.2, 0.6]
    
    # Kısıt: Ağırlıkların toplamı 1.0 olmalı
    constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})
    # Sınırlar: Her ağırlık 0 ile 1 arasında olmalı
    bounds = ((0, 1), (0, 1), (0, 1))
    
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
    
    test_seasons = ref["season"].unique()
    train_mask = ~df_full["_season"].isin(test_seasons)
    test_mask = df_full["_id"].isin(test_ids)
    
    train_df = df_full[train_mask].copy()
    test_df = df_full[test_mask].copy()
    
    print("3. Modeller egitiliyor...")
    elo_model = EloModel().fit(train_df, train_df["_y"].values)
    poisson_model = PoissonModel().fit(train_df)
    
    print("4. Egitim setinde tahminler aliniyor (Optimizasyon icin)...")
    p_elo_tr = elo_model.predict_proba(train_df)
    p_poisson_tr = poisson_model.predict_proba(train_df)
    p_market_tr = MarketModel().predict_proba(train_df)
    
    print("5. En iyi agirliklar hesaplaniyor...")
    best_w = optimize_weights(train_df["_y"].values, p_elo_tr, p_poisson_tr, p_market_tr)
    print(f"   -> Bulunan En Iyi Agirliklar: Elo: {best_w[0]:.3f} | Poisson: {best_w[1]:.3f} | Market: {best_w[2]:.3f}")
    
    print("\n6. Test setinde nihai tahminler yapiliyor...")
    p_elo_te = elo_model.predict_proba(test_df)
    p_poisson_te = poisson_model.predict_proba(test_df)
    p_market_te = MarketModel().predict_proba(test_df)
    
    p_blend_te = (best_w[0] * p_elo_te) + (best_w[1] * p_poisson_te) + (best_w[2] * p_market_te)
    p_blend_te = p_blend_te / p_blend_te.sum(axis=1, keepdims=True)
    
    y_true = test_df["_y"].values
    print("\n" + "="*50)
    print("OPTIMIZE EDILMIS BLEND SONUCLARI (5854 TEST MACI)")
    print("="*50)
    
    m_market = calc_metrics(y_true, p_market_te)
    m_blend = calc_metrics(y_true, p_blend_te)
    
    print(f"Market (Hedef) | LogLoss: {m_market['log_loss']:.4f} | Brier: {m_market['brier']:.4f} | Acc: %{m_market['accuracy']*100:.2f}")
    print(f"Opt. Blend     | LogLoss: {m_blend['log_loss']:.4f} | Brier: {m_blend['brier']:.4f} | Acc: %{m_blend['accuracy']*100:.2f}")
    
    if m_blend['log_loss'] < m_market['log_loss']:
        print("\nMÜKEMMEL! Piyasayi (Market) gectik!")
    else:
        print("\nPiyasayi henuz gecemedik ama v1.6'nin cok altindayiz.")

if __name__ == "__main__":
    main()