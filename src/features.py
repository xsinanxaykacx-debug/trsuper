from collections import defaultdict, deque
import numpy as np
import pandas as pd

K_ELO = 20.0
def build_features(matches):
    required = {"match_id", "date", "season", "league", "home", "away", "home_goals", "away_goals", "y"}
    missing = required - set(matches.columns)
    if missing:
        raise ValueError(f"Feature girdisinde eksik sütunlar: {sorted(missing)}")
    df = matches.sort_values(["date", "match_id"], kind="stable").reset_index(drop=True).copy()
    elo, recent, home_form, away_form = {}, defaultdict(lambda: deque(maxlen=10)), defaultdict(lambda: deque(maxlen=5)), defaultdict(lambda: deque(maxlen=5))
    opp_elo, last_date, h2h, league_recent, season_count, season_start = defaultdict(lambda: deque(maxlen=5)), {}, defaultdict(lambda: deque(maxlen=10)), defaultdict(lambda: deque(maxlen=500)), defaultdict(int), {}
    rows = []
    for day, group in df.groupby("date", sort=True):
        records = group.to_dict("records")
        pre_elo = {}
        for r in records:
            L, h, a, season = r["league"], r["home"], r["away"], r["season"]
            kh, ka = (L, h), (L, a)
            eh, ea = elo.get(kh, 1500.0), elo.get(ka, 1500.0)
            pre_elo[r["match_id"]] = (eh, ea)
            rh, ra = list(recent[kh]), list(recent[ka])
            hf, af = list(home_form[kh]), list(away_form[ka])
            h2 = list(h2h[(L, tuple(sorted((h, a))))])
            lr = list(league_recent[L])
            sh = season_start.get((L, season), day)
            def avg(seq, pos):
                return float(np.mean([x[pos] for x in seq])) if seq else 0.0
            rows.append({
                "match_id": r["match_id"], "date": day, "season": season, "league": L,
                "home": h, "away": a, "y": r["y"], "odd_H": r.get("odd_H", np.nan),
                "odd_D": r.get("odd_D", np.nan), "odd_A": r.get("odd_A", np.nan),
                "elo_h": eh, "elo_a": ea, "elo_diff": eh-ea,
                "form_h_pts_5": avg(rh[-5:], 0), "form_h_gf_5": avg(rh[-5:], 1), "form_h_ga_5": avg(rh[-5:], 2),
                "form_a_pts_5": avg(ra[-5:], 0), "form_a_gf_5": avg(ra[-5:], 1), "form_a_ga_5": avg(ra[-5:], 2),
                "form_h_pts_10": avg(rh, 0), "form_h_gf_10": avg(rh, 1), "form_h_ga_10": avg(rh, 2),
                "form_a_pts_10": avg(ra, 0), "form_a_gf_10": avg(ra, 1), "form_a_ga_10": avg(ra, 2),
                "form_h_home_pts": avg(hf, 0), "form_h_home_gf": avg(hf, 1), "form_h_home_ga": avg(hf, 2),
                "form_a_away_pts": avg(af, 0), "form_a_away_gf": avg(af, 1), "form_a_away_ga": avg(af, 2),
                "opp_elo_h": float(np.mean(opp_elo[kh])) if opp_elo[kh] else 1500.0,
                "opp_elo_a": float(np.mean(opp_elo[ka])) if opp_elo[ka] else 1500.0,
                "rest_h": (day-last_date[kh]).days if kh in last_date else np.nan,
                "rest_a": (day-last_date[ka]).days if ka in last_date else np.nan,
                "h2h_home_win_share": sum(v == h for v in h2)/len(h2) if h2 else np.nan,
                "league_home_share": sum(v == "H" for v in lr)/len(lr) if lr else .45,
                "league_draw_share": sum(v == "D" for v in lr)/len(lr) if lr else .26,
                "season_match_h": season_count[(L,h,season)], "season_match_a": season_count[(L,a,season)],
                "days_since_season_start": (day-sh).days, "first_match_h": int(not rh), "first_match_a": int(not ra),
                "is_super_lig": int(L == "Süper Lig")
            })
        deltas = defaultdict(float)
        for r in records:
            if r["y"] not in ("H", "D", "A"): continue
            L, h, a = r["league"], r["home"], r["away"]
            eh, ea = pre_elo[r["match_id"]]
            score = {"H":1.0,"D":0.5,"A":0.0}[r["y"]]
            expected = 1/(1+10**((ea-eh)/400))
            delta = K_ELO*(score-expected)
            deltas[(L,h)] += delta
            deltas[(L,a)] -= delta
        for key, delta in deltas.items(): elo[key] = elo.get(key,1500.0)+delta
        for r in records:
            L,h,a,season = r["league"],r["home"],r["away"],r["season"]
            hg,ag = r["home_goals"],r["away_goals"]
            if pd.notna(hg) and pd.notna(ag):
                hg,ag=int(hg),int(ag)
                hp=3 if hg>ag else 1 if hg==ag else 0
                ap=3 if ag>hg else 1 if hg==ag else 0
                recent[(L,h)].append((hp,hg,ag)); recent[(L,a)].append((ap,ag,hg))
                home_form[(L,h)].append((hp,hg,ag)); away_form[(L,a)].append((ap,ag,hg))
            eh,ea=pre_elo[r["match_id"]]
            opp_elo[(L,h)].append(ea); opp_elo[(L,a)].append(eh)
            last_date[(L,h)]=day; last_date[(L,a)]=day
            h2h[(L,tuple(sorted((h,a))))].append(h if r["y"]=="H" else a if r["y"]=="A" else "D")
            league_recent[L].append(r["y"])
            season_count[(L,h,season)]+=1; season_count[(L,a,season)]+=1
            season_start.setdefault((L,season),day)
    out = pd.DataFrame(rows)
    # Every match's features must be unchanged if its own result is hidden.
    if len(out):
        assert out.loc[0, "first_match_h"] == 1 and out.loc[0, "first_match_a"] == 1
    return out
