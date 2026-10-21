# -*- coding: utf-8 -*-

from pathlib import Path
import math
import numpy as np
import pandas as pd

KAYNAK = Path(
    "data/bankroll_ruin_simulation/dort_buyuk_unique/"
    "ileri_test_guven_araligi/ileri_test_kronolojik_detay.csv"
)

CIKTI_KLASORU = KAYNAK.parent / "takim_bazli_ileri_test"
CIKTI_OZET = CIKTI_KLASORU / "takim_bazli_ozet.csv"
CIKTI_GUNLUK = CIKTI_KLASORU / "takim_bazli_bahisler.csv"

TAKIMLAR = [
    "Galatasaray",
    "Fenerbahçe",
    "Beşiktaş",
    "Trabzonspor",
]

TEKRAR = 10000
BLOK_UZUNLUGU = 10
TOHUM = 20261021


def normalize_metin(deger):
    if pd.isna(deger):
        return ""
    return " ".join(str(deger).strip().casefold().split())


def maksimum_dusus(karlar):
    karlar = np.asarray(karlar, dtype=float)

    if len(karlar) == 0:
        return 0.0

    birikimli = np.cumsum(karlar)
    zirve = np.maximum.accumulate(
        np.concatenate(([0.0], birikimli))
    )[1:]

    return float(np.max(zirve - birikimli))


def dairesel_blok_ornekle(karlar, blok, rng):
    karlar = np.asarray(karlar, dtype=float)
    n = len(karlar)

    if n == 0:
        return np.array([], dtype=float)

    blok = min(blok, n)
    gereken_blok = int(math.ceil(n / blok))
    baslangiclar = rng.integers(
        0, n, size=gereken_blok
    )

    ofsetler = np.arange(blok)
    indisler = (
        baslangiclar[:, None] + ofsetler[None, :]
    ) % n

    return karlar[indisler.ravel()[:n]]


def bootstrap_guven_araligi(karlar, rng):
    karlar = np.asarray(karlar, dtype=float)
    n = len(karlar)

    dagilim = np.empty(TEKRAR, dtype=float)

    for i in range(TEKRAR):
        secilen = dairesel_blok_ornekle(
            karlar,
            BLOK_UZUNLUGU,
            rng
        )
        dagilim[i] = 100.0 * secilen.mean()

    alt, ust = np.percentile(
        dagilim,
        [2.5, 97.5]
    )

    return float(alt), float(ust)


def null_bootstrap_p_degeri(karlar, rng):
    """
    Tek yönlü test:
    H0: beklenen birim bahis kârı <= 0
    H1: beklenen birim bahis kârı > 0

    Getiriler sıfır etrafında merkezlenir ve kronolojik
    dairesel bloklarla yeniden örneklenir.
    """

    karlar = np.asarray(karlar, dtype=float)
    n = len(karlar)

    if n < 2:
        return np.nan

    gozlenen_ortalama = float(karlar.mean())
    sifir_merkezli = karlar - gozlenen_ortalama

    buyuk_esit = 0

    for _ in range(TEKRAR):
        secilen = dairesel_blok_ornekle(
            sifir_merkezli,
            BLOK_UZUNLUGU,
            rng
        )

        null_ortalama = float(secilen.mean())

        if null_ortalama >= gozlenen_ortalama:
            buyuk_esit += 1

    return float(
        (buyuk_esit + 1) / (TEKRAR + 1)
    )


