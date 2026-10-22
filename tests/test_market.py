import pytest
import numpy as np
from src.load import load_data
from src.models.market import MarketModel

def test_market_model():
    # Küçük bir örneklem (hız için)
    df = load_data().head(100).copy()
    
    model = MarketModel()
    probs = model.predict_proba(df)
    
    # 1X2 testi
    assert probs.shape == (len(df), 3)
    assert np.allclose(probs.sum(axis=1), 1.0)
    assert (probs >= 0).all() and (probs <= 1).all()
    
    # Manuel bir doğrulama (İlk satır için)
    ilk_oran_h = df.iloc[0]["_odd_H"]
    ilk_oran_d = df.iloc[0]["_odd_D"]
    ilk_oran_a = df.iloc[0]["_odd_A"]
    
    # Marj = (1/Oran_H) + (1/Oran_D) + (1/Oran_A)
    marj = (1/ilk_oran_h) + (1/ilk_oran_d) + (1/ilk_oran_a)
    beklenen_p_h = (1/ilk_oran_h) / marj
    
    assert np.isclose(probs[0, 0], beklenen_p_h, atol=1e-4)