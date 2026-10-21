from pathlib import Path
import math
import numpy as np
import pandas as pd

ROOT = Path.cwd()
DATA = ROOT / "data" / "csv" / "DATA.csv"
OUT = ROOT / "data" / "pattern_discovery_v2"
OUT.mkdir(parents=True, exist_ok=True)

DAYS = [
    "Pazartesi", "Sali", "Carsamba", "Persembe",
    "Cuma", "Cumartesi", "Pazar"
]

def number(series):
    return pd.to_numeric(
        series.astype(str).str.strip().str.replace(",", ".", regex=False),
        errors="coerce"
    )

def wilson(wins, n):
    if n <= 0:
        return (np.nan, np.nan)
    z = 1.959963984540054
    p = wins / n
    den = 1 + z*z/n
    center = (p + z*z/(2*n)) / den
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return center-half, center+half

def metrics(frame):
    n = len(frame)
    if n == 0:
        return (0, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan)

    wins = int(frame["over"].sum())
    hit = wins / n
    profit = frame["profit"].to_numpy(dtype=float)
    roi = float(profit.mean())
    se = float(profit.std(ddof=1) / math.sqrt(n)) if n > 1 else np.nan
    low = roi - 1.96*se if np.isfinite(se) else np.nan
    high = roi + 1.96*se if np.isfinite(se) else np.nan
    hlow, hhigh = wilson(wins, n)
    return n, hit, roi, low, high, hlow, hhigh

