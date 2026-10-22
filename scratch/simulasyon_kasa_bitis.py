from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(".")
SOURCE = ROOT / "data" / "csv" / "DATA.csv"
OUT = ROOT / "data" / "bankroll_ruin_simulation"
OUT.mkdir(parents=True, exist_ok=True)

START_DATE = pd.Timestamp("2014-01-01")
START_BANKROLL = 100.0
STAKE = 1.0

df = pd.read_csv(SOURCE, encoding="utf-8-sig", dtype=str, low_memory=False)
df.columns = [str(c).strip() for c in df.columns]

required = [
    "Tarih", "Saat", "Skor",
    "Maç_Sonucu_|_1", "Maç_Sonucu_|_X", "Maç_Sonucu_|_2",
    "2,5_Alt/Üst_|_Alt", "2,5_Alt/Üst_|_Üst",
    "AÜ_2,5_Gol_|_Alt", "AÜ_2,5_Gol_|_Üst"
]
missing = [c for c in required if c not in df.columns]
if missing:
    raise SystemExit("Eksik sütunlar: " + ", ".join(missing))

def number(v):
    if pd.isna(v):
        return np.nan
    s = str(v).strip().replace("\u00a0", "").replace(" ", "")
    if not s or s.lower() in {"nan", "none", "<na>", "-"}:
        return np.nan
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return np.nan

df["_date"] = pd.to_datetime(
    df["Tarih"].astype(str).str.strip(),
    format="%d-%m-%Y",
    errors="coerce"
)
df["_time"] = pd.to_timedelta(
    df["Saat"].astype(str).str.strip() + ":00",
    errors="coerce"
)
df["_datetime"] = df["_date"] + df["_time"]

score = df["Skor"].astype(str).str.extract(
    r"^\s*(\d+)\s*[-:]\s*(\d+)\s*$"
)
df["_hg"] = pd.to_numeric(score[0], errors="coerce")
df["_ag"] = pd.to_numeric(score[1], errors="coerce")
df["_total"] = df["_hg"] + df["_ag"]

df = df[
    df["_date"].notna()
    & (df["_date"] >= START_DATE)
    & df["_hg"].notna()
    & df["_ag"].notna()
].copy()

df = df.sort_values(
    ["_datetime", "_date"],
    kind="stable",
    na_position="last"
).reset_index(drop=True)

ms_cols = ["Maç_Sonucu_|_1", "Maç_Sonucu_|_X", "Maç_Sonucu_|_2"]
for c in ms_cols + [
    "2,5_Alt/Üst_|_Alt", "2,5_Alt/Üst_|_Üst",
    "AÜ_2,5_Gol_|_Alt", "AÜ_2,5_Gol_|_Üst"
]:
    df[c] = df[c].map(number)

# 2,5 ALT/ÜST oranları 2019 öncesi ve sonrası farklı sütunlarda.
# Yeni dönem sütunu doluysa onu, değilse eski dönem sütununu kullan.
for side in ["Alt", "Üst"]:
    current = f"2,5_Alt/Üst_|_{side}"
    legacy = f"AÜ_2,5_Gol_|_{side}"
    df[current] = df[current].where(df[current].notna(), df[legacy])

df["_actual"] = np.select(
    [
        df["_hg"] > df["_ag"],
        df["_hg"] == df["_ag"],
        df["_hg"] < df["_ag"],
    ],
    ["MS1", "MSX", "MS2"],
    default=""
)

markets = {}

# MS favorisi: her maçta geçerli MS1/MSX/MS2 oranlarından en düşüğü.
# Eşitlikte sütun sırası MS1, MSX, MS2 önceliklidir.
ms_odds = df[ms_cols].to_numpy(dtype=float)
valid = np.isfinite(ms_odds) & (ms_odds > 1.0)
safe = np.where(valid, ms_odds, np.inf)
idx = np.argmin(safe, axis=1)
has_odds = valid.any(axis=1)
fav_odds = safe[np.arange(len(df)), idx]
fav_name = np.array(["MS1", "MSX", "MS2"])[idx]
fav_win = fav_name == df["_actual"].to_numpy()
markets["MS favorisi"] = (has_odds, fav_odds, fav_win)

# Tekli maç sonucu sistemleri.
for label, col, result in [
    ("MS1", "Maç_Sonucu_|_1", "MS1"),
    ("MSX", "Maç_Sonucu_|_X", "MSX"),
    ("MS2", "Maç_Sonucu_|_2", "MS2"),
]:
    odds = df[col].to_numpy(dtype=float)
    valid = np.isfinite(odds) & (odds > 1.0)
    markets[label] = (valid, odds, df["_actual"].to_numpy() == result)

# 2,5 ALT / ÜST.
total = df["_total"].to_numpy(dtype=float)
for label, col, win_condition in [
    ("2,5 ALT", "2,5_Alt/Üst_|_Alt", total < 3),
    ("2,5 ÜST", "2,5_Alt/Üst_|_Üst", total > 2),
]:
    odds = df[col].to_numpy(dtype=float)
    valid = np.isfinite(odds) & (odds > 1.0) & np.isfinite(total)
    markets[label] = (valid, odds, win_condition)

