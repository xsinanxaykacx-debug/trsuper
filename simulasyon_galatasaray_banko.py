import re
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(r"C:\Users\bzdye\Downloads\trsuper")
INPUT = BASE / "data" / "csv" / "DATA.csv"
OUTDIR = BASE / "data" / "bankroll_ruin_simulation" / "galatasaray"
OUTDIR.mkdir(parents=True, exist_ok=True)

START_BANKROLL = 100.0
STAKE = 1.0
START_DATE = pd.Timestamp("2014-01-01")
EPS = 1e-8

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
    h, a = int(m.group(1)), int(m.group(2))
    return "1" if h > a else ("2" if h < a else "X")

if not INPUT.exists():
    raise FileNotFoundError(f"Dosya bulunamadı: {INPUT}")

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

home = df["Ev_Sahibi"].astype("string").str.strip().str.casefold().eq("galatasaray")
away = df["Deplasman"].astype("string").str.strip().str.casefold().eq("galatasaray")

gs = df[
    (home | away)
    & df["_tarih"].notna()
    & (df["_tarih"] >= START_DATE)
    & df["_sonuc"].notna()
].copy()

gs["_gs_ev_sahibi"] = home.loc[gs.index]
gs = gs.sort_values("_tarih", kind="stable").reset_index(drop=True)

# Yöntem 1: MS1/MSX/MS2 arasındaki en düşük geçerli oran.
favorite_rows = []
for _, row in gs.iterrows():
    options = []
    for outcome in ("1", "X", "2"):
        odds = row[f"_oran_{outcome}"]
        if pd.notna(odds) and np.isfinite(odds) and odds > 1.0:
            options.append((float(odds), outcome))
    if options:
        odds, pick = min(options, key=lambda x: x[0])
        favorite_rows.append({
            "Tarih": row["_tarih"],
            "Ev_Sahibi": row["Ev_Sahibi"],
            "Deplasman": row["Deplasman"],
            "Skor": row["Skor"],
            "Secim": pick,
            "Oran": odds,
            "Kazandi": pick == row["_sonuc"],
        })

# Yöntem 2: Galatasaray'ın kazanmasına bahis.
gswin_rows = []
for _, row in gs.iterrows():
    pick = "1" if bool(row["_gs_ev_sahibi"]) else "2"
    odds = row[f"_oran_{pick}"]
    if pd.notna(odds) and np.isfinite(odds) and odds > 1.0:
        gswin_rows.append({
            "Tarih": row["_tarih"],
            "Ev_Sahibi": row["Ev_Sahibi"],
            "Deplasman": row["Deplasman"],
            "Skor": row["Skor"],
            "Secim": pick,
            "Oran": float(odds),
            "Kazandi": pick == row["_sonuc"],
        })

def simulate(name, rows):
    bets = pd.DataFrame(rows)
    if bets.empty:
        return None, None

    bets = bets.sort_values("Tarih", kind="stable").reset_index(drop=True)
    bankroll = START_BANKROLL
    records = []
    ruin_date = None

    for _, row in bets.iterrows():
        if bankroll < STAKE - EPS:
            ruin_date = row["Tarih"]
            break

        before = bankroll
        won = bool(row["Kazandi"])
        odds = float(row["Oran"])
        profit = odds - 1.0 if won else -STAKE
        bankroll += profit

        records.append({
            "Sistem": name,
            "Tarih": row["Tarih"].strftime("%d-%m-%Y"),
            "Ev_Sahibi": row["Ev_Sahibi"],
            "Deplasman": row["Deplasman"],
            "Skor": row["Skor"],
            "Secim": row["Secim"],
            "Oran": odds,
            "Kazandi": won,
            "Kar_Zarar": profit,
            "Bahis_Oncesi_Kasa": before,
            "Bahis_Sonrasi_Kasa": bankroll,
        })

        if bankroll < STAKE - EPS:
            ruin_date = row["Tarih"]
            break

    details = pd.DataFrame(records)
    if details.empty:
        return None, None

    details_path = OUTDIR / f"{name}_detay.csv"
    details.to_csv(details_path, index=False, encoding="utf-8-sig")

    n = len(details)
    wins = int(details["Kazandi"].sum())
    total_pl = float(details["Kar_Zarar"].sum())
    last_bet = pd.to_datetime(details.iloc[-1]["Tarih"], dayfirst=True)
    end_date = ruin_date if ruin_date is not None else bets["Tarih"].max()
    days = max(0, (end_date - START_DATE).days)

    summary = {
        "Sistem": name,
        "Baslangic_Kasasi": START_BANKROLL,
        "Bahis_Sayisi": n,
        "Kazandi": wins,
        "Kaybetti": n - wins,
        "Kazanma_Yuzdesi": round(wins / n * 100, 2),
        "Toplam_Kar_Zarar": round(total_pl, 4),
        "ROI_Yuzde": round(total_pl / (n * STAKE) * 100, 2),
        "Son_Bahis_Tarihi": last_bet.strftime("%d-%m-%Y"),
        "Kasa_Bitis_Tarihi": ruin_date.strftime("%d-%m-%Y") if ruin_date is not None else "",
        "Dayanilan_Gun": days,
        "Dayanilan_Hafta": round(days / 7, 2),
        "Son_Kasa": round(bankroll, 8),
        "Durum": "KASA BİTTİ" if ruin_date is not None else "VERİ SONUNA KADAR DEVAM",
    }
    return summary, details

results = []
for name, rows in [
    ("GS_MACLARI_MS_FAVORISI", favorite_rows),
    ("GALATASARAY_GALIBI", gswin_rows),
]:
    summary, details = simulate(name, rows)
    if summary:
        results.append(summary)

if not results:
    raise RuntimeError("Uygun oranı olan bahis bulunamadı.")

summary_df = pd.DataFrame(results)
summary_path = OUTDIR / "galatasaray_kasa_ozeti.csv"
summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")

print("\n=== GALATASARAY MAÇLARI — 100 BİRİM KASA ===")
print(f"Galatasaray maç satırı (geçerli skor/tarih): {len(gs)}")
print(f"Veri dönemi: {gs['_tarih'].min():%d-%m-%Y} - {gs['_tarih'].max():%d-%m-%Y}")
print()
print(summary_df.to_string(index=False))
print(f"\nÖzet: {summary_path}")
print(f"Detay klasörü: {OUTDIR}")
