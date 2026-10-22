import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.metrics import log_loss

class EloModel:
    def __init__(self):
        # Başlangıç ağırlıkları: [Ev sahibi avantajı, Elo farkı katsayısı]
        self.w_home = 0.0
        self.w_elo = 0.003
        
    def _softmax(self, z):
        """Z değerlerini olasılığa çevirir."""
        e_z = np.exp(z - np.max(z, axis=1, keepdims=True))
        return e_z / e_z.sum(axis=1, keepdims=True)
        
    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        """Elo farkına göre H, D, A olasılıkları üretir."""
        # Elo farkını 100'e bölerek ölçekle (standart pratik)
        elo_diff = df["elo_diff"].values / 100.0
        
        # Logitler (Ev, Beraberlik, Deplasman)
        z_H = self.w_home + (self.w_elo * elo_diff)
        z_D = np.zeros_like(z_H)  # Beraberlik referans sınıf
        z_A = -self.w_home - (self.w_elo * elo_diff)
        
        z = np.column_stack([z_H, z_D, z_A])
        return self._softmax(z)
        
    def fit(self, df: pd.DataFrame, y: np.ndarray):
        """Sıcaklık parametrelerini log loss minimize ederek bulur."""
        elo_diff = df["elo_diff"].values / 100.0
        
        # y'yi one-hot'a çevir (H=0, D=1, A=2)
        y_idx = np.where(y == "H", 0, np.where(y == "D", 1, 2))
        
        def loss_func(params):
            self.w_home, self.w_elo = params
            z_H = self.w_home + (self.w_elo * elo_diff)
            z_D = np.zeros_like(z_H)
            z_A = -self.w_home - (self.w_elo * elo_diff)
            z = np.column_stack([z_H, z_D, z_A])
            probs = self._softmax(z)
            
            # Log loss hesapla
            chosen = probs[np.arange(len(y_idx)), y_idx]
            return -np.mean(np.log(np.clip(chosen, 1e-15, 1.0)))
            
        # Optimizasyon (Nelder-Mead türev gerektirmez)
        res = minimize(loss_func, [self.w_home, self.w_elo], method="Nelder-Mead")
        self.w_home, self.w_elo = res.x
        return self