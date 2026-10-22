import numpy as np
import pandas as pd

class BlendModel:
    def __init__(self, weights=None):
        # Varsayılan ağırlıklar: Elo %20, Poisson %30, Market %50
        # (Piyasa genelde en güvenilir sinyaldir, bu yüzden en yüksek ağırlık onda)
        self.weights = weights or {"elo": 0.2, "poisson": 0.3, "market": 0.5}

    def predict_proba(self, p_elo: np.ndarray, p_poisson: np.ndarray, p_market: np.ndarray) -> np.ndarray:
        """3 modelin olasılıklarını ağırlıklı olarak birleştirir."""
        w_e = self.weights["elo"]
        w_p = self.weights["poisson"]
        w_m = self.weights["market"]
        
        # Ağırlıklı toplam
        p_blend = (w_e * p_elo) + (w_p * p_poisson) + (w_m * p_market)
        
        # Normalize et (Toplam 1 olsun)
        p_blend = p_blend / p_blend.sum(axis=1, keepdims=True)
        return p_blend