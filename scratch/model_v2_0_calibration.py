# -*- coding: utf-8 -*-
# model_v2_0_calibration.py — v1.6 + multiclass probability calibration (v2 FINAL)
# ============================================================
# KARAR KURALLARI:
#   K1: RF_cal Log Loss ≤ 1.0237
#   K2: RF_cal Brier ≤ 0.6124
#   K3: RF_cal, v1.6 RF LL'yi en az 6/10 sezonda geçmeli (v1.6 değerleri 4 ondalık)
#   ANA BAŞARI = K1 ∧ K2 ∧ K3
#   Yardımcı: RF_cal vs RF_raw (kaç sezonda iyileşme)
# ============================================================

from pathlib import Path
from collections import deque, defaultdict
import re
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import log_loss as sklearn_log_loss, accuracy_score

DATA    = Path(r"C:\Users\bzdye\Downloads\trsuper\data\csv\DATA.csv")
OUT_DIR = DATA.parents[2]
CLASSES = ["H", "D", "A"]
LN3     = float(np.log(3.0))

ISO_PENALTY  = 0.001
BASELINE_TOL = 0.0005   # yuvarlama + sıralama/girdi toleransı; aşarsa neden araştır

V16_RF_LL_PER_SEASON = {
    "2016/2017": 1.0343, "2017/2018": 1.0009, "2018/2019": 1.0354,
    "2019/2020": 1.0522, "2020/2021": 1.0247, "2021/2022": 1.0255,
    "2022/2023": 1.0320, "2023/2024": 1.0128, "2024/2025": 1.0191,
    "2025/2026": 1.0400,
}
V16_RF_LL_AGG = 1.0267
V16_RF_BR_AGG = 0.6154
V16_N_PER_SEASON = {
    "2016/2017": 612, "2017/2018": 601, "2018/2019": 573,
    "2019/2020": 574, "2020/2021": 683, "2021/2022": 666,
    "2022/2023": 579, "2023/2024": 629, "2024/2025": 632,
    "2025/2026": 305,
}
V16_N_TOTAL = 5854

_CLASSES_LEX = sorted(CLASSES)
_COLS_TO_LEX = [CLASSES.index(c) for c in _CLASSES_LEX]

def log_loss_aligned(y_true, y_prob_hda):
    return sklearn_log_loss(y_true, y_prob_hda[:, _COLS_TO_LEX], labels=_CLASSES_LEX)

def manual_log_loss(y_true, y_prob_hda):
    idx = {c: i for i, c in enumerate(CLASSES)}
    return float(np.mean([-np.log(max(y_prob_hda[i, idx[yt]], 1e-15))
                          for i, yt in enumerate(y_true)]))

def brier_multiclass(y_true, y_prob_hda):
    y_true = np.asarray(y_true); y_prob = np.asarray(y_prob_hda)
    return float(sum(np.mean((y_prob[:, j] - (y_true == c).astype(float)) ** 2)
                     for j, c in enumerate(CLASSES)))

def safe_prob(p):
    p = np.clip(p, 1e-15, 1.0)
    s = p.sum(axis=1, keepdims=True); s = np.where(s > 0, s, 1.0)
    return p / s

def _logit(p, eps=1e-12):
    p = np.clip(p, eps, 1 - eps)
    return np.log(p / (1 - p))

def fit_platt_ovr(p_base, y, classes):
    cal = {}
    for c in classes:
        idx = classes.index(c); y_bin = (y == c).astype(int)
        if y_bin.sum() < 5 or (1 - y_bin).sum() < 5:
            cal[c] = None; continue
        logits = _logit(p_base[:, idx]).reshape(-1, 1)
        lr = LogisticRegression(C=1e10, solver='lbfgs', max_iter=1000)
        lr.fit(logits, y_bin); cal[c] = lr
    return cal

