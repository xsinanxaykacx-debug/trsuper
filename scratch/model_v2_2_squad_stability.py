# -*- coding: utf-8 -*-
# model_v2_2_squad_stability.py — v2.2 FINAL (v2)
# ============================================================
# A deneyi: v1.6 + rolling squad stability
# v2 düzeltmeleri:
#   - team_xi_history MAÇ BAZLI (her maç append, None dahil)
#   - compute_stability: en az 2 hesaplanabilir çift → ortalama; aksi NaN
#   - LINEUP PROFILE sanity check (oyuncu sayısı dağılımı)
#   - Kadro yedek içeriyor mu, örneklerle gösterilir
# Karar (kilitli):
#   K1: RF LL ≤ 1.0237
#   K2: RF Brier ≤ 0.6124
#   K3: ≥ 6/10 sezon v1.6'dan iyileşme
#   ANA BAŞARI = Baseline PASS ∧ K1 ∧ K2 ∧ K3
# ============================================================

from pathlib import Path
from collections import deque, defaultdict
import re
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import log_loss as sklearn_log_loss, accuracy_score

try:
    import lightgbm as lgb
    HAS_LGBM = True
except ImportError:
    HAS_LGBM = False
try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

DATA    = Path(r"C:\Users\bzdye\Downloads\trsuper\data\csv\DATA.csv")
OUT_DIR = DATA.parents[2]
CLASSES = ["H", "D", "A"]
LN3     = float(np.log(3.0))

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
V16_N_TOTAL  = 5854
BASELINE_TOL = 0.0005

THRESH_LL    = 1.0237
THRESH_BRIER = 0.6124
MIN_IMPROVE  = 6
BORDERLINE   = 0.001
STABILITY_K  = 3
STABILITY_MAXLEN = STABILITY_K + 1  # 4 maç
STABILITY_MIN_PAIRS = 2             # en az 2 çift

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

def parse_xi(s):
    """'61 Oğuzhan Bahadır; 15 Orhan Taşdelen; ...' → {'Oğuzhan Bahadır', 'Orhan Taşdelen', ...}"""
    if pd.isna(s): return None
    s = str(s).strip()
    if not s: return None
    parts = [p.strip() for p in s.split(";") if p.strip()]
    if len(parts) < 9: return None
    names = set()
    for p in parts:
        m = re.match(r"^\d+\s+(.+)$", p)
        if m:
            name = m.group(1).strip()
            if name: names.add(name)
        else:
            names.add(p)
    return names if len(names) >= 9 else None

def count_lineup_players(s):
    """Kadro string'indeki oyuncu sayısı (parse edilemese de sayar)."""
    if pd.isna(s): return 0
    s = str(s).strip()
    if not s: return 0
    return len([p for p in s.split(";") if p.strip()])

def compute_stability(history_list, min_pairs=STABILITY_MIN_PAIRS):
    """history_list: kronolojik sıralı, None veya set listesi (en yeni sonda).
    Ardışık çiftleri oluştur; iki taraf da set ise overlap hesapla.
    En az min_pairs hesaplanabilir çift varsa ortalama, aksi NaN.
    """
    if len(history_list) < 2:
        return np.nan
    overlaps = []
    for i in range(len(history_list) - 1, 0, -1):
        s1 = history_list[i]; s2 = history_list[i-1]
        if s1 is None or s2 is None:
            continue
        denom = max(len(s1), len(s2))
        if denom == 0: continue
        overlaps.append(len(s1 & s2) / denom)
    if len(overlaps) < min_pairs:
        return np.nan
    return float(np.mean(overlaps))

# --- sanity ---
_sy = ["H", "D", "A", "H", "A"]
_sp = np.array([[0.50,0.30,0.20],[0.20,0.40,0.40],[0.20,0.30,0.50],
                [0.60,0.20,0.20],[0.25,0.25,0.50]])
_expected = -np.mean([np.log(_sp[i, {"H":0,"D":1,"A":2}[_sy[i]]]) for i in range(5)])
_sk = log_loss_aligned(_sy, _sp); _mn = manual_log_loss(_sy, _sp)
print("=== LOG_LOSS ALIGNMENT SANITY CHECK ===")
print(f"  sklearn: {_sk:.6f}  manual: {_mn:.6f}  expected: {_expected:.6f}")
if abs(_sk - _expected) > 1e-6 or abs(_mn - _expected) > 1e-6:
    raise SystemExit("!!! LOG_LOSS alignment FAIL")
