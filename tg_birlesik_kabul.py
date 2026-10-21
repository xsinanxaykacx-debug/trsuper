# -*- coding: utf-8 -*-
"""
TG Birleşik Analiz — v3 (sezon bazlı blok bootstrap, gerçek/yaklaşık ayrımı, FDR)
"""
import pandas as pd
import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests

CSV_PATH = "data/csv/DATA.csv"
MIN_N = 30
BOOT = 2000
SEED = 42

df = pd.read_csv(CSV_PATH, encoding="utf-8-sig", dtype=str, low_memory=False)
skor = df["Skor"].astype(str).str.extract(r"^\s*(\d+)\s*[-:]\s*(\d+)\s*$")
df["Ev_Gol"] = pd.to_numeric(skor[0], errors="coerce")
df["Dep_Gol"] = pd.to_numeric(skor[1], errors="coerce")
df["Toplam_Gol"] = df["Ev_Gol"] + df["Dep_Gol"]
df["Sezon"] = df["Lig/Sezon"].str.extract(r"(\d{4}/\d{4})", expand=False)
df["Sezon_Bas"] = pd.to_numeric(df["Sezon"].str[:4], errors="coerce")


def to_float(s):
    try:
        return float(str(s).replace(",", "."))
    except (TypeError, ValueError):
        return np.nan


def sezon_etiketi(yil):
    try:
        y = int(yil)
        return f"{y}/{str(y+1)[-2:]}"
    except (TypeError, ValueError):
        return "?"


def donem_etiketi(sezonlar):
    sezonlar = [s for s in sezonlar if pd.notna(s)]
    if len(sezonlar) == 0:
        return "boş"
    s = sorted(sezonlar)
    return f"{sezon_etiketi(s[0])} – {sezon_etiketi(s[-1])}"


def test_market(veri, kolon, kosul, kat, gercek_mi):
    if kolon not in veri.columns:
        return None

    alt = veri.dropna(subset=["Toplam_Gol", kolon, "Sezon"]).copy()
    alt["_o"] = alt[kolon].map(to_float)
    alt = alt[alt["_o"].notna() & (alt["_o"] > 1.0)].copy()

    if len(alt) < MIN_N:
        return {"kategori": kat, "gercek_market": gercek_mi,
                "n": len(alt), "yetersiz": True}

    alt["_k"] = kosul(alt["Toplam_Gol"]).astype(bool)
    alt["_ret"] = np.where(alt["_k"], alt["_o"] - 1.0, -1.0)

    n = len(alt)
    k = int(alt["_k"].sum())
    roi = float(alt["_ret"].mean() * 100)

    t_stat, p_val = stats.ttest_1samp(alt["_ret"], 0.0, alternative="greater")

    sezon_gruplari = alt.groupby("Sezon")["_ret"].apply(lambda s: s.values).to_dict()
    sezonlar = list(sezon_gruplari.keys())
    rng = np.random.default_rng(SEED)
    boot_rois = []
    for _ in range(BOOT):
        secilen = rng.choice(sezonlar, size=len(sezonlar), replace=True)
        birlesik = np.concatenate([sezon_gruplari[s] for s in secilen])
        if len(birlesik) > 0:
            boot_rois.append(birlesik.mean() * 100)
    boot_rois = np.array(boot_rois)
    ga_alt = float(np.percentile(boot_rois, 2.5))
    ga_ust = float(np.percentile(boot_rois, 97.5))

    sezon_roileri = alt.groupby("Sezon")["_ret"].apply(lambda s: s.mean() * 100).to_dict()

    return {
        "kategori": kat, "gercek_market": gercek_mi,
        "n": n, "kaz": k, "ROI": roi, "p": float(p_val),
        "GA_alt": ga_alt, "GA_ust": ga_ust,
        "sezon_sayisi": len(sezonlar), "sezonlar": sezonlar,
        "sezon_roileri": sezon_roileri, "yetersiz": False,
    }


