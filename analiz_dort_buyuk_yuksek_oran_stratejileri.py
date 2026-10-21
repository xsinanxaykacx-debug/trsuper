# -*- coding: utf-8 -*-
"""Dört büyük takım için iki yüksek oran stratejisini aynı maç havuzunda test eder."""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "data" / "csv" / "DATA.csv"
OUT = ROOT / "data" / "bankroll_ruin_simulation" / "dort_buyuk_unique" / "yuksek_oran_karsilastirmasi"
STAKE = 1.0
START_BANKROLL = 100.0
BOOTSTRAP_REPS = 20000
BLOCK_LENGTH = 5
SEED = 20261021
ODDS_COLS = {"1": "Maç_Sonucu_|_1", "X": "Maç_Sonucu_|_X", "2": "Maç_Sonucu_|_2"}
TEAMS = {"galatasaray", "fenerbahçe", "fenerbahce", "beşiktaş", "besiktas", "trabzonspor"}


def norm_team(x):
    if pd.isna(x):
        return ""
    return str(x).strip().casefold().replace("ı", "i").replace("İ", "i")


def odds(s):
    s = s.astype("string").str.strip().str.replace(",", ".", regex=False)
    s = s.replace({"": pd.NA, "-": pd.NA, "—": pd.NA, "nan": pd.NA, "None": pd.NA})
    x = pd.to_numeric(s, errors="coerce")
    return x.where((x >= 1.0) & (x < 5.0))


def result_from_score(x):
    if pd.isna(x):
        return None
    m = re.match(r"^\s*(\d+)\s*[-:]\s*(\d+)\s*$", str(x))
    if not m:
        return None
    h, a = int(m.group(1)), int(m.group(2))
    return "1" if h > a else ("2" if h < a else "X")


def bootstrap_ci(profits, seed):
    n = len(profits)
    if n < 2:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    blocks = int(np.ceil(n / BLOCK_LENGTH))
    vals = np.empty(BOOTSTRAP_REPS)
    starts = np.arange(n)
    for i in range(BOOTSTRAP_REPS):
        sample = np.concatenate([
            profits[(int(rng.choice(starts)) + np.arange(BLOCK_LENGTH)) % n]
            for _ in range(blocks)
        ])[:n]
        vals[i] = sample.sum() / (n * STAKE) * 100
    return tuple(np.quantile(vals, [0.025, 0.975]))


