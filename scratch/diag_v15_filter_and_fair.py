# diag_v15_filter_and_fair.py
# - parse_league davranış doğrulaması (v1.5 vs fix)
# - v1.5 filtreleme sırası (birebir aynı, sayısal teyit)
# - 306 maçın fair-odds + MSE/MSD uygunluğu
# - 306 eklenirse test_fair ve common fair boyutu nasıl değişir
# Salt okuma; hiçbir model dosyasını değiştirmez.

from pathlib import Path
import re
import numpy as np
import pandas as pd

DATA = Path(r"C:\Users\bzdye\Downloads\trsuper\data\csv\DATA.csv")
OUT  = DATA.parents[2] / "diag_v15_filter_and_fair.txt"

lines = []
def log(s=""):
    print(s); lines.append(str(s))

df = pd.read_csv(DATA, encoding="utf-8-sig", sep=",", low_memory=False)
df["date"] = pd.to_datetime(df["Tarih"], format="%d-%m-%Y", errors="coerce")

def parse_season(s):
    m = re.search(r"(\d{4})/(\d{4})", str(s));  return f"{m.group(1)}/{m.group(2)}" if m else None
def parse_league_v15(s):
    s = str(s)
    if "Süper" in s:  return "Süper Lig"
    if "1. Lig" in s: return "1. Lig"     # BUG: "1.Lig"ı yakalamaz
    return "Other"
def parse_league_fix(s):
    s = str(s)
    if "Süper" in s:  return "Süper Lig"
    if re.search(r"1\.\s*Lig", s): return "1. Lig"
    return "Other"

df["season"]     = df["Lig/Sezon"].apply(parse_season)
df["league_v15"] = df["Lig/Sezon"].apply(parse_league_v15)
df["league_fix"] = df["Lig/Sezon"].apply(parse_league_fix)
df["y"] = df["MS"].map({"1":"H","X":"D","2":"A"})

for src, dst in [("Maç_Sonucu_|_1","odd_H"),("Maç_Sonucu_|_X","odd_D"),("Maç_Sonucu_|_2","odd_A")]:
    df[dst] = pd.to_numeric(
        df[src].astype(str).str.replace(",", ".", regex=False).str.strip(),
        errors="coerce",
    )

def valid_odds(r):
    o = np.array([r["odd_H"], r["odd_D"], r["odd_A"]], dtype=float)
    return np.isfinite(o).all() and (o > 1.0).all()

df["valid_odds"] = df.apply(valid_odds, axis=1)

