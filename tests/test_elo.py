import numpy as np
from src.load import load_data
from src.features import calculate_elo_features
from src.models.elo import EloModel

def test_elo_model():
    # Küçük bir örneklem alalım (hız için)
    df = load_data().head(100).copy()
    feats = calculate_elo_features(df)
    
    # Özellikleri ve hedefi birleştir
    merged = feats.merge(df[["_id", "_y"]], on="_id")
    
    model = EloModel()
    model.fit(merged, merged["_y"].values)
    
    probs = model.predict_proba(merged)
    
    # Şekil kontrolü (N, 3)
    assert probs.shape == (len(merged), 3)
    
    # Olasılık toplamı 1 olmalı
    assert np.allclose(probs.sum(axis=1), 1.0)
    
    # Olasılıklar 0-1 arasında olmalı
    assert (probs >= 0).all() and (probs <= 1).all()