# -*- coding: utf-8 -*-
"""Oran kalitesi ve maç bütünlüğü denetim betiği."""
import pandas as pd
import numpy as np
from pathlib import Path
import sys

CSV_PATH = "data/csv/DATA.csv"
OUT_PATH = "docs/odds_integrity_report.md"

def main():
    if not Path(CSV_PATH).exists():
        print(f"HATA: {CSV_PATH} bulunamadı.")
        sys.exit(1)

    print("Veri okunuyor...")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig", sep=",", dtype=str)
    
    # Boşlukları ve bilinen eksik metinlerini NaN yap
    df = df.replace(r'^\s*$', np.nan, regex=True)
    df = df.replace(["NAN", "NONE", "NAT", "<NA>", "NULL"], np.nan)

    report = []
    report.append("# Oran Kalitesi ve Maç Bütünlüğü Denetim Raporu\n")
    report.append(f"- **Toplam Satır:** {len(df)}\n")
    report.append(f"- **Toplam Sütun:** {len(df.columns)}\n\n")

    # ==========================================
    # 1. MAÇ KİMLİĞİ VE TEKRAR KONTROLÜ
    # ==========================================
    report.append("## 1. Maç Kimliği ve Tekrar Kontrolü\n")
    if "Maç_ID" in df.columns:
        tekrarlar = df["Maç_ID"].duplicated().sum()
        eksik_id = df["Maç_ID"].isnull().sum()
        report.append(f"- **Maç_ID Sütunu:** Mevcut\n")
        report.append(f"- Tekrar eden Maç_ID sayısı: **{tekrarlar}**\n")
        report.append(f"- Eksik Maç_ID sayısı: **{eksik_id}**\n")
    else:
        report.append("- **Maç_ID sütunu bulunamadı!** (Kritik eksiklik)\n")
    
    # Tüm satır bazında tam kopya kontrolü
    tam_kopya = df.duplicated().sum()
    report.append(f"- Birebir aynı olan (tüm sütunları kopya) satır sayısı: **{tam_kopya}**\n\n")


    # ==========================================
    # 2. ORAN SÜTUNLARININ TESPİTİ VE SAYISAL KONTROLÜ
    # ==========================================
    report.append("## 2. Oran Sütunlarının Sayısal Doğrulaması\n")
    
    # Oran sütunlarını bul ('|' içeren ve İSTATİSTİK olmayan)
    odds_cols = [c for c in df.columns if "|" in c and not c.startswith("İSTATİSTİK")]
    
    gecerli_oran_sutunlari = []
    sayisal_olmayan_sutunlar = []
    
    for col in odds_cols:
        # Sütunu sayıya çevirmeyi dene (virgülleri nokta yap)
        numeric_series = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
        
        # Eksik olmayan ama sayıya dönüşemeyen (yani metin içeren) hücreleri bul
        non_numeric_mask = df[col].notna() & numeric_series.isnull()
        non_numeric_count = non_numeric_mask.sum()
        
        if non_numeric_count > 0:
            ornekler = df.loc[non_numeric_mask, col].unique()[:3]
            sayisal_olmayan_sutunlar.append((col, non_numeric_count, ornekler))
        else:
            # Eğer tamamen sayısalsa, geçerli oran sütunu listesine ekle
            gecerli_oran_sutunlari.append(col)
            df[col] = numeric_series # Orijinal df'i güncelle (sadece bellekte)

    report.append(f"- Toplam `|` içeren sütun sayısı: {len(odds_cols)}\n")
    report.append(f"- **Gerçekten sayısal olan oran sütunu sayısı:** {len(gecerli_oran_sutunlari)}\n")
    
    if sayisal_olmayan_sutunlar:
        report.append("\n### ⚠️ İçinde Sayısal Olmayan Değer Barındıran Sütunlar\n")
        report.append("| Sütun | Metin/Hata İçeren Hücre Sayısı | Örnek Değerler |\n|---|---:|---|\n")
        for col, count, ornekler in sayisal_olmayan_sutunlar[:20]: # İlk 20'yi göster
            report.append(f"| `{col}` | {count} | {list(ornekler)} |\n")
        report.append("\n*(Not: Bu sütunlar analize alınmamalı veya metinler temizlenmelidir.)*\n\n")
    else:
        report.append("- Tüm oran sütunları başarıyla sayıya dönüştürüldü (Sayısal olmayan metin yok).\n\n")


    # ==========================================
    # 3. GEÇERSİZ ORAN DEĞERLERİ (0, <=1.00, Uç Değerler)
    # ==========================================
    report.append("## 3. Geçersiz ve Mantıksız Oran Değerleri\n")
    report.append("| Sütun | 0 Değeri | <= 1.00 | 150+ | 1000+ |\n|---|---:|---:|---:|---:|\n")
    
    for col in gecerli_oran_sutunlari: # Sadece temiz sayısal sütunlar
        sifir = (df[col] == 0).sum()
        birden_kucuk = ((df[col] > 0) & (df[col] <= 1.00)).sum()
        yuksek_150 = (df[col] >= 150).sum()
        yuksek_1000 = (df[col] >= 1000).sum()
        
        # Eğer sütunda herhangi bir anormallik varsa rapora ekle
        if sifir > 0 or birden_kucuk > 0 or yuksek_150 > 0 or yuksek_1000 > 0:
            report.append(f"| `{col}` | {sifir} | {birden_kucuk} | {yuksek_150} | {yuksek_1000} |\n")
    report.append("\n")


    # ==========================================
    # 4. MARKET BAZINDA EKSİKLİK (PAIRWISE MISSINGNESS)
    # ==========================================
    report.append("## 4. Karşılıklı Market Eksiklikleri (Alt/Üst Farkları)\n")
    
    # İncelenecek çiftler
    pairs = [
        ("1,5_Alt/Üst_|_Alt", "1,5_Alt/Üst_|_Üst"),
        ("2,5_Alt/Üst_|_Alt", "2,5_Alt/Üst_|_Üst"),
        ("3,5_Alt/Üst_|_Alt", "3,5_Alt/Üst_|_Üst"),
        ("4,5_Alt/Üst_|_Alt", "4,5_Alt/Üst_|_Üst"),
        ("1._Yarı_2,5_Alt/Üst_|_Alt", "1._Yarı_2,5_Alt/Üst_|_Üst"),
        ("Karşılıklı_Gol_|_Var", "Karşılıklı_Gol_|_Yok")
    ]
    
    report.append("| Market Çifti | Sadece 1. Taraf Dolu | Sadece 2. Taraf Dolu | Her İkisi Boş | Her İkisi Dolu |\n")
    report.append("|---|---:|---:|---:|---:|\n")
    
    for col1, col2 in pairs:
        if col1 in df.columns and col2 in df.columns:
            sadece_1 = (df[col1].notna() & df[col2].isnull()).sum()
            sadece_2 = (df[col1].isnull() & df[col2].notna()).sum()
            ikisi_de_bos = (df[col1].isnull() & df[col2].isnull()).sum()
            ikisi_de_dolu = (df[col1].notna() & df[col2].notna()).sum()
            
            report.append(f"| `{col1.replace('_|_', ' vs ')}` | {sadece_1} | {sadece_2} | {ikisi_de_bos} | {ikisi_de_dolu} |\n")
            
    report.append("\n> **Yorum:** Eğer \"Sadece 1. Taraf Dolu\" veya \"Sadece 2. Taraf Dolu\" sayıları yüksekse, veri kaynağında ciddi bir asimetri (tek taraflı eksiklik) vardır. Bu durum analizde yanlılığa yol açar.\n")

    # ==========================================
    # RAPORU KAYDET
    # ==========================================
    Path("docs").mkdir(exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.writelines(report)

    print(f"\n✅ Denetim raporu başarıyla oluşturuldu: {OUT_PATH}")
    print("Lütfen bu dosyayı inceleyip oranların güvenilirliğini onaylayın.")

if __name__ == "__main__":
    main()
