from src.telegram_bot import (
    DISCLAIMER,
    MODEL_FEATURES,
    format_prediction,
    make_feature_matrix,
    normalize_team_name,
    parse_match_input,
)


def test_parse_match_input_accepts_multiword_teams_and_case_insensitive_vs():
    assert parse_match_input("/tahmin Manchester United VS Arsenal") == (
        "Manchester United",
        "Arsenal",
    )
    assert parse_match_input("/tahmin Beşiktaş vs. Fenerbahçe") == (
        "Beşiktaş",
        "Fenerbahçe",
    )


def test_parse_match_input_rejects_missing_or_same_teams():
    import pytest

    with pytest.raises(ValueError):
        parse_match_input("/tahmin")
    with pytest.raises(ValueError):
        parse_match_input("/tahmin Galatasaray - Fenerbahçe")
    with pytest.raises(ValueError):
        parse_match_input("/tahmin ISTANBUL vs İstanbul")


def test_team_normalization_handles_turkish_case_and_diacritics():
    assert normalize_team_name("İSTANBUL") == normalize_team_name("Istanbul")
    assert normalize_team_name("IĞDIR") == normalize_team_name("ığdır")
    assert normalize_team_name("FENERBAHÇE") == normalize_team_name("Fenerbahce")


def test_feature_matrix_orders_columns_and_replaces_missing_values():
    import numpy as np
    import pandas as pd

    row = {name: float(index) for index, name in enumerate(reversed(MODEL_FEATURES))}
    row["rest_h"] = np.nan
    matrix = make_feature_matrix(pd.DataFrame([row]))
    assert list(matrix.columns) == MODEL_FEATURES
    assert matrix.shape == (1, len(MODEL_FEATURES))
    assert matrix["rest_h"].iloc[0] == 0.0


def test_prediction_format_contains_all_markets_and_disclaimer():
    result = {
        "home": "Galatasaray",
        "away": "Fenerbahçe",
        "p_home_win": 0.45,
        "p_draw": 0.28,
        "p_away_win": 0.27,
        "p_under25": 0.52,
        "p_over25": 0.48,
    }
    message = format_prediction(result)
    assert "1 (Ev sahibi): %45.0" in message
    assert "X (Beraberlik): %28.0" in message
    assert "2 (Deplasman): %27.0" in message
    assert "Alt 2.5: %52.0" in message
    assert "Üst 2.5: %48.0" in message
    assert DISCLAIMER in message
