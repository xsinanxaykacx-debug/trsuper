# -*- coding: utf-8 -*-
"""
Spesifik Oran + Gün Kombinasyonu Analizi
Her market için, her spesifik oran değeri ve her gün için ROI hesaplar.
Çıktı: CSV + Excel (.xlsx)

UYARI: Bu dosya "hipotez adayları" listesidir, "kârlı stratejiler" değildir.
Küçük örneklemler ve çoklu test sorunu nedeniyle sonuçlar doğrulanmamıştır.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys

CSV_PATH = "data/csv/DATA.csv"
OUT_DIR = Path("docs")
CSV_OUT = OUT_DIR / "spesifik_oran_gun_analizi.csv"
XLSX_OUT = OUT_DIR / "spesifik_oran_gun_analizi.xlsx"
MIN_MAC = 5  # Minimum örneklem

def to_float(value):
    if pd.isna(value):
        return np.nan
    try:
        return float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return np.nan

def main():
    if not Path(CSV_PATH).exists():
        print(f"HATA: {CSV_PATH} bulunamadı.")
        sys.exit(1)

    print("Veri okunuyor...")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig", dtype=str, low_memory=False)

    # Skor ayrıştır
    skor = df["Skor"].astype(str).str.extract(r"^\s*(\d+)\s*[-:]\s*(\d+)\s*$")
    df["Ev_Gol"] = pd.to_numeric(skor[0], errors="coerce")
    df["Dep_Gol"] = pd.to_numeric(skor[1], errors="coerce")

    # Tarih ve gün
    df["Tarih_Parsed"] = pd.to_datetime(df["Tarih"], format="%d-%m-%Y", errors="coerce")
    gun_map = {
        0: "Pazartesi", 1: "Salı", 2: "Çarşamba", 3: "Perşembe",
        4: "Cuma", 5: "Cumartesi", 6: "Pazar"
    }
    df["Gun"] = df["Tarih_Parsed"].dt.dayofweek.map(gun_map)

    # Market tanımları
    markets = {
        "MS1":     ("Maç_Sonucu_|_1",         lambda d: d["Ev_Gol"] > d["Dep_Gol"]),
        "MSX":     ("Maç_Sonucu_|_X",         lambda d: d["Ev_Gol"] == d["Dep_Gol"]),
        "MS2":     ("Maç_Sonucu_|_2",         lambda d: d["Ev_Gol"] < d["Dep_Gol"]),
        "KG_VAR":  ("Karşılıklı_Gol_|_Var",   lambda d: (d["Ev_Gol"] > 0) & (d["Dep_Gol"] > 0)),
        "KG_YOK":  ("Karşılıklı_Gol_|_Yok",   lambda d: (d["Ev_Gol"] == 0) | (d["Dep_Gol"] == 0)),
        "1.5_ALT": ("1,5_Alt/Üst_|_Alt",      lambda d: (d["Ev_Gol"] + d["Dep_Gol"]) < 1.5),
        "1.5_UST": ("1,5_Alt/Üst_|_Üst",      lambda d: (d["Ev_Gol"] + d["Dep_Gol"]) > 1.5),
        "2.5_ALT": ("2,5_Alt/Üst_|_Alt",      lambda d: (d["Ev_Gol"] + d["Dep_Gol"]) < 2.5),
        "2.5_UST": ("2,5_Alt/Üst_|_Üst",      lambda d: (d["Ev_Gol"] + d["Dep_Gol"]) > 2.5),
    }

    tum_sonuclar = []

    for market_adi, (kolon, kosul) in markets.items():
        if kolon not in df.columns:
            print(f"UYARI: {kolon} sütunu bulunamadı, {market_adi} atlanıyor.")
            continue

        print(f"İşleniyor: {market_adi}...")

        df[f"{market_adi}_Oran"] = df[kolon].map(to_float)
        df[f"{market_adi}_Kazandi"] = kosul(df)
        df[f"{market_adi}_Net_Kar"] = np.where(
            df[f"{market_adi}_Kazandi"],
            df[f"{market_adi}_Oran"] - 1.0,
            -1.0,
        )

        gecerli = df.dropna(subset=[f"{market_adi}_Oran", "Gun", f"{market_adi}_Kazandi"]).copy()
        gecerli = gecerli[gecerli[f"{market_adi}_Oran"] > 1.0]
        gecerli["Oran_Yuvarlak"] = gecerli[f"{market_adi}_Oran"].round(2)

        gruplu = gecerli.groupby(["Oran_Yuvarlak", "Gun"]).agg(
            Mac_Sayisi=(f"{market_adi}_Kazandi", "size"),
            Kazanan_Sayisi=(f"{market_adi}_Kazandi", "sum"),
            Toplam_Net_Kar=(f"{market_adi}_Net_Kar", "sum"),
            Ortalama_Oran=(f"{market_adi}_Oran", "mean"),
        ).reset_index()

        gruplu["Kazanma_Orani"] = gruplu["Kazanan_Sayisi"] / gruplu["Mac_Sayisi"]
        gruplu["ROI_Yuzde"] = gruplu["Toplam_Net_Kar"] / gruplu["Mac_Sayisi"] * 100
        gruplu["Market"] = market_adi
        gruplu["Basabas_Oran"] = 1.0 / gruplu["Ortalama_Oran"]
        gruplu["Marj_Yuzde"] = (gruplu["Kazanma_Orani"] - gruplu["Basabas_Oran"]) * 100

        gruplu = gruplu[gruplu["Mac_Sayisi"] >= MIN_MAC]
        tum_sonuclar.append(gruplu)

    if not tum_sonuclar:
        print("Hiç sonuç üretilemedi.")
        sys.exit(1)

    tum = pd.concat(tum_sonuclar, ignore_index=True)
    tum = tum.sort_values("ROI_Yuzde", ascending=False)

    # Sütun sırasını düzenle
    kolonlar = [
        "Market", "Oran_Yuvarlak", "Gun", "Mac_Sayisi", "Kazanan_Sayisi",
        "Kazanma_Orani", "Ortalama_Oran", "Basabas_Oran", "Marj_Yuzde",
        "ROI_Yuzde", "Toplam_Net_Kar",
    ]
    tum = tum[kolonlar]

    # Çıktı klasörünü oluştur
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # CSV çıktısı
    tum.to_csv(CSV_OUT, index=False, encoding="utf-8-sig")
    print(f"\nCSV yazıldı: {CSV_OUT}")

    # Excel çıktısı
    try:
        with pd.ExcelWriter(XLSX_OUT, engine="openpyxl") as writer:
            tum.to_excel(writer, sheet_name="Tum_Sonuclar", index=False)

            # Ek sayfa: sadece pozitif ROI, minimum 10 maç
            filtreli = tum[(tum["ROI_Yuzde"] > 0) & (tum["Mac_Sayisi"] >= 10)]
            filtreli = filtreli.sort_values("ROI_Yuzde", ascending=False)
            filtreli.to_excel(writer, sheet_name="Pozitif_ROI_n10", index=False)

            # Ek sayfa: Market bazında özet
            ozet = tum.groupby("Market").agg(
                Toplam_Kombinasyon=("ROI_Yuzde", "size"),
                Pozitif_ROI=("ROI_Yuzde", lambda s: (s > 0).sum()),
                Ortalama_ROI=("ROI_Yuzde", "mean"),
                En_Yuksek_ROI=("ROI_Yuzde", "max"),
            ).reset_index()
            ozet.to_excel(writer, sheet_name="Market_Ozeti", index=False)

        print(f"Excel yazıldı: {XLSX_OUT}")
        print(f"  - Sayfa 1: Tum_Sonuclar ({len(tum)} satır)")
        print(f"  - Sayfa 2: Pozitif_ROI_n10 ({len(filtreli)} satır)")
        print(f"  - Sayfa 3: Market_Ozeti ({len(ozet)} market)")
    except ImportError:
        print("\nUYARI: openpyxl kurulu değil. Excel için:")
        print("  python -m pip install openpyxl")

    # Konsol özeti
    print(f"\n=== ÖZET ===")
    print(f"Toplam kombinasyon: {len(tum)}")
    print(f"Minimum maç eşiği: {MIN_MAC}")
    print(f"\nEn yüksek 10 ROI (dikkat: hipotez adayı, strateji değil):")
    print(tum.head(10)[[
        "Market", "Oran_Yuvarlak", "Gun", "Mac_Sayisi", "Kazanan_Sayisi", "ROI_Yuzde"
    ]].to_string(index=False))

    print(f"\nUYARI: Bu liste 'hipotez adayları'dır.")
    print(f"- n={MIN_MAC} gibi küçük örneklemlerde ROI güvenilmez.")
    print(f"- {len(tum)} test içinde en iyi 10'u şans eseri pozitif gösterebilir.")
    print(f"- Doğrulama için bağımsız dönem + FDR düzeltmesi gerekir.")

if __name__ == "__main__":
    main()