print("  status: PASS\n")

# --- load ---
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
print(f"Toplam: {len(df)} maç | sezon={df['season'].nunique()} | "
      f"lig={df['league'].value_counts().to_dict()}\n")

# --- lineup parse + profile ---
print("=== LINEUP PARSE & PROFILE CHECK ===")
df["_xi_home"] = df["Ev_Kadro"].apply(parse_xi)
df["_xi_away"] = df["Deplasman_Kadro"].apply(parse_xi)

h_count = df["Ev_Kadro"].apply(count_lineup_players)
a_count = df["Deplasman_Kadro"].apply(count_lineup_players)

def profile(name, counts):
    s = counts[counts > 0]
    print(f"  {name} oyuncu sayısı: n={len(s)}, "
          f"min={int(s.min())}, median={int(s.median())}, max={int(s.max())}, "
          f"mean={s.mean():.1f}")
    # 11 mi 18 mi 25 mi?
    n_11 = int((s == 11).sum())
    n_18 = int((s == 18).sum())
    n_gt14 = int((s > 14).sum())
    print(f"    =11: {n_11}  =18: {n_18}  >14: {n_gt14}  (toplam {len(s)})")

profile("Ev_Kadro", h_count)
profile("Deplasman_Kadro", a_count)

h_ok = int(df["_xi_home"].notna().sum()); a_ok = int(df["_xi_away"].notna().sum())
print(f"  Ev_Kadro parse OK       : {h_ok}/{len(df)} ({100*h_ok/len(df):.1f}%)")
print(f"  Deplasman_Kadro parse OK: {a_ok}/{len(df)} ({100*a_ok/len(df):.1f}%)")

print("\n  Örnek kadrolar (oyuncu sayısı ve ilk 3 isim):")
for i in [0, len(df)//2, len(df)-1]:
    for side, col in [("Ev", "Ev_Kadro"), ("Dep", "Deplasman_Kadro")]:
        raw = str(df[col].iloc[i])[:100]
        parsed = df["_xi_home" if side == "Ev" else "_xi_away"].iloc[i]
        n = len(parsed) if parsed is not None else 0
        sample_names = sorted(parsed)[:3] if parsed else []
        print(f"    [{i}/{side}]: {n} oyuncu | ilk 3: {sample_names} | raw='{raw}...'")

# UYARI: 11 mi 18 mi?
median_count = int(h_count[h_count > 0].median()) if (h_count > 0).any() else 0
if median_count > 14:
    print(f"\n  !!! UYARI: median oyuncu sayısı {median_count} — kadroda yedekler olabilir.")
    print(f"      Ev_Kadro ilk 11 değil, tüm kadroyu içeriyor olabilir.")
elif median_count == 11:
    print(f"\n  OK: median oyuncu sayısı 11 — sadece ilk 11.")
else:
    print(f"\n  OK: median oyuncu sayısı {median_count} (11 civarı).")
print()

# --- feature engineering ---
K_ELO = 20.0
elo = {}; recent_all = defaultdict(lambda: deque(maxlen=10))
recent_home = defaultdict(lambda: deque(maxlen=10))
recent_away = defaultdict(lambda: deque(maxlen=10))
opp_elo_recent = defaultdict(lambda: deque(maxlen=5))
last_dt = {}; h2h = defaultdict(lambda: deque(maxlen=10))
league_recent = defaultdict(lambda: deque(maxlen=500))
season_matches = defaultdict(int); season_start_dt = {}

# YENİ: MAÇ BAZLI XI geçmişi (her maç append, None dahil)
team_xi_history = defaultdict(lambda: deque(maxlen=STABILITY_MAXLEN))

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

    # FAZ 1: gün başındaki state'ten feature'lar
    for r in recs:
        L, h, a, d = r["league"], r["Ev_Sahibi"], r["Deplasman"], r["date"]
        season = r["season"]
        h_s = str(h).strip(); a_s = str(a).strip()
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

        # MAÇ BAZLI XI geçmişinden stability (bu maçın XI'si dahil DEĞİL)
        stab_h = compute_stability(list(team_xi_history[h_s]))
        stab_a = compute_stability(list(team_xi_history[a_s]))

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
            "squad_stability_home_prior": stab_h,
            "squad_stability_away_prior": stab_a,
        })

    # FAZ 2a
    deltas = defaultdict(float)
    for r in recs:
        L, h, a = r["league"], r["Ev_Sahibi"], r["Deplasman"]
        e_h = elo.get((L, h), 1500.0); e_a = elo.get((L, a), 1500.0)
        sh = {"H": 1.0, "D": 0.5, "A": 0.0}[r["y"]]
        e_h_exp = 1.0 / (1.0 + 10 ** ((e_a - e_h) / 400.0))
        dl = K_ELO * (sh - e_h_exp); deltas[(L, h)] += dl; deltas[(L, a)] -= dl
    # FAZ 2b
    for (L, t), dl in deltas.items():
        elo[(L, t)] = elo.get((L, t), 1500.0) + dl
    # FAZ 2c
    for r in recs:
        L, h, a, d = r["league"], r["Ev_Sahibi"], r["Deplasman"], r["date"]
        season = r["season"]
        h_s = str(h).strip(); a_s = str(a).strip()
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
        if (L, season) not in season_start_dt: season_start_dt[(L, season)] = d

        # MAÇ BAZLI append (None dahil)
        team_xi_history[h_s].append(r["_xi_home"])
        team_xi_history[a_s].append(r["_xi_away"])