def apply_platt_ovr(cal, p_base, classes):
    p_cal = np.zeros_like(p_base, dtype=float)
    for c in classes:
        idx = classes.index(c)
        if cal[c] is None:
            p_cal[:, idx] = p_base[:, idx]
        else:
            logits = _logit(p_base[:, idx]).reshape(-1, 1)
            p_cal[:, idx] = cal[c].predict_proba(logits)[:, 1]
    return safe_prob(p_cal)

def fit_iso_ovr(p_base, y, classes):
    cal = {}
    for c in classes:
        idx = classes.index(c); y_bin = (y == c).astype(int)
        iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds='clip')
        iso.fit(p_base[:, idx], y_bin); cal[c] = iso
    return cal

def apply_iso_ovr(cal, p_base, classes):
    p_cal = np.zeros_like(p_base, dtype=float)
    for c in classes:
        idx = classes.index(c)
        p_cal[:, idx] = cal[c].predict(p_base[:, idx])
    return safe_prob(p_cal)

# ============================================================
# SANITY CHECKS
# ============================================================
_sy = ["H", "D", "A", "H", "A"]
_sp = np.array([[0.50,0.30,0.20],[0.20,0.40,0.40],[0.20,0.30,0.50],
                [0.60,0.20,0.20],[0.25,0.25,0.50]])
_expected = -np.mean([np.log(_sp[i, {"H":0,"D":1,"A":2}[_sy[i]]]) for i in range(5)])
_sk = log_loss_aligned(_sy, _sp); _mn = manual_log_loss(_sy, _sp)
print("=== LOG_LOSS ALIGNMENT SANITY CHECK ===")
print(f"  sklearn (aligned): {_sk:.6f}")
print(f"  manual           : {_mn:.6f}")
print(f"  expected         : {_expected:.6f}")
if abs(_sk - _expected) > 1e-6 or abs(_mn - _expected) > 1e-6:
    raise SystemExit("!!! LOG_LOSS alignment FAIL")
print("  status: PASS\n")

_dp = np.array([[0.6,0.25,0.15],[0.3,0.4,0.3],[0.2,0.3,0.5],
                [0.7,0.2,0.1],[0.4,0.35,0.25],[0.5,0.3,0.2]])
_dy = np.array(["H","D","A","H","D","H"])
_pc = apply_platt_ovr(fit_platt_ovr(_dp, _dy, CLASSES), _dp, CLASSES)
_pi = apply_iso_ovr(fit_iso_ovr(_dp, _dy, CLASSES), _dp, CLASSES)
print("=== MULTICLASS CALIBRATION SANITY CHECK ===")
print(f"  Platt OvR sum=1    : {'PASS' if np.allclose(_pc.sum(1), 1.0, atol=1e-6) else 'FAIL'}")
print(f"  Isotonic OvR sum=1 : {'PASS' if np.allclose(_pi.sum(1), 1.0, atol=1e-6) else 'FAIL'}")
if not (np.allclose(_pc.sum(1), 1.0, atol=1e-6) and np.allclose(_pi.sum(1), 1.0, atol=1e-6)):
    raise SystemExit("!!! MULTICLASS calibration sum=1 FAIL")
print()

# ============================================================
# 1) Load
# ============================================================
df = pd.read_csv(DATA, encoding="utf-8-sig", sep=",", low_memory=False)
df["date"] = pd.to_datetime(df["Tarih"], format="%d-%m-%Y", errors="coerce")
df = df.dropna(subset=["date"]).copy()

def parse_season(s):
    m = re.search(r"(\d{4})/(\d{4})", str(s));  return f"{m.group(1)}/{m.group(2)}" if m else None
def parse_league(s):
    s = str(s)
    if "Süper" in s:  return "Süper Lig"
    if re.search(r"1\.\s*Lig", s): return "1. Lig"
    return "Other"
def season_start(s):
    m = re.match(r"(\d{4})/", str(s));  return int(m.group(1)) if m else None

