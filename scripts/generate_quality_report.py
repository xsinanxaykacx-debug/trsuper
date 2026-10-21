# -*- coding: utf-8 -*-
"""DATA.csv için salt okunur veri kalitesi raporu üretir; ham CSV'yi değiştirmez."""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ZORUNLU_SUTUNLAR = ["Skor", "MS", "Lig/Sezon"]
GECERLI_MS = {"1", "X", "2"}
IPTAL_IFADELERI = (
    "iptal", "ertelen", "hükmen", "hukmen", "oynanmadı", "oynanmadi",
    "postponed", "cancelled", "canceled", "abandoned",
)
EKSIK_METINLER = {"", "NAN", "NONE", "NAT", "<NA>", "NULL"}
ISTATISTIK_ON_EKLERI = ("İSTATİSTİK", "ISTATISTIK")


def argumanlari_al():
    parser = argparse.ArgumentParser(
        description="DATA.csv veri kalitesi denetimi; ham veriyi değiştirmez."
    )
    parser.add_argument("--csv", default="data/csv/DATA.csv",
                        help="Ham CSV yolu (varsayılan: data/csv/DATA.csv)")
    parser.add_argument("--out", default="docs/data_quality_report.md",
                        help="Rapor yolu (varsayılan: docs/data_quality_report.md)")
    return parser.parse_args()


def eksikleri_temizle(df):
    """Boşlukları ve metinsel eksik belirteçlerini tüm sütunlarda temizler."""
    df = df.replace(r"^\s*$", np.nan, regex=True)
    return df.replace(
        to_replace=r"(?i)^\s*(?:nan|none|nat|<na>|null)\s*$",
        value=np.nan,
        regex=True,
    )


def oran_sutunlarini_bul(columns):
    """İstatistik sütunlarını dışarıda tutup tüm market seçeneği sütunlarını bulur."""
    odds_cols = []
    for col in columns:
        ad = str(col).strip()
        if "|" not in ad:
            continue
        ad_upper = ad.upper()
        if any(ad_upper.startswith(prefix) for prefix in ISTATISTIK_ON_EKLERI):
            continue
        odds_cols.append(col)
    return odds_cols


