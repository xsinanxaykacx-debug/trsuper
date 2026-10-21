# -*- coding: utf-8 -*-
"""Yüksek oran stratejileri için kronolojik dönem dışı doğrulama."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "data" / "bankroll_ruin_simulation" / "dort_buyuk_unique" / "yuksek_oran_karsilastirmasi"
INPUT = BASE / "yuksek_oran_stratejileri_bahis_detay.csv"
OUT = BASE
STAKE = 1.0
BOOTSTRAP_REPS = 20000
BLOCK_LENGTH = 5
SEED = 20261022


def roi_ci(profits, seed):
    n = len(profits)
    if n < 2:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    block_count = int(np.ceil(n / BLOCK_LENGTH))
    values = np.empty(BOOTSTRAP_REPS, dtype=float)
    starts = np.arange(n)
    for i in range(BOOTSTRAP_REPS):
        sample = np.concatenate([
            profits[(int(rng.choice(starts)) + np.arange(BLOCK_LENGTH)) % n]
            for _ in range(block_count)
        ])[:n]
        values[i] = sample.sum() / (n * STAKE) * 100
    return tuple(np.quantile(values, [0.025, 0.975]))


def summarize(g, seed):
    g = g.sort_values(["Tarih_Parsed", "_row_id"], kind="stable")
    n = len(g)
    wins = int(g["Kazandi"].sum())
    net = float(g["Kar_Zarar"].sum())
    lo, hi = roi_ci(g["Kar_Zarar"].to_numpy(float), seed)
    return {
        "Bahis_Sayisi": n,
        "Kazandi": wins,
        "Kaybetti": n - wins,
        "Kazanma_Orani_%": wins / n * 100 if n else np.nan,
        "Ortalama_Oran": g["Secilen_Oran"].mean() if n else np.nan,
        "Toplam_Kar_Zarar": net,
        "ROI_%": net / (n * STAKE) * 100 if n else np.nan,
        "ROI_Bootstrap_%95_Alt": lo,
        "ROI_Bootstrap_%95_Ust": hi,
    }


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Girdi bulunamadı: {INPUT}. Önce ana yüksek oran analizini çalıştır.")
    df = pd.read_csv(INPUT, encoding="utf-8-sig", low_memory=False)
    required = ["Tarih", "Strateji", "Secilen_Market", "Secilen_Oran", "Kazandi", "Kar_Zarar"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError("Eksik sütunlar: " + ", ".join(missing))

    df["_row_id"] = np.arange(len(df))
    df["Tarih_Parsed"] = pd.to_datetime(df["Tarih"], dayfirst=True, errors="coerce")
    for col in ["Secilen_Oran", "Kazandi", "Kar_Zarar"]:
        df[col] = pd.to_numeric(df[col].astype("string").str.replace(",", ".", regex=False), errors="coerce")
    df = df.dropna(subset=["Tarih_Parsed", "Strateji", "Secilen_Market", "Secilen_Oran", "Kazandi", "Kar_Zarar"]).copy()
    df["Yil"] = df["Tarih_Parsed"].dt.year.astype(int)
    df["Donem"] = np.where(df["Yil"] <= 2022, "GELISTIRME_2014_2022", "ZAMAN_DISI_TEST_2023_2025")
    df["Secilen_Market"] = df["Secilen_Market"].astype(str).str.upper().str.strip()
    df["Oran_Araligi"] = pd.cut(
        df["Secilen_Oran"], bins=[1, 2, 2.5, 3, 3.5, 4, 5],
        labels=["1,00-1,99", "2,00-2,49", "2,50-2,99", "3,00-3,49", "3,50-3,99", "4,00-4,99"],
        right=False, include_lowest=True
    )
    df = df.dropna(subset=["Oran_Araligi"]).copy()

    summaries = []
    for i, (keys, group) in enumerate(df.groupby(["Strateji", "Donem"], observed=True, sort=True)):
        rec = {"Strateji": keys[0], "Donem": keys[1]}
        rec.update(summarize(group, SEED + i))
        summaries.append(rec)
    period = pd.DataFrame(summaries)
    period.to_csv(OUT / "yuksek_oran_kronolojik_dogrulama.csv", index=False, encoding="utf-8-sig")

    cuts = []
    group_keys = ["Strateji", "Donem", "Secilen_Market", "Oran_Araligi"]
    for i, (keys, group) in enumerate(df.groupby(group_keys, observed=True, sort=True)):
        rec = dict(zip(group_keys, keys))
        rec.update(summarize(group, SEED + 100 + i))
        rec["Orneklem_Notu"] = (
            "N<30: yorumlama" if len(group) < 30 else
            "N<100: keşifsel, bağımsız doğrulama gerekir" if len(group) < 100 else
            "N>=100: yine de dönem dışı tekrar aranmalı"
        )
        cuts.append(rec)
    breakdown = pd.DataFrame(cuts)
    breakdown.to_csv(OUT / "yuksek_oran_donem_market_oran_dogrulama.csv", index=False, encoding="utf-8-sig")

    test = period[period["Donem"].eq("ZAMAN_DISI_TEST_2023_2025")].copy()
    report = [
        "# Yüksek Oran Stratejileri — Kronolojik Dönem Dışı Doğrulama", "",
        "## Önceden tanımlanan dönem ayrımı", "",
        "- Geliştirme/keşif dönemi: 2014–2022.",
        "- Zaman dışı kontrol dönemi: 2023–2025.",
        "- Bu ayrım, mevcut strateji kuralını değiştirmeden geçmişin daha sonraki yıllarında performansın tekrarlanıp tekrarlanmadığını inceler.",
        "- Bu test gerçek anlamda geleceğe dönük canlı bahis testi değildir; aynı tarihsel veri içinde kronolojik kontrol olarak değerlendirilmelidir.",
        "- %95 aralık, kâr/zarar dizisine blok uzunluğu 5 olan 20.000 tekrarlı hareketli blok bootstrap ile hesaplanmıştır. Kısa dönem ve az bahisli alt gruplarda aralıklar belirsizdir.", "",
        "## Dönem sonuçları", "",
        period.to_string(index=False), "",
        "## 2023–2025 dönem dışı kontrolü", "",
        test.to_string(index=False), "",
        "## Market × oran aralığı × dönem", "",
        breakdown.sort_values(["Strateji", "Donem", "Secilen_Market", "Oran_Araligi"]).to_string(index=False), "",
        "## Karar kuralı", "",
        "- Pozitif ROI tek başına yeterli değildir; %95 aralığın alt sınırı da sıfırın üzerinde olmalıdır.",
        "- Çok sayıda alt grup karşılaştırıldığı için en iyi görünen alt grup, bağımsız doğrulama olmadan seçilmemelidir.",
        "- 2014–2022 iyi, 2023–2025 kötü ise strateji istikrarlı kabul edilmemelidir.",
        "- Bu rapor bahis önerisi değildir; tarihsel sonuçların sağlamlığını kontrol eder.", ""
    ]
    (OUT / "yuksek_oran_kronolojik_dogrulama.md").write_text("\n".join(report), encoding="utf-8")

    print("=== KRONOLOJİK DÖNEM DIŞI DOĞRULAMA ===")
    print("Geliştirme: 2014-2022 | Zaman dışı kontrol: 2023-2025")
    print(period.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print("\n=== 2023-2025: MARKET × ORAN (N>=30) ===")
    view = breakdown[
        breakdown["Donem"].eq("ZAMAN_DISI_TEST_2023_2025") &
        (breakdown["Bahis_Sayisi"] >= 30)
    ].sort_values("ROI_%", ascending=False)
    if view.empty:
        print("N>=30 olan alt grup bulunamadı.")
    else:
        print(view.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print("\nÇıktı klasörü:", OUT)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        raise
