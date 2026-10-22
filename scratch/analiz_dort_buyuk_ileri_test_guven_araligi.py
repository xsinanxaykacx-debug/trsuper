# -*- coding: utf-8 -*-
from pathlib import Path

import numpy as np
import pandas as pd

KAYNAK = Path(
    "data/bankroll_ruin_simulation/dort_buyuk_unique/"
    "benzersiz_mac_bahis_detay.csv"
)
CIKTI = Path(
    "data/bankroll_ruin_simulation/dort_buyuk_unique/"
    "ileri_test_guven_araligi"
)
CIKTI.mkdir(parents=True, exist_ok=True)

BASLANGIC_YILI = 2023
TEKRAR = 10000
BLOK_UZUNLUGU = 20
TOHUM = 20261021


def bool_cevir(seri):
    if pd.api.types.is_bool_dtype(seri):
        return seri.fillna(False)

    metin = seri.astype("string").str.strip().str.casefold()
    return metin.isin(["true", "1", "evet", "yes"])


def maksimum_dusus(karlar):
    if len(karlar) == 0:
        return 0.0

    sermaye = np.cumsum(np.asarray(karlar, dtype=float))
    tepe = np.maximum.accumulate(np.concatenate(([0.0], sermaye)))[1:]
    dusus = tepe - sermaye
    return float(np.max(dusus))


def en_uzun_kayip_serisi(karlar):
    en_uzun = 0
    mevcut = 0

    for kar in karlar:
        if kar < 0:
            mevcut += 1
            en_uzun = max(en_uzun, mevcut)
        else:
            mevcut = 0

    return en_uzun


def blok_bootstrap(karlar, tekrar, blok_uzunlugu, rng):
    """
    Dairesel hareketli blok bootstrap.
    Her tekrarda kronolojik diziden bloklar çekilir.
    Bloklar veri dizisinin sonundan başına sarabilir.
    """
    karlar = np.asarray(karlar, dtype=float)
    n = len(karlar)

    if n < 2:
        return np.array([], dtype=float)

    blok = min(blok_uzunlugu, n)
    blok_baslangiclari = np.arange(n)
    blok_ofsetleri = np.arange(blok)

    gerekli_blok = int(np.ceil(n / blok))
    roi_sonuclari = np.empty(tekrar, dtype=float)

    for i in range(tekrar):
        baslangiclar = rng.choice(
            blok_baslangiclari,
            size=gerekli_blok,
            replace=True
        )

        indisler = (
            baslangiclar[:, None] + blok_ofsetleri[None, :]
        ) % n

        secilen = karlar[indisler.ravel()[:n]]
        roi_sonuclari[i] = secilen.mean() * 100.0

    return roi_sonuclari


def analiz(grup, ad, rng):
    grup = grup.sort_values(
        ["Tarih_Parsed", "Ev_Sahibi", "Deplasman"]
    ).copy()

    karlar = pd.to_numeric(
        grup["Kar_Zarar"], errors="coerce"
    ).dropna().to_numpy(dtype=float)

    n = len(karlar)

    if n == 0:
        return {
            "Strateji": ad,
            "Bahis_Sayisi": 0,
            "ROI_Yuzde": np.nan,
            "ROI_Bootstrap_Alt95": np.nan,
            "ROI_Bootstrap_Ust95": np.nan,
            "Net_Kar_Zarar": 0.0,
            "Maksimum_Dusus": 0.0,
            "En_Uzun_Kayip_Serisi": 0,
        }, pd.DataFrame()

    roi = 100.0 * karlar.mean()
    net = float(karlar.sum())
    mdd = maksimum_dusus(karlar)
    kayip_serisi = en_uzun_kayip_serisi(karlar)

    bootstrap = blok_bootstrap(
        karlar,
        TEKRAR,
        BLOK_UZUNLUGU,
        rng
    )

    if len(bootstrap):
        alt, ust = np.percentile(bootstrap, [2.5, 97.5])
        alt = float(alt)
        ust = float(ust)
    else:
        alt, ust = np.nan, np.nan

    satir = {
        "Strateji": ad,
        "Bahis_Sayisi": n,
        "Kazanan_Bahis": int((karlar > 0).sum()),
        "Kaybeden_Bahis": int((karlar < 0).sum()),
        "Net_Kar_Zarar": net,
        "ROI_Yuzde": roi,
        "ROI_Bootstrap_Alt95": alt,
        "ROI_Bootstrap_Ust95": ust,
        "Bootstrap_Tekrar": TEKRAR,
        "Blok_Uzunlugu_Bahis": min(BLOK_UZUNLUGU, n),
        "Maksimum_Dusus": mdd,
        "En_Uzun_Kayip_Serisi": kayip_serisi,
        "Ortalama_Oran": float(
            pd.to_numeric(
                grup["Bahis_Orani"], errors="coerce"
            ).mean()
        ),
    }

    bootstrap_df = pd.DataFrame({
        "Strateji": ad,
        "Bootstrap_ROI_Yuzde": bootstrap
    })

    return satir, bootstrap_df