df["season"] = df["Lig/Sezon"].apply(parse_season)
df["league"] = df["Lig/Sezon"].apply(parse_league)
df = df.dropna(subset=["season"]).copy()
df = df[df["league"].isin(["Süper Lig", "1. Lig"])].copy()
df["y"] = df["MS"].map({"1":"H","X":"D","2":"A"})
df = df.dropna(subset=["y"]).copy()

for src, dst in [("Maç_Sonucu_|_1","odd_H"),("Maç_Sonucu_|_X","odd_D"),("Maç_Sonucu_|_2","odd_A")]:
    df[dst] = pd.to_numeric(df[src].astype(str).str.replace(",", ".", regex=False).str.strip(), errors="coerce")
for col in ["MSE","MSD"]:
    df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ".", regex=False).str.strip(), errors="coerce")
df = df.sort_values(["date","Maç_ID"]).reset_index(drop=True)
print(f"Toplam: {len(df)} maç | "
      f"{df['date'].min().date()} → {df['date'].max().date()} | "
      f"sezon={df['season'].nunique()} | "
      f"lig={df['league'].value_counts().to_dict()}\n")

# ============================================================
# 2) Feature engineering (identical to v1.6)
# ============================================================
K_ELO = 20.0
elo = {}; recent_all = defaultdict(lambda: deque(maxlen=10))
recent_home = defaultdict(lambda: deque(maxlen=10))
recent_away = defaultdict(lambda: deque(maxlen=10))
opp_elo_recent = defaultdict(lambda: deque(maxlen=5))
last_dt = {}; h2h = defaultdict(lambda: deque(maxlen=10))
league_recent = defaultdict(lambda: deque(maxlen=500))
season_matches = defaultdict(int); season_start_dt = {}

def stats3(q):
    if not q: return (0.0, 0.0, 0.0)
    return (float(np.mean([r[0] for r in q])),
            float(np.mean([r[1] for r in q])),
            float(np.mean([r[2] for r in q])))

def implied_probs(oh, od, oa):
    o = np.array([oh, od, oa], dtype=float)
    if np.any(~np.isfinite(o)) or np.any(o <= 1.0): return None
    inv = 1.0 / o; return inv / inv.sum()

