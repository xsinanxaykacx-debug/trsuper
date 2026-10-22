from pathlib import Path
from statistics import NormalDist
import math
import numpy as np
import pandas as pd

DATA_PATH = Path("data/csv/DATA.csv")
OUT_DIR = Path("data/pattern_discovery_kg")
OUT_DIR.mkdir(parents=True, exist_ok=True)

VAR_COL = "Karşılıklı_Gol_|_Var"
YOK_COL = "Karşılıklı_Gol_|_Yok"
RESULT_COL = "KGVY"
MIN_ODDS = 1.0
MAX_ODDS = 5.0
BAND_WIDTH = 0.10
MIN_N = 30

def parse_odds(series):
    text = series.astype("string").str.strip()
    text = text.str.replace(",", ".", regex=False)
    text = text.replace(["", "nan", "None", "-", "—"], pd.NA)
    return pd.to_numeric(text, errors="coerce")

def find_date_column(df):
    preferred = [
        "Tarih", "Maç_Tarihi", "Mac_Tarihi", "TARIH",
        "Tarih_Saat", "Maç_Tarihi_Saat", "Mac_Tarihi_Saat"
    ]
    for name in preferred:
        if name in df.columns:
            return name

    candidates = [
        c for c in df.columns
        if "tarih" in str(c).casefold() or "date" in str(c).casefold()
    ]
    for c in candidates:
        parsed = pd.to_datetime(df[c], errors="coerce", dayfirst=True)
        if parsed.notna().mean() >= 0.80:
            return c

    raise ValueError(
        "Tarih sütunu otomatik bulunamadi. Tarih olabilecek sutunlar: "
        + repr(candidates)
    )

def wilson_interval(wins, n, z=1.959963984540054):
    if n <= 0:
        return (np.nan, np.nan)
    p = wins / n
    den = 1 + z*z/n
    center = (p + z*z/(2*n)) / den
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return (100*(center-half), 100*(center+half))

def roi_stats(odds, wins):
    n = len(odds)
    if n == 0:
        return {
            "MacSayisi": 0, "Kazanan": 0, "KazanmaOrani": np.nan,
            "KazanmaAlt95": np.nan, "KazanmaUst95": np.nan,
            "ROI_Yuzde": np.nan, "ROI_Alt95_Normal": np.nan,
            "ROI_Ust95_Normal": np.nan, "P_TekYonlu": np.nan
        }

    returns = np.where(wins, odds - 1.0, -1.0)
    roi = float(np.mean(returns))
    se = float(np.std(returns, ddof=1) / math.sqrt(n)) if n > 1 else np.nan
    low = roi - 1.959963984540054 * se if np.isfinite(se) else np.nan
    high = roi + 1.959963984540054 * se if np.isfinite(se) else np.nan
    p_value = 1.0 - NormalDist().cdf(roi / se) if np.isfinite(se) and se > 0 else np.nan
    w = int(np.sum(wins))
    wilson_low, wilson_high = wilson_interval(w, n)

    return {
        "MacSayisi": n,
        "Kazanan": w,
        "KazanmaOrani": 100*w/n,
        "KazanmaAlt95": wilson_low,
        "KazanmaUst95": wilson_high,
        "ROI_Yuzde": 100*roi,
        "ROI_Alt95_Normal": 100*low if np.isfinite(low) else np.nan,
        "ROI_Ust95_Normal": 100*high if np.isfinite(high) else np.nan,
        "P_TekYonlu": p_value
    }