def main():
    if not KAYNAK.exists():
        raise FileNotFoundError(
            f"Analiz girdisi bulunamadı: {KAYNAK.resolve()}"
        )

    df = pd.read_csv(KAYNAK, encoding="utf-8-sig", low_memory=False)

    gerekli = [
        "Tarih",
        "Ev_Sahibi",
        "Deplasman",
        "Strateji",
        "Bahis_Marketi",
        "Bahis_Gecerli",
        "Bahis_Orani",
        "Kar_Zarar",
    ]

    eksik = [c for c in gerekli if c not in df.columns]
    if eksik:
        raise ValueError(f"Eksik sütunlar: {eksik}")

    if "Tarih_Parsed" in df.columns:
        df["Tarih_Parsed"] = pd.to_datetime(
            df["Tarih_Parsed"], errors="coerce"
        )
    else:
        df["Tarih_Parsed"] = pd.to_datetime(
            df["Tarih"], dayfirst=True, errors="coerce"
        )

    df["Bahis_Gecerli"] = bool_cevir(df["Bahis_Gecerli"])
    df["Kar_Zarar"] = pd.to_numeric(
        df["Kar_Zarar"], errors="coerce"
    )
    df["Bahis_Orani"] = pd.to_numeric(
        df["Bahis_Orani"], errors="coerce"
    )

    df = df[
        df["Strateji"].astype(str).eq("DUSUK_ORAN_MS1_MS2")
        & df["Bahis_Gecerli"]
        & df["Tarih_Parsed"].notna()
        & df["Kar_Zarar"].notna()
    ].copy()

    df = df[df["Tarih_Parsed"].dt.year >= BASLANGIC_YILI].copy()
    df = df.sort_values(
        ["Tarih_Parsed", "Ev_Sahibi", "Deplasman"]
    ).copy()

    if df.empty:
        raise ValueError(
            "2023 ve sonrası için geçerli düşük oran bahsi bulunamadı."
        )

    rng = np.random.default_rng(TOHUM)
    raporlar = []
    bootstrap_listesi = []

    # Önce tüm düşük oran stratejisi, sonra MS1/MS2 alt grupları.
    alt_gruplar = [("TUM_DUSUK_ORAN", df)]

    for market in ["MS1", "MS2"]:
        alt_gruplar.append((
            f"DUSUK_ORAN_{market}",
            df[df["Bahis_Marketi"].astype(str).eq(market)].copy()
        ))

    for ad, grup in alt_gruplar:
        sonuc, boot = analiz(grup, ad, rng)
        raporlar.append(sonuc)

        if not boot.empty:
            bootstrap_listesi.append(boot)

    rapor = pd.DataFrame(raporlar)
    rapor.to_csv(
        CIKTI / "ileri_test_guven_araligi_mdd.csv",
        index=False,
        encoding="utf-8-sig"
    )

    if bootstrap_listesi:
        bootstrap_tum = pd.concat(
            bootstrap_listesi,
            ignore_index=True
        )
        bootstrap_tum.to_csv(
            CIKTI / "ileri_test_bootstrap_roi_dagilimi.csv",
            index=False,
            encoding="utf-8-sig"
        )

    # Bahislerin kronolojik ayrıntısı ve sermaye eğrisi.
    df["Birikimli_Kar_Zarar"] = df["Kar_Zarar"].cumsum()
    df["Onceki_Tepe"] = df["Birikimli_Kar_Zarar"].cummax().clip(lower=0)
    df["Dususten_Onceki_Tepe"] = df["Onceki_Tepe"]
    df["Sermaye_Dususu"] = (
        df["Dususten_Onceki_Tepe"] - df["Birikimli_Kar_Zarar"]
    )

    df.to_csv(
        CIKTI / "ileri_test_kronolojik_detay.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print("\n=== ANALİZ KAPSAMI ===")
    print(f"Başlangıç yılı: {BASLANGIC_YILI}")
    print(f"İleri test başlangıcı: {df['Tarih_Parsed'].min().date()}")
    print(f"İleri test bitişi: {df['Tarih_Parsed'].max().date()}")
    print(f"Toplam düşük oran bahsi: {len(df)}")
    print(f"Bootstrap tekrar sayısı: {TEKRAR}")
    print(f"Hareketli blok uzunluğu: {BLOK_UZUNLUGU} bahis")

    print("\n=== ROI GÜVEN ARALIĞI VE MAKSİMUM DÜŞÜŞ ===")
    print(rapor.round(4).to_string(index=False))

    print("\n=== YORUMLAMA NOTU ===")
    print(
        "ROI_Bootstrap_Alt95 ve ROI_Bootstrap_Ust95, "
        "hareketli blok bootstrap yüzde 95 aralığıdır."
    )
    print(
        "Aralık sıfırın üstünde değilse pozitif ROI için yeterli "
        "kanıt oluşmuş sayılmaz."
    )
    print(
        "Bu aralık gelecekte kâr garantisi vermez. Blok uzunluğu "
        "20 bahis olarak sabitlenmiştir; farklı blok uzunlukları "
        "duyarlılık kontrolü olarak ayrıca denenebilir."
    )
    print(
        "Maksimum_Dusus, bahislerden oluşan birikimli kâr eğrisinin "
        "önceki zirvesinden en büyük gerilemesidir."
    )

    print("\n=== OLUŞTURULAN DOSYALAR ===")
    for yol in sorted(CIKTI.glob("*.csv")):
        print(yol.resolve())


if __name__ == "__main__":
    main()
