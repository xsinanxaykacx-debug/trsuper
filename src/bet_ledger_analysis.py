"""Analyze Model C selected-bet ledger: calibration, side/season splits, odds effects.

Run from repository root with: python -m src.bet_ledger_analysis

Important scope:
- Calibration is measured only on bets selected by the Turkish-odds EV > 0.05 rule,
  not on every test match. It is conditional/selection-biased calibration and must
  not be presented as the model's global probability calibration.
- The synthetic sharp prices are generated from the same model probabilities.
  They are not independent Pinnacle/Betfair market odds.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


INPUT_PATH = Path("data/csv/sharp_market_simulation_bet_ledger.csv")
OUTPUT_DIR = Path("data/csv")
CALIBRATION_PATH = OUTPUT_DIR / "bet_ledger_calibration.csv"
SIDE_PATH = OUTPUT_DIR / "bet_ledger_side_breakdown.csv"
SEASON_PATH = OUTPUT_DIR / "bet_ledger_season_breakdown.csv"
PRICE_PATH = OUTPUT_DIR / "bet_ledger_turkey_vs_synthetic.csv"
PRICE_DETAIL_PATH = OUTPUT_DIR / "bet_ledger_price_difference_by_bet.csv"

REQUIRED_COLUMNS = {
    "_id", "_date", "_season", "selected_side",
    "selected_model_probability", "is_win",
    "selected_turkey_odds", "selected_sharp_odds",
    "profit_turkey_flat_1u", "profit_sharp_flat_1u",
}


def wilson_interval(wins: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if total <= 0:
        return np.nan, np.nan
    p = wins / total
    denom = 1.0 + z * z / total
    centre = (p + z * z / (2.0 * total)) / denom
    radius = z * np.sqrt((p * (1.0 - p) / total) + (z * z / (4.0 * total * total))) / denom
    return max(0.0, centre - radius), min(1.0, centre + radius)


def load_ledger(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Bahis günlüğü bulunamadı: {path}\n"
            "Önce python -m src.sharp_market_simulation komutunu çalıştır."
        )
    frame = pd.read_csv(path, encoding="utf-8-sig")
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise KeyError(
            "Bahis günlüğünde beklenen sütunlar eksik: "
            f"{missing}. Dosya, sharp_market_simulation.py tarafından üretilmiş olmalı."
        )
    if frame.empty:
        raise ValueError("Bahis günlüğü boş; analiz yapılamıyor.")

    frame["_date"] = pd.to_datetime(frame["_date"], errors="coerce")
    numeric_columns = [
        "selected_model_probability", "selected_turkey_odds", "selected_sharp_odds",
        "profit_turkey_flat_1u", "profit_sharp_flat_1u",
    ]
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    if frame["is_win"].dtype == object:
        normalized = frame["is_win"].astype(str).str.strip().str.lower()
        frame["is_win"] = normalized.map({
            "true": True, "false": False, "1": True, "0": False,
            "yes": True, "no": False,
        })
        if frame["is_win"].isna().any():
            raise ValueError("is_win sütununda True/False olarak yorumlanamayan değer var.")
    else:
        frame["is_win"] = frame["is_win"].astype(bool)

    frame["selected_side"] = frame["selected_side"].astype(str).str.upper().str.strip()
    frame["_season"] = frame["_season"].astype(str).str.strip()
    frame = frame.dropna(subset=numeric_columns + ["_season"]).copy()

    if not frame["selected_model_probability"].between(0.0, 1.0).all():
        raise ValueError("selected_model_probability içinde [0, 1] dışında değer var.")
    if not frame["selected_side"].isin(["ALT", "UST"]).all():
        raise ValueError(
            "selected_side yalnızca ALT/UST içermeli; bulunan değerler: "
            f"{sorted(frame['selected_side'].unique())}"
        )
    if frame["_id"].duplicated().any():
        duplicates = int(frame["_id"].duplicated().sum())
        raise ValueError(f"Bahis günlüğünde yinelenen maç ID sayısı: {duplicates}")
    return frame.sort_values(["_date", "_id"], kind="stable").reset_index(drop=True)


def calibration_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Group selected-side probabilities and compare predicted vs observed wins."""
    out = frame.copy()
    edges = [0.0, 0.50, 0.55, 0.60, 0.65, 0.70, 1.000000001]
    labels = ["<50%", "50–55%", "55–60%", "60–65%", "65–70%", "70%+"]
    out["probability_band"] = pd.cut(
        out["selected_model_probability"], bins=edges, labels=labels,
        right=False, include_lowest=True,
    )
    rows: list[dict] = []
    for label in labels:
        group = out.loc[out["probability_band"] == label]
        n = int(len(group))
        if n == 0:
            rows.append({
                "probability_band": label, "bets": 0,
                "mean_predicted_probability_pct": np.nan,
                "actual_win_rate_pct": np.nan,
                "calibration_gap_actual_minus_predicted_pp": np.nan,
                "actual_win_rate_ci95_low_pct": np.nan,
                "actual_win_rate_ci95_high_pct": np.nan,
                "brier_score": np.nan, "interpretation": "Bu aralıkta bahis yok",
            })
            continue

        predicted = float(group["selected_model_probability"].mean())
        wins = int(group["is_win"].sum())
        observed = wins / n
        ci_low, ci_high = wilson_interval(wins, n)
        gap_pp = (observed - predicted) * 100.0
        if gap_pp <= -2.0:
            interpretation = "Aşırı özgüven: gerçekleşen oran tahminden düşük"
        elif gap_pp >= 2.0:
            interpretation = "Çekingen: gerçekleşen oran tahminden yüksek"
        else:
            interpretation = "Bu grupta fark %2 puandan küçük"
        rows.append({
            "probability_band": label, "bets": n,
            "mean_predicted_probability_pct": predicted * 100.0,
            "actual_win_rate_pct": observed * 100.0,
            "calibration_gap_actual_minus_predicted_pp": gap_pp,
            "actual_win_rate_ci95_low_pct": ci_low * 100.0,
            "actual_win_rate_ci95_high_pct": ci_high * 100.0,
            "brier_score": float(np.mean(
                (group["selected_model_probability"].to_numpy()
                 - group["is_win"].astype(float).to_numpy()) ** 2
            )),
            "interpretation": interpretation,
        })
    return pd.DataFrame(rows)


