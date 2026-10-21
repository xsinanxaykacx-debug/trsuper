import re
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(r"C:\Users\bzdye\Downloads\trsuper")
INPUT = BASE / "data" / "csv" / "DATA.csv"
OUTDIR = BASE / "data" / "bankroll_ruin_simulation"
OUTDIR.mkdir(parents=True, exist_ok=True)

START_BANKROLL = 100.0
STAKE = 1.0
START_DATE = pd.Timestamp("2014-01-01")
EPS = 1e-8

if not INPUT.exists():
    raise FileNotFoundError(f"Veri dosyası bulunamadı: {INPUT}")

df = pd.read_csv(INPUT, encoding="utf-8-sig", low_memory=False)
df.columns = df.columns.astype(str).str.strip()

required = [
    "Tarih", "Skor",
    "Maç_Sonucu_|_1",
    "Maç_Sonucu_|_X",
    "Maç_Sonucu_|_2",
]
missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(
        f"Eksik sütunlar: {missing}\n"
        f"Dosyadaki sütunlar: {df.columns.tolist()}"
    )

def odds_to_num(series):
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
    if home > away:
        return "1"
    if home < away:
        return "2"
    return "X"

df["_tarih"] = pd.to_datetime(df["Tarih"], dayfirst=True, errors="coerce")
df["_skor_sonucu"] = df["Skor"].map(parse_score)

odds_cols = {
    "1": "Maç_Sonucu_|_1",
    "X": "Maç_Sonucu_|_X",
    "2": "Maç_Sonucu_|_2",
}
for outcome, col in odds_cols.items():
    df[f"_oran_{outcome}"] = odds_to_num(df[col])

df = df[
    df["_tarih"].notna()
    & (df["_tarih"] >= START_DATE)
    & df["_skor_sonucu"].notna()
].copy()

# Her maç için mevcut ve geçerli MS oranları içinden en düşük olanı seç.
def favorite_for_row(row):
    available = []
    for outcome in ("1", "X", "2"):
        price = row[f"_oran_{outcome}"]
        if pd.notna(price) and np.isfinite(price) and price > 1.0:
            available.append((float(price), outcome))
    if not available:
        return pd.Series({"_favori": None, "_favori_orani": np.nan})
    price, outcome = min(available, key=lambda x: x[0])
    return pd.Series({"_favori": outcome, "_favori_orani": price})

fav = df.apply(favorite_for_row, axis=1)
df["_favori"] = fav["_favori"]
df["_favori_orani"] = fav["_favori_orani"]

eligible = df[
    df["_favori"].notna() & df["_favori_orani"].notna()
].copy()

eligible["_kazandi"] = (
    eligible["_favori"] == eligible["_skor_sonucu"]
)

# Her takvim gününde yalnızca bir maç:
# Favori oranı en düşük maç. Eşitlikte kaynak dosyadaki ilk maç.
daily = (
    eligible.sort_values(
        ["_tarih", "_favori_orani"],
        ascending=[True, True],
        kind="stable",
    )
    .drop_duplicates(subset="_tarih", keep="first")
    .sort_values("_tarih", kind="stable")
    .reset_index(drop=True)
)

bankroll = START_BANKROLL
details = []
ruin_date = None

for _, row in daily.iterrows():
    date = row["_tarih"]

    # 1 birimlik yeni bahsi karşılayamıyorsa dur.
    if bankroll < STAKE - EPS:
        ruin_date = date
        break

    before = bankroll
    won = bool(row["_kazandi"])
    odds = float(row["_favori_orani"])
    profit = odds - 1.0 if won else -STAKE
    bankroll += profit

    details.append({
        "Tarih": date.strftime("%d-%m-%Y"),
        "Skor": str(row["Skor"]),
        "Secilen_MS": row["_favori"],
        "Secilen_Oran": odds,
        "Tahmin_Kazandi": won,
        "Bahis_Kari": profit,
        "Bahis_Oncesi_Kasa": before,
        "Bahis_Sonrasi_Kasa": bankroll,
    })

    if bankroll < STAKE - EPS:
        ruin_date = date
        break

details_df = pd.DataFrame(details)
detail_path = OUTDIR / "ms_banko_gunluk_detay.csv"
details_df.to_csv(detail_path, index=False, encoding="utf-8-sig")

if details_df.empty:
    raise RuntimeError("Simülasyona uygun hiçbir bahis bulunamadı.")

bets = len(details_df)
wins = int(details_df["Tahmin_Kazandi"].sum())
losses = bets - wins
profit_total = float(details_df["Bahis_Kari"].sum())
roi = profit_total / (bets * STAKE) * 100
last_bet_date = pd.to_datetime(
    details_df.iloc[-1]["Tarih"], dayfirst=True
)
data_end = df["_tarih"].max()
duration_end = ruin_date if ruin_date is not None else data_end
days_survived = max(0, (duration_end - START_DATE).days)
weeks_survived = days_survived / 7

summary = pd.DataFrame([{
    "Baslangic_Kasasi": START_BANKROLL,
    "Bahis_Basi": STAKE,
    "Secim_Kurali": "Her gün en düşük MS favori oranlı maç",
    "Gunluk_Bahis_Sayisi": bets,
    "Kazandi": wins,
    "Kaybetti": losses,
    "Toplam_Kar_Zarar": round(profit_total, 6),
    "ROI_Yuzde": round(roi, 4),
    "Son_Bahis_Tarihi": last_bet_date.strftime("%d-%m-%Y"),
    "Kasa_Bitis_Tarihi": (
        ruin_date.strftime("%d-%m-%Y") if ruin_date is not None else ""
    ),
    "Dayanilan_Gun": days_survived,
    "Dayanilan_Hafta": round(weeks_survived, 2),
    "Son_Kasa": round(bankroll, 8),
    "Durum": "KASA BİTTİ" if ruin_date is not None else "VERİ SONUNA KADAR DEVAM",
}])

summary_path = OUTDIR / "ms_banko_gunluk_ozet.csv"
summary.to_csv(summary_path, index=False, encoding="utf-8-sig")

print("\n=== 100 BİRİM — GÜNDE EN FAZLA 1 MS BANKO ===")
print(f"Veri dönemi       : {START_DATE:%d-%m-%Y} - {data_end:%d-%m-%Y}")
print(f"Bahis yapılan gün : {bets}")
print(f"Kazandı / kaybetti: {wins} / {losses}")
print(f"Toplam kâr/zarar  : {profit_total:.4f} birim")
print(f"ROI               : {roi:.2f}%")
print(f"Son bahis         : {last_bet_date:%d-%m-%Y}")
print(f"Kasa bitiş tarihi : {ruin_date:%d-%m-%Y}" if ruin_date is not None else "Kasa bitiş tarihi : Veri döneminde bitmedi")
print(f"Dayanma süresi    : {days_survived} gün ({weeks_survived:.2f} hafta)")
print(f"Son kasa          : {bankroll:.8f} birim")
print(f"Durum             : {summary.iloc[0]['Durum']}")
print(f"\nÖzet dosyası      : {summary_path}")
print(f"Bahis detayları   : {detail_path}")
print("\nSon 10 bahis:")
print(details_df.tail(10).to_string(index=False))