def holm_duzeltmesi(p_degerleri):
    """
    Holm-Bonferroni düzeltmesi.
    NaN olan testler düzeltilmiş sonuçta da NaN kalır.
    """

    p_degerleri = np.asarray(
        p_degerleri,
        dtype=float
    )

    sonuc = np.full(
        len(p_degerleri),
        np.nan,
        dtype=float
    )

    gecerli = np.where(
        np.isfinite(p_degerleri)
    )[0]

    if len(gecerli) == 0:
        return sonuc

    sirali = gecerli[
        np.argsort(p_degerleri[gecerli])
    ]

    m = len(sirali)
    onceki = 0.0

    for sira, indeks in enumerate(sirali):
        carpan = m - sira
        duzeltilmis = min(
            1.0,
            carpan * p_degerleri[indeks]
        )
        onceki = max(onceki, duzeltilmis)
        sonuc[indeks] = onceki

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

    eksik = [
        sutun for sutun in gerekli
        if sutun not in df.columns
    ]

    if eksik:
        raise ValueError(
            f"Kaynak dosyada eksik sütunlar var: {eksik}"
        )

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
        & df["Strateji"].astype(str).eq(
            "DUSUK_ORAN_MS1_MS2"
        )
        & df["Bahis_Marketi"].astype(str).isin(
            ["MS1", "MS2"]
        )
    ].copy()

    if df.empty:
        raise ValueError(
            "2023 sonrası geçerli düşük oranlı MS1/MS2 "
            "bahis kaydı bulunamadı."
        )

    df["_Ev_Normal"] = df["Ev_Sahibi"].map(
        normalize_metin
    )
    df["_Dep_Normal"] = df["Deplasman"].map(
        normalize_metin
    )

    df = df.sort_values(
        [
            "Tarih_Parsed",
            "Ev_Sahibi",
            "Deplasman",
        ]
    ).reset_index(drop=True)

    # Aynı maçın aynı stratejide birden fazla satırı varsa
    # bunu sessizce silmek yerine durdurup inceleme istiyoruz.
    anahtarlar = [
        "Tarih_Parsed",
        "_Ev_Normal",
        "_Dep_Normal",
        "Strateji",
    ]

    tekrar_sayisi = int(
        df.duplicated(anahtarlar, keep=False).sum()
    )

    if tekrar_sayisi:
        raise ValueError(
            f"Aynı maç/strateji için {tekrar_sayisi} "
            "mükerrer satır bulundu. Çifte sayımı önlemek "
            "için analiz durduruldu."
        )

    rng = np.random.default_rng(TOHUM)

    raporlar = []
    bahis_detaylari = []

    for takim in TAKIMLAR:
        takim_norm = normalize_metin(takim)

        # Takımın ev sahibi veya deplasman olduğu maçlar.
        # Derbiler her ilgili takımın grubuna girer; bu yüzden
        # takımlar arası gruplar bağımsız örneklemler değildir.
        mask = (
            df["_Ev_Normal"].eq(takim_norm)
            | df["_Dep_Normal"].eq(takim_norm)
        )

        grup = df.loc[mask].copy()
        grup = grup.sort_values(
            [
                "Tarih_Parsed",
                "Ev_Sahibi",
                "Deplasman",
            ]
        ).reset_index(drop=True)

        karlar = grup["Kar_Zarar"].to_numpy(
            dtype=float
        )

        n = len(karlar)

        if n == 0:
            raporlar.append({
                "Takim": takim,
                "Bahis_Sayisi": 0,
                "Kazanc": 0,
                "Kayip": 0,
                "Birim_Bahis_Toplam_Kar": 0.0,
                "ROI_Yuzde": np.nan,
                "ROI_Alt95": np.nan,
                "ROI_Ust95": np.nan,
                "Maksimum_Dusus_Birim": np.nan,
                "En_Uzun_Kayip_Serisi": np.nan,
                "Ham_P_Degeri": np.nan,
            })
            continue

        toplam_kar = float(karlar.sum())
        roi = float(100.0 * karlar.mean())

        alt, ust = bootstrap_guven_araligi(
            karlar,
            rng
        )

        p_degeri = null_bootstrap_p_degeri(
            karlar,
            rng
        )

        kazanc = int((karlar > 0).sum())
        kayip = int((karlar < 0).sum())
        basabas = int((karlar == 0).sum())

        kayip_serisi = 0
        en_uzun_kayip = 0

        for sonuc in karlar:
            if sonuc < 0:
                kayip_serisi += 1
                en_uzun_kayip = max(
                    en_uzun_kayip,
                    kayip_serisi
                )
            else:
                kayip_serisi = 0

        raporlar.append({
            "Takim": takim,
            "Bahis_Sayisi": n,
            "Kazanc": kazanc,
            "Kayip": kayip,
            "Basabas": basabas,
            "Kazanma_Yuzdesi": (
                100.0 * kazanc / n
            ),
            "Birim_Bahis_Toplam_Kar": toplam_kar,
            "ROI_Yuzde": roi,
            "ROI_Alt95": alt,
            "ROI_Ust95": ust,
            "Maksimum_Dusus_Birim": maksimum_dusus(
                karlar
            ),
            "En_Uzun_Kayip_Serisi": en_uzun_kayip,
            "Ham_P_Degeri": p_degeri,
        })

        for _, satir in grup.iterrows():
            bahis_detaylari.append({
                "Takim_Grubu": takim,
                "Tarih": satir["Tarih_Parsed"],
                "Ev_Sahibi": satir["Ev_Sahibi"],
                "Deplasman": satir["Deplasman"],
                "Bahis_Marketi": satir["Bahis_Marketi"],
                "Kar_Zarar": satir["Kar_Zarar"],
            })

    rapor = pd.DataFrame(raporlar)

    rapor["Holm_Duzeltilmis_P"] = holm_duzeltmesi(
        rapor["Ham_P_Degeri"].to_numpy(dtype=float)
    )

    rapor["Pozitif_Edge_Kaniti"] = (
        (rapor["ROI_Alt95"] > 0)
        & (rapor["Holm_Duzeltilmis_P"] < 0.05)
    )

    CIKTI_KLASORU.mkdir(
        parents=True,
        exist_ok=True
    )

    rapor.to_csv(
        CIKTI_OZET,
        index=False,
        encoding="utf-8-sig"
    )

    pd.DataFrame(bahis_detaylari).to_csv(
        CIKTI_GUNLUK,
        index=False,
        encoding="utf-8-sig"
    )

    print("\n=== TAKIM BAZLI İLERİ TEST ===")
    print("Dönem: 2023 ve sonrası")
    print("Strateji: Düşük oranlı MS1/MS2")
    print("Sabit bahis: 1 birim")
    print(f"Bootstrap tekrar: {TEKRAR}")
    print(f"Blok uzunluğu: {BLOK_UZUNLUGU}")
    print("Çoklu test düzeltmesi: Holm-Bonferroni")
    print()
    print(rapor.round(4).to_string(index=False))

    print("\n=== ÖNEMLİ SINIRLAR ===")
    print(
        "Bu tablo, takımın oynadığı maçlardaki düşük oran "
        "stratejisinin performansını ölçer. Takımın kendisine "
        "bahis yapıldığı anlamına gelmez."
    )
    print(
        "Derbiler iki takımın grubunda da yer alabilir. "
        "Bu nedenle takım grupları bağımsız değildir."
    )
    print(
        "ROI güven aralığı sıfırı içeriyorsa pozitif getiri "
        "doğrulanmış sayılmaz. Holm düzeltmesi, dört takım "
        "için yapılan testlerde çoklu karşılaştırmayı dikkate alır."
    )
    print(
        "Bu sonuçlar yeni bir bahis avantajı bulmak için "
        "keşifsel analizdir; tek başına gelecekte kârlılık "
        "kanıtı değildir."
    )

    print("\n=== DOSYALAR ===")
    print(CIKTI_OZET.resolve())
    print(CIKTI_GUNLUK.resolve())


if __name__ == "__main__":
    main()
