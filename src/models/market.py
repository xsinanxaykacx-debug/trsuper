import numpy as np
import pandas as pd

class MarketModel:
    def __init__(self):
        pass
        
    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        """
        Bahis oranlarını (virgüllü format) alıp, marjı temizleyerek
        H, D, A olasılıklarına çevirir.
        """
        oh = df["_odd_H"].values
        od = df["_odd_D"].values
        oa = df["_odd_A"].values
        
        # Oranların tersini al (Implied probability)
        inv_h = 1.0 / oh
        inv_d = 1.0 / od
        inv_a = 1.0 / oa
        
        # Toplam marj (Overround)
        total = inv_h + inv_d + inv_a
        
        # Marjı temizle (Normalize et)
        p_h = inv_h / total
        p_d = inv_d / total
        p_a = inv_a / total
        
        return np.column_stack([p_h, p_d, p_a])