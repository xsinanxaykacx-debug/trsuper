import pytest
import pandas as pd
from src.load import load_data
from src.features import calculate_elo_features

def test_features_no_leakage():
    df = load_data().head(100).copy()
    feats = calculate_elo_features(df)
    
    assert len(feats) == len(df)
    
    first_match = feats.iloc[0]
    assert first_match["elo_h"] == 1500.0
    assert first_match["form_h_pts_5"] == 0.0
    
    first_day = df["_date"].min()
    matches_day1 = df[df["_date"] == first_day]
    feats_day1 = feats[feats["_id"].isin(matches_day1["_id"])]
    
    if len(matches_day1) > 1:
        assert (feats_day1["elo_h"] == 1500.0).all()
        assert (feats_day1["elo_a"] == 1500.0).all()