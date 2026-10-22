# model_v0.py — TAM SÜRÜM (v2)
# ============================================================
# Walk-forward baseline: Multinomial Logistic Regression
# Hedef: MS ∈ {1,X,2} → {H,D,A} 1X2 olasılıkları
#
# Bu dosyada:
#  - log_loss ALIGNMENT DÜZELTİLDİ (sklearn lexicographic varsayımı)
#  - Başlangıçta SANITY CHECK (sklearn vs manuel)
#  - Atomik günlük Elo güncellemesi
#  - Sezon sırası açık başlangıç yılına göre (season_start)
#  - Model vs piyasa AYNI fair satır kümesinde
#  - İki baseline: uniform ve eğitim sınıf dağılımı
#  - Max-prob kalibrasyonu ve SINIF BAZLI kalibrasyon
#  - Bahis simülasyonu YOK
# ============================================================

from pathlib import Path
from collections import deque, defaultdict
import re
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import log_loss as sklearn_log_loss, accuracy_score

DATA    = Path(r"C:\Users\bzdye\Downloads\trsuper\data\csv\DATA.csv")
OUT_DIR = DATA.parents[2]
CLASSES = ["H", "D", "A"]
LN3     = float(np.log(3.0))

# -------- log_loss alignment (H,D,A → lexicographic A,D,H) --------
_CLASSES_LEX = sorted(CLASSES)                          # ['A','D','H']
_COLS_TO_LEX = [CLASSES.index(c) for c in _CLASSES_LEX] # [2,1,0]

def log_loss_aligned(y_true, y_prob_hda):
    """y_prob_hda sütunları CLASSES=['H','D','A'] sırasındadır."""
    return sklearn_log_loss(
        y_true, y_prob_hda[:, _COLS_TO_LEX], labels=_CLASSES_LEX
    )

def manual_log_loss(y_true, y_prob_hda):
    idx = {c: i for i, c in enumerate(CLASSES)}
    losses = [-np.log(max(y_prob_hda[i, idx[yt]], 1e-15))
              for i, yt in enumerate(y_true)]
    return float(np.mean(losses))

# -------- sanity check --------
_sy = ["H", "D", "A", "H", "A"]
_sp = np.array([
    [0.50, 0.30, 0.20],
    [0.20, 0.40, 0.40],
    [0.20, 0.30, 0.50],
    [0.60, 0.20, 0.20],
    [0.25, 0.25, 0.50],
], dtype=float)
_expected = -np.mean([np.log(_sp[i, {"H":0,"D":1,"A":2}[_sy[i]]]) for i in range(5)])
_sk = log_loss_aligned(_sy, _sp)
_mn = manual_log_loss(_sy, _sp)
print("=== LOG_LOSS ALIGNMENT SANITY CHECK ===")
print(f"  sklearn (aligned): {_sk:.6f}")
print(f"  manual           : {_mn:.6f}")
print(f"  expected         : {_expected:.6f}")
if abs(_sk - _expected) > 1e-6 or abs(_mn - _expected) > 1e-6:
    print("!!! KRİTİK: alignment check BAŞARISIZ. Kod duruyor.")
    raise SystemExit(1)
print("  status: PASS\n")

# ============================================================
# 1) Yükle, tarih / sezon / lig / target
# ============================================================
df = pd.read_csv(DATA, encoding="utf-8-sig", sep=",", low_memory=False)
df["date"] = pd.to_datetime(df["Tarih"], format="%d-%m-%Y", errors="coerce")
df = df.dropna(subset=["date"]).copy()

def parse_season(s):
    m = re.search(r"(\d{4})/(\d{4})", str(s))
    return f"{m.group(1)}/{m.group(2)}" if m else None

def parse_league(s):
    s = str(s)
    if "Süper" in s:  return "Süper Lig"
    if "1. Lig" in s: return "1. Lig"
    return "Other"

def season_start(s):
    m = re.match(r"(\d{4})/", str(s))
    return int(m.group(1)) if m else None

df["season"] = df["Lig/Sezon"].apply(parse_season)
df["league"] = df["Lig/Sezon"].apply(parse_league)
df = df.dropna(subset=["season"]).copy()
df = df[df["league"].isin(["Süper Lig", "1. Lig"])].copy()
df["y"] = df["MS"].map({"1": "H", "X": "D", "2": "A"})
df = df.dropna(subset=["y"]).copy()

for src, dst in [
    ("Maç_Sonucu_|_1", "odd_H"),
    ("Maç_Sonucu_|_X", "odd_D"),
    ("Maç_Sonucu_|_2", "odd_A"),
]:
    df[dst] = pd.to_numeric(
        df[src].astype(str).str.replace(",", ".", regex=False).str.strip(),
        errors="coerce",
    )