feat = pd.DataFrame(feat_rows)
feat.to_csv(OUT_DIR / "features_v2_2.csv", index=False)
print(f"features_v2_2.csv: {len(feat)} satır × {len(feat.columns)} sütun\n")

FEATURES_V16 = [
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
FEATURES_V22 = FEATURES_V16 + ["squad_stability_home_prior", "squad_stability_away_prior"]

print(f"=== FEATURE SET BOYUTLARI ===")
print(f"  FEATURES_V16: {len(FEATURES_V16)} özellik")
print(f"  FEATURES_V22: {len(FEATURES_V22)} özellik")

print("\n=== FEATURE SANITY CHECK ===")
for c in ["squad_stability_home_prior", "squad_stability_away_prior"]:
    s = feat[c].dropna()
    print(f"  {c}: dolu={len(s)}/{len(feat)} ({100*len(s)/len(feat):.1f}%), "
          f"mean={s.mean():.4f}, min={s.min():.4f}, max={s.max():.4f}")
    if len(s) < len(feat) * 0.4:
        print(f"    !!! düşük doluluk (< %40)")
    if not (0.0 <= s.mean() <= 1.0):
        print(f"    !!! mean [0,1] dışında")

# --- walk-forward ---
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
    return p[:, [cls.index(c) for c in CLASSES]]

def fit_predict_generic(factory, needs_scale, allow_nan, use_le,
                        X_tr_raw, X_te_raw, y_tr, med):
    if allow_nan:
        X_tr, X_te = X_tr_raw.values, X_te_raw.values
    else:
        X_tr = X_tr_raw.fillna(med).values; X_te = X_te_raw.fillna(med).values
    if needs_scale:
        sc = StandardScaler().fit(X_tr); X_tr = sc.transform(X_tr); X_te = sc.transform(X_te)
    m = factory()
    if use_le:
        le = LabelEncoder(); y_tr_enc = le.fit_transform(y_tr)
        m.fit(X_tr, y_tr_enc); p_raw = m.predict_proba(X_te)
        out = np.zeros((len(p_raw), len(CLASSES)))
        for col_i, cls_val in enumerate(list(m.classes_)):
            orig = le.inverse_transform([int(cls_val)])[0]
            out[:, CLASSES.index(orig)] = p_raw[:, col_i]
        ssum = out.sum(axis=1, keepdims=True); ssum[ssum == 0] = 1.0
        return out / ssum
    else:
        m.fit(X_tr, y_tr); p_raw = m.predict_proba(X_te)
        cls = list(m.classes_)
        return p_raw[:, [cls.index(c) for c in CLASSES]]

OTHER_SPECS = [("LR", lambda: LogisticRegression(max_iter=2000, solver="lbfgs"), True, False, False)]
if HAS_LGBM:
    OTHER_SPECS.append(("LGBM", lambda: lgb.LGBMClassifier(n_estimators=300, max_depth=6,
        learning_rate=0.05, num_leaves=31, random_state=42, verbose=-1), False, True, False))
if HAS_XGB:
    OTHER_SPECS.append(("XGB", lambda: xgb.XGBClassifier(n_estimators=300, max_depth=6,
        learning_rate=0.05, random_state=42, eval_metric="mlogloss", verbosity=0), False, True, True))

ALL_MODEL_NAMES = ["RF_v16", "RF_v22"] + [s[0] for s in OTHER_SPECS]

per_model_rows        = defaultdict(list)
per_model_P_fair      = defaultdict(list)
per_model_Y_fair      = defaultdict(list)
per_model_matchids    = defaultdict(dict)
per_model_y_by_season = defaultdict(dict)
per_season_n_fair     = {}
failures = []

for s in test_seasons:
    s_start = season_start_map[s]
    train_df  = feat[feat["season"].map(season_start_map) < s_start].copy()
    test_full = feat[feat["season"] == s].reset_index(drop=True)
    if len(train_df) < 200 or len(test_full) < 20: continue

    valid_mask = test_full.apply(
        lambda r: implied_probs(r["odd_H"], r["odd_D"], r["odd_A"]) is not None, axis=1)
    test_fair = test_full[valid_mask].reset_index(drop=True)
    if len(test_fair) == 0: continue

    y_tr = train_df["y"].values
    y_fair = test_fair["y"].values
    match_ids_fair = tuple(test_fair["match_id"].tolist())
    y_fair_tuple = tuple(y_fair.tolist())
    per_season_n_fair[s] = len(test_fair)

    # RF_v16
    med_v16 = train_df[FEATURES_V16].median()
    X_tr_v16 = train_df[FEATURES_V16].fillna(med_v16).values
    X_te_v16 = test_fair[FEATURES_V16].fillna(med_v16).values
    try:
        rf_v16 = fit_rf(X_tr_v16, y_tr); p_v16 = predict_rf(rf_v16, X_te_v16)
        per_model_rows["RF_v16"].append({
            "season": s, "n_fair": len(test_fair),
            "ll_raw": log_loss_aligned(y_fair, p_v16),
            "br_raw": brier_multiclass(y_fair, p_v16),
            "acc_raw": float((np.array(CLASSES)[p_v16.argmax(1)] == y_fair).mean()),
        })
        per_model_P_fair["RF_v16"].append(p_v16)
        per_model_Y_fair["RF_v16"].append(y_fair)
        per_model_matchids["RF_v16"][s] = match_ids_fair
        per_model_y_by_season["RF_v16"][s] = y_fair_tuple
    except Exception as e:
        failures.append((s, "RF_v16", str(e))); print(f"  FAIL {s} | RF_v16 | {e}")

    # RF_v22
    med_v22 = train_df[FEATURES_V22].median()
    X_tr_v22 = train_df[FEATURES_V22].fillna(med_v22).values
    X_te_v22 = test_fair[FEATURES_V22].fillna(med_v22).values
    try:
        rf_v22 = fit_rf(X_tr_v22, y_tr); p_v22 = predict_rf(rf_v22, X_te_v22)
        per_model_rows["RF_v22"].append({
            "season": s, "n_fair": len(test_fair),
            "ll_raw": log_loss_aligned(y_fair, p_v22),
            "br_raw": brier_multiclass(y_fair, p_v22),
            "acc_raw": float((np.array(CLASSES)[p_v22.argmax(1)] == y_fair).mean()),
        })
        per_model_P_fair["RF_v22"].append(p_v22)
        per_model_Y_fair["RF_v22"].append(y_fair)
        per_model_matchids["RF_v22"][s] = match_ids_fair
        per_model_y_by_season["RF_v22"][s] = y_fair_tuple
    except Exception as e:
        failures.append((s, "RF_v22", str(e))); print(f"  FAIL {s} | RF_v22 | {e}")

    # Diğer modeller
    for name, factory, ns, an, ul in OTHER_SPECS:
        try:
            p_fair = fit_predict_generic(factory, ns, an, ul,
                                         train_df[FEATURES_V22], test_fair[FEATURES_V22], y_tr, med_v22)
            per_model_rows[name].append({
                "season": s, "n_fair": len(test_fair),
                "ll_raw": log_loss_aligned(y_fair, p_fair),
                "br_raw": brier_multiclass(y_fair, p_fair),
                "acc_raw": float((np.array(CLASSES)[p_fair.argmax(1)] == y_fair).mean()),
            })
            per_model_P_fair[name].append(p_fair)
            per_model_Y_fair[name].append(y_fair)
            per_model_matchids[name][s] = match_ids_fair
            per_model_y_by_season[name][s] = y_fair_tuple
        except Exception as e:
            failures.append((s, name, str(e))); print(f"  FAIL {s} | {name} | {e}")

print("\n=== MODEL FAILURES ===")
if failures:
    for s, n, m in failures: print(f"  {s} | {n} | {m}")
    raise SystemExit("!!! Model hataları — ana karar verilmez")
else:
    print("  Hiç hata yok")

# --- satır hizalama ---
print("\n=== SATIR HİZALAMA KONTROLÜ ===")
align_ok = True
common_seasons = sorted(per_season_n_fair.keys(), key=lambda x: season_start_map[x])
for name in ALL_MODEL_NAMES:
    rows = per_model_rows[name]
    if len(rows) != len(common_seasons):
        print(f"  !!! {name}: {len(rows)} sezon, beklenen {len(common_seasons)}")
        align_ok = False; continue
    for s in common_seasons:
        if s not in per_model_matchids[name]:
            print(f"  !!! {name}/{s}: match_id yok"); align_ok = False; continue
        if per_model_matchids[name][s] != per_model_matchids["RF_v16"][s]:
            print(f"  !!! {name}/{s}: match_id RF_v16'dan farklı"); align_ok = False
        if per_model_y_by_season[name][s] != per_model_y_by_season["RF_v16"][s]:
            print(f"  !!! {name}/{s}: y RF_v16'dan farklı"); align_ok = False
if not align_ok:
    raise SystemExit("!!! Satır hizalama FAIL")
print(f"  Tüm modeller ({len(ALL_MODEL_NAMES)}): aynı {len(common_seasons)} sezon, "
      f"aynı match_id/y")
print(f"  >>> SATIR HİZALAMA: PASS")

# --- baseline replikasyon ---
print("\n" + "=" * 60)
print("=== BASELINE REPLİKASYON (RF_v16 vs v1.6) ===")
print("=" * 60)
baseline_ok = True; baseline_reasons = []

total_n = sum(per_season_n_fair.values())
if total_n != V16_N_TOTAL:
    baseline_ok = False; baseline_reasons.append(f"toplam fair {total_n}/{V16_N_TOTAL}")
for s_exp, n_exp in V16_N_PER_SEASON.items():
    n_act = per_season_n_fair.get(s_exp, -1)
    if n_act != n_exp:
        baseline_ok = False; baseline_reasons.append(f"{s_exp}: n_fair={n_act} beklenen={n_exp}")

print("\n  Per-sezon RF_v16 LL vs v1.6 (tolerans 0.0005):")
for row in per_model_rows["RF_v16"]:
    s = row["season"]; v16 = V16_RF_LL_PER_SEASON.get(s)
    if v16 is None:
        baseline_ok = False; baseline_reasons.append(f"{s}: v1.6 ref yok"); continue
    diff = abs(row["ll_raw"] - v16); ok = diff < BASELINE_TOL
    if not ok:
        baseline_ok = False; baseline_reasons.append(f"{s}: LL Δ={diff:.4f}")
    print(f"    {s}: LL={row['ll_raw']:.4f} v1.6={v16:.4f} Δ={diff:.4f} "
          f"[{'OK' if ok else 'FARK'}]")

YF_v16_all = np.concatenate(per_model_Y_fair["RF_v16"])
PF_v16_all = np.vstack(per_model_P_fair["RF_v16"])
ll_v16_agg = log_loss_aligned(YF_v16_all, PF_v16_all)
br_v16_agg = brier_multiclass(YF_v16_all, PF_v16_all)
d_ll = abs(ll_v16_agg - V16_RF_LL_AGG); d_br = abs(br_v16_agg - V16_RF_BR_AGG)
if d_ll >= BASELINE_TOL:
    baseline_ok = False; baseline_reasons.append(f"agg LL Δ={d_ll:.4f}")
if d_br >= BASELINE_TOL:
    baseline_ok = False; baseline_reasons.append(f"agg Brier Δ={d_br:.4f}")
print(f"\n  Aggregate RF_v16: LL={ll_v16_agg:.4f} (v1.6={V16_RF_LL_AGG:.4f}, Δ={d_ll:.4f})")
print(f"                    Br={br_v16_agg:.4f} (v1.6={V16_RF_BR_AGG:.4f}, Δ={d_br:.4f})")

if not baseline_ok:
    print("\n  >>> !!! BASELINE FAIL")
    for r in baseline_reasons: print(f"      - {r}")
    print("      Ana başarı kararı VERİLMEZ.")
    raise SystemExit(0)
print("\n  >>> BASELINE: PASS")

# --- ANA KARAR ---
print("\n" + "=" * 60)
print("=== ANA KARAR (RF_v22 vs RF_v16) ===")
print("=" * 60)

rf16_by_season = {r["season"]: r["ll_raw"] for r in per_model_rows["RF_v16"]}
rf22_by_season = {r["season"]: r["ll_raw"] for r in per_model_rows["RF_v22"]}

YF_v22_all = np.concatenate(per_model_Y_fair["RF_v22"])
PF_v22_all = np.vstack(per_model_P_fair["RF_v22"])
ll_v22_agg = log_loss_aligned(YF_v22_all, PF_v22_all)
br_v22_agg = brier_multiclass(YF_v22_all, PF_v22_all)

print(f"\n  AGGREGATE (n={len(YF_v22_all)}):")
print(f"    RF_v16 : LL={ll_v16_agg:.4f}  Brier={br_v16_agg:.4f}")
print(f"    RF_v22 : LL={ll_v22_agg:.4f}  Brier={br_v22_agg:.4f}")
print(f"    Δ      : LL={ll_v22_agg-ll_v16_agg:+.5f}  Brier={br_v22_agg-br_v16_agg:+.5f}")

k1 = ll_v22_agg <= THRESH_LL
print(f"\n  K1  RF_v22 LL    ≤ {THRESH_LL:.4f}: {ll_v22_agg:.4f}  "
      f"{'PASS' if k1 else 'FAIL'} (fark {ll_v22_agg-THRESH_LL:+.4f})")
k2 = br_v22_agg <= THRESH_BRIER
print(f"  K2  RF_v22 Brier ≤ {THRESH_BRIER:.4f}: {br_v22_agg:.4f}  "
      f"{'PASS' if k2 else 'FAIL'} (fark {br_v22_agg-THRESH_BRIER:+.4f})")

print(f"\n  K3  Per-sezon RF_v22 LL < RF_v16 (≥{MIN_IMPROVE}/10):")
n_improve = 0; borderline = 0
for s in common_seasons:
    ll16 = rf16_by_season[s]; ll22 = rf22_by_season[s]; delta = ll22 - ll16
    improved = delta < 0; is_bl = abs(delta) < BORDERLINE
    if improved: n_improve += 1
    if is_bl: borderline += 1
    tag = " (İYİLEŞTİ-sınır)" if (is_bl and improved) else \
          (" (kötüleşti-sınır)" if is_bl else "")
    print(f"    {s}  v16={ll16:.4f}  v22={ll22:.4f}  Δ={delta:+.5f}  "
          f"{'İYİLEŞTİ' if improved else 'kötüleşti'}{tag}")
k3 = n_improve >= MIN_IMPROVE
print(f"  Toplam: {n_improve}/10  {'PASS' if k3 else 'FAIL'}")
if borderline > 0:
    print(f"  NOT: {borderline} sezonda |Δ| < {BORDERLINE} — sayıma DAHİL, sınır etiketli.")

ana = k1 and k2 and k3
print(f"\n>>> ANA BAŞARI: {'PASS' if ana else 'FAIL'} ({sum([k1,k2,k3])}/3 kriter)")
print(f"    → {'v2.2 ANA MODEL, v1.6 arşive' if ana else 'v1.6 BASELINE KORUNUR, v2.2 arşive'}")

# CSV
all_rows = []
for name, rows in per_model_rows.items():
    for r in rows:
        all_rows.append({
            "model": name, "season": r["season"], "n_fair": r["n_fair"],
            "ll_fair_full": r["ll_raw"], "brier_fair_full": r["br_raw"],
            "acc_fair_full": r["acc_raw"],
        })
pd.DataFrame(all_rows).to_csv(OUT_DIR / "walkforward_v2_2.csv", index=False)
print(f"\nwalkforward_v2_2.csv yazıldı")