import pandas as pd
import numpy as np
import os
import sys

# --- AYARLAR ---
CSV_PATH = "DATA.csv"
REPORT_PATH = "docs/data_quality_report.md"

if not os.path.exists(CSV_PATH):
    print(f"HATA: {CSV_PATH} bulunamadı.")
    sys.exit(1)

print("Veri okunuyor... (Lütfen bekleyin)")
df = pd.read_csv(CSV_PATH, encoding="utf-8-sig", sep=",", dtype=str)

# Rapor metni için liste
report = []
report.append("# DATA.csv — Veri Kalitesi Denetim Raporu (Revize)\n")
report.append(f"- **Toplam Satır:** {len(df)}\n")
report.append(f"- **Toplam Sütun:** {len(df.columns)}\n\n")

# ==========================================
# 1. DÜZELTME: Lig ve Sezon Ayrımı
# ==========================================
report.append("## 1. Lig ve Sezon Sınıflandırması\n")
if "Lig/Sezon" in df.columns:
    # Sezonu regex ile yakala (Örn: 2020/2021)
    df["Sezon"] = df["Lig/Sezon"].str.extract(r"(\d{4}/\d{4})", expand=False)
    
    # Ligi sezon kısmını çıkararak bul
    df["Lig"] = df["Lig/Sezon"].str.replace(r"\s*\d{4}/\d{4}", "", regex=True).str.strip()
    
    missing_season = df["Sezon"].isnull().sum()
    report.append(f"- Sezonu belirlenemeyen satır sayısı: **{missing_season}**\n")
    
    if missing_season > 0:
        report.append("  - Örnek Belirlenemeyen Değerler: ")
        ornekler = df[df["Sezon"].isnull()]["Lig/Sezon"].dropna().unique()[:5]
        report.append(f"{', '.join(map(str, ornekler))}\n")
    
    report.append(f"- Tespit edilen benzersiz lig sayısı: **{df['Lig'].nunique()}**\n")
    report.append(f"- Tespit edilen benzersiz sezon sayısı: **{df['Sezon'].nunique()}**\n\n")
else:
    report.append("- `Lig/Sezon` sütunu bulunamadı.\n\n")


# ==========================================
# 2. DÜZELTME: Skor ve MS Tutarlılığı
# ==========================================
report.append("## 2. Skor ve Sonuç (MS) Tutarlılığı\n")

# Skor formatını güvenli ayır (Örn: "1-3", "1 - 3", "1:3" hepsini yakalar)
# Sadece rakam ve aradaki ayracı alır, "İptal" gibi metinleri NaN yapar.
skor_split = df["Skor"].str.extract(r"^\s*(\d+)\s*[-:]\s*(\d+)\s*$")
df["Ev_Gol"] = pd.to_numeric(skor_split[0], errors="coerce")
df["Dep_Gol"] = pd.to_numeric(skor_split[1], errors="coerce")

# Vektörel sonuç hesaplama
conditions = [
    (df["Ev_Gol"] > df["Dep_Gol"]),
    (df["Ev_Gol"] == df["Dep_Gol"]),
    (df["Ev_Gol"] < df["Dep_Gol"])
]
choices = ["1", "X", "2"]
df["Hesaplanan_Sonuc"] = np.select(conditions, choices, default=np.nan)

# MS sütununu temizle
df["MS_Temiz"] = df["MS"].astype(str).str.strip().str.upper()

# Karşılaştırma (Sadece skoru geçerli olanlar)
karsilastirilabilir = df["Hesaplanan_Sonuc"].notna() & df["MS_Temiz"].notna()
uyusmazlik = df[karsilastirilabilir & (df["Hesaplanan_Sonuc"] != df["MS_Temiz"])]

report.append(f"- **Skoru ayrıştırılabilen maç sayısı:** {karsilastirilabilir.sum()}\n")
report.append(f"- **Skoru ayrıştırılamayan (İptal, Ertelendi vb.):** {df['Hesaplanan_Sonuc'].isnull().sum()}\n")
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

# Kesin Sonuç Sütunları
result_cols = ["MS"]

# Oran Sütunları: Belirli marketleri hedef al, sonuç sütunlarını hariç tut
# Sadece oran olduğu kesin olan kalıpları arıyoruz. 
hedef_marketler = ["Maç_Sonucu_|", "Alt/Üst_|", "Karşılıklı_Gol_|"]
odds_cols = [c for c in df.columns if any(m in c for m in hedef_marketler) and c not in result_cols]

report.append(f"- Tespit edilen oran sütunu sayısı: **{len(odds_cols)}**\n")
report.append("### Seçili Oran Sütunlarının Doluluğu\n")
report.append("| Sütun | Eksik | Eksik % |\n|---|---:|---:|\n")

for col in odds_cols:
    # Sadece temel marketleri raporlayalım, rapor şişmesin
    if col in ["Maç_Sonucu_|_1", "Maç_Sonucu_|_X", "Maç_Sonucu_|_2", "2,5_Alt/Üst_|_Alt", "2,5_Alt/Üst_|_Üst", "Karşılıklı_Gol_|_Var", "Karşılıklı_Gol_|_Yok"]:
        eksik = df[col].isnull().sum()
        eksik_oran = (eksik / len(df)) * 100
        report.append(f"| `{col}` | {eksik} | %{eksik_oran:.2f} |\n")

report.append("\n> **Not:** Oranların geçerliliği (0, 1.00, 150+ gibi uç değerler) henüz incelenmedi. Bu rapor sadece yapısal bir ön denetimdir.\n")

# ==========================================
# RAPORU KAYDET
# ==========================================
os.makedirs("docs", exist_ok=True)
with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.writelines(report)

print(f"\n✅ Revize edilmiş rapor başarıyla oluşturuldu: {REPORT_PATH}")
print("Lütfen bu dosyayı repoya commit'leyip içeriğini inceleyelim.")