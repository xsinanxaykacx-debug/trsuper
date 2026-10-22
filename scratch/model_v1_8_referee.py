# -*- coding: utf-8 -*-
# model_v1_8_referee.py — v1.6 + referee_home_win_rate_prior (tek feature deneyi)
# ============================================================
# v1.6 → v1.8:
#   + referee_home_win_rate_prior (Laplace shrunk, lig home-win prior)
#   Stadyum feature'ı YOK (v1.7 başarısız sayıldı, ana modele girmedi).
# Karar ölçütü (v1.7 ile aynı, önceden sabit):
#   RF LL ≤ 1.0237, RF Brier ≤ 0.6124, RF-Market farkı 10 sezonda ≥6'da küçülmüş
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
    print("!!! KRİTİK: alignment check BAŞARISIZ. Kod duruyor.")
    raise SystemExit(1)
print("  status: PASS\n")

# ============================================================
# 1) Yükle
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
    df[dst] = pd.to_numeric(
        df[src].astype(str).str.replace(",", ".", regex=False).str.strip(),
        errors="coerce",
    )

for col in ["MSE", "MSD"]:
    df[col] = pd.to_numeric(
        df[col].astype(str).str.replace(",", ".", regex=False).str.strip(),
        errors="coerce",
    )
valid_scores = (
    df["MSE"].notna() & df["MSD"].notna()
    & np.isfinite(df["MSE"]) & np.isfinite(df["MSD"])
    & (df["MSE"] >= 0) & (df["MSD"] >= 0)
    & (df["MSE"] % 1 == 0) & (df["MSD"] % 1 == 0)
)
print(f"Skor validasyonu: geçerli={int(valid_scores.sum())}, "
      f"geçersiz/eksik={int((~valid_scores).sum())}")

df = df.sort_values(["date","Maç_ID"]).reset_index(drop=True)
print(f"Toplam: {len(df)} maç | "
      f"{df['date'].min().date()} → {df['date'].max().date()} | "
      f"sezon={df['season'].nunique()} | "
      f"lig={df['league'].value_counts().to_dict()}")
print(f"lightgbm: {'var' if HAS_LGBM else 'YOK'}  |  "
      f"xgboost: {'var' if HAS_XGB else 'YOK'}\n")

# ============================================================
# 2) Feature engineering (atomik gün bazlı)
# ============================================================
K_ELO = 20.0
elo = {}; recent_all = defaultdict(lambda: deque(maxlen=10))
recent_home = defaultdict(lambda: deque(maxlen=10))
recent_away = defaultdict(lambda: deque(maxlen=10))
opp_elo_recent = defaultdict(lambda: deque(maxlen=5))
last_dt = {}; h2h = defaultdict(lambda: deque(maxlen=10))
league_recent = defaultdict(lambda: deque(maxlen=500))
season_matches = defaultdict(int); season_start_dt = {}