def main():
    args = argumanlari_al()
    csv_path = Path(args.csv)
    out_path = Path(args.out)

    if not csv_path.is_file():
        print(f"HATA: {csv_path} bulunamadı. CSV yolunu kontrol edin.", file=sys.stderr)
        return 1

    print(f"Veri okunuyor: {csv_path}")
    try:
        df = pd.read_csv(
            csv_path,
            encoding="utf-8-sig",
            sep=",",
            dtype=str,
            keep_default_na=True,
            na_values=list(EKSIK_METINLER),
            low_memory=False,
        )
    except (OSError, UnicodeError, pd.errors.ParserError, ValueError) as exc:
        print(f"HATA: CSV okunamadı: {exc}", file=sys.stderr)
        return 1

    df = eksikleri_temizle(df)
    eksik_zorunlu = [col for col in ZORUNLU_SUTUNLAR if col not in df.columns]
    if eksik_zorunlu:
        print(f"HATA: Zorunlu sütun(lar) bulunamadı: {eksik_zorunlu}", file=sys.stderr)
        return 1

    report = [
        "# DATA.csv — Veri Kalitesi Denetim Raporu\n\n",
        f"- **Toplam satır:** {len(df)}\n",
        f"- **Toplam sütun:** {len(df.columns)}\n",
        f"- **Kaynak dosya:** {csv_path.as_posix()}\n\n",
    ]

    # 1. Lig ve sezon sınıflandırması
    report.append("## 1. Lig ve Sezon Sınıflandırması\n\n")
    lig_sezon = df["Lig/Sezon"].astype("string")
    df["Sezon"] = lig_sezon.str.extract(r"(\d{4}\s*/\s*\d{4})", expand=False)
    df["Sezon"] = df["Sezon"].str.replace(r"\s+", "", regex=True)
    df["Lig"] = lig_sezon.str.replace(
        r"\s*\d{4}\s*/\s*\d{4}", "", regex=True
    ).str.strip()

    missing_season = int(df["Sezon"].isna().sum())
    report.append(f"- Sezonu belirlenemeyen satır sayısı: **{missing_season}**\n")
    if missing_season:
        examples = df.loc[df["Sezon"].isna(), "Lig/Sezon"].dropna().astype(str).unique()[:5]
        if len(examples):
            report.append("- Örnek değerler: " + ", ".join(str(x) for x in examples) + "\n")
    report.append(f"- Tespit edilen benzersiz lig sayısı: **{df['Lig'].nunique(dropna=True)}**\n")
    report.append(f"- Tespit edilen benzersiz sezon sayısı: **{df['Sezon'].nunique(dropna=True)}**\n\n")

    # 2. Skor ve MS tutarlılığı
    report.append("## 2. Skor ve Sonuç (MS) Tutarlılığı\n\n")
    skor = df["Skor"].astype("string")
    skor_split = skor.str.extract(r"^\s*(\d+)\s*[-:]\s*(\d+)\s*$")
    df["Ev_Gol"] = pd.to_numeric(skor_split[0], errors="coerce")
    df["Dep_Gol"] = pd.to_numeric(skor_split[1], errors="coerce")

    conditions = [
        df["Ev_Gol"] > df["Dep_Gol"],
        df["Ev_Gol"] == df["Dep_Gol"],
        df["Ev_Gol"] < df["Dep_Gol"],
    ]
    df["Hesaplanan_Sonuc"] = np.select(conditions, ["1", "X", "2"], default="")
    df.loc[df["Ev_Gol"].isna() | df["Dep_Gol"].isna(), "Hesaplanan_Sonuc"] = np.nan

    df["MS_Temiz"] = df["MS"].astype("string").str.strip().str.upper()
    df.loc[df["MS_Temiz"].isin(EKSIK_METINLER), "MS_Temiz"] = pd.NA
    ms_dolu = df["MS_Temiz"].notna()
    ms_gecerli = df["MS_Temiz"].isin(GECERLI_MS)
    ms_gecersiz = ms_dolu & ~ms_gecerli

    mask_bos = df["Skor"].isna()
    skor_metin = df["Skor"].astype("string")
    mask_iptal = (
        ~mask_bos
        & skor_metin.str.contains("|".join(IPTAL_IFADELERI), case=False, na=False, regex=True)
    )
    mask_gecerli = df["Hesaplanan_Sonuc"].notna()
    mask_gecersiz_format = ~mask_bos & ~mask_iptal & ~mask_gecerli

    karsilastirilabilir = mask_gecerli & ms_gecerli
    uyusmazlik_maskesi = karsilastirilabilir & (
        df["Hesaplanan_Sonuc"] != df["MS_Temiz"]
    )
    uyusmazlik = df.loc[uyusmazlik_maskesi]

    report.append(f"- **Skoru ayrıştırılabilen satır sayısı:** {int(mask_gecerli.sum())}\n")
    report.append(f"- **MS değeri geçerli (1/X/2) olan satır sayısı:** {int(ms_gecerli.sum())}\n")
    report.append(f"- **MS değeri eksik olan satır sayısı:** {int((~ms_dolu).sum())}\n")
    report.append(f"- **Geçersiz MS değerine sahip satır sayısı:** **{int(ms_gecersiz.sum())}**\n")
    report.append(f"- **Skor ve MS karşılaştırması yapılabilen maç sayısı:** {int(karsilastirilabilir.sum())}\n")
    report.append(f"- **Skor ile MS sütunu uyuşmayan maç sayısı:** **{len(uyusmazlik)}**\n")
    report.append("\n**Skor kategorileri (birbirini dışlayan):**\n")
    report.append(f"- Skoru boş olan satır sayısı: {int(mask_bos.sum())}\n")
    report.append(f"- İptal/ertelenen/hükmen ifadesi içeren skor sayısı: {int(mask_iptal.sum())}\n")
    report.append(f"- Tanınmayan/geçersiz formattaki skor sayısı: {int(mask_gecersiz_format.sum())}\n")

    if ms_gecersiz.any():
        invalid_counts = df.loc[ms_gecersiz, "MS_Temiz"].value_counts().head(10)
        report.append("\n**En sık görülen geçersiz MS değerleri (ilk 10):**\n")
        for value, count in invalid_counts.items():
            report.append(f"- {value}: {int(count)} satır\n")

    if len(uyusmazlik):
        report.append("\n**Uyuşmazlık örnekleri (inceleme gerekli):**\n")
        for _, row in uyusmazlik.head(10).iterrows():
            report.append(
                f"- Skor: {row['Skor']} | MS: {row['MS']} | "
                f"Hesaplanan: {row['Hesaplanan_Sonuc']}\n"
            )
    report.append("\n")

    # 3. Tüm market/oran sütunları ve eksiklikleri
    report.append("## 3. Oran Sütunları ve Doluluk\n\n")
    odds_cols = oran_sutunlarini_bul(df.columns)
    report.append(f"- **Tespit edilen market/oran sütunu sayısı:** {len(odds_cols)}\n")
    report.append("- Sütun seçimi: adında | karakteri bulunan ve İSTATİSTİK/ISTATISTIK ile başlamayan sütunlar.\n\n")
    report.append("### Tüm market/oran sütunlarının doluluğu\n\n")
    report.append("| Sütun | Eksik | Dolu | Eksik % |\n|---|---:|---:|---:|\n")
    satir_sayisi = len(df)
    for col in odds_cols:
        eksik = int(df[col].isna().sum())
        dolu = satir_sayisi - eksik
        eksik_oran = (eksik / satir_sayisi * 100) if satir_sayisi else 0.0
        report.append(f"| {col} | {eksik} | {dolu} | %{eksik_oran:.2f} |\n")

    report.append("\n> **Kapsam notu:** Bu rapor yapısal ön denetimdir. Oranların sayısal olup olmadığı, 0/1.00 gibi geçersiz değerler ve uç değerler ayrıca denetlenmemiştir.\n")
    report.append("> **Veri güvenliği:** Kaynak CSV salt okunur kullanılır; bu betik ham veriyi değiştirmez.\n")

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("".join(report), encoding="utf-8")
    except OSError as exc:
        print(f"HATA: Rapor yazılamadı: {exc}", file=sys.stderr)
        return 1

    print(f"Rapor oluşturuldu: {out_path}")
    print(f"Satır: {len(df)} | Sütun: {len(df.columns)} | Market/oran sütunu: {len(odds_cols)}")
    print(f"Karşılaştırılabilir maç: {int(karsilastirilabilir.sum())} | Uyuşmazlık: {len(uyusmazlik)}")
    print(f"Geçersiz MS: {int(ms_gecersiz.sum())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