feat_rows = []
for day, group in df.groupby("date", sort=True):
    recs = group.to_dict("records"); pre_match_elo = {}
    for r in recs:
        L, h, a, d = r["league"], r["Ev_Sahibi"], r["Deplasman"], r["date"]
        season = r["season"]
        e_h = elo.get((L, h), 1500.0); e_a = elo.get((L, a), 1500.0)
        pre_match_elo[r["Maç_ID"]] = {"h": e_h, "a": e_a}

        q_h = list(recent_all[(L, h)]); q_a = list(recent_all[(L, a)])
        fh5 = stats3(q_h[-5:]); fh10 = stats3(q_h)
        fa5 = stats3(q_a[-5:]); fa10 = stats3(q_a)
        fh_home = stats3(list(recent_home[(L, h)])[-5:])
        fa_away = stats3(list(recent_away[(L, a)])[-5:])
        opp_h = list(opp_elo_recent[(L, h)]); opp_a = list(opp_elo_recent[(L, a)])
        opp_elo_h = float(np.mean(opp_h)) if opp_h else 1500.0
        opp_elo_a = float(np.mean(opp_a)) if opp_a else 1500.0
        rest_h = (d - last_dt[(L, h)]).days if (L, h) in last_dt else np.nan
        rest_a = (d - last_dt[(L, a)]).days if (L, a) in last_dt else np.nan
        hk = (L, tuple(sorted([h, a]))); q_h2h = list(h2h[hk])
        h2h_share = (sum(1 for w in q_h2h if w == h) / len(q_h2h)) if q_h2h else np.nan
        q_lg = list(league_recent[L])
        lg_home = sum(1 for w in q_lg if w == "H") / len(q_lg) if q_lg else 0.45
        lg_draw = sum(1 for w in q_lg if w == "D") / len(q_lg) if q_lg else 0.26
        sm_h = season_matches.get((L, h, season), 0)
        sm_a = season_matches.get((L, a, season), 0)
        s_first = season_start_dt.get((L, season))
        days_season = (d - s_first).days if s_first else 0

        feat_rows.append({
            "match_id": r["Maç_ID"], "date": d, "season": season, "league": L,
            "home": h, "away": a, "y": r["y"],
            "odd_H": r["odd_H"], "odd_D": r["odd_D"], "odd_A": r["odd_A"],
            "elo_h": e_h, "elo_a": e_a, "elo_diff": e_h - e_a,
            "form_h_pts_5": fh5[0], "form_h_gf_5": fh5[1], "form_h_ga_5": fh5[2],
            "form_a_pts_5": fa5[0], "form_a_gf_5": fa5[1], "form_a_ga_5": fa5[2],
            "form_h_pts_10": fh10[0], "form_h_gf_10": fh10[1], "form_h_ga_10": fh10[2],
            "form_a_pts_10": fa10[0], "form_a_gf_10": fa10[1], "form_a_ga_10": fa10[2],
            "form_h_home_pts": fh_home[0], "form_h_home_gf": fh_home[1], "form_h_home_ga": fh_home[2],
            "form_a_away_pts": fa_away[0], "form_a_away_gf": fa_away[1], "form_a_away_ga": fa_away[2],
            "opp_elo_h": opp_elo_h, "opp_elo_a": opp_elo_a,
            "rest_h": rest_h, "rest_a": rest_a,
            "h2h_current_home_team_win_share": h2h_share,
            "league_home_win_share": lg_home, "league_draw_share": lg_draw,
            "is_super_lig": 1 if L == "Süper Lig" else 0,
            "season_match_h": sm_h, "season_match_a": sm_a,
            "days_since_season_start": days_season,
            "has_history_h": 1 if recent_all[(L, h)] else 0,
            "has_history_a": 1 if recent_all[(L, a)] else 0,
        })

    deltas = defaultdict(float)
    for r in recs:
        L, h, a = r["league"], r["Ev_Sahibi"], r["Deplasman"]
        e_h = elo.get((L, h), 1500.0); e_a = elo.get((L, a), 1500.0)
        sh = {"H": 1.0, "D": 0.5, "A": 0.0}[r["y"]]
        e_h_exp = 1.0 / (1.0 + 10 ** ((e_a - e_h) / 400.0))
        dl = K_ELO * (sh - e_h_exp); deltas[(L, h)] += dl; deltas[(L, a)] -= dl
    for (L, t), dl in deltas.items():
        elo[(L, t)] = elo.get((L, t), 1500.0) + dl
    for r in recs:
        L, h, a, d = r["league"], r["Ev_Sahibi"], r["Deplasman"], r["date"]
        season = r["season"]
        hg, ag = r["MSE"], r["MSD"]
        if pd.notna(hg) and pd.notna(ag):
            hg, ag = int(hg), int(ag)
            hp = 3 if hg > ag else 1 if hg == ag else 0
            ap = 3 if ag > hg else 1 if hg == ag else 0
            recent_all[(L, h)].append((hp, hg, ag)); recent_all[(L, a)].append((ap, ag, hg))
            recent_home[(L, h)].append((hp, hg, ag)); recent_away[(L, a)].append((ap, ag, hg))
        pe = pre_match_elo[r["Maç_ID"]]
        opp_elo_recent[(L, h)].append(pe["a"]); opp_elo_recent[(L, a)].append(pe["h"])
        last_dt[(L, h)] = d; last_dt[(L, a)] = d
        hk = (L, tuple(sorted([h, a])))
        h2h[hk].append(h if r["y"] == "H" else a if r["y"] == "A" else "D")
        league_recent[L].append(r["y"])
        season_matches[(L, h, season)] += 1; season_matches[(L, a, season)] += 1
        if (L, season) not in season_start_dt:
            season_start_dt[(L, season)] = d