referee_home_wins = defaultdict(int)   # (L, referee) -> int
referee_matches   = defaultdict(int)   # (L, referee) -> int
REFEREE_ALPHA     = 20.0

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

    # ---------- FAZ 1 ----------
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

        hk = (L, tuple(sorted([h, a])))
        q_h2h = list(h2h[hk])
        h2h_share = (sum(1 for w in q_h2h if w == h) / len(q_h2h)) if q_h2h else np.nan

        q_lg = list(league_recent[L])
        lg_home = sum(1 for w in q_lg if w == "H") / len(q_lg) if q_lg else 0.45
        lg_draw = sum(1 for w in q_lg if w == "D") / len(q_lg) if q_lg else 0.26

        sm_h = season_matches.get((L, h, season), 0)
        sm_a = season_matches.get((L, a, season), 0)
        s_first = season_start_dt.get((L, season))
        days_season = (d - s_first).days if s_first else 0

        referee = str(r["Hakem"]) if pd.notna(r["Hakem"]) else "Unknown"
        rw = referee_home_wins.get((L, referee), 0)
        rm = referee_matches.get((L, referee), 0)
        referee_win_rate = (rw + REFEREE_ALPHA * lg_home) / (rm + REFEREE_ALPHA)

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
            "referee_home_win_rate_prior": referee_win_rate,
        })

    # ---------- FAZ 2a: Elo deltaları ----------
    deltas = defaultdict(float)
    for r in recs:
        L, h, a = r["league"], r["Ev_Sahibi"], r["Deplasman"]
        e_h = elo.get((L, h), 1500.0); e_a = elo.get((L, a), 1500.0)
        sh = {"H": 1.0, "D": 0.5, "A": 0.0}[r["y"]]
        e_h_exp = 1.0 / (1.0 + 10 ** ((e_a - e_h) / 400.0))
        dl = K_ELO * (sh - e_h_exp)
        deltas[(L, h)] += dl; deltas[(L, a)] -= dl

    # ---------- FAZ 2b: uygula ----------
    for (L, t), dl in deltas.items():
        elo[(L, t)] = elo.get((L, t), 1500.0) + dl

    # ---------- FAZ 2c: güncellemeler ----------
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

        referee_upd = str(r["Hakem"]) if pd.notna(r["Hakem"]) else "Unknown"
        referee_home_wins[(L, referee_upd)] += 1 if r["y"] == "H" else 0
        referee_matches[(L, referee_upd)] += 1

feat = pd.DataFrame(feat_rows)
feat.to_csv(OUT_DIR / "features_v1_8.csv", index=False)
print(f"features_v1_8.csv yazıldı: {len(feat)} satır × {len(feat.columns)} sütun")

print("\n=== FEATURE SANITY CHECK ===")
h2h_col = "h2h_current_home_team_win_share"
print(f"  {h2h_col}: dolu={feat[h2h_col].notna().sum()}, "
      f"ortalama={feat[h2h_col].dropna().mean():.4f}")
print(f"  opp_elo_h ortalama: {feat['opp_elo_h'].mean():.2f}")
print(f"  opp_elo_a ortalama: {feat['opp_elo_a'].mean():.2f}")
print(f"  referee_home_win_rate_prior: "
      f"dolu={feat['referee_home_win_rate_prior'].notna().sum()}, "
      f"mean={feat['referee_home_win_rate_prior'].mean():.4f}, "
      f"min={feat['referee_home_win_rate_prior'].min():.4f}, "
      f"max={feat['referee_home_win_rate_prior'].max():.4f}")

# ============================================================
# 3) Walk-forward
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
    "referee_home_win_rate_prior",
]

season_start_map = {s: season_start(s) for s in feat["season"].dropna().unique()}
seasons = [s for s, _ in sorted(season_start_map.items(), key=lambda kv: kv[1])]
WARMUP = 3
test_seasons = seasons[WARMUP:]

MODEL_SPECS = [
    ("LR",  lambda: LogisticRegression(max_iter=2000, solver="lbfgs"), True, False, False),
    ("RF",  lambda: RandomForestClassifier(n_estimators=300, max_depth=8,
                                            min_samples_leaf=20,
                                            random_state=42, n_jobs=-1), False, False, False),
]
if HAS_LGBM:
    MODEL_SPECS.append(("LGBM", lambda: lgb.LGBMClassifier(
        n_estimators=300, max_depth=6, learning_rate=0.05, num_leaves=31,
        random_state=42, verbose=-1), False, True, False))
if HAS_XGB:
    MODEL_SPECS.append(("XGB", lambda: xgb.XGBClassifier(
        n_estimators=300, max_depth=6, learning_rate=0.05,
        random_state=42, eval_metric="mlogloss", verbosity=0), False, True, True))

