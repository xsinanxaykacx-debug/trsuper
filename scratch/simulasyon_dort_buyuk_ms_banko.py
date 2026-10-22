import re
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(r"C:\Users\bzdye\Downloads\trsuper")
INPUT = BASE / "data" / "csv" / "DATA.csv"
OUTDIR = BASE / "data" / "bankroll_ruin_simulation" / "dort_buyuk"
OUTDIR.mkdir(parents=True, exist_ok=True)

START_BANKROLL = 100.0
STAKE = 1.0
START_DATE = pd.Timestamp("2014-01-01")
EPS = 1e-8

TEAMS = ["Galatasaray", "Fenerbahçe", "Beşiktaş", "Trabzonspor"]

def parse_odds(series):
    s = series.astype("string").str.strip()
    s = s.str.replace(",", ".", regex=False)
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

all_details = []
summaries = []

for team in TEAMS:
    team_norm = team.casefold()

    mask = (
        df["_ev_norm"].eq(team_norm)
        | df["_dep_norm"].eq(team_norm)
    )
    matches = df.loc[mask].sort_values("_tarih", kind="stable").copy()

    records = []
    for _, row in matches.iterrows():
        options = []
        for outcome in ("1", "X", "2"):
            odds = row[f"_oran_{outcome}"]
            if pd.notna(odds) and np.isfinite(odds) and odds > 1.0:
                options.append((float(odds), outcome))

        # MS1/MSX/MS2 oranlarından hiçbiri geçerli değilse maçı atla.
        if not options:
            continue

        odds, pick = min(options, key=lambda x: x[0])
        records.append({
            "Takim": team,
            "Tarih_dt": row["_tarih"],
            "Tarih": row["_tarih"].strftime("%d-%m-%Y"),
            "Ev_Sahibi": row["Ev_Sahibi"],
            "Deplasman": row["Deplasman"],
            "Skor": row["Skor"],
            "Secim": pick,
            "Oran": odds,
            "Kazandi": pick == row["_sonuc"],
        })

    bankroll = START_BANKROLL
    team_details = []
    ruin_date = None

    for row in records:
        if bankroll < STAKE - EPS:
            ruin_date = row["Tarih_dt"]
            break

        before = bankroll
        won = bool(row["Kazandi"])
        profit = row["Oran"] - 1.0 if won else -STAKE
        bankroll += profit

        detail = {
            "Takim": team,
            "Tarih": row["Tarih"],
            "Ev_Sahibi": row["Ev_Sahibi"],
            "Deplasman": row["Deplasman"],
            "Skor": row["Skor"],
            "Secim": row["Secim"],
            "Oran": row["Oran"],
            "Kazandi": won,
            "Kar_Zarar": profit,
            "Bahis_Oncesi_Kasa": before,
            "Bahis_Sonrasi_Kasa": bankroll,
        }
        team_details.append(detail)
        all_details.append(detail)

        if bankroll < STAKE - EPS:
            ruin_date = row["Tarih_dt"]
            break

    if not team_details:
        summaries.append({
            "Takim": team,
            "Gecerli_Bahis": 0,
            "Kazandi": 0,
            "Kaybetti": 0,
            "Kazanma_Yuzdesi": np.nan,
            "Toplam_Kar_Zarar": 0,
            "ROI_Yuzde": np.nan,
            "Son_Bahis_Tarihi": "",
            "Kasa_Bitis_Tarihi": "",
            "Dayanilan_Gun": 0,
            "Dayanilan_Hafta": 0,
            "Son_Kasa": START_BANKROLL,
            "Durum": "UYGUN BAHİS YOK",
        })
        continue

    det = pd.DataFrame(team_details)
    n = len(det)
    wins = int(det["Kazandi"].sum())
    losses = n - wins
    total_pl = float(det["Kar_Zarar"].sum())
    last_bet = pd.to_datetime(det.iloc[-1]["Tarih"], dayfirst=True)
    data_end = matches["_tarih"].max()
    end_date = ruin_date if ruin_date is not None else data_end
    days = max(0, (end_date - START_DATE).days)

    summaries.append({
        "Takim": team,
        "Gecerli_Bahis": n,
        "Kazandi": wins,
        "Kaybetti": losses,
        "Kazanma_Yuzdesi": round(wins / n * 100, 2),
        "Toplam_Kar_Zarar": round(total_pl, 4),
        "ROI_Yuzde": round(total_pl / (n * STAKE) * 100, 2),
        "Son_Bahis_Tarihi": last_bet.strftime("%d-%m-%Y"),
        "Kasa_Bitis_Tarihi": ruin_date.strftime("%d-%m-%Y") if ruin_date is not None else "",
        "Dayanilan_Gun": days,
        "Dayanilan_Hafta": round(days / 7, 2),
        "Son_Kasa": round(bankroll, 8),
        "Durum": "KASA BİTTİ" if ruin_date is not None else "VERİ SONUNA KADAR DEVAM",
    })

summary_df = pd.DataFrame(summaries)
summary_path = OUTDIR / "dort_buyuk_ms_favorisi_ozet.csv"
summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")

details_path = OUTDIR / "dort_buyuk_ms_favorisi_detay.csv"
pd.DataFrame(all_details).to_csv(
    details_path, index=False, encoding="utf-8-sig"
)

print("\n=== DÖRT BÜYÜK — 100 BİRİM MS FAVORİSİ SİMÜLASYONU ===")
print("Kural: Takımın her maçında MS1/MSX/MS2 arasındaki en düşük geçerli oran")
print("Başlangıç kasası: 100 birim | Her takım maçı için bahis: 1 birim")
print(f"Veri başlangıcı: {START_DATE:%d-%m-%Y}")
print()
print(summary_df.to_string(index=False))
print(f"\nÖzet CSV  : {summary_path}")
print(f"Detay CSV : {details_path}")
print("\nNot: VERİ SONUNA KADAR DEVAM, kasanın veri sonuna kadar bitmediğini belirtir.")
print("Bu, sistemin kârlı olduğunu veya gelecekte de dayanacağını kanıtlamaz.")
