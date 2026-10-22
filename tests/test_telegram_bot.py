import pickle

import pytest

from src.telegram_bot import (
    CACHE_VERSION,
    DISCLAIMER,
    MODEL_FEATURES,
    ZKahinPredictor,
    calculate_value_rows,
    format_prediction,
    make_feature_matrix,
    normalize_team_name,
    parse_match_input,
    parse_odds,
    parse_value_input,
    load_or_train_predictor,
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


def test_value_input_parses_multitoken_team_names_and_odds():
    assert parse_value_input(
        "/value Galatasaray vs Fenerbahçe 1.95 3.40 3.20", 3
    ) == ("Galatasaray", "Fenerbahçe", [1.95, 3.4, 3.2])
    assert parse_value_input(
        "/value_ou Manchester United vs Arsenal 1,80 2,00", 2
    ) == ("Manchester United", "Arsenal", [1.8, 2.0])


@pytest.mark.parametrize("raw", [["abc", "2.0"], ["0.99", "2.0"], ["nan", "2.0"], ["inf", "2.0"]])
def test_invalid_odds_are_rejected(raw):
    with pytest.raises(ValueError):
        parse_odds(raw)


def test_value_parser_rejects_bad_syntax():
    with pytest.raises(ValueError):
        parse_value_input("/value Galatasaray Fenerbahçe 1.95 3.40 3.20", 3)
    with pytest.raises(ValueError):
        parse_value_input("/value_ou Galatasaray vs Fenerbahçe 1.80 nope", 2)


def test_ev_uses_model_probability_and_market_probability_removes_margin():
    rows = calculate_value_rows(
        [0.55, 0.25, 0.20],
        [2.0, 4.0, 5.5],
        ["1", "X", "2"],
    )
    assert [row["ev"] for row in rows] == pytest.approx([0.10, 0.0, 0.10])
    assert sum(row["market_probability"] for row in rows) == pytest.approx(1.0)
    assert rows[0]["market_probability"] == pytest.approx(
        (1 / 2.0) / ((1 / 2.0) + (1 / 4.0) + (1 / 5.5))
    )


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
    assert "*Z-Kahin maç analizi*" in message
    assert "1 (Ev sahibi): %45.0" in message
    assert "X (Beraberlik): %28.0" in message
    assert "2 (Deplasman): %27.0" in message
    assert "Alt 2.5: %52.0" in message
    assert "Üst 2.5: %48.0" in message
    assert DISCLAIMER in message


def test_cache_load_does_not_retrain_when_valid_cache_exists(tmp_path, monkeypatch):
    cache_path = tmp_path / "models" / "zkahin_bot_model.pkl"
    cache_path.parent.mkdir()
    predictor = ZKahinPredictor()
    predictor.model_1x2 = object()
    predictor.model_ou25 = object()
    with cache_path.open("wb") as cache_file:
        pickle.dump(
            {"cache_version": CACHE_VERSION, "predictor": predictor},
            cache_file,
        )

    def fail_if_trained(self):
        raise AssertionError("A valid cache should bypass training")

    monkeypatch.setattr(ZKahinPredictor, "load_and_train", fail_if_trained)
    loaded = load_or_train_predictor(cache_path)
    assert isinstance(loaded, ZKahinPredictor)
    assert loaded.model_1x2 is not None
    assert loaded.model_ou25 is not None
