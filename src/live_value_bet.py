"""Z-Kâhin live value-bet scanner for Pinnacle OU 2.5 odds.

Input CSV columns:
  match, pinnacle_under25, pinnacle_over25, plus every model feature column.
Optional display columns: home_team, away_team, kickoff, league.

Model artifact (joblib) should be a dictionary:
  {"model": fitted_stacking_classifier, "feature_columns": [ordered feature names]}
The fitted model must output binary probabilities where class 1 means OVER 2.5
and class 0 means UNDER 2.5. Do not use a model artifact trained on different
features or a different target.

This script intentionally reads a CSV odds feed rather than scraping Pinnacle's
website. Refresh the CSV from a permitted/API data source before each run.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / "models" / "stacked_ou25.joblib"
DEFAULT_INPUT = ROOT / "data" / "csv" / "pinnacle_live.csv"
DEFAULT_OUTPUT = ROOT / "data" / "csv" / "live_value_bets.csv"
EV_THRESHOLD = 0.05
EPS = 1e-9

ODDS_UNDER = "pinnacle_under25"
ODDS_OVER = "pinnacle_over25"
OPTIONAL_COLUMNS = ["match", "home_team", "away_team", "kickoff", "league"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Z-Kâhin Stacking ile Pinnacle OU 2.5 value bet taraması."
    )
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL,
                        help="Eğitilmiş stacking modelinin joblib dosyası.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                        help="Pinnacle oranları ve model özelliklerini içeren CSV.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="Tüm geçerli tahminlerin ve fırsatların yazılacağı CSV.")
    parser.add_argument("--ev-threshold", type=float, default=EV_THRESHOLD,
                        help="Minimum beklenen getiri eşiği; 0.05 = %5.")
    return parser.parse_args()


def valid_odds(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return numeric.notna() & np.isfinite(numeric) & numeric.gt(1.0)


def load_model_bundle(path: Path) -> tuple[Any, list[str]]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Model artefaktı bulunamadı: {path}\n"
            "Stacking modelini ve eğitimde kullanılan özellik sırasını "
            "{'model': model, 'feature_columns': [...]} biçiminde joblib olarak kaydet."
        )

    artifact = joblib.load(path)
    if isinstance(artifact, dict) and "model" in artifact:
        model = artifact["model"]
        feature_columns = artifact.get("feature_columns")
    else:
        model = artifact
        feature_columns = getattr(model, "feature_names_in_", None)

    if not feature_columns:
        raise ValueError(
            "Model özellik listesi bulunamadı. Artefaktı "
            "{'model': fitted_model, 'feature_columns': ordered_names} "
            "biçiminde kaydet; özellikleri tahmin sırasında tahmin etme."
        )

    feature_columns = [str(column) for column in feature_columns]
    if len(feature_columns) != len(set(feature_columns)):
        raise ValueError("Model özellik listesinde yinelenen sütun var.")
    if not hasattr(model, "predict_proba"):
        raise TypeError("Yüklenen model predict_proba() desteklemiyor.")
    return model, feature_columns


def match_label(row: pd.Series) -> str:
    if pd.notna(row.get("match")) and str(row.get("match")).strip():
        return str(row["match"]).strip()
    home = str(row.get("home_team", "")).strip()
    away = str(row.get("away_team", "")).strip()
    if home and away and home.lower() != "nan" and away.lower() != "nan":
        return f"{home} - {away}"
    return "Maç adı CSV'de yok"


def predict_over_probability(model: Any, features: pd.DataFrame) -> np.ndarray:
    probabilities = np.asarray(model.predict_proba(features), dtype=float)
    classes = getattr(model, "classes_", None)

    if probabilities.ndim != 2 or probabilities.shape[0] != len(features):
        raise ValueError("Model predict_proba çıktısının boyutu beklenenden farklı.")
    if probabilities.shape[1] != 2:
        raise ValueError(
            f"OU 2.5 için ikili model bekleniyor; model {probabilities.shape[1]} "
            "olasılık sütunu döndürdü."
        )

    if classes is not None:
        class_list = list(classes)
        over_index = next(
            (i for i, label in enumerate(class_list)
             if str(label).strip().upper() in {"1", "1.0", "OVER", "UST", "ÜST", "O"}),
            None,
        )
        if over_index is None:
            raise ValueError(
                f"Pozitif sınıf (1/OVER/ÜST) model.classes_ içinde bulunamadı: {class_list}"
            )
    else:
        # For a standard binary sklearn classifier, predict_proba[:, 1] is class 1.
        over_index = 1

    p_over = probabilities[:, over_index]
    if not np.isfinite(p_over).all() or ((p_over < 0) | (p_over > 1)).any():
        raise ValueError("Model geçersiz olasılık üretti.")
    return np.clip(p_over, EPS, 1.0 - EPS)


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.ev_threshold < 0:
        raise ValueError("--ev-threshold negatif olamaz.")
    if not args.input.is_file():
        raise FileNotFoundError(
            f"Oran CSV'si bulunamadı: {args.input}\n"
            "CSV'yi Pinnacle oranları ve model özellikleriyle oluşturup tekrar çalıştır."
        )

    logging.info("Stacking modeli yükleniyor: %s", args.model)
    model, feature_columns = load_model_bundle(args.model)

    frame = pd.read_csv(args.input)
    required = {ODDS_UNDER, ODDS_OVER, *feature_columns}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Girdi CSV'sinde eksik sütunlar var: {missing}")
    if frame.empty:
        logging.warning("Girdi CSV'si boş; taranacak maç yok.")
        return 0

    odds_under = pd.to_numeric(frame[ODDS_UNDER], errors="coerce")
    odds_over = pd.to_numeric(frame[ODDS_OVER], errors="coerce")
    valid = valid_odds(odds_under) & valid_odds(odds_over)
    skipped = int((~valid).sum())
    frame = frame.loc[valid].copy().reset_index(drop=True)
    if frame.empty:
        logging.warning("1.00'dan büyük iki taraflı geçerli oranı olan maç yok.")
        return 0
    odds_under = odds_under.loc[valid].to_numpy(dtype=float)
    odds_over = odds_over.loc[valid].to_numpy(dtype=float)

    features = (
        frame.loc[:, feature_columns]
        .replace([np.inf, -np.inf], np.nan)
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0.0)
        .astype(float)
    )

    logging.info("%s maç için tahmin yapılıyor; geçersiz oranlı atlanan: %s",
                 len(frame), skipped)
    p_over = predict_over_probability(model, features)
    p_under = 1.0 - p_over

    # Remove the two-way bookmaker margin by normalizing implied probabilities.
    implied_under = 1.0 / odds_under
    implied_over = 1.0 / odds_over
    overround = implied_under + implied_over
    fair_under = implied_under / overround
    fair_over = implied_over / overround

    # EV is calculated using the actual offered decimal odds, not fair odds.
    ev_under = p_under * odds_under - 1.0
    ev_over = p_over * odds_over - 1.0
    edge_under = p_under - fair_under
    edge_over = p_over - fair_over

    out = frame.copy()
    out["model_p_under25"] = p_under
    out["model_p_over25"] = p_over
    out["pinnacle_fair_p_under25"] = fair_under
    out["pinnacle_fair_p_over25"] = fair_over
    out["edge_under_pp"] = edge_under * 100.0
    out["edge_over_pp"] = edge_over * 100.0
    out["ev_under"] = ev_under
    out["ev_over"] = ev_over

    # Both conditions must hold: model probability exceeds no-vig fair probability
    # and expected return at the offered Pinnacle price exceeds the configured limit.
    take_under = (p_under > fair_under) & (ev_under > args.ev_threshold)
    take_over = (p_over > fair_over) & (ev_over > args.ev_threshold)

    opportunities: list[dict[str, Any]] = []
    for idx in range(len(out)):
        label = match_label(out.iloc[idx])
        for side, take, probability, fair_probability, odds, ev, edge in (
            ("ALT 2.5", take_under, p_under, fair_under, odds_under, ev_under, edge_under),
            ("ÜST 2.5", take_over, p_over, fair_over, odds_over, ev_over, edge_over),
        ):
            if bool(take[idx]):
                opportunities.append({
                    "match": label,
                    "market": side,
                    "pinnacle_odds": float(odds[idx]),
                    "model_probability": float(probability[idx]),
                    "pinnacle_fair_probability": float(fair_probability[idx]),
                    "edge_pp": float(edge[idx] * 100.0),
                    "ev": float(ev[idx]),
                    "kickoff": out.iloc[idx].get("kickoff", ""),
                    "league": out.iloc[idx].get("league", ""),
                })
                print(
                    f"VALUE BET FIRSATI: {label} - {side} - "
                    f"{odds[idx]:.3f} | Model: %{probability[idx] * 100:.2f} "
                    f"| Pinnacle adil: %{fair_probability[idx] * 100:.2f} "
                    f"| EV: %{ev[idx] * 100:.2f}"
                )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False, encoding="utf-8-sig")
    opportunities_path = args.output.with_name(
        f"{args.output.stem}_opportunities{args.output.suffix}"
    )
    pd.DataFrame(opportunities).to_csv(
        opportunities_path, index=False, encoding="utf-8-sig"
    )

    logging.info("Geçerli maç: %s | Fırsat: %s", len(out), len(opportunities))
    logging.info("Tüm tahminler: %s", args.output)
    logging.info("Fırsatlar: %s", opportunities_path)
    if not opportunities:
        print("Bu taramada koşulları karşılayan VALUE BET FIRSATI bulunamadı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
