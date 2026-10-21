# -*- coding: utf-8 -*-
"""DATA.csv için salt okunur veri kalitesi raporu üretir."""
import argparse
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ZORUNLU_SUTUNLAR = ["Skor", "MS", "Lig/Sezon"]
MARKET_ISARETLERI = (
    "Maç_Sonucu_|",
    "Alt/Üst_|",
    "Karşılıklı_Gol_|",
)
IPTAL_IFADELERI = (
    "iptal", "ertelen", "hükmen", "hukmen", "oynanmadı", "oynanmadi", 
    "postponed", "cancelled", "canceled", "abandoned"
)
EKSIK_METINLER = {"", "NAN", "NONE", "NAT", "<NA>", "NULL"}

def argumanlari_al():
    parser = argparse.ArgumentParser(description="DATA.csv veri kalitesi denetimi")
    parser.add_argument("--csv", default="data/csv/DATA.csv", help="Ham CSV dosyasının yolu")
    parser.add_argument("--out", default="docs/data_quality_report.md", help="Çıktı raporunun yolu")
    return parser.parse_args()

def main():
    args = argumanlari_al()
    csv_path = Path(args.csv)
    out_path = Path(args.out)

    if not csv_path.exists():
        print(f"HATA: {csv_path} bulunamadı. Lütfen yolu kontrol edin.")
        sys.exit(1)

    print(f"Veri okunuyor: {csv_path}")
    df = pd.read_csv(csv_path, encoding="utf-8-sig", sep=",", dtype=str)

    # Boşluk içeren hücreleri NaN yap
    df = df.replace(r'^\s*$', np.nan, regex=True)

    # Zorunlu sütun kontrolü
    eksik_zorunlu = [col for col in ZORUNLU_SUTUNLAR if col not in df.columns]
    if eksik_zorunlu:
        print(f"HATA: Şu zorunlu sütunlar bulunamadı: {eksik_zorunlu}")
        sys.exit(1)

    report = []
    report.append("# DATA.csv — Veri Kalitesi Denetim Raporu\n")
    report.append(f"- **Toplam Satır:** {len(df)}\n")
    report.append(f"- **Toplam Sütun:** {len(df.columns)}\n\n")

    # ==========================================
    # 1. LİG VE SEZON AYRIMI (Regex Düzeltildi)
    # ==========================================
    report.append("## 1. Lig ve Sezon Sınıflandırması\n")
    
    # Sezonu ayıklarken olası boşlukları tolere et (örn: "2020 / 2021")
    df["Sezon"] = df["Lig/Sezon"].str.extract(r"(\d{4}\s*/\s*\d{4})", expand=False)
    df["Sezon"] = df["Sezon"].str.replace(r"\s+", "", regex=True) # İçindeki boşlukları temizle
    
    # Ligi ayıklarken sezon kısmını (ve etrafındaki boşlukları) sil
    df["Lig"] = df["Lig/Sezon"].str.replace(r"\s*\d{4}\s*/\s*\d{4}", "", regex=True).str.strip()

    missing_season = df["Sezon"].isnull().sum()
    report.append(f"- Sezonu belirlenemeyen satır sayısı: **{missing_season}**\n")
    if missing_season > 0:
        ornekler = df[df["Sezon"].isnull()]["Lig/Sezon"].dropna().unique()[:3]
        report.append(f"  - Örnek Belirlenemeyen Değerler: {ornekler}\n")

    report.append(f"- Tespit edilen benzersiz lig sayısı: **{df['Lig'].nunique()}**\n")
    report.append(f"- Tespit edilen benzersiz sezon sayısı: **{df['Sezon'].nunique()}**\n\n")


    # ==========================================
    # 2. SKOR VE MS TUTARLILIĞI (Kategoriler Dışlayıcı)
    # ==========================================
    report.append("## 2. Skor ve Sonuç (MS) Tutarlılığı\n")

    # Skor formatını güvenli ayır (Sadece "1-3", "1 : 3" gibi net skorları alır)
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
    df["Hesaplanan_Sonuc"] = np.select(conditions, choices, default=None)

    # MS sütununu temizle
    df["MS_Temiz"] = df["MS"].str.strip().str.upper()
    df.loc[df["MS_Temiz"].isin(EKSIK_METINLER), "MS_Temiz"] = np.nan

    # --- DIŞLAYICI KATEGORİLER ---
    # 1. Boş Skorlar
    mask_bos = df["Skor"].isnull()
    
    # 2. İptal/Ertelenen Skorlar (Boş olmayanlar arasından)
    mask_iptal = ~mask_bos & df["Skor"].str.contains("|".join(IPTAL_IFADELERI), case=False, na=False)
    
    # 3. Geçerli Skorlar (Rakamlara başarıyla ayrıştırılanlar)
    mask_gecerli = df["Hesaplanan_Sonuc"].notna()
    
    # 4. Geçersiz Format (Boş olmayan, iptal olmayan ama sayıya dönmeyen)
    mask_gecersiz_format = ~mask_bos & ~mask_iptal & ~mask_gecerli

    # Karşılaştırma (Hem skoru hem MS'i geçerli olanlar)
    karsilastirilabilir = mask_gecerli & df["MS_Temiz"].notna()
    uyusmazlik = df[karsilastirilabilir & (df["Hesaplanan_Sonuc"] != df["MS_Temiz"])]

    report.append(f"- **Skoru ayrıştırılabilen (Geçerli) maç sayısı:** {mask_gecerli.sum()}\n")
    report.append(f"- **MS değeri olan ve karşılaştırılabilen maç sayısı:** {karsilastirilabilir.sum()}\n")
    report.append(f"- **Skor ile MS sütunu uyuşmayan maç sayısı:** **{len(uyusmazlik)}**\n")
    report.append("\n  **Skor Kategori Dağılımı (Birbirini Dışlayan):**\n")
    report.append(f"  - Skoru boş olan satır sayısı: {mask_bos.sum()}\n")
    report.append(f"  - İptal/Ertelenen/Hükmen içeren skor sayısı: {mask_iptal.sum()}\n")
    report.append(f"  - Tanınmayan/Geçersiz formattaki skor sayısı: {mask_gecersiz_format.sum()}\n")

    if len(uyusmazlik) > 0:
        report.append("\n  **Uyuşmazlık Örnekleri (Silinmedi, İnceleme Gerekli):**\n")
        for _, row in uyusmazlik.head(5).iterrows():
            report.append(f"  - Skor: `{row['Skor']}` | MS: `{row['MS']}` | Hesaplanan: `{row['Hesaplanan_Sonuc']}`\n")
    report.append("\n")


    # ==========================================
    # 3. ORAN SÜTUNLARI VE DOLULUK
    # ==========================================
    report.append("## 3. Oran Sütunları ve Doluluk\n")

    result_cols = ["MS"]
    odds_cols = [c for c in df.columns if any(m in c for m in MARKET_ISARETLERI) and c not in result_cols]

    report.append(f"- Tespit edilen oran sütunu sayısı: **{len(odds_cols)}**\n")
    report.append("### Tüm Oran Sütunlarının Doluluğu\n")
    report.append("| Sütun | Eksik | Eksik % |\n|---|---:|---:|\n")

    for col in odds_cols:
        eksik = df[col].isnull().sum()
        eksik_oran = (eksik / len(df)) * 100
        report.append(f"| `{col}` | {eksik} | %{eksik_oran:.2f} |\n")

    report.append("\n> **Not:** Oranların geçerliliği (0, 1.00, 150+ gibi uç değerler) henüz incelenmedi. Bu rapor sadece yapısal bir ön denetimdir.\n")

    # ==========================================
    # RAPORU KAYDET (Güvenli Path)
    # ==========================================
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(report)

    print(f"\n✅ Rapor başarıyla oluşturuldu: {out_path}")
    print("Lütfen bu dosyayı inceleyip skor/MS uyuşmazlığını kontrol edin.")

if __name__ == "__main__":
    main()