df = df.sort_values(["date", "Maç_ID"]).reset_index(drop=True)
print(f"Toplam: {len(df)} maç | "
      f"{df['date'].min().date()} → {df['date'].max().date()} | "
      f"sezon={df['season'].nunique()} | "
      f"lig={df['league'].value_counts().to_dict()}")

# ============================================================
# 2) As-of-date features (ATOMİK gün bazlı)
# ============================================================
K_ELO = 20.0
elo     = {}
recent  = defaultdict(lambda: deque(maxlen=5))
last_dt = {}
h2h     = defaultdict(lambda: deque(maxlen=10))

def form_stats(q):
    if not q: return (np.nan, np.nan, np.nan)
    return (float(np.mean([x[0] for x in q])),
            float(np.mean([x[1] for x in q])),
            float(np.mean([x[2] for x in q])))

def implied_probs_from_row(odd_h, odd_d, odd_a):
    o = np.array([odd_h, odd_d, odd_a], dtype=float)
    if np.any(~np.isfinite(o)) or np.any(o <= 1.0):
        return None
    inv = 1.0 / o
    return inv / inv.sum()   # sıra: H, D, A

feat_rows = []

for day, group in df.groupby("date", sort=True):
    day_records = group.to_dict("records")

    # FAZ 1: gün başındaki state'ten feature'ları hesapla
    for r in day_records:
        L, h, a, d = r["league"], r["Ev_Sahibi"], r["Deplasman"], r["date"]
        e_h = elo.get((L, h), 1500.0)
        e_a = elo.get((L, a), 1500.0)

        fh = form_stats(recent.get((L, h), deque()))
        fa = form_stats(recent.get((L, a), deque()))
        rest_h = (d - last_dt[(L, h)]).days if (L, h) in last_dt else np.nan
        rest_a = (d - last_dt[(L, a)]).days if (L, a) in last_dt else np.nan

        hk = (L, tuple(sorted([h, a])))
        q  = h2h.get(hk, deque())
        h2h_home_share = (sum(1 for w in q if w == h) / len(q)) if q else np.nan

        feat_rows.append({
            "match_id": r["Maç_ID"], "date": d, "season": r["season"], "league": L,
            "home": h, "away": a, "y": r["y"],
            "odd_H": r["odd_H"], "odd_D": r["odd_D"], "odd_A": r["odd_A"],
            "elo_h": e_h, "elo_a": e_a, "elo_diff": e_h - e_a,
            "form_h_pts": fh[0], "form_h_gf": fh[1], "form_h_ga": fh[2],
            "form_a_pts": fa[0], "form_a_gf": fa[1], "form_a_ga": fa[2],
            "rest_h": rest_h, "rest_a": rest_a,
            "h2h_home_win_share": h2h_home_share,
        })

    # FAZ 2a: Elo deltalarını gün başından hesapla, topla
    day_deltas = defaultdict(float)
    for r in day_records:
        L, h, a = r["league"], r["Ev_Sahibi"], r["Deplasman"]
        e_h = elo.get((L, h), 1500.0)
        e_a = elo.get((L, a), 1500.0)
        sh      = {"H": 1.0, "D": 0.5, "A": 0.0}[r["y"]]
        e_h_exp = 1.0 / (1.0 + 10 ** ((e_a - e_h) / 400.0))
        delta   = K_ELO * (sh - e_h_exp)
        day_deltas[(L, h)] += delta
        day_deltas[(L, a)] -= delta

    # FAZ 2b: Toplam deltaları topluca uygula
    for (L, t), dsum in day_deltas.items():
        elo[(L, t)] = elo.get((L, t), 1500.0) + dsum

    # Form / son tarih / H2H (sıra bağımsız)
    for r in day_records:
        L, h, a, d = r["league"], r["Ev_Sahibi"], r["Deplasman"], r["date"]
        hg, ag = r["MSE"], r["MSD"]
        if pd.notna(hg) and pd.notna(ag):
            hg, ag = int(hg), int(ag)
            recent[(L, h)].append((3 if hg > ag else 1 if hg == ag else 0, hg, ag))
            recent[(L, a)].append((3 if ag > hg else 1 if hg == ag else 0, ag, hg))
        last_dt[(L, h)] = d
        last_dt[(L, a)] = d
        hk = (L, tuple(sorted([h, a])))
        h2h[hk].append(h if r["y"] == "H" else (a if r["y"] == "A" else "D"))

feat = pd.DataFrame(feat_rows)
feat.to_csv(OUT_DIR / "features_v0.csv", index=False)
print(f"features_v0.csv yazıldı: {len(feat)} satır")

# ============================================================
# 3) Walk-forward
# ============================================================
FEATURES = [
    "elo_h", "elo_a", "elo_diff",
    "form_h_pts", "form_h_gf", "form_h_ga",
    "form_a_pts", "form_a_gf", "form_a_ga",
    "rest_h", "rest_a", "h2h_home_win_share",
]