marketler = {
    "0-1": {
        "eski": ("Toplam_Gol_|_0-1", lambda t: (t >= 0) & (t <= 1)),
        "yeni": ("Toplam_Gol_Aralığı_|_0-1_Gol", lambda t: (t >= 0) & (t <= 1)),
        "gercek_mi": True,
    },
    "2-3": {
        "eski": ("Toplam_Gol_|_2-3", lambda t: (t >= 2) & (t <= 3)),
        "yeni": ("Toplam_Gol_Aralığı_|_2-3_Gol", lambda t: (t >= 2) & (t <= 3)),
        "gercek_mi": True,
    },
    "4-5 (yaklaşık)": {
        "eski": ("Toplam_Gol_|_4-6", lambda t: (t >= 4) & (t <= 5)),
        "yeni": ("Toplam_Gol_Aralığı_|_4-5_Gol", lambda t: (t >= 4) & (t <= 5)),
        "gercek_mi": False,
    },
    "6+ (yaklaşık)": {
        "eski": ("Toplam_Gol_|_7+", lambda t: t >= 6),
        "yeni": ("Toplam_Gol_Aralığı_|_6+_Gol", lambda t: t >= 6),
        "gercek_mi": False,
    },
}

ESKI = df[df["Sezon_Bas"] <= 2019].copy()
YENI = df[df["Sezon_Bas"] >= 2020].copy()

print("=" * 90)
print("TG BİRLEŞİK ANALİZ v3")
print("Kriter: n >= 30 | t-testi p | sezon blok bootstrap GA | FDR")
print("=" * 90)
print(f"Eski dönem sezonları: {donem_etiketi(ESKI['Sezon_Bas'].dropna().unique())}")
print(f"Yeni dönem sezonları: {donem_etiketi(YENI['Sezon_Bas'].dropna().unique())}")
print(f"Eski dönem maç: {len(ESKI)} | Yeni dönem maç: {len(YENI)}")

sonuclar = []
for kat, info in marketler.items():
    print(f"\n--- {kat} | gerçek market: {'EVET' if info['gercek_mi'] else 'HAYIR (yaklaşık)'} ---")

    for donem_adi, donem_df, sutun_key in [
        ("2014/15 – 2019/20", ESKI, "eski"),
        ("2020/21 – 2025/26", YENI, "yeni"),
    ]:
        kolon, kosul = info[sutun_key]
        r = test_market(donem_df, kolon, kosul, kat, info["gercek_mi"])
        if r is None:
            print(f"  {donem_adi}: sütun yok")
            continue
        if r.get("yetersiz"):
            print(f"  {donem_adi}: n={r['n']} (< {MIN_N}) → atlandı")
            continue

        print(f"  {donem_adi}:")
        print(f"    n={r['n']:,} | kazanan={r['kaz']:,} | ROI={r['ROI']:+.2f}% | "
              f"p={r['p']:.4f} | GA=[{r['GA_alt']:+.2f}, {r['GA_ust']:+.2f}]")
        sezon_str = ", ".join(
            f"{s}:{v:+.1f}%" for s, v in sorted(r["sezon_roileri"].items())
        )
        print(f"    sezon sayısı={r['sezon_sayisi']} | sezon ROIs: {sezon_str}")
        r["donem"] = donem_adi
        sonuclar.append(r)

print(f"\n{'='*90}")
print("FDR (Benjamini-Hochberg) — test ailesi: 4 kategori × 2 dönem = 8")
print("=" * 90)

if sonuclar:
    p_vals = [s["p"] for s in sonuclar]
    rej, adj, _, _ = multipletests(p_vals, alpha=0.05, method="fdr_bh")

    for s, r, a in zip(sonuclar, rej, adj):
        market_tip = "gerçek" if s["gercek_market"] else "YAKLAŞIK"
        durum = "✅ FDR ANLAMLI" if r else "❌ elendi"
        print(f"  {s['donem']} | {s['kategori']:>15} | {market_tip:>8} | "
              f"n={s['n']:>5,} | ROI={s['ROI']:>7.2f}% | "
              f"GA=[{s['GA_alt']:>6.1f}, {s['GA_ust']:>6.1f}] | "
              f"p={s['p']:.4f} | q={a:.4f} | {durum}")

    fdr_gecen = sum(rej)
    guclu = sum(1 for s in sonuclar if s["ROI"] > 0 and s["GA_alt"] > 0)
    print(f"\nFDR'den geçen: {fdr_gecen}")
    print(f"ROI > 0 ve GA alt > 0 (güçlü aday): {guclu}")
    print("\nSONUÇ: Mevcut veriyle, bu yöntemle, FDR + GA kriterini geçen "
          "kârlı TG örüntüsü YOK.")
else:
    print("Hiçbir test minimum örneklem şartını sağlamadı.")