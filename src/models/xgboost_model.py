import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.preprocessing import LabelEncoder

class XGBoostModel:
    def __init__(self):
        self.model = xgb.XGBClassifier(
            objective='multi:softprob',
            num_class=3,
            n_estimators=150,     # Aşırı ezberi önlemek için düşürdük
            max_depth=4,          # Ağacı sığ tuttuk
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1
        )
        self.label_encoder = LabelEncoder()
        
        # Sızıntısız özellikler + PİYASA ORANLARI EKLENDİ
        self.features = [
            "elo_h", "elo_a", "elo_diff",
            "form_h_pts_5", "form_h_gf_5", "form_h_ga_5",
            "form_a_pts_5", "form_a_gf_5", "form_a_ga_5",
            "form_h_pts_10", "form_h_gf_10", "form_h_ga_10",
            "form_a_pts_10", "form_a_gf_10", "form_a_ga_10",
            "form_h_home_pts", "form_h_home_gf", "form_h_home_ga",
            "form_a_away_pts", "form_a_away_gf", "form_a_away_ga",
            "rest_h", "rest_a", "h2h_home_win_share",
            "_odd_H", "_odd_D", "_odd_A"  # <--- Piyasa Oranları Burada!
        ]

    def fit(self, df: pd.DataFrame, y: np.ndarray):
        y_encoded = self.label_encoder.fit_transform(y)
        X = df[self.features].fillna(0) 
        self.model.fit(X, y_encoded)
        return self

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        X = df[self.features].fillna(0)
        probs = self.model.predict_proba(X)
        
        probs_reordered = np.zeros_like(probs)
        for i, label in enumerate(self.label_encoder.classes_):
            if label == "H": probs_reordered[:, 0] = probs[:, i]
            elif label == "D": probs_reordered[:, 1] = probs[:, i]
            elif label == "A": probs_reordered[:, 2] = probs[:, i]
            
        return probs_reordered