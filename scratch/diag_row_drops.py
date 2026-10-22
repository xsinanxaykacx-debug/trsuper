# diag_row_drops.py — 306 satır nerede düşüyor? + 353 sütun listesi + sınıflandırma
from pathlib import Path
from collections import defaultdict
import re
import numpy as np
import pandas as pd

DATA = Path(r"C:\Users\bzdye\Downloads\trsuper\data\csv\DATA.csv")
OUT  = DATA.parents[2] / "diag_row_drops.txt"

lines = []
def log(s=""):
    print(s); lines.append(str(s))

df = pd.read_csv(DATA, encoding="utf-8-sig", sep=",", low_memory=False)
log(f"0. Ham CSV: {len(df)} satır × {df.shape[1]} sütun (yardımcı sütun YOK)")

# --- 1) Tarih parse ---
df["date"] = pd.to_datetime(df["Tarih"], format="%d-%m-%Y", errors="coerce")
n_ok = int(df["date"].notna().sum())
log(f"\n1. Tarih parse: başarılı={n_ok}, başarısız={len(df)-n_ok}")
if len(df) - n_ok > 0:
    bad = df[df["date"].isna()]
    log(f"   Başarısız Tarih unique: {bad['Tarih'].astype(str).unique()[:15].tolist()}")
df1 = df.dropna(subset=["date"]).copy()
log(f"   Sonrası: {len(df1)}")

# --- 2) Sezon parse ---
def parse_season(s):
    m = re.search(r"(\d{4})/(\d{4})", str(s))
    return f"{m.group(1)}/{m.group(2)}" if m else None

df1["season"] = df1["Lig/Sezon"].apply(parse_season)
n_ok = int(df1["season"].notna().sum())
log(f"\n2. Sezon parse: başarılı={n_ok}, başarısız={len(df1)-n_ok}")
if len(df1) - n_ok > 0:
    bad = df1[df1["season"].isna()]
    log(f"   Başarısız Lig/Sezon unique: {bad['Lig/Sezon'].astype(str).unique()[:15].tolist()}")
df2 = df1.dropna(subset=["season"]).copy()
log(f"   Sonrası: {len(df2)}")

# --- 3) Lig filtresi ---
def parse_league(s):
    s = str(s)
    if "Süper" in s:  return "Süper Lig"
    if "1. Lig" in s: return "1. Lig"
    return "Other"

df2["league"] = df2["Lig/Sezon"].apply(parse_league)
log(f"\n3. Lig dağılımı (parse_league):")
for k, v in df2["league"].value_counts().items():
    log(f"   {k:12s}: {v}")

other = df2[df2["league"] == "Other"]
if len(other) > 0:
    log(f"\n   >>> OTHER'a düşen Lig/Sezon değerleri ({len(other)} satır):")
    for val, cnt in other["Lig/Sezon"].value_counts().items():
        log(f"       '{val}': {cnt}")
    log(f"\n   Other sezon dağılımı:")
    for val, cnt in other["season"].value_counts().sort_index().items():
        log(f"       {val}: {cnt}")

df3 = df2[df2["league"].isin(["Süper Lig", "1. Lig"])].copy()
log(f"   Sonrası: {len(df3)}")

# --- 4) MS map ---
MS_MAP = {"1": "H", "X": "D", "2": "A"}
df3["y"] = df3["MS"].map(MS_MAP)
n_ok = int(df3["y"].notna().sum())
log(f"\n4. MS map: başarılı={n_ok}, başarısız={len(df3)-n_ok}")
if len(df3) - n_ok > 0:
    bad = df3[df3["y"].isna()]
    log(f"   Başarısız MS unique: {bad['MS'].astype(str).unique().tolist()}")
    log(f"   Örnek Lig/Sezon: {bad['Lig/Sezon'].astype(str).unique()[:5].tolist()}")
df4 = df3.dropna(subset=["y"]).copy()
log(f"   Sonrası: {len(df4)}")

# --- ÖZET ---
log("\n" + "=" * 78)
log("ÖZET: 7422 → 7116 NEREDE DÜŞÜYOR?")
log("=" * 78)
log(f"  Başlangıç     : {len(df)}")
log(f"  date drop     : -{len(df) - len(df1)}")
log(f"  season drop   : -{len(df1) - len(df2)}")
log(f"  league drop   : -{len(df2) - len(df3)}")
log(f"  MS drop       : -{len(df3) - len(df4)}")
log(f"  Bitiş         : {len(df4)}")
log(f"  Toplam fark   : {len(df) - len(df4)}")

# --- Lig × Sezon çapraz tablo (filtre sonrası, ligler dahil) ---
log("\n=== Lig × Sezon çapraz tablo (tüm ligler) ===")
log(pd.crosstab(df2["season"], df2["league"]).to_string())

# --- 353 sütun listesi ---
log("\n" + "=" * 78)
log(f"CSV'deki {df.shape[1]} sütunun tam listesi")
log("=" * 78)
for i, c in enumerate(df.columns, 1):
    log(f"  {i:3d}. {c!r}")

# --- Sızıntı sınıflandırması ---
LEAKY_KEYWORDS = [
    "Skor", "İYE", "İYD", "MSE", "MSD", "İYS", "TG", "KGVY",
    "Goller", "Sarı_Kartlar", "Kırmızı_Kartlar", "Değişiklikler",
    "Kaçan_Penaltılar", "İSTATİSTİK_",
]
SAFE_PREMATCH = {
    "Tarih", "Saat", "Lig/Sezon", "Maç_ID", "Ev_Sahibi", "Deplasman",
    "Stadyum", "Hakem",
    "Ev_Sahibi_Teknik_Direktör", "Deplasman_Teknik_Direktör",
    "Ev_Kadro", "Deplasman_Kadro", "Ev_Yedek", "Deplasman_Yedek",
    "Seyirci",
}

def classify(col):
    c = str(col)
    if c in SAFE_PREMATCH:
        # Kadro ve seyirci için alt not
        if c in {"Ev_Kadro", "Deplasman_Kadro", "Ev_Yedek", "Deplasman_Yedek"}:
            return "PREMACH_ONLY_IF_T60_OR_DERIVED"
        if c == "Seyirci":
            return "POST_MATCH_DERIVE_ONLY"
        return "SAFE_PREMATCH"
    if any(k in c for k in LEAKY_KEYWORDS):
        return "LEAKY"
    if "|_" in c or "Oran" in c:
        return "ODDS_BENCHMARK_ONLY"
    return "UNCLASSIFIED"

groups = defaultdict(list)
for c in df.columns:
    groups[classify(c)].append(c)

log("\n" + "=" * 78)
log("SÜTUN SINIFLANDIRMASI")
log("=" * 78)
for g in ["SAFE_PREMATCH", "PREMACH_ONLY_IF_T60_OR_DERIVED", "POST_MATCH_DERIVE_ONLY",
          "ODDS_BENCHMARK_ONLY", "LEAKY", "UNCLASSIFIED"]:
    cols = groups.get(g, [])
    log(f"\n[{g}]  ({len(cols)} sütun)")
    for c in cols:
        log(f"  - {c}")

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"\nRapor: {OUT}")