# MSE/MSD validasyonu (v1.5'teki ile aynı)
for col in ["MSE", "MSD"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")
df["valid_score"] = (
    df["MSE"].notna() & df["MSD"].notna()
    & np.isfinite(df["MSE"]) & np.isfinite(df["MSD"])
    & (df["MSE"] >= 0) & (df["MSD"] >= 0)
    & (df["MSE"] % 1 == 0) & (df["MSD"] % 1 == 0)
)

# ============ 1) parse_league davranışı ============
log("=" * 78); log("1. parse_league DAVRANIŞI"); log("=" * 78)
for s in sorted(df["Lig/Sezon"].dropna().unique()):
    n = int((df["Lig/Sezon"] == s).sum())
    v15 = parse_league_v15(s); fix = parse_league_fix(s)
    mark = "  " if v15 == fix else ">>>"
    log(f"{mark} '{s}'  (n={n})")
    log(f"     v1.5 -> {v15:10s}   fix -> {fix}")
changed = df[df["league_v15"] != df["league_fix"]]
log(f"\nFiltre sonucu değişen satır: {len(changed)}")
if len(changed) > 0:
    log(f"  Sezon(lar): {changed['season'].unique().tolist()}")
    log(f"  Lig/Sezon değeri: {changed['Lig/Sezon'].unique().tolist()}")

# ============ 2) v1.5 filtreleme sırası ============
log("\n" + "=" * 78); log("2. v1.5 FİLTRELEME SIRASI (kodla birebir)"); log("=" * 78)
n0 = len(df)
df1 = df.dropna(subset=["date"]);                                         n1 = len(df1)
df2 = df1.dropna(subset=["season"]);                                      n2 = len(df2)
df3 = df2[df2["league_v15"].isin(["Süper Lig", "1. Lig"])];               n3 = len(df3)
df4 = df3.dropna(subset=["y"]);                                           n4 = len(df4)
log(f"  0. Başlangıç   : {n0}")
log(f"  1. date        : {n0} -> {n1}  (-{n0-n1})")
log(f"  2. season      : {n1} -> {n2}  (-{n1-n2})")
log(f"  3. league      : {n2} -> {n3}  (-{n2-n3})")
log(f"  4. MS          : {n3} -> {n4}  (-{n3-n4})")
log(f"  Filtre sonrası: {n4}")

# ============ 3) 306 maçın odds ve skor durumu ============
log("\n" + "=" * 78); log("3. 306 MAÇIN FAIR-ODDS ve SKOR DURUMU"); log("=" * 78)
the306 = df[df["league_v15"] == "Other"]
log(f"Other sınıfındaki maç: {len(the306)}")
log(f"  valid_odds = True : {int(the306['valid_odds'].sum())}")
log(f"  valid_odds = False: {int((~the306['valid_odds']).sum())}")
log(f"  valid_score = True : {int(the306['valid_score'].sum())}")
log(f"  valid_score = False: {int((~the306['valid_score']).sum())}")

bad_odds = the306[~the306["valid_odds"]]
if len(bad_odds) > 0:
    log(f"\n  valid_odds olmayan {len(bad_odds)} maçın alan bazlı durumu:")
    for c in ["odd_H", "odd_D", "odd_A"]:
        nan_n   = int(bad_odds[c].isna().sum())
        low_n   = int(((bad_odds[c] <= 1.0) & bad_odds[c].notna()).sum())
        log(f"    {c}: NaN={nan_n}, <=1.0={low_n}")

# ============ 4) Test kümesine etkisi (sezon bazında) ============
log("\n" + "=" * 78); log("4. TEST KÜMESİ ETKİSİ (fair, sezon bazında)"); log("=" * 78)

season_starts = {}
for s in df["season"].dropna().unique():
    m = re.match(r"(\d{4})/", str(s))
    if m: season_starts[s] = int(m.group(1))
ordered_seasons = [s for s, _ in sorted(season_starts.items(), key=lambda kv: kv[1])]
WARMUP = 3
test_seasons = ordered_seasons[WARMUP:]

# v1.5 test set (df4 = v1.5 filtre sonrası)
log("\n--- v1.5 (mevcut, 7116) ---")
log(f"{'season':12s} {'test_full':>10s} {'test_fair':>10s}")
v15 = {}
for s in test_seasons:
    sub = df4[df4["season"] == s]
    sub_fair = sub[sub["valid_odds"]]
    v15[s] = (len(sub), len(sub_fair))
    log(f"{s:12s} {len(sub):10d} {len(sub_fair):10d}")
tot_full_v15 = sum(v[0] for v in v15.values())
tot_fair_v15 = sum(v[1] for v in v15.values())
log(f"{'TOTAL':12s} {tot_full_v15:10d} {tot_fair_v15:10d}")

# Fix sonrası
dfc = df2[df2["league_fix"].isin(["Süper Lig", "1. Lig"])]
dfd = dfc.dropna(subset=["y"])
log("\n--- Fix (lig normalizasyonu) ---")
log(f"{'season':12s} {'test_full':>10s} {'test_fair':>10s} {'Δ full':>8s} {'Δ fair':>8s}")
fix = {}
for s in test_seasons:
    sub = dfd[dfd["season"] == s]
    sub_fair = sub[sub["valid_odds"]]
    fix[s] = (len(sub), len(sub_fair))
    log(f"{s:12s} {len(sub):10d} {len(sub_fair):10d} "
        f"{len(sub)-v15[s][0]:+8d} {len(sub_fair)-v15[s][1]:+8d}")
tot_full_fix = sum(v[0] for v in fix.values())
tot_fair_fix = sum(v[1] for v in fix.values())
log(f"{'TOTAL':12s} {tot_full_fix:10d} {tot_fair_fix:10d} "
    f"{tot_full_fix-tot_full_v15:+8d} {tot_fair_fix-tot_fair_v15:+8d}")

# ============ 5) Common fair etkisi ============
log("\n" + "=" * 78); log("5. COMMON FAIR ETKİSİ"); log("=" * 78)
log(f"  v1.5 common fair toplamı : {tot_fair_v15}")
log(f"  Fix sonrası toplam       : {tot_fair_fix}")
log(f"  Net değişim              : {tot_fair_fix - tot_fair_v15:+d} maç")
log(f"\n  Yorum: RF'nin v1.5 metrikleri (1.0236 / 0.6132 / 49.26%)")
log(f"  {tot_fair_v15} maç üzerinde hesaplandı. Fix sonrası fair küme")
log(f"  {tot_fair_fix} maça çıkar. İki metrik kümesi doğrudan karşılaştırılamaz;")
log(f"  v1.6 ayrı bir baseline olarak kurulacak, v1.5 tarihsel referans kalır.")

# ============ 6) 2016/2017 detayı ============
log("\n" + "=" * 78); log("6. 2016/2017 DETAYI"); log("=" * 78)
sub_1617 = df2[df2["season"] == "2016/2017"]
log(f"Toplam maç         : {len(sub_1617)}")
log(f"Lig (v1.5)         : {sub_1617['league_v15'].value_counts().to_dict()}")
log(f"Lig (fix)          : {sub_1617['league_fix'].value_counts().to_dict()}")
one_lig = sub_1617[sub_1617["league_fix"] == "1. Lig"]
log(f"\n1. Lig 2016/2017:")
log(f"  Toplam          : {len(one_lig)}")
log(f"  valid_odds=True : {int(one_lig['valid_odds'].sum())}")
log(f"  valid_odds=False: {int((~one_lig['valid_odds']).sum())}")
log(f"  valid_score=True: {int(one_lig['valid_score'].sum())}")

# ============ 7) Sınıflandırma düzeltmeleri ============
log("\n" + "=" * 78); log("7. SINIFLANDIRMA DÜZELTMELERİ (not)"); log("=" * 78)
for col, tag in [
    ("MS",       "TARGET"),
    ("İY05AÜ",   "LEAKY"), ("İY15AÜ", "LEAKY"), ("İY25AÜ", "LEAKY"),
    ("MS05AÜ",   "LEAKY"), ("MS15AÜ", "LEAKY"),
    ("MS25AÜ",   "LEAKY"), ("MS35AÜ", "LEAKY"),
    ("date",     "HELPER"),
]:
    log(f"  {col:12s} -> {tag}")

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"\nRapor: {OUT}")