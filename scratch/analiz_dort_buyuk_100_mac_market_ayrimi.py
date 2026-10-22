# -*- coding: utf-8 -*-
"""
Dört Büyük — 100 maçlık serilerde seçilen MS marketi ayrıştırması.

Mevcut analiz_dort_buyuk_100_mac_serileri.py tarafından üretilen maç detayını
kullanır. Ham DATA.csv dosyasını değiştirmez ve bahisleri yeniden seçmez.
Her takımın 100 maçlık bloklarında seçilen en düşük oranlı marketi (MS1/MSX/MS2)
ayrı ayrı özetler.
"""
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(r"C:\Users\bzdye\Downloads\trsuper")
OUTDIR = BASE / "data" / "bankroll_ruin_simulation" / "dort_buyuk_100_mac_serileri"
INPUT = OUTDIR / "dort_buyuk_100_mac_seri_detay.csv"
OUT_OVERALL = OUTDIR / "dort_buyuk_100_mac_market_genel_ozet.csv"
OUT_SERIES = OUTDIR / "dort_buyuk_100_mac_market_seri_ozet.csv"
MARKETS = ["1", "X", "2"]


def summarize(group, keys):
    rows = []
    for group_key, part in group.groupby(keys, dropna=False, sort=True):
        if not isinstance(group_key, tuple):
            group_key = (group_key,)
        valid = part[part["Bahis_Gecerli"]].copy()
        n = len(valid)
        wins = int(valid["Bahis_Kazandi"].sum()) if n else 0
        profit = float(valid["Kar_Zarar"].sum()) if n else 0.0
        row = dict(zip(keys, group_key))
        row.update({
            "Bahis_Adedi": n,
            "Kazandi": wins,
            "Kaybetti": n - wins,
            "Kazanma_Yuzdesi": round(100 * wins / n, 2) if n else np.nan,
            "Toplam_Kar_Zarar": round(profit, 4),
            "ROI_Yuzde": round(100 * profit / n, 2) if n else np.nan,
            "Ortalama_Oran": round(float(valid["Secilen_Oran"].mean()), 4) if n else np.nan,
        })
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Detay dosyası bulunamadı: {INPUT}\n"
            "Önce analiz_dort_buyuk_100_mac_serileri.py dosyasını çalıştır."
        )

    df = pd.read_csv(INPUT, encoding="utf-8-sig", low_memory=False)
    required = [
        "Takim", "Mac_Sira_No", "Seri_No", "Secilen_MS", "Secilen_Oran",
        "Bahis_Gecerli", "Bahis_Kazandi", "Kar_Zarar",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Detay CSV'sinde eksik sütunlar: {missing}")

    df["Secilen_MS"] = df["Secilen_MS"].fillna("").astype(str).str.strip()
    df["Bahis_Gecerli"] = df["Bahis_Gecerli"].astype(str).str.strip().str.lower().isin(
        ["true", "1", "yes"]
    )
    df["Bahis_Kazandi"] = df["Bahis_Kazandi"].astype(str).str.strip().str.lower().isin(
        ["true", "1", "yes"]
    )
    df["Secilen_Oran"] = pd.to_numeric(df["Secilen_Oran"], errors="coerce")
    df["Kar_Zarar"] = pd.to_numeric(df["Kar_Zarar"], errors="coerce").fillna(0.0)
    df = df[df["Bahis_Gecerli"] & df["Secilen_MS"].isin(MARKETS)].copy()

    if df.empty:
        raise ValueError("MS1/MSX/MS2 marketlerinde geçerli bahis bulunamadı.")

    overall = summarize(df, ["Takim", "Secilen_MS"])
    overall["Market_Adi"] = overall["Secilen_MS"].map(
        {"1": "MS1 - Ev sahibi", "X": "MSX - Beraberlik", "2": "MS2 - Deplasman"}
    )
    overall = overall[
        ["Takim", "Secilen_MS", "Market_Adi", "Bahis_Adedi", "Kazandi", "Kaybetti",
         "Kazanma_Yuzdesi", "Ortalama_Oran", "Toplam_Kar_Zarar", "ROI_Yuzde"]
    ].sort_values(["Takim", "Secilen_MS"])

    by_series = summarize(df, ["Takim", "Seri_No", "Secilen_MS"])
    by_series["Market_Adi"] = by_series["Secilen_MS"].map(
        {"1": "MS1 - Ev sahibi", "X": "MSX - Beraberlik", "2": "MS2 - Deplasman"}
    )
    by_series = by_series[
        ["Takim", "Seri_No", "Secilen_MS", "Market_Adi", "Bahis_Adedi", "Kazandi",
         "Kaybetti", "Kazanma_Yuzdesi", "Ortalama_Oran", "Toplam_Kar_Zarar", "ROI_Yuzde"]
    ].sort_values(["Takim", "Seri_No", "Secilen_MS"])

    overall.to_csv(OUT_OVERALL, index=False, encoding="utf-8-sig")
    by_series.to_csv(OUT_SERIES, index=False, encoding="utf-8-sig")

    print("\n=== DÖRT BÜYÜK — SEÇİLEN MS MARKETİNE GÖRE GENEL SONUÇ ===")
    print("Yalnızca her maçta MS1/MSX/MS2 içinden en düşük geçerli oran seçilen bahisler.")
    print(overall.to_string(index=False))
    print("\n=== 100 MAÇLIK SERİ × SEÇİLEN MARKET ===")
    print(by_series.to_string(index=False))
    print(f"\nGenel market özeti: {OUT_OVERALL}")
    print(f"Seri-market özeti:  {OUT_SERIES}")


if __name__ == "__main__":
    main()
