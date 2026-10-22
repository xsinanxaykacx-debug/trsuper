import pandas as pd
import numpy as np
import optuna
from src.load import load_data, load_v16_reference
from src.load_global import load_global_data
from src.features import calculate_elo_features
from src.models.xgboost_model import XGBoostModel
from src.evaluate import calc_metrics
from xgboost import XGBClassifier
from sklearn.preprocessing import LabelEncoder

# Optuna'nın log kalabalığını sustur
optuna.logging.set_verbosity(optuna.logging.WARNING)

def main():
    print("1. Veriler Yukleniyor (Devasa)...")
    df_tr = load_data()
    df_global = load_global_data()
    ref = load_v16_reference()
    test_ids = set(ref["_id"])
    
    df_full = pd.concat([df_global, df_tr], ignore_index=True)
    
    print("2. Ozellikler Hesaplaniyor...")
    feats = calculate_elo_features(df_full)
    df_full = df_full.merge(feats, on="_id")
    
    test_seasons = ref["season"].unique()
    train_mask = ~df_full["_season"].isin(test_seasons) & (df_full["_season"] != "2015/2016")
    val_mask = df_full["_season"] == "2015/2016"
    
    train_df = df_full[train_mask].copy()
    val_df = df_full[val_mask].copy()
    
    # Kullanılacak özellikler
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
    X_val = val_df[features].fillna(0)
    
    le = LabelEncoder()
    y_train = le.fit_transform(train_df["_y"].values)
    y_val = le.transform(val_df["_y"].values)
    
    def objective(trial):
        param = {
            'objective': 'multi:softprob',
            'num_class': 3,
            'n_estimators': trial.suggest_int('n_estimators', 100, 500),
            'max_depth': trial.suggest_int('max_depth', 3, 8),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.1),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
            'random_state': 42,
            'n_jobs': -1
        }
        
        model = XGBClassifier(**param)
        model.fit(X_train, y_train)
        
        # Validation setinde LogLoss hesapla (XGBoost'un kendi eval_metric'i ile)
        preds = model.predict_proba(X_val)
        
        # LogLoss hesapla (Optuna minimize edecek)
        from sklearn.metrics import log_loss
        ll = log_loss(y_val, preds)
        return ll

    print("3. Optuna ile Z-Kahin'in en iyi hiperparametreleri araniyor (Bu islem 3-5 dakika surebilir)...")
    study = optuna.create_study(direction='minimize')
    study.optimize(objective, n_trials=15) # 15 farkli kombinasyon deneyecek
    
    print("\n" + "="*50)
    print("EN IYI HIPERPARAMETRELER BULUNDU!")
    print("="*50)
    print(study.best_params)
    print(f"Validation LogLoss: {study.best_value:.4f}")

if __name__ == "__main__":
    main()