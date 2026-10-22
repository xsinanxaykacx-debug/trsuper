# -*- coding: utf-8 -*-
# analyze_v16_errors.py — v1.6 hata analizi (v2, metodoloji düzeltmeli)
# ============================================================
# v2 düzeltmeleri:
#   - Analiz B: LL + Brier + accuracy ÜÇÜ birlikte
#   - Segment analizi: "KEŞİF AMAÇLI" başlığı + çoklu karşılaştırma uyarısı
#   - n<100 segmentler [küçük] etiketli
# ============================================================

from pathlib import Path
from collections import deque, defaultdict
import re
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import log_loss as sklearn_log_loss

DATA    = Path(r"C:\Users\bzdye\Downloads\trsuper\data\csv\DATA.csv")
OUT_DIR = DATA.parents[2]
CLASSES = ["H", "D", "A"]
_CLASSES_LEX = sorted(CLASSES)
_COLS_TO_LEX = [CLASSES.index(c) for c in _CLASSES_LEX]

def log_loss_aligned(y_true, p):
    return sklearn_log_loss(y_true, p[:, _COLS_TO_LEX], labels=_CLASSES_LEX)

def brier_multiclass(y_true, p):
    y_true = np.asarray(y_true); p = np.asarray(p)
    return float(sum(np.mean((p[:, j] - (y_true == c).astype(float)) ** 2)
                     for j, c in enumerate(CLASSES)))

def parse_season(s):
    m = re.search(r"(\d{4})/(\d{4})", str(s));  return f"{m.group(1)}/{m.group(2)}" if m else None
def parse_league(s):
    s = str(s)
    if "Süper" in s:  return "Süper Lig"
    if re.search(r"1\.\s*Lig", s): return "1. Lig"
    return "Other"
def season_start(s):
    m = re.match(r"(\d{4})/", str(s));  return int(m.group(1)) if m else None

def implied_probs(oh, od, oa):
    o = np.array([oh, od, oa], dtype=float)
    if np.any(~np.isfinite(o)) or np.any(o <= 1.0): return None
    inv = 1.0 / o; return inv / inv.sum()

# --- load ---
df = pd.read_csv(DATA, encoding="utf-8-sig", sep=",", low_memory=False)
df["date"] = pd.to_datetime(df["Tarih"], format="%d-%m-%Y", errors="coerce")
df = df.dropna(subset=["date"]).copy()
df["season"] = df["Lig/Sezon"].apply(parse_season)
df["league"] = df["Lig/Sezon"].apply(parse_league)
df = df.dropna(subset=["season"]).copy()
df = df[df["league"].isin(["Süper Lig", "1. Lig"])].copy()
df["y"] = df["MS"].map({"1":"H","X":"D","2":"A"})
df = df.dropna(subset=["y"]).copy()
for src, dst in [("Maç_Sonucu_|_1","odd_H"),("Maç_Sonucu_|_X","odd_D"),("Maç_Sonucu_|_2","odd_A")]:
    df[dst] = pd.to_numeric(df[src].astype(str).str.replace(",",".",regex=False).str.strip(), errors="coerce")
for col in ["MSE","MSD"]:
    df[col] = pd.to_numeric(df[col].astype(str).str.replace(",",".",regex=False).str.strip(), errors="coerce")
df = df.sort_values(["date","Maç_ID"]).reset_index(drop=True)
print(f"Toplam: {len(df)} maç | sezon={df['season'].nunique()}\n")

# --- features ---
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
        sm_h = season_matches.get((L, h, season), 0); sm_a = season_matches.get((L, a, season), 0)
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
        sh = {"H":1.0,"D":0.5,"A":0.0}[r["y"]]
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
        if (L, season) not in season_start_dt: season_start_dt[(L, season)] = d

feat = pd.DataFrame(feat_rows)

