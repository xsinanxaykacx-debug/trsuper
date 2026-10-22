# data_inventory.py — DATA.csv sütun envanteri (salt okuma)
from pathlib import Path
import re
import numpy as np
import pandas as pd

DATA = Path(r"C:\Users\bzdye\Downloads\trsuper\data\csv\DATA.csv")
OUT  = DATA.parents[2] / "data_inventory.txt"

lines = []
def log(s=""):
    print(s); lines.append(str(s))

df = pd.read_csv(DATA, encoding="utf-8-sig", sep=",", low_memory=False)
df["date"] = pd.to_datetime(df["Tarih"], format="%d-%m-%Y", errors="coerce")
df["season_start"] = df["Lig/Sezon"].astype(str).str.extract(r"(\d{4})/")[0].astype(float)

log(f"Toplam: {len(df)} satır × {df.shape[1]} sütun")
log(f"Tarih aralığı: {df['date'].min().date()} → {df['date'].max().date()}")
log(f"Sezon sayısı: {df['season_start'].nunique()}")

# İlgilendiğimiz aday sütunlar
CANDIDATES = [
    # maç öncesi bilinebilir olma ihtimali yüksek
    "Saat", "Stadyum", "Hakem",
    "Ev_Sahibi_Teknik_Direktör", "Deplasman_Teknik_Direktör",
    "Ev_Kadro", "Deplasman_Kadro", "Ev_Yedek", "Deplasman_Yedek",
    # maç sonrası (sızıntı riski yüksek) — sadece sınıflandırma için
    "Seyirci",
    "İY_Skor", "Skor", "İYE", "İYD", "MSE", "MSD", "İYS", "MS",
    "TG", "KGVY",
    # olası kullanışlı olmayanlar
    "Lig/Sezon", "Maç_ID",
]

log("\n" + "=" * 78)
log("SÜTUN ENVANTERİ")
log("=" * 78)

def is_integer_like(series):
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) == 0: return False
    return bool((s % 1 == 0).all())

for col in CANDIDATES:
    if col not in df.columns:
        log(f"\n[{col}]  !! KOLON YOK")
        continue
    s = df[col]
    nn = s.notna().sum()
    miss = (1 - nn / len(s)) * 100
    nun = s.nunique(dropna=True)
    dt_min = df.loc[s.notna(), "date"].min()
    dt_max = df.loc[s.notna(), "date"].max()

    log(f"\n[{col}]")
    log(f"  dtype={s.dtype}  missing={miss:.1f}%  unique={nun}")
    if pd.notna(dt_min):
        log(f"  Dolu olduğu tarih aralığı: {dt_min.date()} → {dt_max.date()}")

    # String / sayısal profil
    if pd.api.types.is_numeric_dtype(s):
        log(f"  min={s.min()}  max={s.max()}  mean={s.mean():.3f}")
        log(f"  Integer görünüm: {is_integer_like(s)}")
    else:
        # Seyirci için "kişi" temizliği
        s_str = s.dropna().astype(str)
        sample = list(s_str.unique()[:5])
        log(f"  örnek değerler: {sample}")
        # Seyirci özel: "24.169 kişi" gibi
        if "kişi" in " ".join(sample).lower() or col == "Seyirci":
            def parse_seyirci(x):
                if pd.isna(x): return np.nan
                x = str(x).replace("kişi", "").replace(".", "").replace(" ", "").strip()
                return pd.to_numeric(x, errors="coerce")
            parsed = s.map(parse_seyirci)
            log(f"  -> 'kişi' suffix temizlenmiş sayısal profil:")
            log(f"     dolu={parsed.notna().sum()}, "
                f"min={parsed.min()}, max={parsed.max()}, "
                f"mean={parsed.mean():.1f}")

    # Sezon bazında dolu oranı
    tmp = df.groupby("season_start")[col].apply(lambda x: x.notna().mean() * 100)
    seasons_short = [f"{int(k)}/{(int(k)+1)%100:02d}" for k in tmp.index if pd.notna(k)]
    row_fmt = "  sezon doluluk %: " + ", ".join(
        f"{sn}={v:.0f}" for sn, v in zip(seasons_short, tmp.values)
    )
    log(row_fmt)

