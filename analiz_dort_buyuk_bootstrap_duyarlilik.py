# -*- coding: utf-8 -*-

from pathlib import Path
import numpy as np
import pandas as pd

KAYNAK = Path(
    "data/bankroll_ruin_simulation/dort_buyuk_unique/"
    "ileri_test_guven_araligi/ileri_test_kronolojik_detay.csv"
)
CIKTI = KAYNAK.parent / "bootstrap_duyarlilik.csv"
DAGILIM_CIKTI = KAYNAK.parent / "bootstrap_duyarlilik_dagilimlari.csv"

TEKRAR = 10000
BLOK_UZUNLUKLARI = [1, 10, 20, 40]
TOHUM = 20261021


def bootstrap_roi(karlar, blok, tekrar, rng):
    karlar = np.asarray(karlar, dtype=float)
    n = len(karlar)

    if n == 0:
        return np.array([], dtype=float)

    blok = min(blok, n)
    adet_blok = int(np.ceil(n / blok))
    ofsetler = np.arange(blok)
    sonuc = np.empty(tekrar, dtype=float)

    for i in range(tekrar):
        baslangic = rng.integers(0, n, size=adet_blok)
        indis = (baslangic[:, None] + ofsetler[None, :]) % n
        secilen = karlar[indis.ravel()[:n]]
        sonuc[i] = secilen.mean() * 100.0

    return sonuc


def main():
    if not KAYNAK.exists():
        raise FileNotFoundError(
            f"Kaynak dosya bulunamadı: {KAYNAK.resolve()}"
        )

    df = pd.read_csv(
        KAYNAK,
        encoding="utf-8-sig",
        low_memory=False
    )

    gerekli = [
        "Tarih_Parsed",
        "Ev_Sahibi",
        "Deplasman",
        "Strateji",
        "Bahis_Marketi",
        "Kar_Zarar",
    ]

    eksik = [sutun for sutun in gerekli if sutun not in df.columns]
    if eksik:
        raise ValueError(f"Eksik sütunlar: {eksik}")

    df["Tarih_Parsed"] = pd.to_datetime(
        df["Tarih_Parsed"],
        errors="coerce"
    )
    df["Kar_Zarar"] = pd.to_numeric(
        df["Kar_Zarar"],
        errors="coerce"
    )

    df = df[
        df["Tarih_Parsed"].notna()
        & df["Kar_Zarar"].notna()
        & (df["Tarih_Parsed"].dt.year >= 2023)
        & df["Strateji"].astype(str).eq("DUSUK_ORAN_MS1_MS2")
        & df["Bahis_Marketi"].astype(str).isin(["MS1", "MS2"])
    ].copy()

    df = df.sort_values(
        ["Tarih_Parsed", "Ev_Sahibi", "Deplasman"]
    ).reset_index(drop=True)

    if df.empty:
        raise ValueError(
            "2023 sonrası geçerli MS1/MS2 bahis kaydı bulunamadı."
        )

    gruplar = [
        ("TUM_DUSUK_ORAN", df),
        ("DUSUK_ORAN_MS1", df[df["Bahis_Marketi"].eq("MS1")]),
        ("DUSUK_ORAN_MS2", df[df["Bahis_Marketi"].eq("MS2")]),
    ]

    rng = np.random.default_rng(TOHUM)
    sonuclar = []
    dagilimlar = []

    for ad, grup in gruplar:
        karlar = grup["Kar_Zarar"].to_numpy(dtype=float)
        n = len(karlar)

        if n == 0:
            continue

        gozlenen_roi = float(karlar.mean() * 100.0)

        for blok in BLOK_UZUNLUKLARI:
            kullanilan_blok = min(blok, n)

            dagilim = bootstrap_roi(
                karlar=karlar,
                blok=kullanilan_blok,
                tekrar=TEKRAR,
                rng=rng
            )

            alt, ust = np.percentile(dagilim, [2.5, 97.5])
            pozitif_oran = 100.0 * np.mean(dagilim > 0)

            sonuclar.append({
                "Strateji": ad,
                "Bahis_Sayisi": n,
                "Blok_Uzunlugu": kullanilan_blok,
                "Gozlenen_ROI_Yuzde": gozlenen_roi,
                "Bootstrap_Alt95": float(alt),
                "Bootstrap_Ust95": float(ust),
                "Bootstrap_ROI_Pozitif_Yuzde": float(pozitif_oran),
                "Tekrar": TEKRAR,
            })

            dagilimlar.append(pd.DataFrame({
                "Strateji": ad,
                "Blok_Uzunlugu": kullanilan_blok,
                "Bootstrap_ROI_Yuzde": dagilim,
            }))

    rapor = pd.DataFrame(sonuclar)
    rapor.to_csv(
        CIKTI,
        index=False,
        encoding="utf-8-sig"
    )

    dagilim_df = pd.concat(dagilimlar, ignore_index=True)
    dagilim_df.to_csv(
        DAGILIM_CIKTI,
        index=False,
        encoding="utf-8-sig"
    )

    print("\n=== BOOTSTRAP BLOK UZUNLUĞU DUYARLILIK ANALİZİ ===")
    print(f"2023 sonrası geçerli bahis sayısı: {len(df)}")
    print(f"Bootstrap tekrar sayısı: {TEKRAR}")
    print(f"Blok uzunlukları: {BLOK_UZUNLUKLARI}")
    print()
    print(rapor.round(4).to_string(index=False))

    print("\n=== OLUŞTURULAN DOSYALAR ===")
    print(CIKTI.resolve())
    print(DAGILIM_CIKTI.resolve())

    print("\n=== YORUM NOTU ===")
    print(
        "Blok uzunluğu 1 bağımsız yeniden örneklemeyi; "
        "10, 20 ve 40 daha uzun bloklarla duyarlılığı inceler."
    )
    print(
        "Güven aralığı sıfırı içeriyorsa pozitif getiri "
        "istatistiksel olarak doğrulanmış değildir."
    )
    print(
        "Pozitif bootstrap tekrar yüzdesi tek başına "
        "kârlılık kanıtı değildir."
    )


if __name__ == "__main__":
    main()