feat = pd.DataFrame(feat_rows)
print(f"features: {len(feat)} satır × {len(feat.columns)} sütun\n")

# ============================================================
# 3) Walk-forward with calibration
# ============================================================
FEATURES = [
    "elo_h", "elo_a", "elo_diff",
    "form_h_pts_5", "form_h_gf_5", "form_h_ga_5",
    "form_a_pts_5", "form_a_gf_5", "form_a_ga_5",
    "form_h_pts_10", "form_h_gf_10", "form_h_ga_10",
    "form_a_pts_10", "form_a_gf_10", "form_a_ga_10",
    "form_h_home_pts", "form_h_home_gf", "form_h_home_ga",
    "form_a_away_pts", "form_a_away_gf", "form_a_away_ga",
    "opp_elo_h", "opp_elo_a",
    "rest_h", "rest_a",
    "h2h_current_home_team_win_share",
    "league_home_win_share", "league_draw_share", "is_super_lig",
    "season_match_h", "season_match_a", "days_since_season_start",
    "has_history_h", "has_history_a",
]

season_start_map = {s: season_start(s) for s in feat["season"].dropna().unique()}
seasons = [s for s, _ in sorted(season_start_map.items(), key=lambda kv: kv[1])]
WARMUP = 3
test_seasons = seasons[WARMUP:]

def fit_rf(X, y):
    m = RandomForestClassifier(n_estimators=300, max_depth=8,
                               min_samples_leaf=20, random_state=42, n_jobs=-1)
    m.fit(X, y); return m

def predict_rf(m, X):
    p = m.predict_proba(X)
    cls = list(m.classes_)
    return safe_prob(p[:, [cls.index(c) for c in CLASSES]])

def get_oof_folds(train_df, n_folds_max=4):
    train_seasons = sorted(train_df["season"].unique(), key=lambda s: season_start_map[s])
    if len(train_seasons) < 2:
        return []
    n_take = min(n_folds_max, len(train_seasons) - 1)
    oof_seasons = train_seasons[-n_take:]
    folds = []
    for inner_s in oof_seasons:
        inner_train = train_df[train_df["season"].map(season_start_map) < season_start_map[inner_s]]
        inner_test  = train_df[train_df["season"] == inner_s]
        if len(inner_train) < 200 or len(inner_test) < 20:
            continue
        med_i = inner_train[FEATURES].median()
        X_i = inner_train[FEATURES].fillna(med_i).values
        X_t = inner_test[FEATURES].fillna(med_i).values
        rf_i = fit_rf(X_i, inner_train["y"].values)
        p_i = predict_rf(rf_i, X_t)
        folds.append({"season": inner_s, "p": p_i, "y": inner_test["y"].values})
    return folds

per_season = []
rf_Y_fair_all, rf_P_raw_all, rf_P_cal_all, mkt_P_all = [], [], [], []