FEATURES = [
    "elo_h","elo_a","elo_diff",
    "form_h_pts_5","form_h_gf_5","form_h_ga_5",
    "form_a_pts_5","form_a_gf_5","form_a_ga_5",
    "form_h_pts_10","form_h_gf_10","form_h_ga_10",
    "form_a_pts_10","form_a_gf_10","form_a_ga_10",
    "form_h_home_pts","form_h_home_gf","form_h_home_ga",
    "form_a_away_pts","form_a_away_gf","form_a_away_ga",
    "opp_elo_h","opp_elo_a","rest_h","rest_a",
    "h2h_current_home_team_win_share",
    "league_home_win_share","league_draw_share","is_super_lig",
    "season_match_h","season_match_a","days_since_season_start",
    "has_history_h","has_history_a",
]

season_start_map = {s: season_start(s) for s in feat["season"].dropna().unique()}
seasons = [s for s,_ in sorted(season_start_map.items(), key=lambda kv: kv[1])]
test_seasons = seasons[3:]

def fit_rf(X, y):
    m = RandomForestClassifier(n_estimators=300, max_depth=8,
                               min_samples_leaf=20, random_state=42, n_jobs=-1)
    m.fit(X, y); return m

def predict_rf(m, X):
    p = m.predict_proba(X)
    cls = list(m.classes_)
    return p[:, [cls.index(c) for c in CLASSES]]

# --- walk-forward: per-match tahmin kaydı ---
records = []
for s in test_seasons:
    s_start = season_start_map[s]
    train_df = feat[feat["season"].map(season_start_map) < s_start].copy()
    test_full = feat[feat["season"] == s].reset_index(drop=True)
    if len(train_df) < 200 or len(test_full) < 20: continue
    valid = test_full.apply(
        lambda r: implied_probs(r["odd_H"], r["odd_D"], r["odd_A"]) is not None, axis=1)
    test_fair = test_full[valid].reset_index(drop=True)
    if len(test_fair) == 0: continue

    med = train_df[FEATURES].median()
    rf = fit_rf(train_df[FEATURES].fillna(med).values, train_df["y"].values)
    p_rf = predict_rf(rf, test_fair[FEATURES].fillna(med).values)

    for i, r in test_fair.iterrows():
        p_mkt = implied_probs(r["odd_H"], r["odd_D"], r["odd_A"])
        records.append({
            "match_id": r["match_id"], "season": s, "league": r["league"],
            "date": r["date"], "home": r["home"], "away": r["away"],
            "y": r["y"],
            "odd_H": r["odd_H"], "odd_D": r["odd_D"], "odd_A": r["odd_A"],
            "p_rf_H": p_rf[i,0], "p_rf_D": p_rf[i,1], "p_rf_A": p_rf[i,2],
            "p_mkt_H": p_mkt[0], "p_mkt_D": p_mkt[1], "p_mkt_A": p_mkt[2],
        })

pred = pd.DataFrame(records)
pred.to_csv(OUT_DIR / "v16_per_match_predictions.csv", index=False)
print(f"v16_per_match_predictions.csv: {len(pred)} maç × {len(pred.columns)} sütun")
print(f"  Toplam LL (RF) : {log_loss_aligned(pred['y'].values, pred[['p_rf_H','p_rf_D','p_rf_A']].values):.4f}")
print(f"  Toplam LL (MKT): {log_loss_aligned(pred['y'].values, pred[['p_mkt_H','p_mkt_D','p_mkt_A']].values):.4f}")
print()

y_arr     = pred["y"].values
p_rf_arr  = pred[["p_rf_H","p_rf_D","p_rf_A"]].values
p_mkt_arr = pred[["p_mkt_H","p_mkt_D","p_mkt_A"]].values
y_idx     = np.array([CLASSES.index(v) for v in y_arr])

pred["odds_min"]      = pred[["odd_H","odd_D","odd_A"]].min(axis=1)
pred["fav_band"]      = pd.cut(pred["odds_min"],
                               bins=[0, 1.5, 2.0, 2.5, 3.0, 4.0, 100],
                               labels=["1.0-1.5","1.5-2.0","2.0-2.5","2.5-3.0","3.0-4.0","4.0+"])
