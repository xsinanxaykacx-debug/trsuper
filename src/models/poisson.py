import numpy as np
import pandas as pd
from scipy.stats import poisson
from scipy.optimize import minimize

class PoissonModel:
    def __init__(self):
        # Fit edilecek parametreler
        self.scale = 1.0
        self.home_adv = 1.1
        self.rho = -0.05  # Dixon-Coles düzeltmesi

    def _get_lambda(self, df):
        # Son 10 maçlık gol atma (hücum) ve yeme (savunma) ortalamaları
        h_att = df["form_h_gf_10"].values
        h_def = df["form_h_ga_10"].values
        a_att = df["form_a_gf_10"].values
        a_def = df["form_a_ga_10"].values
        
        # Beklenen goller (Lambda)
        lam_h = np.maximum(0.1, h_att * a_def * self.scale * self.home_adv)
        lam_a = np.maximum(0.1, a_att * h_def * self.scale)
        return lam_h, lam_a

    def _calc_probs(self, df, max_goals=8):
        lam_h, lam_a = self._get_lambda(df)
        n = len(df)
        
        # Skor gridi (0-8 arası goller)
        x = np.arange(max_goals + 1)
        y = np.arange(max_goals + 1)
        probs = np.zeros((n, max_goals + 1, max_goals + 1))
        
        for i in range(n):
            # Poisson dağılımı
            p_h = poisson.pmf(x, lam_h[i])
            p_a = poisson.pmf(y, lam_a[i])
            p_grid = np.outer(p_h, p_a)
            
            # Dixon-Coles Düzeltmesi (Düşük skorlar için)
            for xi in range(max_goals + 1):
                for yi in range(max_goals + 1):
                    if xi == 0 and yi == 0:
                        p_grid[xi, yi] *= (1 - lam_h[i] * lam_a[i] * self.rho)
                    elif xi == 0 and yi == 1:
                        p_grid[xi, yi] *= (1 + lam_h[i] * self.rho)
                    elif xi == 1 and yi == 0:
                        p_grid[xi, yi] *= (1 + lam_a[i] * self.rho)
                    elif xi == 1 and yi == 1:
                        p_grid[xi, yi] *= (1 - self.rho)
                        
            # Olasılıkları normalize et
            probs[i] = p_grid / p_grid.sum()
            
        return probs

    def fit(self, df):
        hg = df["MSE"].values.astype(int)
        ag = df["MSD"].values.astype(int)
        
        def loss(params):
            self.scale, self.home_adv, self.rho = params
            probs = self._calc_probs(df)
            # Gerçekleşen skorun olasılığı (8 golden büyükse 8 kabul et)
            hg_clip = np.clip(hg, 0, 8)
            ag_clip = np.clip(ag, 0, 8)
            actual_probs = probs[np.arange(len(df)), hg_clip, ag_clip]
            return -np.mean(np.log(np.clip(actual_probs, 1e-15, 1.0)))
            
        # Optimizasyon sınırları (lambda negatif olmasın, rho çok sapmasın)
        bounds = [(0.1, 3.0), (0.5, 2.0), (-0.2, 0.2)]
        res = minimize(loss, [self.scale, self.home_adv, self.rho], method="L-BFGS-B", bounds=bounds)
        self.scale, self.home_adv, self.rho = res.x
        return self

    def predict_proba(self, df):
        """1X2 Olasılıklarını döndürür."""
        probs = self._calc_probs(df)
        n = len(df)
        max_g = probs.shape[1]
        p_H = np.zeros(n)
        p_D = np.zeros(n)
        p_A = np.zeros(n)
        
        for i in range(n):
            for x in range(max_g):
                for y in range(max_g):
                    if x > y: p_H[i] += probs[i, x, y]
                    elif x == y: p_D[i] += probs[i, x, y]
                    else: p_A[i] += probs[i, x, y]
                    
        return np.column_stack([p_H, p_D, p_A])

    def predict_markets(self, df):
        """1X2, Alt/Üst 2.5 ve Karşılıklı Gol (BTTS) olasılıklarını döndürür."""
        probs = self._calc_probs(df)
        n = len(df)
        max_g = probs.shape[1]
        results = []
        
        for i in range(n):
            p_over, p_btts, p_H, p_D, p_A = 0.0, 0.0, 0.0, 0.0, 0.0
            for x in range(max_g):
                for y in range(max_g):
                    p = probs[i, x, y]
                    if x + y > 2: p_over += p
                    if x > 0 and y > 0: p_btts += p
                    if x > y: p_H += p
                    elif x == y: p_D += p
                    else: p_A += p
                    
            results.append({
                "p_H": p_H, "p_D": p_D, "p_A": p_A,
                "p_over25": p_over, "p_under25": 1.0 - p_over,
                "p_btts": p_btts
            })
            
        return pd.DataFrame(results)