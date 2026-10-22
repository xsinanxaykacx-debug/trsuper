import pandas as pd

from src.features import calculate_elo_features
from src.load_epl import normalize_epl_team_name


def test_epl_team_aliases_are_normalized_case_insensitively():
    assert normalize_epl_team_name("Man United") == "Manchester United"
    assert normalize_epl_team_name("Nott'm Forest") == "Nottingham Forest"
    assert normalize_epl_team_name("  MAN UTD ") == "Manchester United"
    assert normalize_epl_team_name("Unlisted FC") == "Unlisted FC"


def test_feature_state_is_isolated_by_league_for_same_team_name():
    df = pd.DataFrame(
        [
            {"_id": 1, "_date": "2024-01-01", "Lig/Sezon": "EPL 2023/2024",
             "Ev_Sahibi": "United", "Deplasman": "Alpha", "MSE": 2, "MSD": 0, "_y": "H"},
            {"_id": 2, "_date": "2024-01-01", "Lig/Sezon": "Süper Lig 2023/2024",
             "Ev_Sahibi": "United", "Deplasman": "Beta", "MSE": 0, "MSD": 1, "_y": "A"},
            {"_id": 3, "_date": "2024-01-08", "Lig/Sezon": "EPL 2023/2024",
             "Ev_Sahibi": "United", "Deplasman": "Gamma", "MSE": 0, "MSD": 0, "_y": "D"},
            {"_id": 4, "_date": "2024-01-08", "Lig/Sezon": "Süper Lig 2023/2024",
             "Ev_Sahibi": "United", "Deplasman": "Delta", "MSE": 0, "MSD": 0, "_y": "D"},
        ]
    )
    df["_date"] = pd.to_datetime(df["_date"])
    features = calculate_elo_features(df).set_index("_id")

    assert features.loc[3, "elo_h"] > 1500.0
    assert features.loc[4, "elo_h"] < 1500.0
    assert features.loc[3, "form_h_pts_5"] == 3.0
    assert features.loc[4, "form_h_pts_5"] == 0.0