pred["p_draw_mkt"]    = pred["p_mkt_D"]
pred["draw_band"]     = pd.cut(pred["p_draw_mkt"],
                               bins=[0, 0.20, 0.25, 0.30, 0.35, 1.0],
                               labels=["<0.20","0.20-0.25","0.25-0.30","0.30-0.35","0.35+"])
pred["season_phase"]  = pred.groupby("season")["date"].transform(
    lambda d: pd.qcut(d.rank(method="first"), q=3, labels=["early","mid","late"]))

# ============================================================
# ANALİZ A: Kalibrasyon
# ============================================================
print("=" * 74)
print("ANALİZ A: Kalibrasyon — lig × favori oran bandı")
print("=" * 74)
print("  Her segment için: n, RF_LL, MKT_LL, Δ(MKT-RF), RF_acc")
print(f"  {'segment':30s} {'n':>5s} {'RF_LL':>8s} {'MKT_LL':>8s} {'Δ':>8s} {'RF_acc':>8s}")

for league in ["Süper Lig", "1. Lig"]:
    for band in pred["fav_band"].cat.categories:
        m = (pred["league"] == league) & (pred["fav_band"] == band)
        n = int(m.sum())
        if n < 30: continue
        y_seg = y_arr[m.values]; p_rf_seg = p_rf_arr[m.values]; p_mkt_seg = p_mkt_arr[m.values]
        ll_rf  = log_loss_aligned(y_seg, p_rf_seg)
        ll_mkt = log_loss_aligned(y_seg, p_mkt_seg)
        acc_rf = float((np.array(CLASSES)[p_rf_seg.argmax(1)] == y_seg).mean())
        print(f"  {league:10s} | {str(band):15s} {n:5d} {ll_rf:8.4f} {ll_mkt:8.4f} "
              f"{ll_mkt-ll_rf:+8.4f} {acc_rf:8.4f}")

# ============================================================
# ANALİZ B: RF vs Market ayrışması (ÜÇ METRİK)
# ============================================================
print("\n" + "=" * 74)
print("ANALİZ B: RF vs Market ayrışması")
print("=" * 74)
print("  NOT: Accuracy tek başına olasılık kalitesini ölçmez.")
print("       LL ve Brier ile birlikte yorumlanmalı.")
print()

rf_top = p_rf_arr.argmax(axis=1)
mkt_top = p_mkt_arr.argmax(axis=1)
agree = rf_top == mkt_top
print(f"  Toplam maç: {len(pred)}")
print(f"  RF ve MKT aynı sınıfı seçti: {agree.sum()} ({100*agree.mean():.1f}%)")
print(f"  Farklı sınıf: {(~agree).sum()} ({100*(~agree).mean():.1f}%)")

def three_metrics(y, p_rf, p_mkt, label=""):
    ll_rf  = log_loss_aligned(y, p_rf)
    ll_mkt = log_loss_aligned(y, p_mkt)
    br_rf  = brier_multiclass(y, p_rf)
    br_mkt = brier_multiclass(y, p_mkt)
    acc_rf = float((np.array(CLASSES)[p_rf.argmax(1)] == y).mean())
    acc_mkt = float((np.array(CLASSES)[p_mkt.argmax(1)] == y).mean())
    print(f"  {label}")
    print(f"    {'':10s} {'RF':>10s} {'MKT':>10s} {'Δ(MKT-RF)':>12s}")
    print(f"    {'LogLoss':10s} {ll_rf:10.4f} {ll_mkt:10.4f} {ll_mkt-ll_rf:+12.4f}")
    print(f"    {'Brier':10s} {br_rf:10.4f} {br_mkt:10.4f} {br_mkt-br_rf:+12.4f}")
    print(f"    {'Accuracy':10s} {acc_rf:10.4f} {acc_mkt:10.4f} {acc_mkt-acc_rf:+12.4f}")