season_start_map = {s: season_start(s) for s in feat["season"].dropna().unique()}
seasons = [s for s, _ in sorted(season_start_map.items(), key=lambda kv: kv[1])]
print("Sezon sırası:", seasons)

WARMUP = 3
test_seasons = seasons[WARMUP:]
print(f"Test sezonları: {test_seasons}")

def class_freq(train_df):
    return np.array([(train_df["y"] == c).mean() for c in CLASSES], dtype=float)

results = []
Y_fair, P_model_fair, P_mkt_fair = [], [], []
Y_full, P_model_full             = [], []

for s in test_seasons:
    s_start   = season_start_map[s]
    train     = feat[feat["season"].map(season_start_map) < s_start].copy()
    test_full = feat[feat["season"] == s].reset_index(drop=True)

    if len(train) < 200 or len(test_full) < 20:
        print(f"  skip {s}: train={len(train)} test={len(test_full)}"); continue

    valid_mask = test_full.apply(
        lambda r: implied_probs_from_row(r["odd_H"], r["odd_D"], r["odd_A"]) is not None,
        axis=1,
    )
    test_fair = test_full[valid_mask].copy()

    med    = train[FEATURES].median()
    X_tr   = train[FEATURES].fillna(med)
    scaler = StandardScaler().fit(X_tr)

    clf = LogisticRegression(max_iter=2000, solver="lbfgs")
    clf.fit(scaler.transform(X_tr), train["y"])

    def predict_proba(frame):
        X = scaler.transform(frame[FEATURES].fillna(med))
        p = clf.predict_proba(X)
        cls = list(clf.classes_)
        return p[:, [cls.index(c) for c in CLASSES]]  # H, D, A sırası

    p_full   = predict_proba(test_full)
    ll_full  = log_loss_aligned(test_full["y"].values, p_full)
    acc_full = accuracy_score(test_full["y"],
                              np.array(CLASSES)[p_full.argmax(axis=1)])
    Y_full.extend(test_full["y"].tolist()); P_model_full.append(p_full)

    row = {
        "season": s, "season_start": s_start,
        "n_train": len(train),
        "n_test_full": len(test_full), "n_test_fair": len(test_fair),
        "model_ll_full":  round(ll_full, 4),
        "model_acc_full": round(acc_full, 4),
    }

    if len(test_fair) > 0:
        p_fair = predict_proba(test_fair)
        y_fair = test_fair["y"].values
        P_mkt  = np.vstack([
            implied_probs_from_row(r["odd_H"], r["odd_D"], r["odd_A"])
            for r in test_fair.to_dict("records")
        ])

        ll_model  = log_loss_aligned(y_fair, p_fair)
        br_model  = float(np.mean([
            np.mean((p_fair[:, j] - (y_fair == c).astype(int)) ** 2)
            for j, c in enumerate(CLASSES)
        ]))
        acc_model = float((np.array(CLASSES)[p_fair.argmax(axis=1)] == y_fair).mean())

        ll_mkt = log_loss_aligned(y_fair, P_mkt)
        br_mkt = float(np.mean([
            np.mean((P_mkt[:, j] - (y_fair == c).astype(int)) ** 2)
            for j, c in enumerate(CLASSES)
        ]))
        acc_mkt = float((np.array(CLASSES)[P_mkt.argmax(axis=1)] == y_fair).mean())

        p_train_class = class_freq(train)
        P_freq        = np.tile(p_train_class, (len(y_fair), 1))
        ll_freq       = log_loss_aligned(y_fair, P_freq)
        ll_unif       = LN3

        row.update({
            "model_ll_fair":      round(ll_model, 4),
            "market_ll_fair":     round(ll_mkt, 4),
            "model_brier_fair":   round(br_model, 4),
            "market_brier_fair":  round(br_mkt, 4),
            "model_acc_fair":     round(acc_model, 4),
            "market_acc_fair":    round(acc_mkt, 4),
            "baseline_freq_ll_fair":    round(ll_freq, 4),
            "baseline_uniform_ll_fair": round(ll_unif, 4),
            "train_class_freq":   [round(float(x), 4) for x in p_train_class],
        })

        Y_fair.extend(y_fair.tolist())
        P_model_fair.append(p_fair)
        P_mkt_fair.append(P_mkt)

    results.append(row)

res = pd.DataFrame(results)
print("\n=== WALK-FORWARD (her sezon) ===")
show_cols = [
    "season", "n_train", "n_test_full", "n_test_fair",
    "model_ll_full",
    "model_ll_fair", "market_ll_fair",
    "model_brier_fair", "market_brier_fair",
    "baseline_freq_ll_fair", "baseline_uniform_ll_fair",
]
print(res[[c for c in show_cols if c in res.columns]].to_string(index=False))

