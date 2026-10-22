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

# Ağırlık optimizasyonu (Validation seti için)
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
    
    test_seasons = ref["season"].unique()
    
    train_mask = ~df_full["_season"].isin(test_seasons) & (df_full["_season"] != "2015/2016")
    val_mask = df_full["_season"] == "2015/2016"
    test_mask = df_full["_id"].isin(test_ids)
    
    train_df = df_full[train_mask].copy()
    val_df = df_full[val_mask].copy()
    test_df = df_full[test_mask].copy()
    
    print("3. Modeller egitiliyor ve agirliklar bulunuyor...")
    elo_model = EloModel().fit(train_df, train_df["_y"].values)
    poisson_model = PoissonModel().fit(train_df)
    xgb_model = XGBoostModel().fit(train_df, train_df["_y"].values)
    
    p_elo_val = elo_model.predict_proba(val_df)
    p_poisson_val = poisson_model.predict_proba(val_df)
    p_market_val = MarketModel().predict_proba(val_df)
    p_xgb_val = xgb_model.predict_proba(val_df)
    
    best_w = optimize_weights(val_df["_y"].values, p_elo_val, p_poisson_val, p_market_val, p_xgb_val)
    
    print("4. Test seti icin Ultimate Blend tahminleri yapiliyor...")
    p_elo_te = elo_model.predict_proba(test_df)
    p_poisson_te = poisson_model.predict_proba(test_df)
    p_market_te = MarketModel().predict_proba(test_df)
    p_xgb_te = xgb_model.predict_proba(test_df)
    
    p_ultimate = (best_w[0] * p_elo_te) + (best_w[1] * p_poisson_te) + (best_w[2] * p_market_te) + (best_w[3] * p_xgb_te)
    p_ultimate = p_ultimate / p_ultimate.sum(axis=1, keepdims=True)
    
    print("\n5. 1X2 VALUE BET SIMULASYONU BASLIYOR...")
    
    # Test setindeki oranlari ve gercek sonuclari alalim
    eval_df = test_df[["_id", "_odd_H", "_odd_D", "_odd_A", "_y"]].copy()
    eval_df["p_H"] = p_ultimate[:, 0]
    eval_df["p_D"] = p_ultimate[:, 1]
    eval_df["p_A"] = p_ultimate[:, 2]
    
    # Sadece oranlari gecerli olanlari al
    valid_bets = eval_df.dropna(subset=["_odd_H", "_odd_D", "_odd_A"]).copy()
    print(f"   Gecerli 1X2 oranina sahip mac sayisi: {len(valid_bets)} / {len(test_df)}")
    
    # Farkli EV esikleri deneyelim
    thresholds = [0.0, 0.02, 0.05, 0.10]
    
    print("\n" + "="*70)
    print("1X2 VALUE BET SONUCLARI (Ortalama 1 Birim Bahis)")
    print("="*70)
    
    for th in thresholds:
        all_bets = []
        
        for _, row in valid_bets.iterrows():
            actual_y = row["_y"]
            
            # Ev Sahibi (H) kontrolu
            ev_h = (row["p_H"] * row["_odd_H"]) - 1.0
            if ev_h > th:
                kazandi = (actual_y == "H")
                kar = (row["_odd_H"] - 1.0) if kazandi else -1.0
                all_bets.append({"type": "H", "profit": kar, "win": kazandi})
                
            # Beraberlik (D) kontrolu
            ev_d = (row["p_D"] * row["_odd_D"]) - 1.0
            if ev_d > th:
                kazandi = (actual_y == "D")
                kar = (row["_odd_D"] - 1.0) if kazandi else -1.0
                all_bets.append({"type": "D", "profit": kar, "win": kazandi})
                
            # Deplasman (A) kontrolu
            ev_a = (row["p_A"] * row["_odd_A"]) - 1.0
            if ev_a > th:
                kazandi = (actual_y == "A")
                kar = (row["_odd_A"] - 1.0) if kazandi else -1.0
                all_bets.append({"type": "A", "profit": kar, "win": kazandi})
                
        if len(all_bets) == 0:
            print(f"EV Esigi > {th:.2f} | Yeterli bahis bulunamadi.")
            continue
            
        bets_df = pd.DataFrame(all_bets)
        total_staked = len(bets_df)
        total_profit = bets_df["profit"].sum()
        roi = (total_profit / total_staked) * 100
        win_rate = bets_df["win"].mean() * 100
        
        print(f"EV Esigi > {th:.2f} | Oynanan: {total_staked:4d} | Kazanma: %{win_rate:.1f} | Kâr: {total_profit:+7.1f} Birim | ROI: %{roi:+.1f}")

if __name__ == "__main__":
    main()