disagree = ~agree
if disagree.sum() > 0:
    three_metrics(y_arr[disagree], p_rf_arr[disagree], p_mkt_arr[disagree],
                  label=f"\n  Ayrışan altküme (n={disagree.sum()}):")
    print(f"    Yorum: LL ve Brier'e bak — accuracy'ye tek başına güvenme.")

max_diff = np.abs(p_rf_arr - p_mkt_arr).max(axis=1)
pred["max_diff"] = max_diff
print(f"\n  Ayrışma büyüklüğüne göre (üç metrik):")
print(f"    {'eşik':12s} {'n':>5s} {'RF_LL':>8s} {'MKT_LL':>8s} "
      f"{'RF_Brier':>10s} {'MKT_Brier':>10s} {'RF_acc':>8s} {'MKT_acc':>8s}")
for th in [0.05, 0.10, 0.15, 0.20]:
    m = max_diff > th
    if m.sum() < 30: continue
    y_m = y_arr[m]; p_rf_m = p_rf_arr[m]; p_mkt_m = p_mkt_arr[m]
    ll_rf = log_loss_aligned(y_m, p_rf_m); ll_mkt = log_loss_aligned(y_m, p_mkt_m)
    br_rf = brier_multiclass(y_m, p_rf_m); br_mkt = brier_multiclass(y_m, p_mkt_m)
    acc_rf = float((np.array(CLASSES)[p_rf_m.argmax(1)] == y_m).mean())
    acc_mkt = float((np.array(CLASSES)[p_mkt_m.argmax(1)] == y_m).mean())
    print(f"    |Δp|>{th:.2f}   {m.sum():5d} {ll_rf:8.4f} {ll_mkt:8.4f} "
          f"{br_rf:10.4f} {br_mkt:10.4f} {acc_rf:8.4f} {acc_mkt:8.4f}")

# ============================================================
# ANALİZ C: Yüksek güvenli yanlış tahminler
# ============================================================
print("\n" + "=" * 74)
print("ANALİZ C: Yüksek güvenli yanlış tahminler (RF_top_prob > 0.6, yanlış)")
print("=" * 74)
rf_top_prob = p_rf_arr.max(axis=1)
rf_correct = (rf_top == y_idx)
high_conf_err = (rf_top_prob > 0.6) & (~rf_correct)
print(f"  Toplam: {high_conf_err.sum()} / {len(pred)} ({100*high_conf_err.mean():.1f}%)")

if high_conf_err.sum() > 0:
    mkt_correct_on_err = (mkt_top[high_conf_err] == y_idx[high_conf_err])
    print(f"  Market bu maçlarda doğru mu?")
    print(f"    MKT doğru: {mkt_correct_on_err.sum()} / {high_conf_err.sum()} "
          f"({100*mkt_correct_on_err.mean():.1f}%)")
    print(f"    MKT yanlış: {(~mkt_correct_on_err).sum()} / {high_conf_err.sum()} "
          f"({100*(~mkt_correct_on_err).mean():.1f}%)")

    print(f"\n  RF yanlış yüksek güvenli tahmin dağılımı (RF'nin seçtiği sınıf):")
    for c in CLASSES:
        c_idx = CLASSES.index(c)
        m = high_conf_err & (rf_top == c_idx)
        if m.sum() > 0:
            print(f"    RF→{c}: n={m.sum()}")

    md_err = max_diff[high_conf_err]
    md_ok  = max_diff[rf_correct]
    print(f"\n  Ayrışma |Δp| (max):")
    print(f"    Yüksek güvenli YANLIŞ: mean={md_err.mean():.3f}  median={np.median(md_err):.3f}")
    print(f"    Doğru:                mean={md_ok.mean():.3f}   median={np.median(md_ok):.3f}")

