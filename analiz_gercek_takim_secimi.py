# -*- coding: utf-8 -*-
"""Dört büyük takım — gerçek seçilen takım analizi."""

from pathlib import Path
import re
import unicodedata
import warnings

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

warnings.filterwarnings("ignore", category=RuntimeWarning)

GIRDI = Path(
    "data/bankroll_ruin_simulation/dort_buyuk_unique/"
    "benzersiz_mac_bahis_detay.csv"
)
CIKTI = Path(
    "data/bankroll_ruin_simulation/dort_buyuk_unique/"
    "gercek_takim_secimi"
)

BASLANGIC_TARIHI = pd.Timestamp("2023-01-01")
STRATEJI = "DUSUK_ORAN_MS1_MS2"
TEKRAR = 10000
BLOK_UZUNLUGU = 10
TOHUM = 20261021

TAKIMLAR = [
    "Galatasaray",
    "Fenerbahçe",
    "Beşiktaş",
    "Trabzonspor",
]


def norm(metin):
    """Türkçe karakterleri ve büyük/küçük harf farkını normalize et."""
    if pd.isna(metin):
        return ""
    metin = str(metin).strip().casefold()
    metin = metin.replace("ı", "i")
    metin = unicodedata.normalize("NFKD", metin)
    metin = "".join(
        c for c in metin if not unicodedata.combining(c)
    )
    return re.sub(r"\s+", " ", metin)


def bool_donustur(deger):
    if pd.isna(deger):
        return False
    if isinstance(deger, (bool, np.bool_)):
        return bool(deger)
    if isinstance(deger, (int, np.integer, float, np.floating)):
        return bool(deger) if np.isfinite(deger) else False
    return norm(deger) in {"true", "1", "evet", "yes"}


def mdd(karlar):
    """Başlangıç sermayesini sıfır kabul ederek azami düşüşü hesapla."""
    karlar = np.asarray(karlar, dtype=float)
    if len(karlar) == 0:
        return np.nan
    sermaye = np.concatenate(([0.0], np.cumsum(karlar)))
    zirve = np.maximum.accumulate(sermaye)
    return float(np.max(zirve - sermaye))


def blok_bootstrap_roi(karlar, tekrar=TEKRAR, blok=BLOK_UZUNLUGU):
    """
    Kronolojik hareketli blok bootstrap.
    Dairesel bloklar kullanılır; zaman bağımlılığını kısmen korur.
    Sonuçlar yüzde ROI olarak döner.
    """
    karlar = np.asarray(karlar, dtype=float)
    n = len(karlar)

    if n < 2:
        return np.nan, np.nan

    blok = max(1, min(int(blok), n))
    rng = np.random.default_rng(TOHUM + n)
    blok_sayisi = int(np.ceil(n / blok))
    baslangiclar = rng.integers(0, n, size=(tekrar, blok_sayisi))

    ofsetler = np.arange(blok)
    indeksler = (
        baslangiclar[:, :, None] + ofsetler[None, None, :]
    ) % n
    ornekler = karlar[indeksler.reshape(tekrar, -1)[:, :n]]
    roi = ornekler.mean(axis=1) * 100.0

    alt, ust = np.percentile(roi, [2.5, 97.5])
    return float(alt), float(ust)


def ozet_analiz(df, grup_turu, grup_adi):
    karlar = df["Kar_Zarar"].to_numpy(dtype=float)
    n = len(karlar)

    if n == 0:
        return None

    toplam_kar = float(karlar.sum())
    roi = toplam_kar / n * 100.0
    kazanan = int((karlar > 0).sum())
    kaybeden = int((karlar < 0).sum())
    sifir = int((karlar == 0).sum())

    ci_alt, ci_ust = blok_bootstrap_roi(karlar)

    if n >= 2 and np.std(karlar, ddof=1) > 0:
        test = stats.ttest_1samp(
            karlar, 0.0, alternative="greater"
        )
        p_degeri = float(test.pvalue)
    else:
        p_degeri = 1.0

    return {
        "Grup_Turu": grup_turu,
        "Takim": grup_adi,
        "Bahis_Sayisi": n,
        "Kazanan": kazanan,
        "Kaybeden": kaybeden,
        "Sifir_Kar": sifir,
        "Toplam_Kar": round(toplam_kar, 4),
        "ROI_Yuzde": round(roi, 4),
        "Bootstrap_CI95_Alt": round(ci_alt, 4),
        "Bootstrap_CI95_Ust": round(ci_ust, 4),
        "MDD_Birim": round(mdd(karlar), 4),
        "Tek_Yonlu_T_P": p_degeri,
    }