def evaluate(df, strategy, market_col, odds_col, seed):
    b = df.loc[df[market_col].notna()].copy()
    b["Secilen_Market"] = b[market_col]
    b["Secilen_Oran"] = b[odds_col]
    b["Kazandi"] = (b["Gercek_Sonuc"] == b["Secilen_Market"]).astype(int)
    b["Kar_Zarar"] = np.where(b["Kazandi"].eq(1), (b["Secilen_Oran"] - 1) * STAKE, -STAKE)
    b = b.sort_values(["Tarih_Sort", "_row_id"], kind="stable").reset_index(drop=True)
    p = b["Kar_Zarar"].to_numpy(float)
    n = len(b)
    net = float(p.sum())
    roi = net / (n * STAKE) * 100 if n else np.nan
    lo, hi = bootstrap_ci(p, seed) if n else (np.nan, np.nan)
    equity = peak = START_BANKROLL
    max_dd = 0.0
    placed = 0
    stop_date = ""
    for row in b.itertuples(index=False):
        if equity < STAKE:
            stop_date = str(row.Tarih)
            break
        equity += float(row.Kar_Zarar)
        placed += 1
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak * 100 if peak > 0 else 0)
    summary = {
        "Strateji": strategy, "Bahis_Sayisi": n, "Kazandi": int(b["Kazandi"].sum()),
        "Kaybetti": n - int(b["Kazandi"].sum()),
        "Kazanma_Orani_%": b["Kazandi"].mean() * 100 if n else np.nan,
        "Toplam_Kar_Zarar": net, "ROI_%": roi,
        "ROI_Bootstrap_%95_Alt": lo, "ROI_Bootstrap_%95_Ust": hi,
        "100_Birim_Teorik_Son_Kasa": START_BANKROLL + net,
        "100_Birim_Kasa_Ile_Oynanan_Bahis": placed,
        "100_Birim_Kasa_Gercek_Son_Kasa": equity,
        "Kasa_Durus_Tarihi": stop_date, "Maksimum_Dusus_%": max_dd,
        "Ortalama_Oran": b["Secilen_Oran"].mean() if n else np.nan,
    }
    b["Strateji"] = strategy
    return summary, b


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Veri dosyası bulunamadı: {INPUT}")
    df = None
    for enc in ("utf-8-sig", "utf-8", "cp1254", "latin1"):
        try:
            df = pd.read_csv(INPUT, encoding=enc, low_memory=False)
            break
        except UnicodeDecodeError:
            pass
    if df is None:
        raise RuntimeError("CSV kodlaması okunamadı.")
    required = ["Tarih", "Skor", "Ev_Sahibi", "Deplasman", *ODDS_COLS.values()]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError("Eksik sütunlar: " + ", ".join(missing))
    df["_row_id"] = np.arange(len(df))
    home, away = df["Ev_Sahibi"].map(norm_team), df["Deplasman"].map(norm_team)
    team_mask = home.isin(TEAMS) | away.isin(TEAMS)
    df = df.loc[team_mask].copy()
    df["Tarih_Sort"] = pd.to_datetime(df["Tarih"], dayfirst=True, errors="coerce")
    df["Gercek_Sonuc"] = df["Skor"].map(result_from_score)
    for m, c in ODDS_COLS.items():
        df["Oran_" + m] = odds(df[c])
    complete = df["Gercek_Sonuc"].notna() & df[["Oran_1", "Oran_X", "Oran_2"]].notna().all(axis=1)
    common = df.loc[complete].sort_values(["Tarih_Sort", "_row_id"], kind="stable").reset_index(drop=True).copy()

    # A: MS1 ve MS2 içindeki düşük oranlı tarafın tersini seç; eşitlikte pas.
    common["A_Market"] = np.where(common["Oran_1"] > common["Oran_2"], "1",
                          np.where(common["Oran_2"] > common["Oran_1"], "2", None))
    common["A_Oran"] = np.where(common["A_Market"].eq("1"), common["Oran_1"],
                        np.where(common["A_Market"].eq("2"), common["Oran_2"], np.nan))

    # B: MS1/MSX/MS2 içindeki en yüksek oranı seç; tepe eşitliğinde pas.
    mat = common[["Oran_1", "Oran_X", "Oran_2"]].to_numpy(float)
    maxval = mat.max(axis=1)
    top_count = np.isclose(mat, maxval[:, None], rtol=0, atol=1e-12).sum(axis=1)
    labels = np.array(["1", "X", "2"], dtype=object)
    idx = mat.argmax(axis=1)
    common["B_Market"] = np.where(top_count == 1, labels[idx], None)
    common["B_Oran"] = np.where(top_count == 1, maxval, np.nan)

    sa, ba = evaluate(common, "A_Favorinin_Tersi_MS1_MS2", "A_Market", "A_Oran", SEED)
    sb, bb = evaluate(common, "B_MS1_MSX_MS2_En_Yuksek_Oran", "B_Market", "B_Oran", SEED + 1)
    summary = pd.DataFrame([sa, sb])
    OUT.mkdir(parents=True, exist_ok=True)
    summary.to_csv(OUT / "yuksek_oran_stratejileri_ozet.csv", index=False, encoding="utf-8-sig")
    pd.concat([ba, bb], ignore_index=True).to_csv(
        OUT / "yuksek_oran_stratejileri_bahis_detay.csv", index=False, encoding="utf-8-sig")
    common[["Tarih", "Ev_Sahibi", "Deplasman", "Skor", "Gercek_Sonuc",
            "Oran_1", "Oran_X", "Oran_2", "A_Market", "A_Oran", "B_Market", "B_Oran"]].to_csv(
        OUT / "ortak_mac_havuzu.csv", index=False, encoding="utf-8-sig")

    lines = [
        "# Dört Büyük Takım — Yüksek Oran Stratejileri", "",
        "## Yöntem", "",
        f"- Ortak havuz: dört büyük takımın en az birinin oynadığı, skoru okunabilen ve üç oranın da 1,00 dahil–5,00 hariç geçerli olduğu {len(common)} maç.",
        "- A: MS1/MS2 arasında daha yüksek oranlı taraf; eşit MS1/MS2 oranında bahis yok.",
        "- B: MS1/MSX/MS2 arasında en yüksek oran; en yüksek oran eşitliğinde bahis yok.",
        "- Her bahis 1 birim, başlangıç kasası 100 birim. Tarih sıralı hareketli blok bootstrap: blok 5, 20.000 tekrar.", "",
        "## Sonuç", "",
        "| Strateji | Bahis | Kazandı | Kaybetti | Kazanma % | Net K/Z | ROI % | ROI %95 alt | ROI %95 üst | Teorik son kasa | 100 birimle oynanan | Gerçek son kasa | Maks. düşüş % |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for s in (sa, sb):
        lines.append(
            f"| {s['Strateji']} | {s['Bahis_Sayisi']} | {s['Kazandi']} | {s['Kaybetti']} | "
            f"{s['Kazanma_Orani_%']:.2f} | {s['Toplam_Kar_Zarar']:.2f} | {s['ROI_%']:.2f} | "
            f"{s['ROI_Bootstrap_%95_Alt']:.2f} | {s['ROI_Bootstrap_%95_Ust']:.2f} | "
            f"{s['100_Birim_Teorik_Son_Kasa']:.2f} | {s['100_Birim_Kasa_Ile_Oynanan_Bahis']} | "
            f"{s['100_Birim_Kasa_Gercek_Son_Kasa']:.2f} | {s['Maksimum_Dusus_%']:.2f} |"
        )
    lines += [
        "", "## Önemli notlar", "",
        "- Teorik son kasa, tüm tarihsel bahislerin net sonucunu 100 birime ekler; kasa sıfırın altına inse bile tüm bahisleri oynanmış varsayar.",
        "- Gerçek son kasa simülasyonunda kasa 1 birimin altına düştüğünde yeni bahis açılmaz.",
        "- Yüksek oran, yüksek kâr garantisi değildir. ROI güven aralığı sıfırı içeriyorsa pozitif avantaj için yeterli kanıt yoktur.",
        "- İki strateji aynı ortak maç havuzunu kullanır; eşit oran kuralları nedeniyle bahis adetleri farklı olabilir.", "",
        "## Dosyalar", "",
        "- yuksek_oran_stratejileri_ozet.csv: karşılaştırmalı özet.",
        "- yuksek_oran_stratejileri_bahis_detay.csv: her bahis ve sonucu.",
        "- ortak_mac_havuzu.csv: ortak maç ve oran havuzu.", ""
    ]
    (OUT / "yuksek_oran_stratejileri_raporu.md").write_text("\n".join(lines), encoding="utf-8")
    print("=== DÖRT BÜYÜK TAKIM: YÜKSEK ORAN STRATEJİLERİ ===")
    print(f"Kaynak toplam satır: {len(pd.read_csv(INPUT, encoding='utf-8-sig', low_memory=False))}")
    print(f"Dört büyük takım maçı (ilk filtre): {int(team_mask.sum())}")
    print(f"Ortak uygun maç havuzu: {len(common)}")
    print(summary.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print("\nÇıktı klasörü:", OUT)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        raise
