# -*- coding: utf-8 -*-
"""Yüksek oran stratejileri için yıl × oran aralığı × seçilen market analizi."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "data" / "bankroll_ruin_simulation" / "dort_buyuk_unique" / "yuksek_oran_karsilastirmasi" / "yuksek_oran_stratejileri_bahis_detay.csv"
OUT = ROOT / "data" / "bankroll_ruin_simulation" / "dort_buyuk_unique" / "yuksek_oran_karsilastirmasi"
STAKE = 1.0
ODDS_EDGES = [1.0, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0]
ODDS_LABELS = ["1,00-1,99", "2,00-2,49", "2,50-2,99", "3,00-3,49", "3,50-3,99", "4,00-4,99"]


def main():
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Bahis detay dosyası bulunamadı: {INPUT}\n"
            "Önce analiz_dort_buyuk_yuksek_oran_stratejileri.py dosyasını çalıştır."
        )
    df = pd.read_csv(INPUT, encoding="utf-8-sig", low_memory=False)
    required = ["Tarih", "Strateji", "Secilen_Market", "Secilen_Oran", "Kazandi", "Kar_Zarar"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError("Eksik sütunlar: " + ", ".join(missing))

    df["Tarih_Parsed"] = pd.to_datetime(df["Tarih"], dayfirst=True, errors="coerce")
    df["Yil"] = df["Tarih_Parsed"].dt.year
    df["Secilen_Oran"] = pd.to_numeric(
        df["Secilen_Oran"].astype("string").str.replace(",", ".", regex=False), errors="coerce"
    )
    df["Kazandi"] = pd.to_numeric(df["Kazandi"], errors="coerce")
    df["Kar_Zarar"] = pd.to_numeric(df["Kar_Zarar"], errors="coerce")
    df = df.dropna(subset=["Yil", "Strateji", "Secilen_Market", "Secilen_Oran", "Kazandi", "Kar_Zarar"]).copy()
    df["Yil"] = df["Yil"].astype(int)
    df["Secilen_Market"] = df["Secilen_Market"].astype(str).str.strip().str.upper()
    df["Oran_Araligi"] = pd.cut(
        df["Secilen_Oran"], bins=ODDS_EDGES, labels=ODDS_LABELS, right=False, include_lowest=True
    )
    df = df.dropna(subset=["Oran_Araligi"]).copy()
    df["Basabas_Kazanma_Orani_%"] = 100 / df["Secilen_Oran"]

    def summarize(group):
        n = len(group)
        wins = int(group["Kazandi"].sum())
        profit = float(group["Kar_Zarar"].sum())
        return pd.Series({
            "Bahis_Sayisi": n,
            "Kazandi": wins,
            "Kaybetti": n - wins,
            "Kazanma_Orani_%": 100 * wins / n if n else np.nan,
            "Ortalama_Oran": group["Secilen_Oran"].mean() if n else np.nan,
            "Basabas_Kazanma_Orani_Ortalama_%": group["Basabas_Kazanma_Orani_%"].mean() if n else np.nan,
            "Toplam_Kar_Zarar": profit,
            "ROI_%": 100 * profit / (n * STAKE) if n else np.nan,
        })

    tables = {
        "yil": (["Strateji", "Yil"], "yuksek_oran_yil_ozeti.csv"),
        "oran_araligi": (["Strateji", "Oran_Araligi"], "yuksek_oran_aralik_ozeti.csv"),
        "market": (["Strateji", "Secilen_Market"], "yuksek_oran_market_ozeti.csv"),
        "yil_oran_araligi": (["Strateji", "Yil", "Oran_Araligi"], "yuksek_oran_yil_oran_ozeti.csv"),
        "yil_market": (["Strateji", "Yil", "Secilen_Market"], "yuksek_oran_yil_market_ozeti.csv"),
        "tam_kirilim": (["Strateji", "Yil", "Oran_Araligi", "Secilen_Market"], "yuksek_oran_yil_oran_market_ozeti.csv"),
    }
    outputs = {}
    for key, (cols, filename) in tables.items():
        result = df.groupby(cols, observed=True, dropna=False).apply(summarize, include_groups=False).reset_index()
        result.to_csv(OUT / filename, index=False, encoding="utf-8-sig")
        outputs[key] = result

    overall = df.groupby("Strateji", observed=True).apply(summarize, include_groups=False).reset_index()
    overall.to_csv(OUT / "yuksek_oran_genel_kontrol.csv", index=False, encoding="utf-8-sig")

    # Raporda örnek sayısı az olan hücreleri ayrı işaretle; bunlardan sistem çıkarılmamalı.
    detailed = outputs["tam_kirilim"].copy()
    detailed["Guvenilir_Orneklem_Notu"] = np.where(
        detailed["Bahis_Sayisi"] < 30, "N<30: çok küçük örneklem, yorumlama",
        np.where(detailed["Bahis_Sayisi"] < 100, "N<100: keşifsel sonuç", "N>=100: yine de bağımsız doğrulama gerekir")
    )
    detailed.to_csv(OUT / "yuksek_oran_yil_oran_market_ozeti_notlu.csv", index=False, encoding="utf-8-sig")

    report = [
        "# Yüksek Oran Stratejileri — Yıl × Oran × Market Analizi", "",
        "## Kapsam", "",
        f"- İncelenen bahis satırı: {len(df)}",
        f"- Tarih aralığı: {df['Tarih_Parsed'].min().date()} – {df['Tarih_Parsed'].max().date()}",
        "- Sabit bahis: 1 birim.",
        "- Oran aralıkları: 1,00–1,99; 2,00–2,49; 2,50–2,99; 3,00–3,49; 3,50–3,99; 4,00–4,99.",
        "- ROI = toplam kâr/zarar / toplam bahis tutarı.",
        "- Başabaş kazanma oranı her bahis için 1/oran olarak hesaplanır; tabloda bunun hücre ortalaması gösterilir.", "",
        "## Genel kontrol", "",
        overall.to_string(index=False), "",
        "## Yıllara göre özet", "",
        outputs["yil"].to_string(index=False), "",
        "## Oran aralıklarına göre özet", "",
        outputs["oran_araligi"].to_string(index=False), "",
        "## Seçilen markete göre özet", "",
        outputs["market"].to_string(index=False), "",
        "## Yıl × oran aralığı × market", "",
        detailed.sort_values(["Strateji", "Yil", "Oran_Araligi", "Secilen_Market"]).to_string(index=False), "",
        "## Yorumlama kuralları", "",
        "- Küçük örneklemde yüksek ROI görülmesi tek başına avantaj kanıtı değildir.",
        "- Çok sayıda yıl/oran/market kombinasyonu incelendiği için tesadüfen iyi görünen hücreler çıkabilir; bu sonuçlar keşif amaçlıdır.",
        "- Bağımsız doğrulama olmadan en iyi görünen hücreden yeni bahis sistemi türetilmemelidir.",
        "- Bu analiz yalnızca mevcut strateji betiğinin ürettiği bahisleri inceler; stratejilerin seçmediği maçları yeni bahis olarak eklemez.", "",
        "## Üretilen dosyalar", "",
    ]
    for _, filename in tables.values():
        report.append(f"- {filename}")
    report += [
        "- yuksek_oran_yil_oran_market_ozeti_notlu.csv",
        "- yuksek_oran_genel_kontrol.csv",
        ""
    ]
    (OUT / "yuksek_oran_yil_oran_market_raporu.md").write_text("\n".join(report), encoding="utf-8")

    print("=== YIL × ORAN ARALIĞI × MARKET ANALİZİ ===")
    print(f"Bahis satırı: {len(df)}")
    print(f"Tarih aralığı: {df['Tarih_Parsed'].min().date()} - {df['Tarih_Parsed'].max().date()}")
    print("\n=== GENEL KONTROL ===")
    print(overall.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print("\n=== YILLARA GÖRE ===")
    print(outputs["yil"].to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print("\n=== ORAN ARALIKLARINA GÖRE ===")
    print(outputs["oran_araligi"].to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print("\n=== MARKET'E GÖRE ===")
    print(outputs["market"].to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print("\nÇıktı klasörü:", OUT)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        raise
