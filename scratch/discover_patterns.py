import re
import math
from pathlib import Path

import numpy as np
import pandas as pd

# ============================================================
# AYARLAR
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "csv" / "DATA.csv"
OUTPUT_DIR = BASE_DIR / "data" / "pattern_discovery_v2"

MIN_SAMPLE = 30
THRESHOLDS = [60, 65, 70, 75, 80]

# 1.00-5.00 arasında 0.10 genişliğinde bantlar.
# 5.00 ve üzeri bu ilk taramaya alınmaz.
ODDS_MIN = 1.00
ODDS_MAX = 5.00
ODDS_STEP = 0.10

MARKETS = {
    "MS1": ("Maç_Sonucu_|_1", "MS1"),
    "MSX": ("Maç_Sonucu_|_X", "MSX"),
    "MS2": ("Maç_Sonucu_|_2", "MS2"),
    "KG_VAR": ("Karşılıklı_Gol_|_Var", "KG_VAR"),
    "KG_YOK": ("Karşılıklı_Gol_|_Yok", "KG_YOK"),
    "1.5_ALT": ("1,5_Alt/Üst_|_Alt", "1.5_ALT"),
    "1.5_UST": ("1,5_Alt/Üst_|_Üst", "1.5_UST"),
    "2.5_ALT": ("2,5_Alt/Üst_|_Alt", "2.5_ALT"),
    "2.5_UST": ("2,5_Alt/Üst_|_Üst", "2.5_UST"),
    "3.5_ALT": ("3,5_Alt/Üst_|_Alt", "3.5_ALT"),
    "3.5_UST": ("3,5_Alt/Üst_|_Üst", "3.5_UST"),
    "4.5_ALT": ("4,5_Alt/Üst_|_Alt", "4.5_ALT"),
    "4.5_UST": ("4,5_Alt/Üst_|_Üst", "4.5_UST"),
}

DAY_NAMES = {
    0: "Pazartesi",
    1: "Salı",
    2: "Çarşamba",
    3: "Perşembe",
    4: "Cuma",
    5: "Cumartesi",
    6: "Pazar",
}


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def parse_decimal(series):
    """Ondalık virgül veya nokta içeren değerleri sayıya çevirir."""
    s = series.astype("string").str.strip()
    s = s.str.replace(",", ".", regex=False)
    s = s.replace({
        "": pd.NA,
        "-": pd.NA,
        "nan": pd.NA,
        "None": pd.NA,
        "NA": pd.NA,
    })
    return pd.to_numeric(s, errors="coerce")


def normalize_league(value):
    """Sezon ve isim farklılıklarını iki ana lig ailesinde toplar."""
    name = str(value).strip()

    if re.search(r"(?i)\b1\.?\s*Lig\b", name):
        return "Türkiye 1. Lig"

    if re.search(r"(?i)Süper\s*Lig", name):
        return "Türkiye Süper Lig"

    return "DİĞER / EŞLEŞMEDİ"


def extract_season(value):
    match = re.search(r"(\d{4}/\d{4})\s*$", str(value).strip())
    return match.group(1) if match else "SEZON_BULUNAMADI"


def parse_score(value):
    """Skor yalnızca tam sayı x tam sayı biçimindeyse geçerlidir."""
    match = re.fullmatch(
        r"\s*(\d+)\s*[-–:]\s*(\d+)\s*",
        str(value)
    )
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2))


def odds_band(odds):
    if not np.isfinite(odds) or odds < ODDS_MIN or odds >= ODDS_MAX:
        return None

    lower = math.floor((odds + 1e-10) / ODDS_STEP) * ODDS_STEP
    lower = round(lower, 2)
    upper = round(lower + ODDS_STEP, 2)

    return f"{lower:.2f}-{upper:.2f}"


def wilson_interval(wins, n, z=1.959963984540054):
    """%95 Wilson güven aralığı; yüzde ölçeğinde döndürür."""
    if n <= 0:
        return np.nan, np.nan

    p = wins / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    margin = (
        z
        * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
        / denominator
    )

    return 100 * (center - margin), 100 * (center + margin)


# ============================================================
# VERİYİ OKU VE HAZIRLA
# ============================================================

