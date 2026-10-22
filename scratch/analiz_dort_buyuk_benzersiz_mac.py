# -*- coding: utf-8 -*-
import re
from pathlib import Path

import numpy as np
import pandas as pd

GIRDI = Path("data/csv/DATA.csv")
CIKTI = Path("data/bankroll_ruin_simulation/dort_buyuk_unique")
CIKTI.mkdir(parents=True, exist_ok=True)

TAKIMLAR = {"Galatasaray", "Fenerbahçe", "Beşiktaş", "Trabzonspor"}

ORAN_SUTUNLARI = {
    "MS1": "Maç_Sonucu_|_1",
    "MSX": "Maç_Sonucu_|_X",
    "MS2": "Maç_Sonucu_|_2",
}


def oran_duzelt(seri):
    s = seri.astype("string").str.strip()
    s = s.str.replace(",", ".", regex=False)
    s = s.replace(["", "-", "NA", "N/A", "nan", "None"], pd.NA)
    sayi = pd.to_numeric(s, errors="coerce")
    return sayi.where(np.isfinite(sayi) & (sayi > 1.0))


def skor_sonucu(deger):
    if pd.isna(deger):
        return pd.NA

    eslesme = re.search(
        r"(?<!\d)(\d+)\s*[-:]\s*(\d+)(?!\d)",
        str(deger)
    )

    if not eslesme:
        return pd.NA

    ev_gol = int(eslesme.group(1))
    dep_gol = int(eslesme.group(2))

    if ev_gol > dep_gol:
        return "1"
    if ev_gol == dep_gol:
        return "X"
    return "2"


def donem_belirle(yil):
    if yil <= 2019:
        return "KESIF_2014_2019"
    if yil <= 2022:
        return "DOGRULAMA_2020_2022"
    return "ILERI_TEST_2023_SONRASI"


def ozetle(veri, gruplar):
    sonuclar = []

    for anahtar, grup in veri.groupby(
        gruplar,
        dropna=False,
        sort=True
    ):
        if not isinstance(anahtar, tuple):
            anahtar = (anahtar,)

        bahisler = grup.loc[grup["Bahis_Gecerli"]].copy()

        n = len(bahisler)
        kazanan = int(bahisler["Bahis_Kazandi"].sum()) if n else 0
        kaybeden = n - kazanan
        net_kar = float(bahisler["Kar_Zarar"].sum()) if n else 0.0

        satir = dict(zip(gruplar, anahtar))
        satir.update({
            "Bahis_Sayisi": n,
            "Kazanan_Bahis": kazanan,
            "Kaybeden_Bahis": kaybeden,
            "Kazanma_Yuzdesi": (
                100.0 * kazanan / n if n else np.nan
            ),
            "Ortalama_Oran": (
                float(bahisler["Bahis_Orani"].mean())
                if n else np.nan
            ),
            "Toplam_Bahis_Tutari": float(n),
            "Net_Kar_Zarar": net_kar,
            "ROI_Yuzde": (
                100.0 * net_kar / n if n else np.nan
            ),
        })

        sonuclar.append(satir)

    return pd.DataFrame(sonuclar)