# ============================================================
# 4) Genel metrikler
# ============================================================
print("\n=== TÜM TEST (referans) ===")
if Y_full:
    Yf = np.array(Y_full); Pf = np.vstack(P_model_full)
    print(f"  Model log loss (full): {log_loss_aligned(Yf, Pf):.4f}")
    print(f"  Model accuracy (full): {(np.array(CLASSES)[Pf.argmax(axis=1)] == Yf).mean():.4f}")
    print(f"  Model Brier   (full): {np.mean([np.mean((Pf[:, j] - (Yf == c).astype(int))**2) for j, c in enumerate(CLASSES)]):.4f}")

if Y_fair:
    YF = np.array(Y_fair); PF = np.vstack(P_model_fair); PM = np.vstack(P_mkt_fair)

    ll_model_a = log_loss_aligned(YF, PF)
    ll_mkt_a   = log_loss_aligned(YF, PM)
    br_model_a = np.mean([np.mean((PF[:, j] - (YF == c).astype(int))**2) for j, c in enumerate(CLASSES)])
    br_mkt_a   = np.mean([np.mean((PM[:, j] - (YF == c).astype(int))**2) for j, c in enumerate(CLASSES)])
    acc_model_a = (np.array(CLASSES)[PF.argmax(axis=1)] == YF).mean()
    acc_mkt_a   = (np.array(CLASSES)[PM.argmax(axis=1)] == YF).mean()

    print(f"\n=== ADİL KARŞILAŞTIRMA (aynı {len(YF)} maç) ===")
    print(f"  {'':12s} {'Model':>10s} {'Market':>10s}")
    print(f"  {'Log loss':12s} {ll_model_a:10.4f} {ll_mkt_a:10.4f}")
    print(f"  {'Brier':12s} {br_model_a:10.4f} {br_mkt_a:10.4f}")
    print(f"  {'Accuracy':12s} {acc_model_a:10.4f} {acc_mkt_a:10.4f}")

    per = res.dropna(subset=["baseline_freq_ll_fair"])
    w = per["n_test_fair"].values
    ll_freq_w = float(np.average(per["baseline_freq_ll_fair"].values, weights=w)) if w.sum() else np.nan

    print(f"\n=== BASELINE KARŞILAŞTIRMA (fair küme) ===")
    print(f"  Uniform (1/3,1/3,1/3) log loss : {LN3:.4f}")
    print(f"  Eğitim sınıf dağılımı log loss : {ll_freq_w:.4f}  (sezon-ağırlıklı)")
    print(f"  Model log loss                 : {ll_model_a:.4f}")
    print(f"  Piyasa log loss                : {ll_mkt_a:.4f}")
    print(f"  Fark (baseline_freq - model)   : {ll_freq_w - ll_model_a:+.4f}  "
          f"(pozitif = model baseline'dan iyi)")
    print(f"  Fark (piyasa - model)          : {ll_mkt_a - ll_model_a:+.4f}  "
          f"(pozitif = model piyasadan iyi)")

    # Max-prob kalibrasyon
    maxp    = PF.max(axis=1)
    correct = (np.array(CLASSES)[PF.argmax(axis=1)] == YF).astype(int)
    bins    = np.linspace(0.34, 1.0, 9)
    print("\n=== MAX-PROB KALİBRASYON (fair küme) ===")
    for b in range(1, len(bins)):
        m = (maxp >= bins[b-1]) & (maxp < bins[b])
        if m.sum() < 30: continue
        print(f"  [{bins[b-1]:.2f},{bins[b]:.2f})  n={m.sum():5d}  "
              f"mean_p={maxp[m].mean():.3f}  actual={correct[m].mean():.3f}")

    # Sınıf bazlı kalibrasyon
    print("\n=== SINIF BAZLI KALİBRASYON (fair küme) ===")
    class_bins = np.array([0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35,
                           0.40, 0.45, 0.50, 0.60, 0.70, 0.80, 0.90, 1.01])
    for j, c in enumerate(CLASSES):
        p_c = PF[:, j]
        y_c = (YF == c).astype(int)
        print(f"\n--- Sınıf: {c} ---")
        for b in range(1, len(class_bins)):
            m = (p_c >= class_bins[b-1]) & (p_c < class_bins[b])
            if m.sum() < 30: continue
            print(f"  [{class_bins[b-1]:.2f},{class_bins[b]:.2f})  n={m.sum():5d}  "
                  f"mean_p={p_c[m].mean():.3f}  actual={y_c[m].mean():.3f}")
        print(f"  Brier({c}): {np.mean((p_c - y_c)**2):.4f}")

res.to_csv(OUT_DIR / "walkforward_v0.csv", index=False)
print(f"\nwalkforward_v0.csv yazıldı")