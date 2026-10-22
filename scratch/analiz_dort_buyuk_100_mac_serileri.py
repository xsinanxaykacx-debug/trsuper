# -*- coding: utf-8 -*-
"""
Dört Büyük — 100 maçlık seri analizi.

Her takımın tarih sıralı maçlarında MS1/MSX/MS2 içindeki en düşük geçerli
oranı seçer. Sonuçları örtüşmeyen 100 takım-maçlık seriler halinde raporlar.
Ham veriye dokunmaz.
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(r"C:\Users\bzdye\Downloads\trsuper")
INPUT = BASE / "data" / "csv" / "DATA.csv"
OUTDIR = BASE / "data" / "bankroll_ruin_simulation" / "dort_buyuk_100_mac_serileri"
OUTDIR.mkdir(parents=True, exist_ok=True)

START_DATE = pd.Timestamp("2014-01-01")
STAKE = 1.0
SERIES_SIZE = 100
TEAMS = ["Galatasaray", "Fenerbahçe", "Beşiktaş", "Trabzonspor"]


def parse_odds(series):
    s = series.astype("string").str.strip().str.replace(",", ".", regex=False)
    s = s.replace(["", "-", "—", "nan", "None", "<NA>"], pd.NA)
    return pd.to_numeric(s, errors="coerce")


def parse_score(value):
    if pd.isna(value):
        return None
    m = re.search(r"(?<!\d)(\d+)\s*[-:]\s*(\d+)(?!\d)", str(value))
    if not m:
        return None
    home, away = int(m.group(1)), int(m.group(2))
    return "1" if home > away else ("2" if home < away else "X")


def longest_streak(values, target):
    best = current = 0
    for value in values:
        if bool(value) == target:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


if not INPUT.exists():
    raise FileNotFoundError(f"Veri dosyası bulunamadı: {INPUT}")

df = pd.read_csv(INPUT, encoding="utf-8-sig", low_memory=False)
df.columns = df.columns.astype(str).str.strip()

required = [
    "Tarih", "Skor", "Ev_Sahibi", "Deplasman",
    "Maç_Sonucu_|_1", "Maç_Sonucu_|_X", "Maç_Sonucu_|_2",
]
missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Eksik sütunlar: {missing}")

df["_tarih"] = pd.to_datetime(df["Tarih"], dayfirst=True, errors="coerce")
df["_sonuc"] = df["Skor"].map(parse_score)
for outcome, col in [
    ("1", "Maç_Sonucu_|_1"),
    ("X", "Maç_Sonucu_|_X"),
    ("2", "Maç_Sonucu_|_2"),
]:
    df[f"_oran_{outcome}"] = parse_odds(df[col])

df["_ev_norm"] = df["Ev_Sahibi"].astype("string").str.strip().str.casefold()
df["_dep_norm"] = df["Deplasman"].astype("string").str.strip().str.casefold()
df = df[
    df["_tarih"].notna()
    & (df["_tarih"] >= START_DATE)
    & df["_sonuc"].notna()
].copy()

all_series = []
all_details = []
team_overview = []

for team in TEAMS:
    team_norm = team.casefold()
    mask = df["_ev_norm"].eq(team_norm) | df["_dep_norm"].eq(team_norm)
    matches = df.loc[mask].sort_values("_tarih", kind="stable").copy()

    records = []
    for _, row in matches.iterrows():
        options = []
        for outcome in ("1", "X", "2"):
            odds = row[f"_oran_{outcome}"]
            if pd.notna(odds) and np.isfinite(odds) and odds > 1.0:
                options.append((float(odds), outcome))
        team_result = "EV" if row["_sonuc"] == "1" else ("DEP" if row["_sonuc"] == "2" else "BERABERE")
        if options:
            odds, pick = min(options, key=lambda item: item[0])
            won = pick == row["_sonuc"]
            profit = odds - 1.0 if won else -STAKE
        else:
            odds, pick, won, profit = np.nan, "", pd.NA, 0.0
        records.append({
            "Takim": team,
            "Tarih": row["_tarih"],
            "Ev_Sahibi": row["Ev_Sahibi"],
            "Deplasman": row["Deplasman"],
            "Skor": row["Skor"],
            "Takim_Maci_Sonucu": team_result,
            "Secilen_MS": pick,
            "Secilen_Oran": odds,
            "Bahis_Gecerli": bool(options),
            "Bahis_Kazandi": won,
            "Kar_Zarar": profit,
        })

    bets = pd.DataFrame(records)
    if bets.empty:
        team_overview.append({
            "Takim": team, "Gecerli_Bahis": 0, "Tam_100luk_Seri": 0,
            "Kismi_Seri_Bahis": 0, "Toplam_Kar_Zarar": 0.0, "ROI_Yuzde": np.nan,
        })
        continue

    bets = bets.reset_index(drop=True)
    bets["Mac_Sira_No"] = np.arange(1, len(bets) + 1)
    bets["Seri_No"] = (bets["Mac_Sira_No"] - 1) // SERIES_SIZE + 1
    bets["Seri_Ici_Mac_No"] = (bets["Mac_Sira_No"] - 1) % SERIES_SIZE + 1
    bets["Birikimli_Kar_Zarar"] = bets["Kar_Zarar"].cumsum()

    for series_no, block in bets.groupby("Seri_No", sort=True):
        n = len(block)
        valid = block["Bahis_Gecerli"]
        valid_block = block.loc[valid]
        n_bets = len(valid_block)
        wins = int(valid_block["Bahis_Kazandi"].sum()) if n_bets else 0
        profit = float(block["Kar_Zarar"].sum())
        # Seri başlangıcında kasa sıfır kabul edilerek, seri içi kâr eğrisi ölçülür.
        equity = block["Kar_Zarar"].cumsum().to_numpy(dtype=float)
        peaks = np.maximum.accumulate(np.r_[0.0, equity])[1:]
        drawdown = peaks - equity
        start = block.iloc[0]
        end = block.iloc[-1]
        all_series.append({
            "Takim": team,
            "Seri_No": int(series_no),
            "Seri_Tipi": "TAM_SERI" if n == SERIES_SIZE else "KISMI_SERI",
            "Mac_Adedi": n,
            "Gecerli_Bahis": n_bets,
            "Oran_Eksik_Gecersiz_Mac": int(n - n_bets),
            "Baslangic_Mac_No": int(start["Mac_Sira_No"]),
            "Bitis_Mac_No": int(end["Mac_Sira_No"]),
            "Baslangic_Tarihi": start["Tarih"].strftime("%d-%m-%Y"),
            "Bitis_Tarihi": end["Tarih"].strftime("%d-%m-%Y"),
            "Kazandi": wins,
            "Kaybetti": n_bets - wins,
            "Kazanma_Yuzdesi": round(wins / n_bets * 100, 2) if n_bets else np.nan,
            "Ortalama_Oran": round(float(valid_block["Secilen_Oran"].mean()), 4) if n_bets else np.nan,
            "Toplam_Kar_Zarar": round(profit, 4),
            "ROI_Yuzde": round(profit / (n_bets * STAKE) * 100, 2) if n_bets else np.nan,
            "Seri_Ici_Maks_Dusus": round(float(drawdown.max(initial=0.0)), 4),
            "En_Uzun_Kayip_Serisi": longest_streak(valid_block["Bahis_Kazandi"].tolist(), False),
            "Birikimli_Kar_Zarar_Son": round(float(end["Birikimli_Kar_Zarar"]), 4),
        })

    all_details.append(bets)
    full_count = len(bets) // SERIES_SIZE
    rem = len(bets) % SERIES_SIZE
    valid_bets = bets.loc[bets["Bahis_Gecerli"]]
    team_profit = float(bets["Kar_Zarar"].sum())
    n_valid = len(valid_bets)
    team_overview.append({
        "Takim": team,
        "Toplam_Takim_Maci": len(bets),
        "Tam_100luk_Seri": full_count,
        "Kismi_Seri_Mac": rem,
        "Gecerli_Bahis": n_valid,
        "Oran_Eksik_Gecersiz_Mac": int(len(bets) - n_valid),
        "Kazandi": int(valid_bets["Bahis_Kazandi"].sum()),
        "Kaybetti": int(n_valid - valid_bets["Bahis_Kazandi"].sum()),
        "Toplam_Kar_Zarar": round(team_profit, 4),
        "ROI_Yuzde": round(team_profit / (n_valid * STAKE) * 100, 2) if n_valid else np.nan,
        "Son_Mac_Tarihi": bets.iloc[-1]["Tarih"].strftime("%d-%m-%Y"),
    })

series_df = pd.DataFrame(all_series)
details_df = pd.concat(all_details, ignore_index=True) if all_details else pd.DataFrame()
overview_df = pd.DataFrame(team_overview)

series_path = OUTDIR / "dort_buyuk_100_mac_seri_ozet.csv"
details_path = OUTDIR / "dort_buyuk_100_mac_seri_detay.csv"
overview_path = OUTDIR / "dort_buyuk_100_mac_genel_ozet.csv"
series_df.to_csv(series_path, index=False, encoding="utf-8-sig")
details_df.to_csv(details_path, index=False, encoding="utf-8-sig")
overview_df.to_csv(overview_path, index=False, encoding="utf-8-sig")

print("\n=== DÖRT BÜYÜK — 100 MAÇLIK SERİ ANALİZİ ===")
print("Kural: Her takımın maçlarında MS1/MSX/MS2 içindeki en düşük geçerli oran seçilir.")
print("Seriler: Tarih sırasıyla, örtüşmeyen 100 takım-maçlık bloklar; oranı olmayan maç seride kalır ama bahis hesabına girmez.")
print("Kâr: Kazanırsa oran - 1, kaybederse -1 birim. Bu analiz tahmin sistemi avantajını kanıtlamaz.\n")
print("=== GENEL ÖZET ===")
print(overview_df.to_string(index=False))
print("\n=== SERİ BAZINDA SONUÇ ===")
if not series_df.empty:
    print(series_df.to_string(index=False))
print(f"\nGenel özet : {overview_path}")
print(f"Seri özeti : {series_path}")
print(f"Maç detayı : {details_path}")