def main():
    if not DATA.exists():
        raise FileNotFoundError(f"Veri dosyasi bulunamadi: {DATA}")

    print("Veri okunuyor:", DATA)
    df = pd.read_csv(
        DATA, sep=None, engine="python",
        encoding="utf-8-sig", dtype=str
    )

    needed = ["Tarih", "Skor", "MS25AÜ", "2,5_Alt/Üst_|_Üst"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"Eksik sutunlar: {missing}")

    df["date"] = pd.to_datetime(
        df["Tarih"], format="%d-%m-%Y", errors="coerce"
    )

    score = df["Skor"].astype(str).str.extract(
        r"^\s*(\d+)\s*[-:]\s*(\d+)\s*$"
    )
    home = pd.to_numeric(score[0], errors="coerce")
    away = pd.to_numeric(score[1], errors="coerce")

    df["over"] = np.where(home.notna() & away.notna(),
                          ((home + away) > 2).astype(float), np.nan)

    label = df["MS25AÜ"].astype(str).str.strip().str.upper()
    label_over = np.where(label.eq("ÜST"), 1,
                 np.where(label.eq("ALT"), 0, np.nan))

    valid_score = pd.Series(df["over"], index=df.index).notna()
    valid_label = pd.Series(label_over, index=df.index).notna()
    mismatch = valid_score & valid_label & (df["over"] != label_over)

    df["odds"] = number(df["2,5_Alt/Üst_|_Üst"])

    print("Toplam satir:", len(df))
    print("Gecersiz tarih:", int(df["date"].isna().sum()))
    print("Skor-etiket uyusmazligi:", int(mismatch.sum()))
    print("Bos/gecersiz oran:", int(df["odds"].isna().sum()))

    df = df.loc[
        ~mismatch
        & df["date"].notna()
        & df["over"].notna()
        & df["odds"].notna()
    ].copy()

    df["over"] = df["over"].astype(int)
    df = df.loc[(df["odds"] >= 1.0) & (df["odds"] < 5.0)].copy()

    df["weekday_id"] = df["date"].dt.dayofweek
    df["weekday"] = df["weekday_id"].map(dict(enumerate(DAYS)))
    df["band_low"] = np.floor(df["odds"] * 10 + 1e-8) / 10
    df["band_high"] = df["band_low"] + 0.1
    df["profit"] = np.where(df["over"] == 1, df["odds"] - 1.0, -1.0)
    df["period"] = np.where(df["date"].dt.year <= 2020,
                            "2013-2020", "2021-2026")

    print("Analize giren mac:", len(df))
    if len(df) == 0:
        raise ValueError("Filtrelerden sonra analiz edilecek mac kalmadi.")

    print("Tarih araligi:",
          df["date"].min().date(), "-", df["date"].max().date())
    print("Oran araligi: 1,00 dahil; 5,00 haric; bant genisligi 0,10")

    rows = []
    for day_id in range(7):
        for band in sorted(df["band_low"].unique()):
            part = df.loc[
                (df["weekday_id"] == day_id) & (df["band_low"] == band)
            ]
            if part.empty:
                continue

            n, hit, roi, low, high, hlow, hhigh = metrics(part)
            early = metrics(part.loc[part["period"] == "2013-2020"])
            late = metrics(part.loc[part["period"] == "2021-2026"])

            se = part["profit"].std(ddof=1) / math.sqrt(n) if n > 1 else np.nan
            z = roi / se if np.isfinite(se) and se > 0 else 0.0
            pvalue = 0.5 * math.erfc(z / math.sqrt(2.0))

            rows.append((
                DAYS[day_id], day_id, band, band + 0.1, n,
                int(part["over"].sum()), hit, hlow, hhigh,
                roi, low, high, early[0], early[2],
                late[0], late[2], pvalue
            ))

    cols = [
        "Gun", "GunNo", "OranAlt", "OranUst", "MacSayisi",
        "UstKazanan", "UstKazanmaOrani", "KazanmaWilsonAlt95",
        "KazanmaWilsonUst95", "ROI", "ROI_Alt95_Normal",
        "ROI_Ust95_Normal", "ErkenDonemN", "ErkenDonemROI",
        "GecDonemN", "GecDonemROI", "P_Degeri_TekYonlu"
    ]
    result = pd.DataFrame(rows, columns=cols)
    result["FDR_Q"] = np.nan

    test_idx = result.index[result["MacSayisi"] >= 30].to_numpy()
    if len(test_idx):
        pv = result.loc[test_idx, "P_Degeri_TekYonlu"].to_numpy(dtype=float)
        order = np.argsort(pv)
        ranked = pv[order] * len(pv) / np.arange(1, len(pv) + 1)
        ranked = np.minimum.accumulate(ranked[::-1])[::-1]
        q = np.empty(len(pv), dtype=float)
        q[order] = np.minimum(ranked, 1.0)
        result.loc[test_idx, "FDR_Q"] = q

    result["ROI_Yuzde"] = result["ROI"] * 100
    result["Kazanma_Yuzde"] = result["UstKazanmaOrani"] * 100
    result["ErkenROI_Yuzde"] = result["ErkenDonemROI"] * 100
    result["GecROI_Yuzde"] = result["GecDonemROI"] * 100

    result.to_csv(
        OUT / "haftanin_gunu_25ust_oran_bantlari.csv",
        index=False, encoding="utf-8-sig"
    )

    overall_rows = []
    for day_id in range(7):
        part = df.loc[df["weekday_id"] == day_id]
        n, hit, roi, low, high, hlow, hhigh = metrics(part)
        overall_rows.append((
            DAYS[day_id], n, int(part["over"].sum()),
            hit, hlow, hhigh, roi, low, high
        ))

    overall = pd.DataFrame(overall_rows, columns=[
        "Gun", "MacSayisi", "UstKazanan", "UstKazanmaOrani",
        "KazanmaAlt95", "KazanmaUst95", "ROI",
        "ROI_Alt95_Normal", "ROI_Ust95_Normal"
    ])
    overall.to_csv(
        OUT / "haftanin_gunu_25ust_genel.csv",
        index=False, encoding="utf-8-sig"
    )

    selected = result.loc[result["MacSayisi"] >= 30].copy()
    selected = selected.sort_values(
        ["FDR_Q", "ROI"], ascending=[True, False], na_position="last"
    )
    selected.to_csv(
        OUT / "haftanin_gunu_25ust_test_edilen_bantlar.csv",
        index=False, encoding="utf-8-sig"
    )

    candidates = selected.loc[
        (selected["ROI"] > 0)
        & (selected["FDR_Q"] < 0.05)
        & (selected["ErkenDonemN"] >= 20)
        & (selected["GecDonemN"] >= 20)
        & (selected["ErkenDonemROI"] > 0)
        & (selected["GecDonemROI"] > 0)
    ].copy()
    candidates.to_csv(
        OUT / "haftanin_gunu_25ust_adaylar.csv",
        index=False, encoding="utf-8-sig"
    )

    print("\n=== HAFTANIN GUNUNE GORE GENEL SONUC ===")
    show = overall.copy()
    for c in ["UstKazanmaOrani", "KazanmaAlt95", "KazanmaUst95",
              "ROI", "ROI_Alt95_Normal", "ROI_Ust95_Normal"]:
        show[c] = (show[c] * 100).round(2)
    print(show.to_string(index=False))

    print("\n=== POZITIF ROI GOSTEREN ILK 20 BANT (N >= 30) ===")
    top = selected.loc[selected["ROI"] > 0].head(20).copy()
    if top.empty:
        print("N >= 30 olan bantlarda pozitif ROI bulunamadi.")
    else:
        display_cols = [
            "Gun", "OranAlt", "OranUst", "MacSayisi",
            "UstKazanmaOrani", "ROI_Yuzde", "ROI_Alt95_Normal",
            "FDR_Q", "ErkenDonemN", "ErkenROI_Yuzde",
            "GecDonemN", "GecROI_Yuzde"
        ]
        top["UstKazanmaOrani"] *= 100
        top["ROI_Alt95_Normal"] *= 100
        for c in ["ROI_Yuzde", "ROI_Alt95_Normal",
                  "ErkenROI_Yuzde", "GecROI_Yuzde"]:
            top[c] = top[c].round(2)
        top["UstKazanmaOrani"] = top["UstKazanmaOrani"].round(2)
        top["FDR_Q"] = top["FDR_Q"].round(4)
        print(top[display_cols].to_string(index=False))

    print("\nTest edilen bant sayisi (N >= 30):", len(test_idx))
    print("FDR q < 0,05 sayisi:",
          int((result.loc[test_idx, "FDR_Q"] < 0.05).sum()) if len(test_idx) else 0)
    print("Donemler arasi kosullari da saglayan aday:", len(candidates))
    print("\nDosyalar kaydedildi:")
    print(OUT / "haftanin_gunu_25ust_genel.csv")
    print(OUT / "haftanin_gunu_25ust_oran_bantlari.csv")
    print(OUT / "haftanin_gunu_25ust_test_edilen_bantlar.csv")
    print(OUT / "haftanin_gunu_25ust_adaylar.csv")
    print("\nNOT: ROI guven araliklari ve p degerleri yaklasik normal yontemlidir.")
    print("Bu kesif analizi tek basina gelecekte kazanc garantisi vermez.")

if __name__ == "__main__":
    main()