def fit_predict(factory, needs_scale, allow_nan, use_label_encoder,
                X_tr_raw, X_te_raw, y_tr, med):
    if allow_nan:
        X_tr, X_te = X_tr_raw.values, X_te_raw.values
    else:
        X_tr = X_tr_raw.fillna(med).values
        X_te = X_te_raw.fillna(med).values
    if needs_scale:
        sc = StandardScaler().fit(X_tr)
        X_tr = sc.transform(X_tr); X_te = sc.transform(X_te)
    m = factory()
    if use_label_encoder:
        le = LabelEncoder(); y_tr_enc = le.fit_transform(y_tr)
        m.fit(X_tr, y_tr_enc)
        p_raw = m.predict_proba(X_te)
        out = np.zeros((len(p_raw), len(CLASSES)))
        for col_i, cls_val in enumerate(list(m.classes_)):
            orig = le.inverse_transform([int(cls_val)])[0]
            out[:, CLASSES.index(orig)] = p_raw[:, col_i]
        s = out.sum(axis=1, keepdims=True); s[s == 0] = 1.0
        return out / s
    else:
        m.fit(X_tr, y_tr)
        p_raw = m.predict_proba(X_te)
        cls = list(m.classes_)
        return p_raw[:, [cls.index(c) for c in CLASSES]]

model_names = [s[0] for s in MODEL_SPECS]
per_model_results  = {n: [] for n in model_names}
per_model_Y_fair   = {n: [] for n in model_names}
per_model_P_fair   = {n: [] for n in model_names}
per_model_fair_seasons = {n: [] for n in model_names}
failures = []

for s in test_seasons:
    s_start = season_start_map[s]
    train_df  = feat[feat["season"].map(season_start_map) < s_start].copy()
    test_full = feat[feat["season"] == s].reset_index(drop=True)
    if len(train_df) < 200 or len(test_full) < 20:
        print(f"  skip {s}: train={len(train_df)} test={len(test_full)}"); continue

    valid_mask = test_full.apply(
        lambda r: implied_probs(r["odd_H"], r["odd_D"], r["odd_A"]) is not None, axis=1)
    test_fair = test_full[valid_mask].reset_index(drop=True)

    med = train_df[FEATURES].median()
    X_tr = train_df[FEATURES].copy()
    X_te_full = test_full[FEATURES].copy()
    X_te_fair = test_fair[FEATURES].copy()

    y_tr = train_df["y"].values; y_full = test_full["y"].values; y_fair = test_fair["y"].values

    if len(test_fair) > 0:
        P_mkt = np.vstack([implied_probs(r["odd_H"], r["odd_D"], r["odd_A"])
                           for r in test_fair.to_dict("records")])
        p_freq = np.array([(train_df["y"] == c).mean() for c in CLASSES])
        P_freq = np.tile(p_freq, (len(test_fair), 1))
        ll_freq = log_loss_aligned(y_fair, P_freq)
        ll_mkt  = log_loss_aligned(y_fair, P_mkt)
        br_mkt  = brier_multiclass(y_fair, P_mkt)
        acc_mkt = float((np.array(CLASSES)[P_mkt.argmax(axis=1)] == y_fair).mean())
    else:
        P_mkt = None; ll_freq = ll_mkt = br_mkt = acc_mkt = None

    for name, factory, needs_scale, allow_nan, use_le in MODEL_SPECS:
        try:
            p_full = fit_predict(factory, needs_scale, allow_nan, use_le,
                                 X_tr, X_te_full, y_tr, med)
            p_fair = fit_predict(factory, needs_scale, allow_nan, use_le,
                                 X_tr, X_te_fair, y_tr, med) if len(test_fair) > 0 else None

            assert p_full.shape == (len(test_full), 3), \
                f"{name}: p_full şekli hatalı {p_full.shape}"
            assert np.isfinite(p_full).all(), f"{name}: p_full NaN/sonsuz"
            assert (p_full >= 0).all(), f"{name}: p_full negatif"
            assert np.allclose(p_full.sum(axis=1), 1.0, atol=1e-6), \
                f"{name}: p_full satır toplamı 1 değil"

            if p_fair is not None:
                assert p_fair.shape == (len(test_fair), 3), \
                    f"{name}: p_fair şekli hatalı {p_fair.shape}"
                assert np.isfinite(p_fair).all(), f"{name}: p_fair NaN/sonsuz"
                assert (p_fair >= 0).all(), f"{name}: p_fair negatif"
                assert np.allclose(p_fair.sum(axis=1), 1.0, atol=1e-6), \
                    f"{name}: p_fair satır toplamı 1 değil"
        except Exception as e:
            failures.append((s, name, str(e)))
            print(f"  FAIL {s} | {name} | {e}")
            continue

        row = {
            "season": s, "model": name,
            "n_train": len(train_df),
            "n_test_full": len(test_full), "n_test_fair": len(test_fair),
            "model_ll_full":  round(log_loss_aligned(y_full, p_full), 4),
            "model_acc_full": round(accuracy_score(y_full,
                                    np.array(CLASSES)[p_full.argmax(axis=1)]), 4),
        }
        if p_fair is not None:
            row.update({
                "model_ll_fair": round(log_loss_aligned(y_fair, p_fair), 4),
                "model_brier_fair": round(brier_multiclass(y_fair, p_fair), 4),
                "model_acc_fair": round(
                    float((np.array(CLASSES)[p_fair.argmax(axis=1)] == y_fair).mean()), 4),
                "market_ll_fair": round(ll_mkt, 4),
                "market_brier_fair": round(br_mkt, 4),
                "market_acc_fair": round(acc_mkt, 4),
                "baseline_freq_ll_fair": round(ll_freq, 4),
            })
            per_model_Y_fair[name].append(y_fair)
            per_model_P_fair[name].append(p_fair)
            per_model_fair_seasons[name].append(s)
        per_model_results[name].append(row)