# ============================================================
# ANALİZ D: Segment bazlı LL (KEŞİF AMAÇLI)
# ============================================================
print("\n" + "=" * 74)
print("ANALİZ D: Segment bazlı LL — KEŞİF AMAÇLI")
print("=" * 74)
print("  !!! UYARI: Bu tablo çoklu karşılaştırma içerir (çok sayıda segment).")
print("      FDR/Bonferroni düzeltmesi YAPILMADI. Bu sonuçlar YENİ ÖZELLİK")
print("      EKLEMEK İÇİN KANIT DEĞİL, sonraki deney için HİPOTEZ ÜRETME")
print("      aracıdır. Tesadüfi iyi/kötü segmentler olabilir.")
print()

def segment_report(pred, seg_col, seg_label, min_n=30):
    print(f"  --- {seg_label} ---")
    print(f"  {'segment':20s} {'n':>5s} {'RF_LL':>8s} {'MKT_LL':>8s} {'Δ':>8s} {'flag':>6s}")
    for val in pred[seg_col].dropna().unique():
        m = pred[seg_col] == val
        n = int(m.sum())
        if n < min_n: continue
        y_seg = y_arr[m.values]; p_rf_seg = p_rf_arr[m.values]; p_mkt_seg = p_mkt_arr[m.values]
        ll_rf  = log_loss_aligned(y_seg, p_rf_seg)
        ll_mkt = log_loss_aligned(y_seg, p_mkt_seg)
        flag = "[küçük]" if n < 100 else ""
        print(f"  {str(val):20s} {n:5d} {ll_rf:8.4f} {ll_mkt:8.4f} "
              f"{ll_mkt-ll_rf:+8.4f} {flag:>6s}")

segment_report(pred, "league", "Lig")
segment_report(pred, "season", "Sezon")
segment_report(pred, "fav_band", "Favori oran bandı")
segment_report(pred, "draw_band", "Beraberlik olasılığı bandı (MKT)")
segment_report(pred, "season_phase", "Sezon fazı")

print("\n" + "=" * 74)
print("ÖZET: En yüksek RF kaybı olan segmentler (MKT - RF LL)")
print("       (keşif amaçlı; FDR düzeltmesi YOK)")
print("=" * 74)

def collect_segments(pred, seg_col, label):
    out = []
    for val in pred[seg_col].dropna().unique():
        m = pred[seg_col] == val
        n = int(m.sum())
        if n < 50: continue
        y_seg = y_arr[m.values]; p_rf_seg = p_rf_arr[m.values]; p_mkt_seg = p_mkt_arr[m.values]
        ll_rf  = log_loss_aligned(y_seg, p_rf_seg)
        ll_mkt = log_loss_aligned(y_seg, p_mkt_seg)
        out.append({"segment_type": label, "segment": str(val), "n": n,
                    "rf_ll": round(ll_rf,4), "mkt_ll": round(ll_mkt,4),
                    "gap": round(ll_mkt - ll_rf, 4),
                    "small_sample": n < 100})
    return out

rows = []
rows += collect_segments(pred, "league", "lig")
rows += collect_segments(pred, "fav_band", "fav_band")
rows += collect_segments(pred, "draw_band", "draw_band")
rows += collect_segments(pred, "season_phase", "sezon_fazı")
seg_df = pd.DataFrame(rows).sort_values("gap", ascending=False)
print(seg_df.head(15).to_string(index=False))
seg_df.to_csv(OUT_DIR / "v16_error_segments.csv", index=False)
print(f"\nv16_error_segments.csv yazıldı")
print(f"v16_per_match_predictions.csv yazıldı (kalıcı)")

print("\n" + "=" * 74)
print("SONRAKİ ADIM NOTU")
print("=" * 74)
print("  Bu analizden çıkacak 'en yüksek gap' segmentleri HİPOTEZ olarak")
print("  kullanılacak. Yeni bir feature veya model, AYNI walk-forward protokolünde")
print("  ve ÖNCEDEN belirlenmiş kriterlerle test edilecek. Bu tablodaki bir")
print("  segmentin kötü çıkması, o segment için özel bir çözümün işe yarayacağını")
print("  KANITLAMAZ — sadece araştırmaya değer olduğunu gösterir.")