for s in test_seasons:
    s_start = season_start_map[s]
    train_df  = feat[feat["season"].map(season_start_map) < s_start].copy()
    test_full = feat[feat["season"] == s].reset_index(drop=True)
    if len(train_df) < 200 or len(test_full) < 20:
        continue

    valid_mask = test_full.apply(
        lambda r: implied_probs(r["odd_H"], r["odd_D"], r["odd_A"]) is not None, axis=1)
    test_fair = test_full[valid_mask].reset_index(drop=True)
    y_fair = test_fair["y"].values

    # --- OOF split validation (en az 2 fold zorunlu) ---
    folds = get_oof_folds(train_df, n_folds_max=4)
    cal_chosen = 'none_insufficient_oof'   # default: yeterli OOF yoksa kalibre etme
    final_cal = None; apply_cal = None
    oof_seasons_used = [f["season"] for f in folds]

    if len(folds) >= 2:
        fit_folds = folds[:-1]; val_fold = folds[-1]
        p_fit = np.vstack([f["p"] for f in fit_folds]); y_fit = np.concatenate([f["y"] for f in fit_folds])
        p_val = val_fold["p"]; y_val = val_fold["y"]
        try:
            cal_platt_fit = fit_platt_ovr(p_fit, y_fit, CLASSES)
            cal_iso_fit   = fit_iso_ovr(p_fit, y_fit, CLASSES)
            p_platt_val = apply_platt_ovr(cal_platt_fit, p_val, CLASSES)
            p_iso_val   = apply_iso_ovr(cal_iso_fit, p_val, CLASSES)
            ll_platt_val = log_loss_aligned(y_val, p_platt_val)
            ll_iso_val   = log_loss_aligned(y_val, p_iso_val)
            ll_raw_val   = log_loss_aligned(y_val, p_val)

            # Simplicity bias: Isotonic must beat Platt by ISO_PENALTY
            if ll_iso_val + ISO_PENALTY < ll_platt_val:
                chosen_method = 'isotonic'; chosen_ll = ll_iso_val
            else:
                chosen_method = 'platt'; chosen_ll = ll_platt_val

            if chosen_ll >= ll_raw_val:
                cal_chosen = 'none_raw_better'
            else:
                p_all = np.vstack([f["p"] for f in folds]); y_all = np.concatenate([f["y"] for f in folds])
                if chosen_method == 'isotonic':
                    final_cal = fit_iso_ovr(p_all, y_all, CLASSES); apply_cal = apply_iso_ovr
                else:
                    final_cal = fit_platt_ovr(p_all, y_all, CLASSES); apply_cal = apply_platt_ovr
                cal_chosen = chosen_method
        except Exception as e:
            print(f"  calib FAIL {s}: {e}"); cal_chosen = 'none_insufficient_oof'
    # NOT: len(folds) < 2 ise cal_chosen = 'none_insufficient_oof' kalır.

    # Full train RF (identical to v1.6)
    med = train_df[FEATURES].median()
    X_tr = train_df[FEATURES].fillna(med).values
    rf = fit_rf(X_tr, train_df["y"].values)
    X_fair = test_fair[FEATURES].fillna(med).values
    p_raw = predict_rf(rf, X_fair)
    p_cal = apply_cal(final_cal, p_raw, CLASSES) if apply_cal is not None else p_raw.copy()

    P_mkt = np.vstack([implied_probs(r["odd_H"], r["odd_D"], r["odd_A"])
                       for r in test_fair.to_dict("records")])

    ll_raw = log_loss_aligned(y_fair, p_raw); ll_cal = log_loss_aligned(y_fair, p_cal)
    ll_mkt = log_loss_aligned(y_fair, P_mkt)
    br_raw = brier_multiclass(y_fair, p_raw); br_cal = brier_multiclass(y_fair, p_cal)
    br_mkt = brier_multiclass(y_fair, P_mkt)
    acc_raw = float((np.array(CLASSES)[p_raw.argmax(1)] == y_fair).mean())
    acc_cal = float((np.array(CLASSES)[p_cal.argmax(1)] == y_fair).mean())
    acc_mkt = float((np.array(CLASSES)[P_mkt.argmax(1)] == y_fair).mean())

    per_season.append({
        "season": s, "n_fair": len(test_fair), "cal_method": cal_chosen,
        "oof_seasons": ",".join(oof_seasons_used),
        "ll_raw": ll_raw, "ll_cal": ll_cal, "ll_mkt": ll_mkt,
        "br_raw": br_raw, "br_cal": br_cal, "br_mkt": br_mkt,
        "acc_raw": acc_raw, "acc_cal": acc_cal, "acc_mkt": acc_mkt,
    })
    rf_Y_fair_all.append(y_fair); rf_P_raw_all.append(p_raw)
    rf_P_cal_all.append(p_cal); mkt_P_all.append(P_mkt)