def ana():
    if not GIRDI.exists():
        raise FileNotFoundError(f"Kaynak dosya bulunamadı: {GIRDI}")

    df = pd.read_csv(
        GIRDI,
        encoding="utf-8-sig",
        low_memory=False,
    )
    print("Kaynak satır:", len(df))

    gerekli = {
        "Tarih_Parsed", "Ev_Sahibi", "Deplasman",
        "Strateji", "Bahis_Marketi", "Bahis_Orani",
        "Bahis_Gecerli", "Kar_Zarar",
    }
    eksik = gerekli - set(df.columns)
    if eksik:
        raise ValueError(
            "Kaynakta gerekli sütunlar eksik: "
            + ", ".join(sorted(eksik))
        )

    print("\nStrateji dağılımı:")
    print(df["Strateji"].value_counts(dropna=False).to_string())

    df["Tarih_Parsed"] = pd.to_datetime(
        df["Tarih_Parsed"], errors="coerce"
    )
    df["Strateji_norm"] = df["Strateji"].map(norm)
    df["Bahis_Marketi_norm"] = df["Bahis_Marketi"].map(norm)
    df["Bahis_Orani"] = pd.to_numeric(
        df["Bahis_Orani"], errors="coerce"
    )
    df["Kar_Zarar"] = pd.to_numeric(
        df["Kar_Zarar"], errors="coerce"
    )
    df["Gecerli_bool"] = df["Bahis_Gecerli"].map(bool_donustur)

    strateji_norm = norm(STRATEJI)
    secim = df.loc[
        (df["Strateji_norm"] == strateji_norm)
        & (df["Tarih_Parsed"] >= BASLANGIC_TARIHI)
        & (df["Bahis_Marketi_norm"].isin(["ms1", "ms2"]))
        & df["Gecerli_bool"]
        & df["Bahis_Orani"].gt(1.0)
        & df["Kar_Zarar"].notna()
    ].copy()

    if secim.empty:
        print("\nBu strateji için 2023 ve sonrası geçerli bahis bulunamadı.")
        print("Dosyadaki strateji adlarını yukarıdaki listeden kontrol et.")
        return

    # MS1 = ev sahibi, MS2 = deplasman.
    secim["Secilen_Takim"] = np.where(
        secim["Bahis_Marketi_norm"].eq("ms1"),
        secim["Ev_Sahibi"].astype("string"),
        secim["Deplasman"].astype("string"),
    )
    secim["Secilen_Takim_Norm"] = secim["Secilen_Takim"].map(norm)

    takim_normlari = {norm(t): t for t in TAKIMLAR}
    secim["Buyuk_Takim"] = secim["Secilen_Takim_Norm"].map(
        takim_normlari
    )

    # Sadece bahis yapılan taraf dört büyük takımdan biriyse dahil et.
    buyuk = secim.loc[secim["Buyuk_Takim"].notna()].copy()
    buyuk = buyuk.sort_values(
        ["Tarih_Parsed", "Ev_Sahibi", "Deplasman"],
        kind="stable",
    ).reset_index(drop=True)

    print("Strateji ve geçerli bahis filtresi sonrası:", len(secim))
    print("Dört büyükten biri gerçekten seçilmiş bahis:", len(buyuk))

    if buyuk.empty:
        print("\nSeçilen tarafı dört büyük takımdan biri olan bahis yok.")
        print("Seçilen taraf örnekleri:")
        print(secim["Secilen_Takim"].value_counts().head(20).to_string())
        return

    # Ev/deplasman: seçilen takımın maçtaki konumu.
    buyuk["Secilen_Taraf"] = np.where(
        buyuk["Bahis_Marketi_norm"].eq("ms1"),
        "Ev",
        "Deplasman",
    )

    sonuclar = []

    # Her takım için gerçek seçilen tarafın performansı.
    for takim in TAKIMLAR:
        alt = buyuk.loc[buyuk["Buyuk_Takim"] == takim].copy()
        sonuc = ozet_analiz(alt, "TAKIM_TOPLAM", takim)
        if sonuc:
            sonuclar.append(sonuc)

        for taraf in ["Ev", "Deplasman"]:
            alt_taraf = alt.loc[alt["Secilen_Taraf"] == taraf].copy()
            sonuc = ozet_analiz(
                alt_taraf, "TAKIM_TARAF", f"{takim} - {taraf}"
            )
            if sonuc:
                sonuclar.append(sonuc)

    portfoy = ozet_analiz(buyuk, "DORT_BUYUK_PORTFOY", "Dört büyük toplam")
    if portfoy:
        sonuclar.append(portfoy)

    sonuc_df = pd.DataFrame(sonuclar)

    # Holm-Bonferroni düzeltmesini yalnızca dört ana takım testine uygula.
    ana_mask = sonuc_df["Grup_Turu"].eq("TAKIM_TOPLAM")
    if ana_mask.any():
        p_degerleri = sonuc_df.loc[
            ana_mask, "Tek_Yonlu_T_P"
        ].fillna(1.0).to_numpy()
        _, p_duzeltilmis, _, _ = multipletests(
            p_degerleri, alpha=0.05, method="holm"
        )
        sonuc_df["Holm_Duzeltilmis_P"] = np.nan
        sonuc_df.loc[ana_mask, "Holm_Duzeltilmis_P"] = p_duzeltilmis
    else:
        sonuc_df["Holm_Duzeltilmis_P"] = np.nan

    sonuc_df["CI95_Sifirin_Ustunde"] = (
        sonuc_df["Bootstrap_CI95_Alt"] > 0
    )
    sonuc_df["Guclu_Kanit"] = (
        sonuc_df["CI95_Sifirin_Ustunde"]
        & sonuc_df["Holm_Duzeltilmis_P"].lt(0.05)
    )

    CIKTI.mkdir(parents=True, exist_ok=True)
    csv_yolu = CIKTI / "gercek_takim_secimi_sonuclari.csv"
    md_yolu = CIKTI / "gercek_takim_secimi_raporu.md"
    veri_yolu = CIKTI / "analize_giren_bahisler.csv"

    sonuc_df.to_csv(csv_yolu, index=False, encoding="utf-8-sig")
    buyuk.to_csv(veri_yolu, index=False, encoding="utf-8-sig")

    gorunum = [
        "Grup_Turu", "Takim", "Bahis_Sayisi", "Toplam_Kar",
        "ROI_Yuzde", "Bootstrap_CI95_Alt", "Bootstrap_CI95_Ust",
        "MDD_Birim", "Tek_Yonlu_T_P", "Holm_Duzeltilmis_P",
        "Guclu_Kanit",
    ]
    print("\n=== SONUÇLAR ===")
    print(sonuc_df[gorunum].to_string(index=False))

    ana_sonuclar = sonuc_df.loc[ana_mask].copy()
    if not ana_sonuclar.empty:
        aday = ana_sonuclar.loc[
            ana_sonuclar["CI95_Sifirin_Ustunde"]
            & ana_sonuclar["Holm_Duzeltilmis_P"].lt(0.05)
        ]
    else:
        aday = pd.DataFrame()

    rapor = [
        "# Dört Büyük Takım — Gerçek Seçilen Takım Analizi",
        "",
        f"- Kaynak: `{GIRDI}`",
        f"- Tarih filtresi: {BASLANGIC_TARIHI.date()} ve sonrası",
        f"- Strateji: `{STRATEJI}`",
        "- Bahis birimi: kaynak `Kar_Zarar` sütunundaki birim",
        f"- Bootstrap tekrar sayısı: {TEKRAR:,}",
        f"- Hareketli blok uzunluğu: {BLOK_UZUNLUGU}",
        f"- Analize giren dört büyük takım seçimi: {len(buyuk)}",
        "",
        "## Sonuçlar",
        "",
        sonuc_df[gorunum].to_string(index=False),
        "",
        "## Değerlendirme",
        "",
    ]

    if aday.empty:
        rapor.append(
            "Dört ana takım testinde, %95 blok-bootstrap ROI güven "
            "aralığının alt sınırı sıfırın üzerinde olan ve Holm "
            "düzeltmeli tek yönlü t-test p değeri 0,05'in altında "
            "kalan bir takım yok. Bu veriyle doğrulanmış bir avantaj "
            "iddiası desteklenmiyor."
        )
    else:
        rapor.append(
            "Aşağıdaki takım(lar) iki belirtilen ölçütü de geçti: "
            + ", ".join(aday["Takim"].tolist())
            + ". Bu sonuç yine de farklı dönem veya bağımsız veriyle "
            "doğrulanmalıdır."
        )

    rapor.extend([
        "",
        "## Yöntem ve sınırlamalar",
        "",
        "- Takım, bahis yapılan taraf üzerinden belirlenmiştir: MS1 ev "
        "sahibi; MS2 deplasman.",
        "- Geçersiz bahisler, oranı 1 veya daha düşük olanlar ve kâr-zararı "
        "eksik satırlar dışarıda bırakılmıştır.",
        "- Güven aralığı kronolojik sıralı kâr-zarar dizisi üzerinde "
        "dairesel hareketli blok bootstrap ile hesaplanmıştır.",
        "- Tek yönlü t-test p değerleri zaman bağımlılığını modellemez; "
        "bootstrap güven aralığından bağımsız bir kanıt gibi "
        "yorumlanmamalıdır.",
        "- Holm düzeltmesi dört takımın ana karşılaştırmasına uygulanmıştır. "
        "Ev/deplasman kırılımları keşif amaçlıdır.",
        "- MDD, sıfır başlangıç kârından hesaplanan azami düşüşün bahis "
        "birimi cinsinden büyüklüğüdür; yüzde bankroll düşüşü değildir.",
        "",
        "## Dosyalar",
        "",
        f"- Sonuç tablosu: `{csv_yolu}`",
        f"- Analize giren bahisler: `{veri_yolu}`",
    ])

    md_yolu.write_text("\n".join(rapor), encoding="utf-8")

    print("\nKaydedildi:")
    print(csv_yolu.resolve())
    print(md_yolu.resolve())
    print(veri_yolu.resolve())


if __name__ == "__main__":
    ana()