print("\n=== MODEL FAILURES ===")
if failures:
    for s, n, m in failures: print(f"  {s} | {n:6s} | {m}")
else:
    print("  Hiç hata yok")

fair_success_seasons = {
    n: {row["season"] for row in per_model_results[n]
        if pd.notna(row.get("model_ll_fair"))
        and pd.notna(row.get("model_brier_fair"))
        and row.get("n_test_fair", 0) > 0}
    for n in model_names
}
succeeded = [n for n in model_names if fair_success_seasons[n]]

if len(succeeded) >= 2:
    common = sorted(set.intersection(*[fair_success_seasons[n] for n in succeeded]))
    print(f"\nCommon fair seasons ({len(common)}): {common}")
else:
    common = []
    print("\nKarşılaştırma için yeterli fair değerlendirmesi yapan model yok")

if common:
    n_map = {}
    for n in succeeded:
        sub = pd.DataFrame(per_model_results[n])
        sub = sub[sub["season"].isin(common)]
        n_map[n] = sub.set_index("season")["n_test_fair"].to_dict()
    ref = succeeded[0]
    for n in succeeded[1:]:
        for s in common:
            assert n_map[ref][s] == n_map[n][s], \
                f"Aynı sezon farklı test sayısı: {s} {ref}={n_map[ref][s]} {n}={n_map[n][s]}"
    print("  n_test_fair eşitliği: PASS")

all_rows = []
for n in model_names: all_rows.extend(per_model_results[n])
res_long = pd.DataFrame(all_rows)

print("\n=== PER-SEZON LOG LOSS (fair) ===")
ll_piv = res_long.pivot(index="season", columns="model", values="model_ll_fair")
ll_piv["Market"]        = res_long.groupby("season")["market_ll_fair"].first()
ll_piv["Baseline_freq"] = res_long.groupby("season")["baseline_freq_ll_fair"].first()
print(ll_piv.round(4).to_string())

print("\n=== PER-SEZON BRIER (fair, standart multi-class toplam) ===")
br_piv = res_long.pivot(index="season", columns="model", values="model_brier_fair")
br_piv["Market"] = res_long.groupby("season")["market_brier_fair"].first()
print(br_piv.round(4).to_string())