def performance_summary(frame: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    rows: list[dict] = []
    for key, group in frame.groupby(group_columns, dropna=False, sort=True):
        keys = key if isinstance(key, tuple) else (key,)
        row = dict(zip(group_columns, keys))
        n = int(len(group))
        wins = int(group["is_win"].sum())
        turkey_profit = float(group["profit_turkey_flat_1u"].sum())
        sharp_profit = float(group["profit_sharp_flat_1u"].sum())
        turkey_roi = turkey_profit / n * 100.0 if n else np.nan
        sharp_roi = sharp_profit / n * 100.0 if n else np.nan
        row.update({
            "bets": n, "wins": wins, "losses": n - wins,
            "win_rate_pct": wins / n * 100.0 if n else np.nan,
            "turkey_total_profit_1u": turkey_profit, "turkey_roi_pct": turkey_roi,
            "synthetic_sharp_total_profit_1u": sharp_profit,
            "synthetic_sharp_roi_pct": sharp_roi,
            "sharp_minus_turkey_profit_1u": sharp_profit - turkey_profit,
            "sharp_minus_turkey_roi_pp": sharp_roi - turkey_roi,
            "mean_turkey_odds": float(group["selected_turkey_odds"].mean()),
            "mean_synthetic_sharp_odds": float(group["selected_sharp_odds"].mean()),
        })
        rows.append(row)
    return pd.DataFrame(rows)


def price_difference_analysis(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Attribute flat-stake payout differences to exact matches and summary groups."""
    out = frame.copy()
    out["turkey_profit_recomputed"] = np.where(
        out["is_win"], out["selected_turkey_odds"] - 1.0, -1.0
    )
    out["synthetic_sharp_profit_recomputed"] = np.where(
        out["is_win"], out["selected_sharp_odds"] - 1.0, -1.0
    )
    out["profit_difference_sharp_minus_turkey"] = (
        out["synthetic_sharp_profit_recomputed"] - out["turkey_profit_recomputed"]
    )
    out["odds_difference_sharp_minus_turkey"] = (
        out["selected_sharp_odds"] - out["selected_turkey_odds"]
    )
    out["price_difference_driver"] = np.where(
        ~out["is_win"], "Kaybeden bahis: iki kaynakta da -1 birim",
        np.where(
            out["profit_difference_sharp_minus_turkey"] < -1e-12,
            "Kazanan bahis: sentetik ödeme daha düşük",
            np.where(
                out["profit_difference_sharp_minus_turkey"] > 1e-12,
                "Kazanan bahis: sentetik ödeme daha yüksek",
                "Kazanan bahis: ödeme aynı",
            ),
        ),
    )

    if not np.allclose(out["turkey_profit_recomputed"], out["profit_turkey_flat_1u"], atol=1e-6):
        raise ValueError("Türkiye kârı, oran ve is_win sütunlarından yeniden üretilemedi.")
    if not np.allclose(out["synthetic_sharp_profit_recomputed"], out["profit_sharp_flat_1u"], atol=1e-6):
        raise ValueError("Sentetik kâr, oran ve is_win sütunlarından yeniden üretilemedi.")

    details_columns = [
        "_id", "_date", "_season", "Ev_Sahibi", "Deplasman",
        "selected_side", "selected_model_probability", "is_win",
        "selected_turkey_odds", "selected_sharp_odds",
        "odds_difference_sharp_minus_turkey",
        "turkey_profit_recomputed", "synthetic_sharp_profit_recomputed",
        "profit_difference_sharp_minus_turkey", "price_difference_driver",
    ]
    details = out[[col for col in details_columns if col in out.columns]].copy()
    details = details.sort_values("profit_difference_sharp_minus_turkey", kind="stable").reset_index(drop=True)

    summary = performance_summary(out, ["_season", "selected_side"])
    all_summary = performance_summary(out.assign(_all="ALL"), ["_all"])
    return pd.concat([summary, all_summary], ignore_index=True), details


def print_table(title: str, frame: pd.DataFrame) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)
    if frame.empty:
        print("(Sonuç yok)")
        return
    with pd.option_context("display.max_columns", None, "display.width", 220, "display.max_colwidth", 55):
        print(frame.to_string(index=False, float_format=lambda value: f"{value:,.3f}"))


def main() -> None:
    print("1. Bahis günlüğü okunuyor...")
    bets = load_ledger(INPUT_PATH)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"   Dosya: {INPUT_PATH}")
    print(f"   Analize giren bahis: {len(bets):,}")
    print(f"   Sezonlar: {', '.join(sorted(bets['_season'].unique()))}")
    print("   NOT: Kalibrasyon, tüm maçları değil yalnızca EV > 0.05 seçilmiş bahisleri kapsar.")

    calibration = calibration_table(bets)
    calibration.to_csv(CALIBRATION_PATH, index=False, encoding="utf-8-sig")
    print_table("1. OLASILIK KALİBRASYONU — SEÇİLMİŞ BAHİSLER", calibration)
    p = bets["selected_model_probability"].to_numpy(dtype=float)
    y = bets["is_win"].astype(float).to_numpy()
    print(f"Seçilmiş bahislerde ortalama tahmin: %{p.mean() * 100.0:.2f}")
    print(f"Seçilmiş bahislerde gerçekleşen kazanma oranı: %{y.mean() * 100.0:.2f}")
    print(f"Seçilmiş bahislerde Brier skoru: {np.mean((p - y) ** 2):.5f}")

    side = performance_summary(bets, ["selected_side"])
    side.to_csv(SIDE_PATH, index=False, encoding="utf-8-sig")
    print_table("2. ALT 2.5 / ÜST 2.5 KIRILIMI (SABİT 1 BİRİM)", side)

    season = performance_summary(bets, ["_season"])
    season.to_csv(SEASON_PATH, index=False, encoding="utf-8-sig")
    print_table("3. SEZON KIRILIMI (SABİT 1 BİRİM)", season)
    print_table("3B. SEZON × ALT/ÜST KIRILIMI", performance_summary(bets, ["_season", "selected_side"]))

    price_summary, price_details = price_difference_analysis(bets)
    price_summary.to_csv(PRICE_PATH, index=False, encoding="utf-8-sig")
    price_details.to_csv(PRICE_DETAIL_PATH, index=False, encoding="utf-8-sig")
    print_table("4. TÜRKİYE vs SENTETİK — KÂR FARKININ KAYNAĞI", price_summary)

    turkey_profit = float(bets["profit_turkey_flat_1u"].sum())
    sharp_profit = float(bets["profit_sharp_flat_1u"].sum())
    delta = sharp_profit - turkey_profit
    winners = bets.loc[bets["is_win"]]
    winning_delta = float((winners["selected_sharp_odds"] - winners["selected_turkey_odds"]).sum())
    losing_count = int((~bets["is_win"]).sum())
    print("\nKÂR FARKI MUTABAKATI")
    print(f"Türkiye toplam kâr/zarar: {turkey_profit:+.2f} birim")
    print(f"Sentetik toplam kâr/zarar: {sharp_profit:+.2f} birim")
    print(f"Sentetik - Türkiye farkı: {delta:+.2f} birim")
    print(f"Kazanan bahislerde oran farklarının toplamı: {winning_delta:+.2f} birim")
    print(f"Kaybeden bahis sayısı (her iki kaynakta da -1 birim): {losing_count:,}")
    print(f"Kontrol: farklar eşleşiyor mu? {'EVET' if np.isclose(delta, winning_delta, atol=1e-6) else 'HAYIR'}")
    print_table("SENTETİK FİYATIN TÜRKİYE'YE GÖRE EN ÇOK KÂR DÜŞÜRDÜĞÜ İLK 15 BAHİS", price_details.head(15))

    print("\nÇıktı dosyaları:")
    print(f"  Kalibrasyon: {CALIBRATION_PATH}")
    print(f"  ALT/ÜST: {SIDE_PATH}")
    print(f"  Sezon: {SEASON_PATH}")
    print(f"  Türkiye vs sentetik özet: {PRICE_PATH}")
    print(f"  Maç bazında fiyat farkı: {PRICE_DETAIL_PATH}")
    print("\nYORUM SINIRI: Kalibrasyon yalnızca EV filtresinden geçen seçilmiş bahisler içindir. "
          "Genel model kalibrasyonunu ölçmek için seçilmemiş maçların tahmin olasılıkları da gerekir. "
          "Sentetik oranlar bağımsız sharp piyasa verisi değildir.")


if __name__ == "__main__":
    main()