# Maç_ID tekil mi?
log("\n" + "=" * 78)
log("MAÇ_ID KONTROLÜ")
log("=" * 78)
if "Maç_ID" in df.columns:
    log(f"Toplam satır: {len(df)}, unique Maç_ID: {df['Maç_ID'].nunique()}")
    log(f"Tekrarlı Maç_ID sayısı: {len(df) - df['Maç_ID'].nunique()}")

# Hakem ve TD kardinalite
log("\n" + "=" * 78)
log("KATEGORİK KARDİNALİTE")
log("=" * 78)
for col in ["Hakem", "Stadyum",
            "Ev_Sahibi_Teknik_Direktör", "Deplasman_Teknik_Direktör",
            "Ev_Sahibi", "Deplasman"]:
    if col in df.columns:
        log(f"  {col}: unique={df[col].nunique()}")

# Hakem başına ortalama maç sayısı (bilgi yoğunluğu sinyali)
if "Hakem" in df.columns:
    hc = df["Hakem"].value_counts()
    log(f"\n  Hakem başına maç: medyan={hc.median():.0f}, "
        f"mean={hc.mean():.1f}, min={hc.min()}, max={hc.max()}")
    log(f"  En az 20 maç yöneten hakem sayısı: {(hc >= 20).sum()}")

# TD başına ortalama maç
if "Ev_Sahibi_Teknik_Direktör" in df.columns:
    for col in ["Ev_Sahibi_Teknik_Direktör", "Deplasman_Teknik_Direktör"]:
        tc = df[col].value_counts()
        log(f"\n  {col} başına maç: medyan={tc.median():.0f}, "
            f"mean={tc.mean():.1f}, max={tc.max()}")
        log(f"  En az 30 maçlı TD sayısı: {(tc >= 30).sum()}")

# Stadyum başına maç
if "Stadyum" in df.columns:
    sc = df["Stadyum"].value_counts()
    log(f"\n  Stadyum başına maç: medyan={sc.median():.0f}, "
        f"mean={sc.mean():.1f}, max={sc.max()}")
    log(f"  En az 30 maçlı stadyum sayısı: {(sc >= 30).sum()}")

# Örnek satırlar: sadece aday sütunlar
log("\n" + "=" * 78)
log("ÖRNEK SATIRLAR (aday sütunlar)")
log("=" * 78)
show = ["date", "Lig/Sezon", "Ev_Sahibi", "Deplasman",
        "Saat", "Stadyum", "Hakem",
        "Ev_Sahibi_Teknik_Direktör", "Deplasman_Teknik_Direktör",
        "Seyirci"]
show = [c for c in show if c in df.columns]
log(df[show].head(8).to_string())

# Kısa sınıflandırma
log("\n" + "=" * 78)
log("ÖN SINIFLANDIRMA")
log("=" * 78)
classification = {
    "Saat": "maç öncesi bilinir",
    "Stadyum": "maç öncesi bilinir (sabit tesis)",
    "Hakem": "maç öncesi bilinir (atama duyurulur)",
    "Ev_Sahibi_Teknik_Direktör": "maç öncesi bilinir (sezon içi istikrarlı)",
    "Deplasman_Teknik_Direktör": "maç öncesi bilinir",
    "Ev_Kadro": "maç öncesi kesin değil (T-60 dk açıklanır)",
    "Deplasman_Kadro": "maç öncesi kesin değil",
    "Ev_Yedek": "maç öncesi kesin değil",
    "Deplasman_Yedek": "maç öncesi kesin değil",
    "Seyirci": "MAÇ SONRASI (kayıt) — doğrudan kullanılamaz; geçmiş seyirci ortalaması as-of-date türetilebilir",
}
for c, note in classification.items():
    if c in df.columns:
        log(f"  {c}: {note}")

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"\nRapor: {OUT}")