res = pd.DataFrame(per_season)

# ============================================================
# 4) Baseline equality checks
# ============================================================
print("=== v1.6 BASELINE EŞİTLİK KONTROLÜ ===")
print("(BASELINE_TOL=0.0005: yuvarlama + sıralama/girdi toleransı. Fark varsa")
print(" kalibrasyon sonuçları yorumlanmadan önce neden araştırılmalı.)\n")
baseline_ok = True
total_fair = int(res["n_fair"].sum()) if len(res) > 0 else 0
print(f"  Test sezon sayısı: {len(res)}/10")
print(f"  Toplam fair maç: {total_fair}/{V16_N_TOTAL}")
if len(res) != 10 or total_fair != V16_N_TOTAL: baseline_ok = False

for s_expect, n_expect in V16_N_PER_SEASON.items():
    match = res[res["season"] == s_expect]
    if len(match) == 0 or match["n_fair"].iloc[0] != n_expect:
        print(f"  !!! {s_expect}: n_fair={match['n_fair'].iloc[0] if len(match) else 'YOK'}, beklenen={n_expect}")
        baseline_ok = False

for _, row in res.iterrows():
    v16 = V16_RF_LL_PER_SEASON.get(row["season"])
    if v16 is None: continue
    diff = abs(row["ll_raw"] - v16)
    ok = diff < BASELINE_TOL
    if not ok: baseline_ok = False
    print(f"  {row['season']}: raw_LL={row['ll_raw']:.4f} v1.6={v16:.4f} Δ={diff:.4f} "
          f"[{'OK' if ok else 'FARK'}]")

if rf_Y_fair_all:
    YF_all    = np.concatenate(rf_Y_fair_all)
    P_raw_all = np.vstack(rf_P_raw_all)
    P_cal_all = np.vstack(rf_P_cal_all)
    PM_all    = np.vstack(mkt_P_all)

    ll_raw_a = log_loss_aligned(YF_all, P_raw_all)
    br_raw_a = brier_multiclass(YF_all, P_raw_all)
    ll_cal_a = log_loss_aligned(YF_all, P_cal_all)
    br_cal_a = brier_multiclass(YF_all, P_cal_all)
    ll_mkt_a = log_loss_aligned(YF_all, PM_all)
    br_mkt_a = brier_multiclass(YF_all, PM_all)
    acc_raw_a = float((np.array(CLASSES)[P_raw_all.argmax(1)] == YF_all).mean())
    acc_cal_a = float((np.array(CLASSES)[P_cal_all.argmax(1)] == YF_all).mean())
    acc_mkt_a = float((np.array(CLASSES)[PM_all.argmax(1)] == YF_all).mean())

    d_ll = abs(ll_raw_a - V16_RF_LL_AGG)
    d_br = abs(br_raw_a - V16_RF_BR_AGG)
    agg_ok = d_ll < BASELINE_TOL and d_br < BASELINE_TOL
    if not agg_ok: baseline_ok = False
    print(f"  AGG RF raw: LL={ll_raw_a:.4f} v1.6={V16_RF_LL_AGG:.4f} Δ={d_ll:.4f}  "
          f"Brier={br_raw_a:.4f} v1.6={V16_RF_BR_AGG:.4f} Δ={d_br:.4f}  "
          f"[{'OK' if agg_ok else 'FARK'}]")

    if baseline_ok:
        print("\n  >>> v1.6 BASELINE: PASS")
    else:
        print("\n  >>> !!! v1.6 BASELINE FARKI VAR")
        print("      Kalibrasyon sonuçlarını yorumlamadan önce farkın nedenini araştır.")

# ============================================================
# 5) Per-season table
# ============================================================
print("\n=== PER-SEZON (fair) ===")
for _, row in res.iterrows():
    print(f"  {row['season']}  n={row['n_fair']:4d}  cal={row['cal_method']:22s}  "
          f"oof=[{row['oof_seasons']}]  "
          f"LL_raw={row['ll_raw']:.4f}  LL_cal={row['ll_cal']:.4f}  LL_mkt={row['ll_mkt']:.4f}")

