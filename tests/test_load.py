import pytest
from pathlib import Path
from src.load import load_data, load_v16_reference

def test_load_data():
    df = load_data()
    assert len(df) > 7000
    assert set(df["_y"].dropna().unique()) == {"H", "D", "A"}
    assert df["_date"].isna().sum() == 0
    assert df["_season"].isna().sum() == 0
    assert df["_odd_H"].notna().mean() > 0.9

def test_v16_reference():
    ref = load_v16_reference()
    assert len(ref) == 5854
    assert ref["_id"].duplicated().sum() == 0