if common:
    cm = res_long[res_long["season"].isin(common)]
    sub_first = cm[cm["model"] == succeeded[0]]
    n_total = int(sub_first["n_test_fair"].sum())

    print(f"\n=== AGGREGATE FAIR (ortak fair sezonlar, aynı {n_total} maç) ===")
    agg_rows = []
    for n in succeeded:
        sub = cm[cm["model"] == n]
        if len(sub) == 0: continue
        w = sub["n_test_fair"].values
        agg_rows.append({
            "model": n, "n": int(w.sum()),
            "log_loss": round(np.average(sub["model_ll_fair"].values, weights=w), 4),
            "brier":    round(np.average(sub["model_brier_fair"].values, weights=w), 4),
            "accuracy": round(np.average(sub["model_acc_fair"].values, weights=w), 4),
        })
    w = sub_first["n_test_fair"].values
    agg_rows.append({"model": "Market", "n": n_total,
        "log_loss": round(np.average(sub_first["market_ll_fair"].values, weights=w), 4),
        "brier":    round(np.average(sub_first["market_brier_fair"].values, weights=w), 4),
        "accuracy": round(np.average(sub_first["market_acc_fair"].values, weights=w), 4)})
    agg_rows.append({"model": "Baseline_freq", "n": n_total,
        "log_loss": round(np.average(sub_first["baseline_freq_ll_fair"].values, weights=w), 4),
        "brier": None, "accuracy": None})
    agg_rows.append({"model": "Uniform", "n": n_total,
                     "log_loss": round(LN3, 4), "brier": None, "accuracy": None})
    print(pd.DataFrame(agg_rows).to_string(index=False))

    print("\n=== PER-MODEL KALİBRASYON BIAS (fair, common sezonlar) ===")
    for n in succeeded:
        Ys, Ps = [], []
        for i, s in enumerate(per_model_fair_seasons[n]):
            if s in common:
                Ys.append(per_model_Y_fair[n][i])
                Ps.append(per_model_P_fair[n][i])
        if not Ys: continue
        YF_n = np.concatenate(Ys); PF_n = np.vstack(Ps)
        assert len(YF_n) == len(PF_n)
        bs = [PF_n[:, j].mean() - (YF_n == c).mean() for j, c in enumerate(CLASSES)]
        print(f"  {n:6s}  n={len(YF_n):5d}  "
              f"H_bias={bs[0]:+.4f}  D_bias={bs[1]:+.4f}  A_bias={bs[2]:+.4f}")

    cand = [a for a in agg_rows
            if a["model"] in succeeded and a["brier"] is not None]
    if cand:
        best = min(cand, key=lambda a: a["log_loss"])
        bname = best["model"]
        Ys, Ps = [], []
        for i, s in enumerate(per_model_fair_seasons[bname]):
            if s in common:
                Ys.append(per_model_Y_fair[bname][i])
                Ps.append(per_model_P_fair[bname][i])
        YF = np.concatenate(Ys); PF = np.vstack(Ps)
        print(f"\n=== SINIF BAZLI KALİBRASYON ({bname}, common sezonlar) ===")
        print(f"  n={len(YF)}")
        bins = np.array([0.0,0.05,0.10,0.15,0.20,0.25,0.30,0.35,0.40,
                         0.45,0.50,0.60,0.70,0.80,0.90,1.01])
        for j, c in enumerate(CLASSES):
            p_c = PF[:, j]; y_c = (YF == c).astype(int)
            print(f"\n--- Sınıf: {c} ---")
            for b in range(1, len(bins)):
                m = (p_c >= bins[b-1]) & (p_c < bins[b])
                if m.sum() < 30: continue
                print(f"  [{bins[b-1]:.2f},{bins[b]:.2f})  n={m.sum():5d}  "
                      f"mean_p={p_c[m].mean():.3f}  actual={y_c[m].mean():.3f}")

res_long.to_csv(OUT_DIR / "walkforward_v1_8.csv", index=False)
print(f"\nwalkforward_v1_8.csv yazıldı")