# ============================================================
# 6) Aggregate + criteria
# ============================================================
if rf_Y_fair_all:
    print(f"\n=== AGGREGATE (aynı {len(YF_all)} fair maç) ===")
    for name, ll, br, acc in [("RF_raw", ll_raw_a, br_raw_a, acc_raw_a),
                              ("RF_cal", ll_cal_a, br_cal_a, acc_cal_a),
                              ("Market", ll_mkt_a, br_mkt_a, acc_mkt_a)]:
        print(f"  {name:8s}  LL={ll:.4f}  Brier={br:.4f}  Acc={acc:.4f}")

    print("\n=== ANA BAŞARI KRİTERLERİ (v1.6'ya göre) ===")
    k1 = ll_cal_a <= 1.0237
    k2 = br_cal_a <= 0.6124
    print(f"  K1  LL_cal ≤ 1.0237      : {ll_cal_a:.4f}  {'PASS' if k1 else 'FAIL'}")
    print(f"  K2  Brier_cal ≤ 0.6124   : {br_cal_a:.4f}  {'PASS' if k2 else 'FAIL'}")

    n_v16 = 0
    print(f"  K3  Per-sezon LL_cal < v1.6_RF_LL (>=6/10):")
    for _, row in res.iterrows():
        v16 = V16_RF_LL_PER_SEASON.get(row["season"])
        improved = v16 is not None and row["ll_cal"] < v16
        if improved: n_v16 += 1
        delta = (row["ll_cal"] - v16) if v16 else float('nan')
        print(f"    {row['season']}  v1.6={v16:.4f}  cal={row['ll_cal']:.4f}  Δ={delta:+.5f}  "
              f"{'İYİLEŞTİ' if improved else 'kötüleşti'}")
    k3 = n_v16 >= 6
    print(f"  Toplam: {n_v16}/10  {'PASS' if k3 else 'FAIL'}")
    print(f"  (K3 v1.6 değerleri 4 ondalık — sınır farklar kesin iyileşme sayılmamalı)")

    ana_basari = k1 and k2 and k3
    print(f"\n  >>> ANA BAŞARI: {'PASS' if ana_basari else 'FAIL'} "
          f"({sum([k1,k2,k3])}/3 kriter)")

    print("\n=== KALİBRASYON KATKISI (raw'a göre — ana kriter DEĞİL) ===")
    n_raw = 0
    for _, row in res.iterrows():
        improved = row["ll_cal"] < row["ll_raw"]
        if improved: n_raw += 1
        delta = row["ll_cal"] - row["ll_raw"]
        print(f"  {row['season']}  raw={row['ll_raw']:.4f}  cal={row['ll_cal']:.4f}  "
              f"Δ={delta:+.5f}  {'İYİLEŞTİ' if improved else 'kötüleşti'}")
    print(f"  Toplam: {n_raw}/10  {'PASS' if n_raw >= 6 else 'FAIL'}")

    print(f"\n=== KALİBRASYON BIAS (aggregate) ===")
    bs_raw = [P_raw_all[:, j].mean() - (YF_all == c).mean() for j, c in enumerate(CLASSES)]
    bs_cal = [P_cal_all[:, j].mean() - (YF_all == c).mean() for j, c in enumerate(CLASSES)]
    print(f"  Raw  H={bs_raw[0]:+.4f}  D={bs_raw[1]:+.4f}  A={bs_raw[2]:+.4f}")
    print(f"  Cal  H={bs_cal[0]:+.4f}  D={bs_cal[1]:+.4f}  A={bs_cal[2]:+.4f}")

    res.to_csv(OUT_DIR / "walkforward_v2_0.csv", index=False)
    print(f"\nwalkforward_v2_0.csv yazıldı")