def main():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"CSV bulunamadı: {DATA_FILE}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("CSV okunuyor...")
    df = pd.read_csv(DATA_FILE, encoding="utf-8-sig", low_memory=False)

    required = ["Tarih", "Lig/Sezon", "Skor"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Eksik zorunlu sütunlar: {missing}")

    df["Tarih_Parsed"] = pd.to_datetime(
        df["Tarih"].astype("string").str.strip(),
        format="%d-%m-%Y",
        errors="coerce",
    )

    df["Lig"] = df["Lig/Sezon"].map(normalize_league)
    df["Sezon"] = df["Lig/Sezon"].map(extract_season)
    df["Gun"] = df["Tarih_Parsed"].dt.dayofweek.map(DAY_NAMES)

    scores = df["Skor"].map(parse_score)
    df["Ev_Gol"] = [x[0] for x in scores]
    df["Dep_Gol"] = [x[1] for x in scores]

    df["Skor_Gecerli"] = (
        df["Ev_Gol"].notna()
        & df["Dep_Gol"].notna()
        & df["Tarih_Parsed"].notna()
    )

    df["Toplam_Gol"] = df["Ev_Gol"] + df["Dep_Gol"]

    # Her market için gerçek maç sonucu.
    df["MS1_Sonuc"] = (df["Ev_Gol"] > df["Dep_Gol"]).astype("float")
    df["MSX_Sonuc"] = (df["Ev_Gol"] == df["Dep_Gol"]).astype("float")
    df["MS2_Sonuc"] = (df["Ev_Gol"] < df["Dep_Gol"]).astype("float")

    df["KG_VAR_Sonuc"] = (
        (df["Ev_Gol"] > 0) & (df["Dep_Gol"] > 0)
    ).astype("float")
    df["KG_YOK_Sonuc"] = (
        (df["Ev_Gol"] == 0) | (df["Dep_Gol"] == 0)
    ).astype("float")

    for line in [1.5, 2.5, 3.5, 4.5]:
        key = str(line)
        df[f"{key}_ALT_Sonuc"] = (df["Toplam_Gol"] < line).astype("float")
        df[f"{key}_UST_Sonuc"] = (df["Toplam_Gol"] > line).astype("float")

    # Gerçek skorla market sonucu tutarlı mı?
    # Kaynak oran sütunları yalnızca oran kabul edilir; sonuç etiketi
    # skor üzerinden bağımsız biçimde hesaplanır.
    market_rows = []
    coverage_rows = []

    for market, (odds_col, result_key) in MARKETS.items():
        if odds_col not in df.columns:
            coverage_rows.append({
                "Market": market,
                "Oran_Sutunu": odds_col,
                "Sutun_Mevcut": False,
                "Skoru_Gecerli_Mac": int(df["Skor_Gecerli"].sum()),
                "Orani_Gecerli_Mac": 0,
            })
            continue

        odds = parse_decimal(df[odds_col])
        result_col = f"{result_key}_Sonuc"

        df[f"{result_key}_Oran"] = odds
        df[f"{result_key}_Sonuc"] = df[result_col]

        usable = (
            df["Skor_Gecerli"]
            & odds.notna()
            & (odds > 1.0)
            & (odds < ODDS_MAX)
            & df["Gun"].notna()
        )

        coverage_rows.append({
            "Market": market,
            "Oran_Sutunu": odds_col,
            "Sutun_Mevcut": True,
            "Skoru_Gecerli_Mac": int(df["Skor_Gecerli"].sum()),
            "Orani_Gecerli_Mac": int(usable.sum()),
        })

        tmp = pd.DataFrame({
            "Lig": df.loc[usable, "Lig"],
            "Sezon": df.loc[usable, "Sezon"],
            "Gun": df.loc[usable, "Gun"],
            "Market": market,
            "Oran": odds.loc[usable],
            "Sonuc": df.loc[usable, result_col],
        })

        tmp["Oran_Araligi"] = tmp["Oran"].map(odds_band)
        tmp = tmp[tmp["Oran_Araligi"].notna()].copy()
        tmp["Kazandi"] = tmp["Sonuc"].astype(int)
        tmp["Net_Birim_Kar"] = np.where(
            tmp["Kazandi"] == 1,
            tmp["Oran"] - 1.0,
            -1.0,
        )
        market_rows.append(tmp)

    pd.DataFrame(coverage_rows).to_csv(
        OUTPUT_DIR / "market_kapsami.csv",
        index=False,
        encoding="utf-8-sig",
    )

    if not market_rows:
        raise RuntimeError("Analiz edilebilir market bulunamadı.")

    observations = pd.concat(market_rows, ignore_index=True)

    # ========================================================
    # ÖRÜNTÜ TARAMASI
    # ========================================================

    pattern_keys = ["Lig", "Gun", "Market", "Oran_Araligi"]
    season_keys = ["Lig", "Sezon", "Gun", "Market", "Oran_Araligi"]

    def summarize(group, keys):
        result = group.groupby(keys, dropna=False).agg(
            Mac_Sayisi=("Kazandi", "size"),
            Kazanan_Sayisi=("Kazandi", "sum"),
            Toplam_Net_Kar=("Net_Birim_Kar", "sum"),
            Ortalama_Oran=("Oran", "mean"),
        ).reset_index()

        result["Basari_Yuzdesi"] = (
            result["Kazanan_Sayisi"] / result["Mac_Sayisi"] * 100
        )
        result["ROI_Yuzde"] = (
            result["Toplam_Net_Kar"] / result["Mac_Sayisi"] * 100
        )

        intervals = [
            wilson_interval(int(w), int(n))
            for w, n in zip(
                result["Kazanan_Sayisi"],
                result["Mac_Sayisi"],
            )
        ]

        result["Basari_GA95_Alt"] = [x[0] for x in intervals]
        result["Basari_GA95_Ust"] = [x[1] for x in intervals]

        return result

    all_patterns = summarize(observations, pattern_keys)
    all_patterns = all_patterns[
        all_patterns["Mac_Sayisi"] >= MIN_SAMPLE
    ].copy()

    all_patterns = all_patterns.sort_values(
        ["Basari_Yuzdesi", "Mac_Sayisi"],
        ascending=[False, False],
    )

    all_patterns.to_csv(
        OUTPUT_DIR / "tum_oruntuler.csv",
        index=False,
        encoding="utf-8-sig",
    )

    threshold_patterns = all_patterns[
        all_patterns["Basari_Yuzdesi"] >= min(THRESHOLDS)
    ].copy()

    threshold_patterns.to_csv(
        OUTPUT_DIR / "basari_esigini_gecenler.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # Sezon bazlı sonuçlar: doğrulama için temel tablo.
    season_patterns = summarize(observations, season_keys)

    season_patterns.to_csv(
        OUTPUT_DIR / "sezon_bazli_oruntuler.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # Eşik özeti: toplam maç gözlemleri örtüşebilir, bağımsız maç sayısı değildir.
    threshold_summary = []
    for threshold in THRESHOLDS:
        selected = all_patterns[
            all_patterns["Basari_Yuzdesi"] >= threshold
        ]
        threshold_summary.append({
            "Basari_Esigi_Yuzde": threshold,
            "Oruntu_Sayisi": len(selected),
            "Toplam_Kazanan": int(selected["Kazanan_Sayisi"].sum()),
            "Toplam_Mac_Gozlemi": int(selected["Mac_Sayisi"].sum()),
        })

    pd.DataFrame(threshold_summary).to_csv(
        OUTPUT_DIR / "esik_ozeti.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # Lig adlarının normalize edilmiş toplamları.
    league_summary = (
        df.groupby("Lig", dropna=False)
        .agg(
            Mac_Sayisi=("Skor_Gecerli", "size"),
            Gecerli_Skor=("Skor_Gecerli", "sum"),
            Farkli_Orijinal_Ad=("Lig/Sezon", "nunique"),
        )
        .reset_index()
    )

    league_summary.to_csv(
        OUTPUT_DIR / "lig_normalizasyonu.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # ========================================================
    # ÖZET
    # ========================================================

    print("\n=== TARAMA TAMAMLANDI ===")
    print(f"CSV satırı: {len(df)}")
    print(f"Geçerli skor ve tarih: {int(df['Skor_Gecerli'].sum())}")
    print(f"Lig ailesi sayısı: {df['Lig'].nunique()}")
    print(f"Market sayısı: {len(MARKETS)}")
    print(f"Minimum örneklem: {MIN_SAMPLE}")
    print(f"Örneklem filtresini geçen örüntü: {len(all_patterns)}")

    for threshold in THRESHOLDS:
        count = int(
            (all_patterns["Basari_Yuzdesi"] >= threshold).sum()
        )
        print(f"%{threshold} ve üzeri örüntü: {count}")

    print(f"\nRapor klasörü: {OUTPUT_DIR}")
    print("Dosyalar:")
    for filename in [
        "market_kapsami.csv",
        "lig_normalizasyonu.csv",
        "tum_oruntuler.csv",
        "basari_esigini_gecenler.csv",
        "esik_ozeti.csv",
        "sezon_bazli_oruntuler.csv",
    ]:
        print(f"  {filename}")

    print(
        "\nUYARI: Bu dosyalar keşif sonuçlarıdır. "
        "Sezonlar arası doğrulama ve çoklu test düzeltmesi "
        "yapılmadan örüntüler doğrulanmış avantaj sayılmaz."
    )


if __name__ == "__main__":
    main()