summary = []
details = []
weekly = []

for market, (valid, odds, wins) in markets.items():
    indices = np.flatnonzero(valid)
    if not len(indices):
        print(f"UYARI: {market} için geçerli bahis bulunamadı.")
        continue

    bankroll = START_BANKROLL
    peak = bankroll
    min_bankroll = bankroll
    max_dd = 0.0
    losing_streak = 0
    longest_losing_streak = 0
    total_wins = 0
    total_losses = 0
    total_profit = 0.0
    first_date = None
    last_date = None
    ruin_date = None
    week_bets = {}
    week_profit = {}
    week_wins = {}
    week_losses = {}

    for i in indices:
        date = df.iloc[i]["_date"]
        price = float(odds[i])

        # Kasa yeni 1 birimlik bahsi karşılayamıyorsa dur.
        if bankroll < STAKE:
            ruin_date = last_date
            break

        if first_date is None:
            first_date = date

        won = bool(wins[i])
        profit = price - 1.0 if won else -STAKE
        bankroll += profit
        total_profit += profit
        last_date = date

        week_key = date.strftime("%G-W%V")
        week_bets[week_key] = week_bets.get(week_key, 0) + 1
        week_profit[week_key] = week_profit.get(week_key, 0.0) + profit
        week_wins[week_key] = week_wins.get(week_key, 0) + int(won)
        week_losses[week_key] = week_losses.get(week_key, 0) + int(not won)

        if won:
            total_wins += 1
            losing_streak = 0
        else:
            total_losses += 1
            losing_streak += 1
            longest_losing_streak = max(
                longest_losing_streak, losing_streak
            )

        peak = max(peak, bankroll)
        min_bankroll = min(min_bankroll, bankroll)
        if peak > 0:
            max_dd = max(max_dd, (peak - bankroll) / peak * 100)

        details.append({
            "Sistem": market,
            "Tarih": date.strftime("%d-%m-%Y"),
            "Saat": str(df.iloc[i]["Saat"]),
            "Oran": round(price, 4),
            "Tahmin_Kazandi": won,
            "Kar_Zarar": round(profit, 4),
            "Kasa": round(bankroll, 4),
        })

        # Kasa sıfırsa veya 1 birimin altına inmişse sonraki maça geçme.
        if bankroll < STAKE:
            ruin_date = date
            break

    n = total_wins + total_losses
    elapsed_days = (last_date - START_DATE).days + 1 if last_date is not None else 0
    elapsed_weeks = (elapsed_days + 6) // 7
    roi = total_profit / n * 100 if n else 0.0

    summary.append({
        "Sistem": market,
        "Baslangic_Kasasi": START_BANKROLL,
        "Bahis_Sayisi": n,
        "Kazandi": total_wins,
        "Kaybetti": total_losses,
        "ROI_Yuzde": round(roi, 2),
        "Son_Bahis_Tarihi": last_date.strftime("%d-%m-%Y") if last_date is not None else "",
        "Kasa_Bitis_Tarihi": ruin_date.strftime("%d-%m-%Y") if ruin_date is not None else "",
        "2014ten_Itibaren_Dayanilan_Hafta": elapsed_weeks,
        "Son_Kasa": round(bankroll, 4),
        "En_Dusuk_Kasa": round(min_bankroll, 4),
        "En_Uzun_Kayip_Serisi": longest_losing_streak,
        "Maksimum_Dusus_Yuzde": round(max_dd, 2),
        "Durum": "KASA BİTTİ" if ruin_date is not None else "VERİ SONUNA KADAR DAYANDI",
    })

    for wk, count in week_bets.items():
        weekly.append({
            "Sistem": market,
            "ISO_Hafta": wk,
            "Bahis_Sayisi": count,
            "Kazandi": week_wins[wk],
            "Kaybetti": week_losses[wk],
            "Haftalik_Kar_Zarar": round(week_profit[wk], 4),
        })

result = pd.DataFrame(summary)
if not result.empty:
    result = result.sort_values(
        ["Durum", "2014ten_Itibaren_Dayanilan_Hafta", "Son_Kasa"],
        ascending=[True, True, True],
        kind="stable"
    )

result.to_csv(OUT / "sistem_ozeti.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(details).to_csv(OUT / "bahis_detayi.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(weekly).to_csv(OUT / "haftalik_kasa.csv", index=False, encoding="utf-8-sig")

print("\n=== 100 BİRİM KASA SİMÜLASYONU ===")
print("Başlangıç: 01-01-2014 | Sabit bahis: 1 birim")
print("MS favorisi: her maçta en düşük geçerli MS1/MSX/MS2 oranı")
print(f"Analize giren maç: {len(df)}")
print(f"Veri sonu: {df['_date'].max():%d-%m-%Y}")
print("\n" + result.to_string(index=False))
print("\nOluşturulan dosyalar:")
print((OUT / "sistem_ozeti.csv").resolve())
print((OUT / "haftalik_kasa.csv").resolve())
print((OUT / "bahis_detayi.csv").resolve())