def ana():
    if not GIRDI.exists():
        raise FileNotFoundError(
            f"Kaynak dosya bulunamadı: {GIRDI.resolve()}"
        )

    print("DATA.csv okunuyor...")
    df = pd.read_csv(
        GIRDI,
        encoding="utf-8-sig",
        dtype=str,
        low_memory=False
    )
    df.columns = [str(sutun).strip() for sutun in df.columns]

    gerekli = [
        "Tarih",
        "Skor",
        "Ev_Sahibi",
        "Deplasman",
        *ORAN_SUTUNLARI.values()
    ]

    eksik = [sutun for sutun in gerekli if sutun not in df.columns]

    if eksik:
        raise ValueError(
            f"DATA.csv içinde eksik sütunlar: {eksik}\n"
            f"Mevcut sütunlar: {df.columns.tolist()}"
        )

    df["Tarih_Parsed"] = pd.to_datetime(
        df["Tarih"],
        dayfirst=True,
        errors="coerce"
    )

    df["Ev_Sahibi"] = df["Ev_Sahibi"].astype("string").str.strip()
    df["Deplasman"] = df["Deplasman"].astype("string").str.strip()
    df["Sonuc"] = df["Skor"].map(skor_sonucu)

    for market, sutun in ORAN_SUTUNLARI.items():
        df[market] = oran_duzelt(df[sutun])

    # Dört büyük takımdan en az birinin oynadığı maçlar.
    maske = (
        df["Ev_Sahibi"].isin(TAKIMLAR)
        | df["Deplasman"].isin(TAKIMLAR)
    )

    maclar = df.loc[maske].copy()
    maclar = maclar.dropna(
        subset=["Tarih_Parsed", "Sonuc"]
    ).copy()

    ilk_satir_sayisi = len(maclar)

    # Aynı maçın iki takım üzerinden iki kez sayılmasını engelle.
    maclar["Benzersiz_Mac_Anahtari"] = (
        maclar["Tarih_Parsed"].dt.strftime("%Y-%m-%d").fillna("")
        + "|" + maclar["Ev_Sahibi"].fillna("")
        + "|" + maclar["Deplasman"].fillna("")
    )

    maclar = maclar.drop_duplicates(
        subset=["Benzersiz_Mac_Anahtari"],
        keep="first"
    ).copy()

    silinen_tekrar = ilk_satir_sayisi - len(maclar)

    maclar["Yil"] = maclar["Tarih_Parsed"].dt.year
    maclar["Donem"] = maclar["Yil"].map(donem_belirle)

    stratejiler = []

    # STRATEJİ 1 ve 2:
    # Her maçta sabit olarak ev sahibi veya deplasman seçilir.
    for market, strateji_adi, sonuc_kodu in [
        ("MS1", "SABIT_MS1", "1"),
        ("MS2", "SABIT_MS2", "2"),
    ]:
        d = maclar.copy()

        d["Strateji"] = strateji_adi
        d["Bahis_Marketi"] = market
        d["Bahis_Orani"] = d[market]
        d["Bahis_Sonucu"] = sonuc_kodu
        d["Bahis_Gecerli"] = d["Bahis_Orani"].notna()

        d["Bahis_Kazandi"] = (
            d["Bahis_Gecerli"]
            & d["Sonuc"].eq(d["Bahis_Sonucu"])
        )

        d["Kar_Zarar"] = np.where(
            d["Bahis_Gecerli"],
            np.where(
                d["Bahis_Kazandi"],
                d["Bahis_Orani"] - 1.0,
                -1.0
            ),
            np.nan
        )

        d["Esit_MS1_MS2"] = False
        stratejiler.append(d)

    # STRATEJİ 3:
    # MS1 ve MS2 arasında düşük oranlı olan seçilir.
    d = maclar.copy()

    d["Strateji"] = "DUSUK_ORAN_MS1_MS2"

    d["Esit_MS1_MS2"] = (
        d["MS1"].notna()
        & d["MS2"].notna()
        & d["MS1"].eq(d["MS2"])
    )

    d["Bahis_Marketi"] = np.select(
        [
            d["MS1"].lt(d["MS2"]),
            d["MS2"].lt(d["MS1"])
        ],
        [
            "MS1",
            "MS2"
        ],
        default="ESIT"
    )

    d["Bahis_Orani"] = d[["MS1", "MS2"]].min(
        axis=1,
        skipna=False
    )

    d["Bahis_Sonucu"] = d["Bahis_Marketi"].map({
        "MS1": "1",
        "MS2": "2"
    })

    d["Bahis_Gecerli"] = (
        d["MS1"].notna()
        & d["MS2"].notna()
        & ~d["Esit_MS1_MS2"]
    )

    d["Bahis_Kazandi"] = (
        d["Bahis_Gecerli"]
        & d["Sonuc"].eq(d["Bahis_Sonucu"])
    )

    d["Kar_Zarar"] = np.where(
        d["Bahis_Gecerli"],
        np.where(
            d["Bahis_Kazandi"],
            d["Bahis_Orani"] - 1.0,
            -1.0
        ),
        np.nan
    )

    stratejiler.append(d)

    detay = pd.concat(
        stratejiler,
        ignore_index=True,
        sort=False
    )

    # Genel ve dönem bazlı raporlar.
    genel_ozet = ozetle(detay, ["Strateji"])
    donem_ozet = ozetle(detay, ["Donem", "Strateji"])

    dusuk_oran = detay.loc[
        detay["Strateji"].eq("DUSUK_ORAN_MS1_MS2")
    ].copy()

    dusuk_oran_gecerli = dusuk_oran.loc[
        dusuk_oran["Bahis_Gecerli"]
    ].copy()

    dusuk_market_ozet = ozetle(
        dusuk_oran_gecerli,
        ["Bahis_Marketi"]
    )

    dusuk_market_donem_ozet = ozetle(
        dusuk_oran_gecerli,
        ["Donem", "Bahis_Marketi"]
    )

    # Dosyaları kaydet.
    genel_ozet.to_csv(
        CIKTI / "benzersiz_mac_strateji_ozet.csv",
        index=False,
        encoding="utf-8-sig"
    )

    donem_ozet.to_csv(
        CIKTI / "benzersiz_mac_donem_ozet.csv",
        index=False,
        encoding="utf-8-sig"
    )

    dusuk_market_ozet.to_csv(
        CIKTI / "dusuk_oran_market_ozet.csv",
        index=False,
        encoding="utf-8-sig"
    )

    dusuk_market_donem_ozet.to_csv(
        CIKTI / "dusuk_oran_market_donem_ozet.csv",
        index=False,
        encoding="utf-8-sig"
    )

    detay_sutunlari = [
        "Tarih",
        "Tarih_Parsed",
        "Yil",
        "Donem",
        "Ev_Sahibi",
        "Deplasman",
        "Skor",
        "Sonuc",
        "MS1",
        "MSX",
        "MS2",
        "Strateji",
        "Bahis_Marketi",
        "Bahis_Orani",
        "Bahis_Sonucu",
        "Bahis_Gecerli",
        "Bahis_Kazandi",
        "Kar_Zarar",
        "Esit_MS1_MS2"
    ]

    detay_sutunlari = [
        sutun for sutun in detay_sutunlari
        if sutun in detay.columns
    ]

    detay[detay_sutunlari].to_csv(
        CIKTI / "benzersiz_mac_bahis_detay.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print("\n=== VERİ KAPSAMI ===")
    print(f"DATA.csv satırı: {len(df)}")
    print(f"Dört büyük maçları, geçerli tarih/skor: {ilk_satir_sayisi}")
    print(f"Kaldırılan tekrar: {silinen_tekrar}")
    print(f"Benzersiz analiz maçı: {len(maclar)}")

    if not maclar.empty:
        print(
            "Tarih aralığı: "
            f"{maclar['Tarih_Parsed'].min().date()} - "
            f"{maclar['Tarih_Parsed'].max().date()}"
        )

    print(
        "MS1/MS2 oranları eşit maç: "
        f"{int(dusuk_oran['Esit_MS1_MS2'].sum())}"
    )

    print(
        "\nNot: Her bahis 1 birimdir. Eksik oranlı maçlar ilgili "
        "stratejinin bahis sayısına girmez."
    )
    print(
        "Not: Düşük oran stratejisinde MS1 ve MS2 oranı eşit "
        "olan maçlar bahis dışıdır."
    )

    def tablo_yaz(baslik, tablo):
        print(f"\n=== {baslik} ===")
        if tablo.empty:
            print("Sonuç yok.")
        else:
            print(tablo.round(3).to_string(index=False))

    tablo_yaz("GENEL STRATEJİ SONUÇLARI", genel_ozet)
    tablo_yaz("DÖNEM x STRATEJİ", donem_ozet)
    tablo_yaz("DÜŞÜK ORAN: MS1/MS2 AYRIMI", dusuk_market_ozet)
    tablo_yaz(
        "DÜŞÜK ORAN: DÖNEM x MARKET",
        dusuk_market_donem_ozet
    )

    print("\nOluşturulan dosyalar:")
    for dosya in sorted(CIKTI.glob("*.csv")):
        print(f" - {dosya.resolve()}")


if __name__ == "__main__":
    ana()
