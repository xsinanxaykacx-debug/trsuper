from pathlib import Path
import ast
import re
import numpy as np
import pandas as pd
from sklearn.metrics import log_loss

ROOT = Path.cwd()
TOLERANS = 0.01

DATA_PATH = ROOT / "data" / "csv" / "DATA.csv"
PRED_PATH = ROOT / "archive_v16" / "v16_per_match_predictions.csv"
MODEL_PATH = ROOT / "archive_v16" / "model_v1_6.py"
WF_PATH = ROOT / "archive_v16" / "walkforward_v16_exact.csv"

def bolum(s):
    print("\n" + "=" * 78)
    print(s)
    print("=" * 78)

def sutun(df, *adaylar):
    for a in adaylar:
        if a in df.columns:
            return a
    norm = {re.sub(r"[\W_]+", "", str(c)).casefold(): c for c in df.columns}
    for a in adaylar:
        k = re.sub(r"[\W_]+", "", a).casefold()
        if k in norm:
            return norm[k]
    raise KeyError(
        f"Sütun bulunamadı: {adaylar}\n"
        f"Benzer mevcut başlıklar: {list(df.columns[:80])}"
    )

def sayiya_cevir(s):
    return pd.to_numeric(
        s.astype("string").str.strip().str.replace(",", ".", regex=False),
        errors="coerce"
    )

def gol_int(x):
    if pd.isna(x):
        return np.nan
    z = str(x).strip().replace(",", ".")
    try:
        v = float(z)
    except (ValueError, TypeError):
        return np.nan
    if not np.isfinite(v) or v < 0 or abs(v - round(v)) > 1e-9:
        return np.nan
    return int(round(v))

def skor_ayir(x):
    if pd.isna(x):
        return None
    m = re.fullmatch(r"\s*(\d+)\s*[-:]\s*(\d+)\s*", str(x))
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))

def sonuc(h, a):
    if pd.isna(h) or pd.isna(a):
        return None
    return "H" if h > a else ("D" if h == a else "A")

def etiket_duzelt(x):
    if pd.isna(x):
        return None
    s = str(x).strip().upper()
    return {"1": "H", "H": "H", "MS1": "H",
            "X": "D", "D": "D", "MSX": "D",
            "2": "A", "A": "A", "MS2": "A"}.get(s)

def metrik(y, p):
    labels = ["H", "D", "A"]
    y = np.asarray(y)
    p = np.asarray(p, dtype=float)
    p = np.clip(p, 1e-15, 1.0)
    p = p / p.sum(axis=1, keepdims=True)
    onehot = np.column_stack([y == k for k in labels]).astype(float)
    return {
        "N": len(y),
        "LogLoss": log_loss(y, p, labels=labels),
        "Brier": float(np.mean(np.sum((p - onehot) ** 2, axis=1))),
        "Accuracy": float(np.mean(np.array(labels)[p.argmax(axis=1)] == y))
    }

for p in [DATA_PATH, PRED_PATH, MODEL_PATH, WF_PATH]:
    if not p.exists():
        raise FileNotFoundError(f"Gerekli dosya yok: {p}")

data = pd.read_csv(DATA_PATH, encoding="utf-8-sig", low_memory=False)
pred = pd.read_csv(PRED_PATH, encoding="utf-8-sig", low_memory=False)
src = MODEL_PATH.read_text(encoding="utf-8-sig")
lines = src.splitlines()
tree = ast.parse(src)

id_col = sutun(data, "Maç_ID", "Mac_ID")
date_col = sutun(data, "Tarih")
season_col = sutun(data, "Lig/Sezon")
score_col = sutun(data, "Skor")
mse_col = sutun(data, "MSE")
msd_col = sutun(data, "MSD")
odd_cols = [
    sutun(data, "Maç_Sonucu_|_1", "Mac_Sonucu_|_1"),
    sutun(data, "Maç_Sonucu_|_X", "Mac_Sonucu_|_X"),
    sutun(data, "Maç_Sonucu_|_2", "Mac_Sonucu_|_2")
]

data["_id"] = pd.to_numeric(data[id_col], errors="coerce").astype("Int64")
data["_date"] = pd.to_datetime(data[date_col], dayfirst=True, errors="coerce")
data["_season"] = data[season_col].astype("string").str.extract(r"(\d{4}/\d{4})")[0]
for c, out in zip(odd_cols, ["_odd_H", "_odd_D", "_odd_A"]):
    data[out] = sayiya_cevir(data[c])