def bh_fdr(p_values):
    p = np.asarray(p_values, dtype=float)
    result = np.full(len(p), np.nan)
    valid_idx = np.where(np.isfinite(p))[0]
    if len(valid_idx) == 0:
        return result
    vals = p[valid_idx]
    order = np.argsort(vals)
    ranked = vals[order]
    m = len(ranked)
    q = ranked * m / np.arange(1, m+1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    q = np.clip(q, 0, 1)
    restored = np.empty(m)
    restored[order] = q
    result[valid_idx] = restored
    return result

def main():
    print("Veri okunuyor:", DATA_PATH.resolve())
    df = pd.read_csv(DATA_PATH, low_memory=False)

    required = [VAR_COL, YOK_COL, RESULT_COL]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("Eksik gerekli sütun(lar): " + repr(missing))

    date_col = find_date_column(df)
    dates = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
    if dates.notna().mean() < 0.80:
        raise ValueError(
            f"Tarih sutunu bulundu ancak tarihler okunamadi: {date_col!r}"
        )

    result = (
        df[RESULT_COL].astype("string").str.strip()
        .str.upper().str.replace("İ", "I", regex=False)
    )
    result = result.replace({
        "VAR": "VAR", "YOK": "YOK",
        "NAN": pd.NA, "": pd.NA, "NONE": pd.NA
    })

    work = pd.DataFrame({
        "Tarih": dates,
        "Gun": dates.dt.dayofweek.map({
            0: "Pazartesi", 1: "Sali", 2: "Carsamba",
            3: "Persembe", 4: "Cuma", 5: "Cumartesi", 6: "Pazar"
        }),
        "Yil": dates.dt.year,
        "Sonuc": result,
        "VarOran": parse_odds(df[VAR_COL]),
        "YokOran": parse_odds(df[YOK_COL])
    })

    print("Toplam satir:", len(work))
    print("Tarih sutunu:", date_col)
    print("Gecersiz tarih:", int(work["Tarih"].isna().sum()))
    print("KGVY VAR:", int((work["Sonuc"] == "VAR").sum()))
    print("KGVY YOK:", int((work["Sonuc"] == "YOK").sum()))
    print("Tarih araligi:",
          work["Tarih"].min().date(), "-", work["Tarih"].max().date())

    all_general = []
    all_bands = []
    all_tests = []

    markets = [
        ("KG_VAR", "VarOran", "VAR"),
        ("KG_YOK", "YokOran", "YOK")
    ]

    day_order = [
        "Pazartesi", "Sali", "Carsamba", "Persembe",
        "Cuma", "Cumartesi", "Pazar"
    ]

    for market, odds_col, winning_label in markets:
        valid = work[
            work["Tarih"].notna()
            & work["Sonuc"].isin(["VAR", "YOK"])
            & work[odds_col].notna()
            & (work[odds_col] >= MIN_ODDS)
            & (work[odds_col] < MAX_ODDS)
        ].copy()

        valid["Oran"] = valid[odds_col].astype(float)
        valid["Kazandi"] = valid["Sonuc"].eq(winning_label)
        valid["OranAlt"] = (
            np.floor((valid["Oran"] + 1e-10) / BAND_WIDTH)
            * BAND_WIDTH
        ).round(2)
        valid["OranUst"] = (valid["OranAlt"] + BAND_WIDTH).round(2)

        print(f"\n=== {market} ===")
        print("Analize giren mac:", len(valid))
        print("Oran araligi:", MIN_ODDS, "dahil;", MAX_ODDS, "haric")
        print("Kazanan bahis:", int(valid["Kazandi"].sum()))
        print("Kazanma orani:",
              round(100*valid["Kazandi"].mean(), 2) if len(valid) else "N/A")

        # Haftanin gunune gore genel sonuc
        for day in day_order:
            g = valid[valid["Gun"] == day]
            stats = roi_stats(g["Oran"].to_numpy(), g["Kazandi"].to_numpy())
            all_general.append({"Pazar": market, "Gun": day, **stats})

        # Oran bandi + haftanin gunu
        for day in day_order:
            day_df = valid[valid["Gun"] == day]
            if day_df.empty:
                continue
            for low in np.arange(MIN_ODDS, MAX_ODDS, BAND_WIDTH):
                low = round(float(low), 2)
                high = round(low + BAND_WIDTH, 2)
                g = day_df[
                    (day_df["Oran"] >= low)
                    & (day_df["Oran"] < high)
                ]
                if len(g) == 0:
                    continue

                stats = roi_stats(
                    g["Oran"].to_numpy(), g["Kazandi"].to_numpy()
                )
                early = g[g["Yil"].between(2014, 2019)]
                late = g[g["Yil"].between(2020, 2025)]
                early_roi = roi_stats(
                    early["Oran"].to_numpy(),
                    early["Kazandi"].to_numpy()
                )["ROI_Yuzde"]
                late_roi = roi_stats(
                    late["Oran"].to_numpy(),
                    late["Kazandi"].to_numpy()
                )["ROI_Yuzde"]

                row = {
                    "Pazar": market, "Gun": day,
                    "OranAlt": low, "OranUst": high,
                    **stats,
                    "ErkenDonemN": len(early),
                    "ErkenROI_Yuzde": early_roi,
                    "GecDonemN": len(late),
                    "GecROI_Yuzde": late_roi
                }
                all_bands.append(row)
                if len(g) >= MIN_N:
                    all_tests.append(row.copy())

    general_df = pd.DataFrame(all_general)
    bands_df = pd.DataFrame(all_bands)
    tests_df = pd.DataFrame(all_tests)

    if not tests_df.empty:
        tests_df["FDR_Q"] = bh_fdr(tests_df["P_TekYonlu"].to_numpy())
        tests_df["FDR_Gecti"] = tests_df["FDR_Q"] < 0.05
        tests_df = tests_df.sort_values(
            ["ROI_Yuzde"], ascending=False
        )
        candidates = tests_df[
            (tests_df["ROI_Yuzde"] > 0)
            & (tests_df["ROI_Alt95_Normal"] > 0)
            & (tests_df["FDR_Q"] < 0.05)
            & (tests_df["ErkenDonemN"] >= 20)
            & (tests_df["GecDonemN"] >= 20)
            & (tests_df["ErkenROI_Yuzde"] > 0)
            & (tests_df["GecROI_Yuzde"] > 0)
        ].copy()
    else:
        candidates = pd.DataFrame()

    general_path = OUT_DIR / "kg_haftanin_gunu_genel.csv"
    bands_path = OUT_DIR / "kg_haftanin_gunu_oran_bantlari.csv"
    tests_path = OUT_DIR / "kg_haftanin_gunu_test_edilen_bantlar.csv"
    candidates_path = OUT_DIR / "kg_haftanin_gunu_adaylar.csv"

    general_df.to_csv(general_path, index=False, encoding="utf-8-sig")
    bands_df.to_csv(bands_path, index=False, encoding="utf-8-sig")
    tests_df.to_csv(tests_path, index=False, encoding="utf-8-sig")
    candidates.to_csv(candidates_path, index=False, encoding="utf-8-sig")

    print("\n=== HAFTANIN GUNUNE GORE GENEL SONUC ===")
    if not general_df.empty:
        print(general_df.round(2).to_string(index=False))

    print(f"\nTest edilen oran bandi (N >= {MIN_N}):", len(tests_df))
    print("FDR q < 0,05:", int(tests_df["FDR_Gecti"].sum()) if not tests_df.empty else 0)
    print("Tum kosullari saglayan aday:", len(candidates))

    print("\n=== POZITIF ROI GOSTEREN EN IYI 20 BANT ===")
    if not tests_df.empty:
        positive = tests_df[tests_df["ROI_Yuzde"] > 0].head(20)
        if positive.empty:
            print("Pozitif ROI gosteren bant yok.")
        else:
            show_cols = [
                "Pazar", "Gun", "OranAlt", "OranUst", "MacSayisi",
                "KazanmaOrani", "ROI_Yuzde", "ROI_Alt95_Normal",
                "FDR_Q", "ErkenDonemN", "ErkenROI_Yuzde",
                "GecDonemN", "GecROI_Yuzde"
            ]
            print(positive[show_cols].round(2).to_string(index=False))

    print("\n=== ADAYLAR ===")
    if candidates.empty:
        print("Belirlenen istatistiksel ve donemsel kosullari saglayan aday yok.")
    else:
        print(candidates.to_string(index=False))

    print("\nDosyalar kaydedildi:")
    for p in [general_path, bands_path, tests_path, candidates_path]:
        print(p.resolve())

    print(
        "\nNOT: ROI guven araligi normal yaklasimlidir; FDR duzeltmesi "
        "test edilen tum KG Var/Yok bantlari uzerinde uygulanmistir. "
        "Kesif analizi gelecekte kazanc garantisi vermez."
    )

if __name__ == "__main__":
    main()
