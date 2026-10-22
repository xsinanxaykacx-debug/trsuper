import unittest
import pandas as pd
from src.features import build_features

def sample():
    return pd.DataFrame([
        {"match_id":"1","date":pd.Timestamp("2020-01-01"),"season":"2019/2020","league":"Süper Lig","home":"A","away":"B","home_goals":3,"away_goals":0,"y":"H"},
        {"match_id":"2","date":pd.Timestamp("2020-01-02"),"season":"2019/2020","league":"Süper Lig","home":"B","away":"A","home_goals":2,"away_goals":1,"y":"H"},
        {"match_id":"3","date":pd.Timestamp("2020-01-03"),"season":"2019/2020","league":"Süper Lig","home":"A","away":"B","home_goals":0,"away_goals":2,"y":"A"},
    ])

class FeatureTests(unittest.TestCase):
    def test_no_current_match_result_leakage(self):
        frame=sample()
        base=build_features(frame)
        changed=frame.copy()
        changed.loc[changed.match_id=="2",["home_goals","away_goals","y"]]=[99,0,"H"]
        altered=build_features(changed)
        cols=["elo_h","elo_a","elo_diff","form_h_pts_5","form_h_gf_5","form_a_pts_5","form_a_ga_5"]
        left=base.loc[base.match_id=="2",cols].to_numpy()
        right=altered.loc[altered.match_id=="2",cols].to_numpy()
        self.assertEqual(left.tolist(),right.tolist())
    def test_future_result_cannot_change_past_features(self):
        frame=sample()
        base=build_features(frame)
        changed=frame.copy()
        changed.loc[changed.match_id=="3",["home_goals","away_goals","y"]]=[0,8,"A"]
        altered=build_features(changed)
        cols=["elo_h","elo_a","elo_diff","form_h_pts_5","form_h_gf_5","form_a_pts_5","form_a_ga_5"]
        self.assertEqual(base.loc[base.match_id=="1",cols].to_numpy().tolist(),altered.loc[altered.match_id=="1",cols].to_numpy().tolist())

if __name__=="__main__": unittest.main()
