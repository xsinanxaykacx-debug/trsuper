import pandas as pd
import numpy as np
import os
import sys
import argparse

# --- AYARLAR ---
# Kullanıcıdan dosya yollarını almak için argparse kullanıyoruz
parser = argparse.ArgumentParser(description="Veri Kalitesi Raporu Üretici")
parser.add_argument("--csv", default="DATA.csv", help="Ham CSV dosyasının yolu")
parser.add_argument("--out", default="docs/data_quality_report_v2.md", help="Çıktı raporunun yolu")
args = parser.parse_args()

if not os.path.exists(args.csv):
    print(f"HATA: {args.csv} bulunamadı. Lütfen yolu kontrol edin.")
    sys.exit(1)

print(f"Veri okunuyor: {args.csv}")
# Tüm veriyi string olarak okuyoruz ki sayısal dönüşümlerde veri kaybı olmasın
df = pd.read_csv(args.csv, encoding="utf-8-sig", sep=",", dtype=str)

# Boşluk içeren hücreleri (örn: "  ") NaN olarak kabul et
df = df.replace(r'^\s*$', np.nan, regex=True)

report = []
report.append("# DATA.csv — Veri Kalitesi Denetim Raporu (Revize v2)\n")
report.append(f"- **Toplam Satır:** {len(df)}\n")
report.append(f"- **Toplam Sütun:** {len(df.columns)}\n\n")

# ==========================================
# 1. DÜZELTME: Lig ve Sezon Ayrımı
# ==========================================
report.append("## 1. Lig ve Sezon Sınıflandırması\n")
if "Lig/Sezon" in df.columns:
    # Sezonu regex ile yakala (\s* doğru kullanıldı)
    df["Sezon"] = df["Lig/Sezon"].str.extract(r"(\d{4}/\d{4})", expand=False)
    df["Lig"] = df["Lig/Sezon"].str.replace(r"\s*\d{4}/\d{4}", "", regex=True).str.strip()
    
    missing_season = df["Sezon"].isnull().sum()
    report.append(f"- Sezonu belirlenemeyen satır sayısı: **{missing_season}**\n")
    if missing_season > 0:
        ornekler = df[df["Sezon"].isnull()]["Lig/Sezon"].dropna().unique()[:3]
        report.append(f"  - Örnek Belirlenemeyen Değerler: {ornekler}\n")
    
    report.append(f"- Tespit edilen benzersiz lig sayısı: **{df['Lig'].nunique()}**\n")
    report.append(f"- Tespit edilen benzersiz sezon sayısı: **{df['Sezon'].nunique()}**\n\n")


# ==========================================
# 2. DÜZELTME: Skor ve MS Tutarlılığı
# ==========================================
report.append("## 2. Skor ve Sonuç (MS) Tutarlılığı\n")

# Skor formatını güvenli ayır ("1-3", "1 - 3", "1:3" vb.)
skor_split = df["Skor"].str.extract(r"^\s*(\d+)\s*[-:]\s*(\d+)\s*$")
df["Ev_Gol"] = pd.to_numeric(skor_split[0], errors="coerce")
df["Dep_Gol"] = pd.to_numeric(skor_split[1], errors="coerce")

# Vektörel sonuç hesaplama (Uyumluluk için default=None kullanıldı)
conditions = [
    (df["Ev_Gol"] > df["Dep_Gol"]),
    (df["Ev_Gol"] == df["Dep_Gol"]),
    (df["Ev_Gol"] < df["Dep_Gol"])
]
choices = ["1", "X", "2"]
df["Hesaplanan_Sonuc"] = np.select(conditions, choices, default=None)

# MS sütununu temizle (Eksik değerleri koruyarak)
df["MS_Temiz"] = df["MS"].str.strip().str.upper()
# "NAN", "NONE", "NAT" gibi metinleşmiş eksikleri tekrar NaN yap
df.loc[df["MS_Temiz"].isin(["NAN", "NONE", "NAT", "<NA>"]), "MS_Temiz"] = np.nan

# Karşılaştırma
karsilastirilabilir = df["Hesaplanan_Sonuc"].notna() & df["MS_Temiz"].notna()
uyusmazlik = df[karsilastirilabilir & (df["Hesaplanan_Sonuc"] != df["MS_Temiz"])]

# Skor ayrıştırılamayanları kategorize et
skor_olmayan = df["Skor"].isnull().sum()
skor_gecersiz = df["Hesaplanan_Sonuc"].isnull().sum() - skor_olmayan

report.append(f"- **Skoru ayrıştırılabilen maç sayısı:** {karsilastirilabilir.sum()}\n")
report.append(f"- **Skoru boş olan satır sayısı:** {skor_olmayan}\n")
report.append(f"- **Geçersiz/İptal/Ertelenmiş formatındaki skor sayısı:** {skor_gecersiz}\n")
report.append(f"- **Skor ile MS sütunu uyuşmayan maç sayısı:** **{len(uyusmazlik)}**\n")

if len(uyusmazlik) > 0:
    report.append("\n  **Uyuşmazlık Örnekleri (Silinmedi, İnceleme Gerekli):**\n")
    for _, row in uyusmazlik.head(5).iterrows():
        report.append(f"  - Skor: `{row['Skor']}` | MS: `{row['MS']}` | Hesaplanan: `{row['Hesaplanan_Sonuc']}`\n")
report.append("\n")


# ==========================================
# 3. DÜZELTME: Sonuç ve Oran Sütunlarının Ayrımı
# ==========================================
report.append("## 3. Oran Sütunları ve Doluluk\n")

result_cols = ["MS"]
hedef_marketler = ["Maç_Sonucu_|", "Alt/Üst_|", "Karşılıklı_Gol_|"]
odds_cols = [c for c in df.columns if any(m in c for m in hedef_marketler) and c not in result_cols]

report.append(f"- Tespit edilen oran sütunu sayısı: **{len(odds_cols)}**\n")
report.append("### Seçili Oran Sütunlarının Doluluğu\n")
report.append("| Sütun | Eksik | Eksik % |\n|---|---:|---:|\n")

for col in odds_cols:
    if col in ["Maç_Sonucu_|_1", "Maç_Sonucu_|_X", "Maç_Sonucu_|_2", "2,5_Alt/Üst_|_Alt", "2,5_Alt/Üst_|_Üst", "Karşılıklı_Gol_|_Var", "Karşılıklı_Gol_|_Yok"]:
        # Oran sütunlarındaki boşlukları da eksik say
        eksik = df[col].isnull().sum()
        eksik_oran = (eksik / len(df)) * 100
        report.append(f"| `{col}` | {eksik} | %{eksik_oran:.2f} |\n")

report.append("\n> **Not:** Oranların geçerliliği (0, 1.00, 150+ gibi uç değerler) henüz incelenmedi. Bu rapor sadece yapısal bir ön denetimdir.\n")

# ==========================================
# RAPORU KAYDET
# ==========================================
os.makedirs(os.path.dirname(args.out), exist_ok=True)
with open(args.out, "w", encoding="utf-8") as f:
    f.writelines(report)

print(f"\n✅ Revize edilmiş rapor başarıyla oluşturuldu: {args.out}")