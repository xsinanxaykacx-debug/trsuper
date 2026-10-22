import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

from sklearn.model_selection import StratifiedKFold
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier

from src.load import load_data, load_v16_reference
from src.load_global import load_global_data
from src.features import calculate_elo_features

def main():
    print("1. Veriler Yukleniyor...")
    df_tr = load_data()
    df_global = load_global_data()
    ref = load_v16_reference()
    
    # DÜZELTME: Türkiye verisinde de _y_ou25 hedefini oluştur
    df_tr["_y_ou25"] = np.where(
        df_tr["MSE"].notna() & df_tr["MSD"].notna(),
        (df_tr["MSE"] + df_tr["MSD"] > 2.5).astype(float),
        np.nan
    )
    
    test_ids = set(ref["_id"])
    
    df_full = pd.concat([df_global, df_tr], ignore_index=True)
    
    print("2. Ozellikler Hesaplaniyor...")
    feats = calculate_elo_features(df_full)
    df_full = df_full.merge(feats, on="_id")
    
    # HEDEF: Model C (Alt/Üst 2.5)
    df_full = df_full.dropna(subset=["_y_ou25"])
    
    test_seasons = ref["season"].unique()
    train_mask = ~df_full["_season"].isin(test_seasons) & (df_full["_season"] != "2015/2016")
    test_mask = df_full["_id"].isin(test_ids)
    
    train_df = df_full[train_mask].copy()
    test_df = df_full[test_mask].copy()
    
    features = [
        "elo_h", "elo_a", "elo_diff",
        "form_h_pts_5", "form_h_gf_5", "form_h_ga_5",
        "form_a_pts_5", "form_a_gf_5", "form_a_ga_5",
        "form_h_pts_10", "form_h_gf_10", "form_h_ga_10",
        "form_a_pts_10", "form_a_gf_10", "form_a_ga_10",
        "form_h_home_pts", "form_h_home_gf", "form_h_home_ga",
        "form_a_away_pts", "form_a_away_gf", "form_a_away_ga",
        "rest_h", "rest_a", "h2h_home_win_share",
        "_odd_H", "_odd_D", "_odd_A"
    ]
    
    X_train = train_df[features].fillna(0)
    y_train = train_df["_y_ou25"].values
    
    X_test = test_df[features].fillna(0)
    y_test = test_df["_y_ou25"].values
    
    print(f"Train: {len(X_train)} mac | Test: {len(X_test)} mac")
    
    if len(X_test) == 0:
        print("HATA: Test seti hala bos! Kontrol edin.")
        return
    
    # 3. Base Modeller (Temel Modeller)
    print("3. Base Modeller Egitiliyor (XGBoost, LightGBM, CatBoost)...")
    
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    oof_preds = np.zeros((len(X_train), 3)) 
    test_preds = np.zeros((len(X_test), 3))
    
    models = [
        xgb.XGBClassifier(objective='binary:logistic', n_estimators=113, max_depth=4, learning_rate=0.05, random_state=42, n_jobs=-1),
        lgb.LGBMClassifier(objective='binary', n_estimators=150, max_depth=5, learning_rate=0.05, random_state=42, n_jobs=-1, verbose=-1),
        CatBoostClassifier(objective='Logloss', iterations=150, depth=5, learning_rate=0.05, random_state=42, verbose=0)
    ]
    
    for i, model in enumerate(models):
        model_name = type(model).__name__
        print(f"   {model_name} egitiliyor...")
        
        for train_idx, val_idx in skf.split(X_train, y_train):
            X_tr, X_val = X_train.iloc[train_idx], X_train.iloc[val_idx]
            y_tr, y_val = y_train[train_idx], y_train[val_idx]
            
            model.fit(X_tr, y_tr)
            oof_preds[val_idx, i] = model.predict_proba(X_val)[:, 1]
            
        model.fit(X_train, y_train)
        test_preds[:, i] = model.predict_proba(X_test)[:, 1]
        
        ll = log_loss(y_test, test_preds[:, i])
        print(f"   {model_name} Test LogLoss: {ll:.5f}")

    # 4. Meta-Model (Ust Akil)
    print("\n4. Meta-Model (Logistic Regression) Egitiliyor...")
    meta_model = LogisticRegression(random_state=42)
    meta_model.fit(oof_preds, y_train)
    
    # 5. Nihai Tahmin ve Sonuc
    final_preds = meta_model.predict_proba(test_preds)[:, 1]
    final_ll = log_loss(y_test, final_preds)
    
    print("\n" + "="*50)
    print("STACKING (YIGINLAMA) SONUCLARI")
    print("="*50)
    print(f"RAW XGBoost LogLoss: 0.68715 (Referans)")
    print(f"STACKED Ensemble LogLoss: {final_ll:.5f}")
    
    if final_ll < 0.68715:
        print(f"\nBASARILI! Stacking, tek XGBoost'tan {0.68715 - final_ll:.5f} daha iyi.")
        if final_ll <= 0.66:
            print("HEDEF (0.66) ASILDI!")
    else:
        print("\nStacking modeli beklenen iyilesmeyi saglamadi.")

if __name__ == "__main__":
    main()