pred_id_col = sutun(pred, "match_id")
pred["_id"] = pd.to_numeric(pred[pred_id_col], errors="coerce").astype("Int64")
pred["_y"] = pred["y"].map(etiket_duzelt)

bolum("1. DOSYA VE SÜTUN ÖZETİ")
print(f"DATA: {DATA_PATH}")
print(f"DATA satır/sütun: {data.shape}")
print(f"TAHMİN satır/sütun: {pred.shape}")
print(f"DATA ID sütunu: {id_col}")
print(f"Tarih/sezon/skor: {date_col} / {season_col} / {score_col}")
print(f"Gol sütunları: {mse_col} / {msd_col}")
print(f"Oran sütunları: {odd_cols}")
print(f"Tolerans: {TOLERANS} (bahis oranı yuvarlama)")
print(f"DATA benzersiz ID: {data['_id'].nunique()}")
print(f"Tahmin benzersiz ID: {pred['_id'].nunique()}")
print(f"Tahmin y dağılımı:\n{pred['_y'].value_counts(dropna=False).to_string()}")

bolum("2. AST: FEATURE ENGINEERING VE OLASI SIZINTI")
funcs = [n for n in ast.walk(tree)
         if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
for name in ["elo_h", "elo_a", "elo_diff", "form_h_pts_5",
             "form_h_gf_5", "h2h_current_home_team_win_share",
             "league_home_win_share", "rest_h", "season_match_h"]:
    hits = []
    for f in funcs:
        body = "\n".join(lines[f.lineno-1:f.end_lineno])
        if name in body:
            hits.append(f)
    if hits:
        f = min(hits, key=lambda n: n.end_lineno - n.lineno)
        print(f"\n{name}: {f.name}(), satır {f.lineno}-{f.end_lineno}")
        for i in range(f.lineno-1, f.end_lineno):
            print(f"{i+1:4d}| {lines[i]}")
    else:
        print(f"\n{name}: fonksiyon içinde bulunamadı")

print("\nŞüpheli ileri-bakış kalıpları:")
for pat in ["shift(-", "center=True", "bfill"]:
    found = [i+1 for i, line in enumerate(lines) if pat in line]
    print(f"  {pat}: {found if found else 'YOK'}")

feat_line = next((i+1 for i, x in enumerate(lines)
                  if re.search(r"\bfeat\s*=", x)), None)
loop_line = next((i+1 for i, x in enumerate(lines)
                  if "for s in test_seasons" in x), None)
print(f"\nfeat ataması: {feat_line}; test sezon döngüsü: {loop_line}")
print("UYARI: feat'in split öncesi oluşturulması tek başına sızıntı kanıtı değildir.")
print("Özelliklerin her maç için yalnızca önceki maçları kullanıp kullanmadığı incelenmeli.")

feat_end = next((i for i, x in enumerate(lines) if "features_v1.csv" in x), None)
if feat_end is not None:
    start = min(119, len(lines))
    print(f"\nFeature engineering kaynak kesiti, satır {start+1}-{feat_end+1}:")
    for i in range(start, min(feat_end+1, len(lines))):
        print(f"{i+1:4d}| {lines[i]}")

bolum("3. ORAN EŞLEŞMESİ")
merged = pred.merge(
    data[["_id", "_date", "_season", "_odd_H", "_odd_D", "_odd_A"]],
    on="_id", how="left", validate="one_to_one"
)
print(f"ID eşleşmesi: {int(merged['_date'].notna().sum())}/{len(pred)}")
for pc, dc in [("odd_H", "_odd_H"), ("odd_D", "_odd_D"), ("odd_A", "_odd_A")]:
    if pc not in merged.columns:
        print(f"{pc}: tahmin dosyasında sütun yok")
        continue
    a = pd.to_numeric(merged[pc].astype(str).str.replace(",", ".", regex=False),
                      errors="coerce")
    b = merged[dc]
    both = a.notna() & b.notna()
    close = both & ((a-b).abs() < TOLERANS)
    print(f"{pc}: karşılaştırılabilir={int(both.sum())}, "
          f"tolerans içi={int(close.sum())}, "
          f"farklı={int((both & ~close).sum())}")
    if (both & ~close).any():
        print(merged.loc[both & ~close, ["_id", pc, dc]].head(5).to_string(index=False))

bolum("4. SEZON VE TEST KÜMESİ EŞLEŞMESİ")
wf = pd.read_csv(WF_PATH, encoding="utf-8-sig")
print("Walk-forward sezon tablosu:")
print(wf.to_string(index=False))
print(f"\nDATA sezon dağılımı:\n{data['_season'].value_counts(dropna=False).sort_index().to_string()}")
print(f"\nTahmin sezon dağılımı:\n{pred['season'].value_counts(dropna=False).sort_index().to_string()}")

common = pred.merge(
    data[["_id", "_date", "_season", "_odd_H", "_odd_D", "_odd_A",
          score_col, mse_col, msd_col]],
    on="_id", how="left", validate="one_to_one", suffixes=("_pred", "_data")
)
date_pred = pd.to_datetime(common["date"], errors="coerce")
print(f"\nTahmin tarih = DATA tarihi: "
      f"{int((date_pred.dt.date == common['_date'].dt.date).sum())}/{len(common)}")
print(f"Tahmin sezon = DATA sezonu: "
      f"{int((common['season'] == common['_season']).sum())}/{len(common)}")

bolum("5. SKOR VE ETİKET DOĞRULAMASI")
common["_mse_int"] = common[mse_col].map(gol_int)
common["_msd_int"] = common[msd_col].map(gol_int)
common["_y_goals"] = [
    sonuc(h, a) for h, a in zip(common["_mse_int"], common["_msd_int"])
]
common["_score_pair"] = common[score_col].map(skor_ayir)
score_ok = common["_score_pair"].notna()
common["_score_h"] = common["_score_pair"].map(
    lambda x: x[0] if x is not None else np.nan)
common["_score_a"] = common["_score_pair"].map(
    lambda x: x[1] if x is not None else np.nan)

for name, a, b in [
    ("MSE = Skor ev sahibi golü", common["_mse_int"], common["_score_h"]),
    ("MSD = Skor deplasman golü", common["_msd_int"], common["_score_a"])
]:
    valid = a.notna() & b.notna()
    print(f"{name}: {int((a[valid] == b[valid]).sum())}/{int(valid.sum())}")
    bad = valid & (a != b)
    if bad.any():
        print(common.loc[bad, ["_id", score_col, mse_col, msd_col]].head(5).to_string(index=False))

valid_y = common["_y"].notna() & common["_y_goals"].notna()
same = common.loc[valid_y, "_y"] == common.loc[valid_y, "_y_goals"]
print(f"pred y / gerçek skor karşılaştırması: {int(same.sum())}/{int(valid_y.sum())}")
print(f"Gerçek skordan sonuç çıkarılabilen: {int(common['_y_goals'].notna().sum())}/{len(common)}")
bad_y = valid_y & (common["_y"] != common["_y_goals"])
if bad_y.any():
    print("Etiket uyuşmazlığı örnekleri:")
    print(common.loc[bad_y, ["_id", "y", "_y", "_y_goals", score_col, mse_col, msd_col]]
          .head(10).to_string(index=False))

bolum("6. AYNI 5854 KÜMEDE MARKET LOG LOSS")
odds = common[["_odd_H", "_odd_D", "_odd_A"]].to_numpy(dtype=float)
valid_odds = np.isfinite(odds).all(axis=1) & (odds > 1.0).all(axis=1)
valid = common["_y_goals"].notna().to_numpy() & valid_odds
print(f"Market için geçerli maç: {int(valid.sum())}/{len(common)}")
if valid.any():
    inv = 1.0 / odds[valid]
    p = inv / inv.sum(axis=1, keepdims=True)
    y = common.loc[valid, "_y_goals"].to_numpy()
    m = metrik(y, p)
    print(f"N={m['N']}")
    print(f"Market LogLoss={m['LogLoss']:.6f}")
    print(f"Market Brier={m['Brier']:.6f}")
    print(f"Market Accuracy=%{100*m['Accuracy']:.2f}")
    print("Önceki 0.9927 / 0.5918 / %51.84 değerleri yalnızca referanstır;")
    print("aynı etiket ve örneklem doğrulanmadan eşik olarak kullanılmayacaktır.")
else:
    print("HESAPLANAMADI: geçerli skor ve üçlü oran kümesi yok.")

bolum("7. SONUÇ / DOSYA GÜVENLİĞİ")
print(f"DATA dosyası yalnızca okundu: {DATA_PATH}")
print(f"Arşiv dosyaları yalnızca okundu: {MODEL_PATH.parent}")
print("Bu betik DATA.csv veya archive_v16 içeriğini değiştirmedi.")