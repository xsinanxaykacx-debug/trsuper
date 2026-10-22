import numpy as np
from src.load import load_data
from src.features import calculate_elo_features
from src.models.poisson import PoissonModel

def test_poisson_model():
    # Küçük bir örneklem (hız için)
    df = load_data().head(100).copy()
    feats = calculate_elo_features(df)
    
    # Hedef (y) ve gerçek skorları (MSE, MSD) birleştir
    merged = feats.merge(df[["_id", "MSE", "MSD", "_y"]], on="_id")
    
    model = PoissonModel()
    model.fit(merged)
    
    probs = model.predict_proba(merged)
    
    # 1X2 testi
    assert probs.shape == (len(merged), 3)
    assert np.allclose(probs.sum(axis=1), 1.0)
    assert (probs >= 0).all()
    
    # Market (Alt/Üst, BTTS) testi
    markets = model.predict_markets(merged)
    assert len(markets) == len(merged)
    assert "p_over25" in markets.columns
    assert "p_btts" in markets.columns
    assert (markets["p_over25"] >= 0).all()
    assert (markets["p_over25"] <= 1).all()