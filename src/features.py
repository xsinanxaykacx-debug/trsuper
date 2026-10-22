import re
import pandas as pd
import numpy as np
from collections import deque, defaultdict
from src.load import load_data


def _league_key(value) -> str:
    """Return a season-independent league key for feature-state isolation."""
    if pd.isna(value):
        return "__UNKNOWN_LEAGUE__"
    value = str(value).strip()
    value = re.sub(r"\\s*\\d{4}/\\d{4}\\s*$", "", value).strip()
    return value or "__UNKNOWN_LEAGUE__"


def calculate_elo_features(df: pd.DataFrame, K: float = 20.0, base_elo: float = 1500.0) -> pd.DataFrame:
    """
    Her maç için maç öncesi Elo ve form özelliklerini hesaplar.
    Sızıntıyı önlemek için maçlar günlere bölünür; özellikler o günün başında hesaplanır,
    güncellemeler maçlar bittikten sonra yapılır.
    """
    df = df.sort_values(["_date", "_id"]).reset_index(drop=True)
    
    # State keys include the league, so same-named clubs in different leagues
    # can never share Elo, form, rest, or head-to-head history.
    elo = defaultdict(lambda: base_elo)
    recent_all = defaultdict(lambda: deque(maxlen=10))
    recent_home = defaultdict(lambda: deque(maxlen=10))
    recent_away = defaultdict(lambda: deque(maxlen=10))
    last_dt = {}
    h2h = defaultdict(lambda: deque(maxlen=10))
    
    feat_rows = []
    
    # Günlük gruplama (Aynı gün oynanan maçlar birbirini etkilemesin)
    for day, group in df.groupby("_date", sort=True):
        day_records = group.to_dict("records")
        pre_match_elo = {}
        
        # 1. AŞAMA: Günün maçları için özellikleri hesapla (Geçmişe bakarak)
        for r in day_records:
            mid = r["_id"]
            league = _league_key(r.get("Lig/Sezon", r.get("Lig")))
            h = (league, str(r["Ev_Sahibi"]).strip())
            a = (league, str(r["Deplasman"]).strip())
            
            e_h = elo[h]
            e_a = elo[a]
            pre_match_elo[mid] = {"h": e_h, "a": e_a}
            
            q_h = list(recent_all[h])
            q_a = list(recent_all[a])
            
            fh5 = np.mean(q_h[-5:], axis=0) if q_h else [0, 0, 0]
            fh10 = np.mean(q_h, axis=0) if q_h else [0, 0, 0]
            fa5 = np.mean(q_a[-5:], axis=0) if q_a else [0, 0, 0]
            fa10 = np.mean(q_a, axis=0) if q_a else [0, 0, 0]
            
            fh_home = np.mean(list(recent_home[h]), axis=0) if recent_home[h] else [0, 0, 0]
            fa_away = np.mean(list(recent_away[a]), axis=0) if recent_away[a] else [0, 0, 0]
            
            rest_h = (day - last_dt[h]).days if h in last_dt else np.nan
            rest_a = (day - last_dt[a]).days if a in last_dt else np.nan
            
            hk = tuple(sorted([h, a]))
            q_h2h = list(h2h[hk])
            h2h_share = sum(1 for winner in q_h2h if winner == h) / len(q_h2h) if q_h2h else np.nan
            
            feat_rows.append({
                "_id": mid,
                "elo_h": e_h, "elo_a": e_a, "elo_diff": e_h - e_a,
                "form_h_pts_5": fh5[0], "form_h_gf_5": fh5[1], "form_h_ga_5": fh5[2],
                "form_a_pts_5": fa5[0], "form_a_gf_5": fa5[1], "form_a_ga_5": fa5[2],
                "form_h_pts_10": fh10[0], "form_h_gf_10": fh10[1], "form_h_ga_10": fh10[2],
                "form_a_pts_10": fa10[0], "form_a_gf_10": fa10[1], "form_a_ga_10": fa10[2],
                "form_h_home_pts": fh_home[0], "form_h_home_gf": fh_home[1], "form_h_home_ga": fh_home[2],
                "form_a_away_pts": fa_away[0], "form_a_away_gf": fa_away[1], "form_a_away_ga": fa_away[2],
                "rest_h": rest_h, "rest_a": rest_a,
                "h2h_home_win_share": h2h_share
            })
            
        # 2. AŞAMA: Maçlar bitti, state'i güncelle (Gelecek maçlar için)
        deltas = defaultdict(float)
        
        for r in day_records:
            mid = r["_id"]
            league = _league_key(r.get("Lig/Sezon", r.get("Lig")))
            h = (league, str(r["Ev_Sahibi"]).strip())
            a = (league, str(r["Deplasman"]).strip())
            y = r["_y"]
            
            hg = pd.to_numeric(r["MSE"], errors="coerce")
            ag = pd.to_numeric(r["MSD"], errors="coerce")
            
            if pd.notna(hg) and pd.notna(ag):
                hg, ag = int(hg), int(ag)
                hp = 3 if hg > ag else (1 if hg == ag else 0)
                ap = 3 if ag > hg else (1 if hg == ag else 0)
                
                recent_all[h].append((hp, hg, ag))
                recent_all[a].append((ap, ag, hg))
                recent_home[h].append((hp, hg, ag))
                recent_away[a].append((ap, ag, hg))
                
            e_h = pre_match_elo[mid]["h"]
            e_a = pre_match_elo[mid]["a"]
            score_h = 1.0 if y == "H" else (0.5 if y == "D" else 0.0)
            exp_h = 1.0 / (1.0 + 10 ** ((e_a - e_h) / 400.0))
            delta = K * (score_h - exp_h)
            
            deltas[h] += delta
            deltas[a] -= delta
            
            last_dt[h] = day
            last_dt[a] = day
            
            hk = tuple(sorted([h, a]))
            winner = h if y == "H" else (a if y == "A" else None)
            h2h[hk].append(winner)
            
        for team, delta in deltas.items():
            elo[team] += delta

    return pd.DataFrame(feat_rows)

if __name__ == "__main__":
    df = load_data()
    feats = calculate_elo_features(df)
    print(f"Ozellikler hesaplandi: {len(feats)} satir, {len(feats.columns)} sutun")
    print("Ozelliklerin ilk 2 satiri:")
    print(feats.head(2).to_string())