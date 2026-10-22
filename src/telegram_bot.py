"""Telegram bot for Z-Kahin football match analysis.

Run from the repository root:
    set TELEGRAM_BOT_TOKEN=your_bot_token
    python -m src.telegram_bot

The OU 2.5 model follows the repository's Model C feature protocol. The bot
keeps two 1X2 classifiers: an odds-free model for /tahmin and an odds-aware
model for /value that receives the three supplied 1X2 odds. The odds-aware
model is trained only on historical matches with all three valid odds. Neither
model output is a betting recommendation.
"""
from __future__ import annotations

import asyncio
import logging
import os
from threading import Thread

from flask import Flask
import joblib
import re
import unicodedata
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.preprocessing import LabelEncoder

from src.ablation_study import (
    MIN_TRAIN_ROWS,
    MOMENTUM_FEATURES,
    REST_FEATURES,
    TRAIN_SEASONS,
    add_momentum,
    make_model,
)
from src.features import calculate_elo_features
from src.load_global import load_global_data

LOGGER = logging.getLogger("z_kahin.telegram_bot")

BASE_FEATURES = [
    "elo_h", "elo_a", "elo_diff",
    "form_h_pts_5", "form_h_gf_5", "form_h_ga_5",
    "form_a_pts_5", "form_a_gf_5", "form_a_ga_5",
    "form_h_pts_10", "form_h_gf_10", "form_h_ga_10",
    "form_a_pts_10", "form_a_gf_10", "form_a_ga_10",
    "form_h_home_pts", "form_h_home_gf", "form_h_home_ga",
    "form_a_away_pts", "form_a_away_gf", "form_a_away_ga",
]
MODEL_FEATURES = BASE_FEATURES + REST_FEATURES + MOMENTUM_FEATURES
ODDS_FEATURES = MODEL_FEATURES + ["_odd_H", "_odd_D", "_odd_A"]
DISCLAIMER = (
    "Bu tahminler yapay zeka tarafından üretilmiştir, "
    "kesinlikle yatırım/bahis tavsiyesi değildir."
)
TRAIN_SEASONS_REQUIRED = set(TRAIN_SEASONS)
CURRENT_LEAGUE_KEY = "Dunya"
CACHE_PATH = Path(os.environ.get("ZKAHIN_CACHE_PATH", str(Path(__file__).resolve().parents[1] / "models" / "zkahin_bot_model.pkl"))).expanduser()
CACHE_VERSION = 2
VALUE_THRESHOLD = 0.05


def normalize_team_name(value: str) -> str:
    """Case-insensitive, accent-insensitive lookup key for Turkish team names."""
    normalized = unicodedata.normalize("NFKD", str(value).strip().casefold())
    plain = "".join(char for char in normalized if not unicodedata.combining(char))
    return plain.replace("ı", "i")


def parse_match_input(text: str) -> tuple[str, str]:
    """Parse '/tahmin Home Team vs Away Team' input."""
    command_and_args = text.strip().split(maxsplit=1)
    if len(command_and_args) != 2:
        raise ValueError("Kullanım: /tahmin Ev Sahibi vs Deplasman")
    match = re.split(r"\s+vs\.?\s+", command_and_args[1], maxsplit=1, flags=re.IGNORECASE)
    if len(match) != 2 or not match[0].strip() or not match[1].strip():
        raise ValueError("Kullanım: /tahmin Ev Sahibi vs Deplasman")
    home, away = match[0].strip(), match[1].strip()
    if normalize_team_name(home) == normalize_team_name(away):
        raise ValueError("Ev sahibi ve deplasman takımları farklı olmalı.")
    return home, away


def parse_odds(raw_values: list[str]) -> list[float]:
    """Parse decimal odds, accepting dot or comma decimal separators."""
    odds: list[float] = []
    for raw in raw_values:
        try:
            value = float(raw.strip().replace(",", "."))
        except (TypeError, ValueError) as exc:
            raise ValueError("Oranlar sayı olmalı. Örnek: 1.95 3.40 3.20") from exc
        if not np.isfinite(value) or value < 1.0:
            raise ValueError("Her oran 1.00 veya daha büyük olmalı.")
        odds.append(value)
    return odds


def parse_value_input(text: str, odds_count: int) -> tuple[str, str, list[float]]:
    """Split final N tokens as odds; team names may contain spaces."""
    parts = text.strip().split()
    usage = (
        "Kullanım: /value Ev Sahibi vs Deplasman 1.95 3.40 3.20"
        if odds_count == 3
        else "Kullanım: /value_ou Ev Sahibi vs Deplasman 1.80 2.00"
    )
    if len(parts) < odds_count + 3:
        raise ValueError(usage)
    raw_odds = parts[-odds_count:]
    match_text = " ".join(parts[1:-odds_count])
    match = re.split(r"\s+vs\.?\s+", match_text, maxsplit=1, flags=re.IGNORECASE)
    if len(match) != 2 or not match[0].strip() or not match[1].strip():
        raise ValueError(usage)
    home, away = match[0].strip(), match[1].strip()
    if normalize_team_name(home) == normalize_team_name(away):
        raise ValueError("Ev sahibi ve deplasman takımları farklı olmalı.")
    return home, away, parse_odds(raw_odds)


def calculate_value_rows(
    probabilities: list[float], odds: list[float], labels: list[str]
) -> list[dict[str, float | str]]:
    """Compute EV and raw implied market probabilities (1 / decimal odds)."""
    if len(probabilities) != len(odds) or len(odds) != len(labels):
        raise ValueError("Olasılık, oran ve seçenek sayıları eşleşmiyor.")
    if any(not np.isfinite(p) or p < 0.0 or p > 1.0 for p in probabilities):
        raise ValueError("Model olasılıkları geçersiz.")
    return [
        {
            "label": label,
            "model_probability": float(probability),
            "market_probability": float(1.0 / odd),
            "odds": float(odd),
            "ev": float(probability * odd - 1.0),
        }
        for label, probability, odd in zip(labels, probabilities, odds)
    ]


def make_feature_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [name for name in MODEL_FEATURES if name not in frame.columns]
    if missing:
        raise KeyError(f"Model özellikleri eksik: {missing}")
    return (
        frame.loc[:, MODEL_FEATURES]
        .replace([np.inf, -np.inf], np.nan)
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0.0)
        .astype(np.float32)
    )


def make_odds_feature_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    """Build model-C-style pre-match features plus the three 1X2 odds."""
    missing = [name for name in ODDS_FEATURES if name not in frame.columns]
    if missing:
        raise KeyError(f"Oranlı 1X2 model özellikleri eksik: {missing}")
    values = frame.loc[:, ODDS_FEATURES].replace([np.inf, -np.inf], np.nan)
    values = values.apply(pd.to_numeric, errors="coerce")
    if values[["_odd_H", "_odd_D", "_odd_A"]].isna().any().any():
        raise ValueError("Oranlı 1X2 modeli için üç oran da sayısal olmalı.")
    if (values[["_odd_H", "_odd_D", "_odd_A"]] <= 1.0).any().any():
        raise ValueError("Oranlar 1.00'dan büyük olmalı.")
    return values.fillna(0.0).astype(np.float32)


def _league_key(value: Any) -> str:
    if pd.isna(value):
        return "__UNKNOWN_LEAGUE__"
    key = re.sub(r"\s*\d{4}/\d{4}\s*$", "", str(value).strip()).strip()
    return key or "__UNKNOWN_LEAGUE__"


class ZKahinPredictor:
    """Load historical matches once, fit both classifiers, and retain live team state."""

    def __init__(self) -> None:
        self.matches: pd.DataFrame | None = None
        self.data: pd.DataFrame | None = None
        self.model_1x2: xgb.XGBClassifier | None = None  # oran girişi olmayan /tahmin modeli
        self.model_1x2_odds: xgb.XGBClassifier | None = None  # oranlı /value modeli
        self.model_ou25: xgb.XGBClassifier | None = None
        self.label_encoder = LabelEncoder()
        self.label_encoder_odds = LabelEncoder()
        self.team_names: dict[str, list[str]] = {}
        self.elo: dict[tuple[str, str], float] = {}
        self.recent_all: dict[tuple[str, str], deque] = {}
        self.recent_home: dict[tuple[str, str], deque] = {}
        self.recent_away: dict[tuple[str, str], deque] = {}
        self.last_dt: dict[tuple[str, str], pd.Timestamp] = {}
        self.h2h: dict[tuple[tuple[str, str], tuple[str, str]], deque] = {}
        self.team_latest_league: dict[str, str] = {}

    def load_and_train(self) -> None:
        LOGGER.info("Tarihsel veri yükleniyor.")
        matches = load_global_data().copy()
        required = {
            "_id", "_date", "_season", "Lig/Sezon", "Ev_Sahibi", "Deplasman",
            "MSE", "MSD", "_y", "_y_ou25",
        }
        missing = sorted(required - set(matches.columns))
        if missing:
            raise KeyError(f"Veri setinde gerekli sütunlar eksik: {missing}")
        if matches["_id"].duplicated().any():
            raise ValueError("Veri setinde yinelenen _id var.")

        matches["_date"] = pd.to_datetime(matches["_date"], errors="coerce")
        matches["_season"] = matches["_season"].astype(str).str.strip()
        matches["_y_ou25"] = pd.to_numeric(matches["_y_ou25"], errors="coerce")
        matches = matches.dropna(
            subset=["_date", "_season", "_y", "_y_ou25", "Ev_Sahibi", "Deplasman"]
        ).copy()
        matches["_y"] = matches["_y"].astype(str).str.strip().str.upper()
        matches["_y_ou25"] = matches["_y_ou25"].astype(int)
        matches = matches[matches["_y"].isin(["H", "D", "A"])]
        if not matches["_y_ou25"].isin([0, 1]).all():
            raise ValueError("_y_ou25 yalnızca 0 (ALT) ve 1 (ÜST) olabilir.")

        absent = sorted(TRAIN_SEASONS_REQUIRED - set(matches["_season"].unique()))
        if absent:
            raise ValueError(f"Eğitim için gerekli sezonlar eksik: {absent}")

        LOGGER.info("Kronolojik maç öncesi özellikleri hesaplanıyor (%s maç).", len(matches))
        features = add_momentum(calculate_elo_features(matches))
        data = matches.merge(features, on="_id", how="inner", validate="one_to_one")
        data = data.sort_values(["_date", "_id"], kind="stable").reset_index(drop=True)

        train = data.loc[data["_season"].isin(TRAIN_SEASONS)].copy().reset_index(drop=True)
        if len(train) < MIN_TRAIN_ROWS:
            raise RuntimeError(f"Eğitim örneği yetersiz: {len(train)}")
        if train["_y_ou25"].nunique() != 2:
            raise RuntimeError("Eğitim verisinde ALT/ÜST hedefinin iki sınıfı da bulunmalı.")
        if not train["_y"].isin(["H", "D", "A"]).all():
            raise RuntimeError("Eğitim verisinde geçersiz 1X2 hedefi var.")

        X_train = make_feature_matrix(train)
        LOGGER.info("ALT/ÜST Model C eğitiliyor (%s maç).", len(train))
        model_ou25 = make_model()
        model_ou25.fit(X_train, train["_y_ou25"].astype(int).to_numpy())

        # Oransız model: /tahmin komutunda oran girdisi bulunmadığı için
        # yalnızca kronolojik maç öncesi özelliklerle eğitilir.
        self.label_encoder = LabelEncoder()
        y_1x2 = self.label_encoder.fit_transform(train["_y"].to_numpy())
        model_1x2 = xgb.XGBClassifier(
            objective="multi:softprob",
            num_class=3,
            eval_metric="mlogloss",
            n_estimators=350,
            max_depth=4,
            learning_rate=0.04,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=5,
            reg_lambda=1.0,
            random_state=42,
            n_jobs=-1,
        )
        LOGGER.info("Oransız 1X2 modeli eğitiliyor (%s maç).", len(train))
        model_1x2.fit(X_train, y_1x2)

        # Oranlı model: yalnızca maç başlamadan önce mevcut olan ve üç oranı da
        # geçerli (> 1.00) maçları kullanır. Sonuç etiketi aynı maçın oranlarından
        # türetilmez; oranlar sadece model girdisidir.
        odds_valid = (
            train[["_odd_H", "_odd_D", "_odd_A"]].apply(pd.to_numeric, errors="coerce").notna().all(axis=1)
            & train[["_odd_H", "_odd_D", "_odd_A"]].apply(pd.to_numeric, errors="coerce").gt(1.0).all(axis=1)
        )
        train_odds = train.loc[odds_valid].copy()
        if len(train_odds) < MIN_TRAIN_ROWS or not train_odds["_y"].isin(["H", "D", "A"]).all():
            raise RuntimeError(f"Oranlı 1X2 eğitimi için yeterli geçerli maç yok: {len(train_odds)}")
        X_train_odds = make_odds_feature_matrix(train_odds)
        self.label_encoder_odds = LabelEncoder()
        y_1x2_odds = self.label_encoder_odds.fit_transform(train_odds["_y"].to_numpy())
        model_1x2_odds = xgb.XGBClassifier(
            objective="multi:softprob",
            num_class=3,
            eval_metric="mlogloss",
            n_estimators=350,
            max_depth=4,
            learning_rate=0.04,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=5,
            reg_lambda=1.0,
            random_state=42,
            n_jobs=-1,
        )
        LOGGER.info("Oranlı 1X2 modeli eğitiliyor (%s geçerli oranlı maç).", len(train_odds))
        model_1x2_odds.fit(X_train_odds, y_1x2_odds)

        self.matches = matches
        self.data = data
        self.model_ou25 = model_ou25
        self.model_1x2 = model_1x2
        self.model_1x2_odds = model_1x2_odds
        self._build_live_state(matches)
        self._build_team_index(matches)
        self.matches = None
        self.data = None
        LOGGER.info("Z-Kahin hazır. Eğitim satırı: %s.", len(train))

    def _build_team_index(self, matches: pd.DataFrame) -> None:
        index: dict[str, set[str]] = defaultdict(set)
        for value in pd.concat(
            [matches["Ev_Sahibi"], matches["Deplasman"]], ignore_index=True
        ).dropna().astype(str).str.strip():
            if value:
                index[normalize_team_name(value)].add(value)
        self.team_names = {key: sorted(values) for key, values in index.items()}

    def resolve_team(self, query: str) -> str | None:
        choices = self.team_names.get(normalize_team_name(query), [])
        if len(choices) == 1:
            return choices[0]
        # Prefer an exact case-insensitive spelling if normalization collides.
        exact = [name for name in choices if name.casefold() == query.strip().casefold()]
        if len(exact) == 1:
            return exact[0]
        return None

    def _build_live_state(self, matches: pd.DataFrame) -> None:
        """Replay matches chronologically to retain current Elo/form/rest/H2H state."""
        elo: defaultdict = defaultdict(lambda: 1500.0)
        recent_all: defaultdict = defaultdict(lambda: deque(maxlen=10))
        recent_home: defaultdict = defaultdict(lambda: deque(maxlen=10))
        recent_away: defaultdict = defaultdict(lambda: deque(maxlen=10))
        last_dt: dict[tuple[str, str], pd.Timestamp] = {}
        h2h: defaultdict = defaultdict(lambda: deque(maxlen=10))

        ordered = matches.sort_values(["_date", "_id"], kind="stable")
        for day, group in ordered.groupby("_date", sort=True):
            records = group.to_dict("records")
            pre_match_elo: dict[Any, tuple[float, float]] = {}
            for row in records:
                league = _league_key(row.get("Lig/Sezon"))
                home = (league, str(row["Ev_Sahibi"]).strip())
                away = (league, str(row["Deplasman"]).strip())
                pre_match_elo[row["_id"]] = (elo[home], elo[away])

            deltas: defaultdict = defaultdict(float)
            for row in records:
                league = _league_key(row.get("Lig/Sezon"))
                home = (league, str(row["Ev_Sahibi"]).strip())
                away = (league, str(row["Deplasman"]).strip())
                home_goals = pd.to_numeric(row.get("MSE"), errors="coerce")
                away_goals = pd.to_numeric(row.get("MSD"), errors="coerce")
                result = str(row.get("_y", "")).upper()

                if pd.notna(home_goals) and pd.notna(away_goals):
                    hg, ag = int(home_goals), int(away_goals)
                    home_points = 3 if hg > ag else (1 if hg == ag else 0)
                    away_points = 3 if ag > hg else (1 if hg == ag else 0)
                    recent_all[home].append((home_points, hg, ag))
                    recent_all[away].append((away_points, ag, hg))
                    recent_home[home].append((home_points, hg, ag))
                    recent_away[away].append((away_points, ag, hg))

                home_elo, away_elo = pre_match_elo[row["_id"]]
                score_home = 1.0 if result == "H" else (0.5 if result == "D" else 0.0)
                expected_home = 1.0 / (1.0 + 10 ** ((away_elo - home_elo) / 400.0))
                delta = 20.0 * (score_home - expected_home)
                deltas[home] += delta
                deltas[away] -= delta
                last_dt[home] = day
                last_dt[away] = day

                pair = tuple(sorted((home, away)))
                winner = home if result == "H" else (away if result == "A" else None)
                h2h[pair].append(winner)

            for team, delta in deltas.items():
                elo[team] += delta

        self.elo = dict(elo)
        self.recent_all = dict(recent_all)
        self.recent_home = dict(recent_home)
        self.recent_away = dict(recent_away)
        self.last_dt = last_dt
        self.h2h = dict(h2h)
        latest_league: dict[str, str] = {}
        for row in ordered.to_dict("records"):
            league = _league_key(row.get("Lig/Sezon"))
            latest_league[str(row["Ev_Sahibi"]).strip()] = league
            latest_league[str(row["Deplasman"]).strip()] = league
        self.team_latest_league = latest_league

    @staticmethod
    def _mean_recent(queue: deque, count: int | None = None) -> tuple[float, float, float]:
        values = list(queue)
        if count is not None:
            values = values[-count:]
        if not values:
            return 0.0, 0.0, 0.0
        means = np.mean(values, axis=0)
        return float(means[0]), float(means[1]), float(means[2])

    def _make_live_row(self, home_name: str, away_name: str) -> pd.DataFrame:
        prediction_date = pd.Timestamp(datetime.now().date())
        home = (self.team_latest_league.get(home_name, CURRENT_LEAGUE_KEY), home_name)
        away = (self.team_latest_league.get(away_name, CURRENT_LEAGUE_KEY), away_name)

        elo_home = float(self.elo.get(home, 1500.0))
        elo_away = float(self.elo.get(away, 1500.0))
        home5 = self._mean_recent(self.recent_all.get(home, deque()), 5)
        home10 = self._mean_recent(self.recent_all.get(home, deque()))
        away5 = self._mean_recent(self.recent_all.get(away, deque()), 5)
        away10 = self._mean_recent(self.recent_all.get(away, deque()))
        home_home = self._mean_recent(self.recent_home.get(home, deque()))
        away_away = self._mean_recent(self.recent_away.get(away, deque()))

        rest_home = (
            float((prediction_date - self.last_dt[home]).days)
            if home in self.last_dt else np.nan
        )
        rest_away = (
            float((prediction_date - self.last_dt[away]).days)
            if away in self.last_dt else np.nan
        )
        pair = tuple(sorted((home, away)))
        h2h_history = self.h2h.get(pair, deque())
        h2h_share = (
            float(sum(1 for winner in h2h_history if winner == home) / len(h2h_history))
            if h2h_history else np.nan
        )

        row = {
            "elo_h": elo_home,
            "elo_a": elo_away,
            "elo_diff": elo_home - elo_away,
            "form_h_pts_5": home5[0], "form_h_gf_5": home5[1], "form_h_ga_5": home5[2],
            "form_a_pts_5": away5[0], "form_a_gf_5": away5[1], "form_a_ga_5": away5[2],
            "form_h_pts_10": home10[0], "form_h_gf_10": home10[1], "form_h_ga_10": home10[2],
            "form_a_pts_10": away10[0], "form_a_gf_10": away10[1], "form_a_ga_10": away10[2],
            "form_h_home_pts": home_home[0],
            "form_h_home_gf": home_home[1],
            "form_h_home_ga": home_home[2],
            "form_a_away_pts": away_away[0],
            "form_a_away_gf": away_away[1],
            "form_a_away_ga": away_away[2],
            "rest_h": rest_home,
            "rest_a": rest_away,
            "h2h_home_win_share": h2h_share,
        }
        row["momentum_h_pts"] = row["form_h_pts_5"] - row["form_h_pts_10"]
        row["momentum_h_gf"] = row["form_h_gf_5"] - row["form_h_gf_10"]
        row["momentum_h_ga"] = row["form_h_ga_5"] - row["form_h_ga_10"]
        row["momentum_a_pts"] = row["form_a_pts_5"] - row["form_a_pts_10"]
        row["momentum_a_gf"] = row["form_a_gf_5"] - row["form_a_gf_10"]
        row["momentum_a_ga"] = row["form_a_ga_5"] - row["form_a_ga_10"]
        return make_feature_matrix(pd.DataFrame([row]))

    def predict(
        self,
        home_query: str,
        away_query: str,
        odds_1x2: list[float] | None = None,
    ) -> dict[str, Any]:
        if self.model_1x2 is None or self.model_1x2_odds is None or self.model_ou25 is None:
            raise RuntimeError("Modeller henüz yüklenmedi.")
        home = self.resolve_team(home_query)
        away = self.resolve_team(away_query)
        if home is None or away is None:
            raise ValueError("UNKNOWN_TEAM")
        if home == away:
            raise ValueError("Ev sahibi ve deplasman takımları farklı olmalı.")

        features = self._make_live_row(home, away)
        if odds_1x2 is None:
            model = self.model_1x2
            encoder = self.label_encoder
            model_features = features
        else:
            if len(odds_1x2) != 3 or any(not np.isfinite(o) or o <= 1.0 for o in odds_1x2):
                raise ValueError("Oranlı 1X2 modeli için üç geçerli oran (> 1.00) gerekli.")
            model = self.model_1x2_odds
            encoder = self.label_encoder_odds
            model_features = make_odds_feature_matrix(
                pd.DataFrame([{
                    **features.iloc[0].to_dict(),
                    "_odd_H": odds_1x2[0],
                    "_odd_D": odds_1x2[1],
                    "_odd_A": odds_1x2[2],
                }])
            )
        raw_1x2 = model.predict_proba(model_features)[0]
        probabilities_by_label = {
            encoder.inverse_transform([int(class_id)])[0]: float(probability)
            for class_id, probability in zip(model.classes_, raw_1x2)
        }
        p_over = float(self.model_ou25.predict_proba(features)[0][1])
        p_over = float(np.clip(p_over, 0.0, 1.0))
        return {
            "home": home,
            "away": away,
            "p_home_win": probabilities_by_label.get("H", 0.0),
            "p_draw": probabilities_by_label.get("D", 0.0),
            "p_away_win": probabilities_by_label.get("A", 0.0),
            "p_under25": 1.0 - p_over,
            "p_over25": p_over,
        }


def _markdown_escape(value: str) -> str:
    escaped = str(value)
    for char in ("\\_*[]()~" + chr(96) + ">#+-=|{}.!"):
        escaped = escaped.replace(char, "\\" + char)
    return escaped


def format_prediction(result: dict[str, Any]) -> str:
    home = _markdown_escape(result["home"])
    away = _markdown_escape(result["away"])
    return (
        f"⚽ *Z-Kahin maç analizi*\n"
        f"*{home} - {away}*\n\n"
        f"📊 *1X2 olasılıkları*\n"
        f"1 (Ev sahibi): %{result['p_home_win'] * 100:.1f}\n"
        f"X (Beraberlik): %{result['p_draw'] * 100:.1f}\n"
        f"2 (Deplasman): %{result['p_away_win'] * 100:.1f}\n\n"
        f"🥅 *Alt/Üst 2.5 gol*\n"
        f"Alt 2.5: %{result['p_under25'] * 100:.1f}\n"
        f"Üst 2.5: %{result['p_over25'] * 100:.1f}\n\n"
        f"_{DISCLAIMER}_"
    )


async def start_command(update: Any, context: Any) -> None:
    message = update.effective_message
    if message is None:
        return
    await message.reply_text(
        "⚽ *Z-Kahin'e hoş geldin!*\n\n"
        "Geçmiş maç verileriyle 1X2 ve Alt/Üst 2.5 gol olasılıkları sunarım.\n\n"
        "`/tahmin Galatasaray vs Fenerbahçe`\n"
        "`/value Galatasaray vs Fenerbahçe 1.95 3.40 3.20`\n"
        "`/value_ou Galatasaray vs Fenerbahçe 1.80 2.00`\n\n"
        "Komutlar için /yardim yaz.",
        parse_mode="Markdown"
    )


async def help_command(update: Any, context: Any) -> None:
    message = update.effective_message
    if message is None:
        return
    await message.reply_text(
        "📚 *Kullanılabilir komutlar*\n\n"
        "/start — Botu başlatır.\n"
        "/tahmin Ev Sahibi vs Deplasman — 1X2 ve Alt/Üst 2.5 olasılıkları.\n"
        "/value Ev Sahibi vs Deplasman 1 X 2 — 1X2 oranlarıyla EV analizi.\n"
        "/value\\_ou Ev Sahibi vs Deplasman Alt Üst — Alt/Üst oranlarıyla EV analizi.\n"
        "/yardim — Komutları listeler.\n"
        "/hakkinda — Veri ve kullanım sınırları.\n\n"
        "*Örnekler*\n"
        "`/tahmin Galatasaray vs Fenerbahçe`\n"
        "`/value Galatasaray vs Fenerbahçe 1.95 3.40 3.20`\n"
        "`/value_ou Galatasaray vs Fenerbahçe 1.80 2.00`",
        parse_mode="Markdown"
    )


async def about_command(update: Any, context: Any) -> None:
    message = update.effective_message
    if message is None:
        return
    await message.reply_text(
        "ℹ️ *Z-Kahin hakkında*\n\n"
        "Yaklaşık 180.000 tarihsel maç içeren veri kaynağından yararlanan bir futbol analiz prototipidir. "
        "Olasılıklar garanti veya kârlılık iddiası taşımaz; yalnızca bilgilendirme amaçlıdır.\n\n"
        f"_{DISCLAIMER}_",
        parse_mode="Markdown"
    )


async def prediction_command(update: Any, context: Any) -> None:
    message = update.effective_message
    if message is None:
        return
    text = message.text or ""
    try:
        home_query, away_query = parse_match_input(text)
    except ValueError as exc:
        await message.reply_text(str(exc))
        return

    predictor: ZKahinPredictor | None = context.application.bot_data.get("predictor")
    if predictor is None:
        await message.reply_text("Model henüz hazır değil. Biraz sonra tekrar dene.")
        return

    try:
        result = await asyncio.to_thread(predictor.predict, home_query, away_query)
    except ValueError as exc:
        if str(exc) == "UNKNOWN_TEAM":
            await message.reply_text(
                "Takım bulunamadı, lütfen doğru yazdığınızdan emin olun."
            )
        else:
            await message.reply_text(str(exc))
    except Exception:
        LOGGER.exception("Tahmin oluşturulamadı.")
        await message.reply_text(
            "Tahmin hazırlanırken bir hata oluştu. Lütfen daha sonra tekrar dene."
        )
        return
    else:
        await message.reply_text(format_prediction(result), parse_mode="Markdown")


async def value_command(update: Any, context: Any) -> None:
    message = update.effective_message
    if message is None:
        return
    try:
        home_query, away_query, odds = parse_value_input(message.text or "", 3)
    except ValueError as exc:
        await message.reply_text(f"⚠️ {exc}")
        return

    predictor: ZKahinPredictor | None = context.application.bot_data.get("predictor")
    if predictor is None:
        await message.reply_text("Model henüz hazır değil. Biraz sonra tekrar dene.")
        return
    try:
        result = await asyncio.to_thread(predictor.predict, home_query, away_query, odds)
    except ValueError as exc:
        if str(exc) == "UNKNOWN_TEAM":
            await message.reply_text("Takım bulunamadı, lütfen doğru yazdığınızdan emin olun.")
        else:
            await message.reply_text(f"⚠️ {exc}")
        return
    except Exception:
        LOGGER.exception("1X2 value analizi oluşturulamadı.")
        await message.reply_text("Value analizi hazırlanırken hata oluştu. Daha sonra tekrar dene.")
        return

    rows = calculate_value_rows(
        [result["p_home_win"], result["p_draw"], result["p_away_win"]],
        odds,
        ["1 (Ev sahibi)", "X (Beraberlik)", "2 (Deplasman)"],
    )
    found = [row for row in rows if row["ev"] > VALUE_THRESHOLD]
    home = _markdown_escape(result["home"])
    away = _markdown_escape(result["away"])
    if found:
        lines = [f"💰 *VALUE BET BULUNDU!*\n*{home} - {away}*"]
        for row in found:
            lines.append(
                f"\n*{_markdown_escape(str(row['label']))}* — "
                f"Model: %{row['model_probability'] * 100:.1f}, "
                f"Piyasa: %{row['market_probability'] * 100:.1f}, "
                f"EV: {row['ev'] * 100:+.1f}% "
                f"(oran {row['odds']:.2f})"
            )
        lines.extend(["", f"_{DISCLAIMER}_"])
        await message.reply_text("\n".join(lines), parse_mode="Markdown")
    else:
        best = max(rows, key=lambda row: row["ev"])
        await message.reply_text(
            f"❌ *Bu oranlarda Value yok.*\n"
            f"En yüksek EV: {best['ev'] * 100:+.1f}% — {_markdown_escape(str(best['label']))}\n\n"
            f"_{DISCLAIMER}_",
            parse_mode="Markdown",
        )


async def value_ou_command(update: Any, context: Any) -> None:
    message = update.effective_message
    if message is None:
        return
    try:
        home_query, away_query, odds = parse_value_input(message.text or "", 2)
    except ValueError as exc:
        await message.reply_text(f"⚠️ {exc}")
        return

    predictor: ZKahinPredictor | None = context.application.bot_data.get("predictor")
    if predictor is None:
        await message.reply_text("Model henüz hazır değil. Biraz sonra tekrar dene.")
        return
    try:
        result = await asyncio.to_thread(predictor.predict, home_query, away_query)
    except ValueError as exc:
        if str(exc) == "UNKNOWN_TEAM":
            await message.reply_text("Takım bulunamadı, lütfen doğru yazdığınızdan emin olun.")
        else:
            await message.reply_text(f"⚠️ {exc}")
        return
    except Exception:
        LOGGER.exception("Alt/Üst value analizi oluşturulamadı.")
        await message.reply_text("Alt/Üst analizi hazırlanırken hata oluştu. Daha sonra tekrar dene.")
        return

    rows = calculate_value_rows(
        [result["p_under25"], result["p_over25"]],
        odds,
        ["Alt 2.5", "Üst 2.5"],
    )
    found = [row for row in rows if row["ev"] > VALUE_THRESHOLD]
    home = _markdown_escape(result["home"])
    away = _markdown_escape(result["away"])
    if found:
        lines = [f"💰 *ALT/ÜST VALUE BET BULUNDU!*\n*{home} - {away}*"]
        for row in found:
            lines.append(
                f"\n*{_markdown_escape(str(row['label']))}* — "
                f"Model: %{row['model_probability'] * 100:.1f}, "
                f"Piyasa: %{row['market_probability'] * 100:.1f}, "
                f"EV: {row['ev'] * 100:+.1f}% "
                f"(oran {row['odds']:.2f})"
            )
        lines.extend(["", f"_{DISCLAIMER}_"])
        await message.reply_text("\n".join(lines), parse_mode="Markdown")
    else:
        best = max(rows, key=lambda row: row["ev"])
        await message.reply_text(
            f"❌ *Bu oranlarda Value yok.*\n"
            f"En yüksek EV: {best['ev'] * 100:+.1f}% — {_markdown_escape(str(best['label']))}\n\n"
            f"_{DISCLAIMER}_",
            parse_mode="Markdown",
        )


def load_or_train_predictor(cache_path: Path = CACHE_PATH) -> ZKahinPredictor:
    """Load a pre-trained artifact; never train during a bot/serverless startup."""
    repo_model_path = Path(__file__).resolve().parents[1] / "models" / "zkahin_bot_model.pkl"
    release_url = os.environ.get(
        "ZKAHIN_MODEL_URL",
        "https://github.com/xsinanxaykacx-debug/trsuper/releases/latest/download/zkahin_bot_model.pkl",
    ).strip()
    candidates = [cache_path, repo_model_path]
    seen: set[str] = set()

    def load_artifact(path: Path) -> ZKahinPredictor | None:
        try:
            payload = joblib.load(path)
            if (
                isinstance(payload, dict)
                and payload.get("cache_version") == CACHE_VERSION
                and isinstance(payload.get("predictor"), ZKahinPredictor)
                and payload["predictor"].model_1x2 is not None
                and payload["predictor"].model_1x2_odds is not None
                and payload["predictor"].model_ou25 is not None
            ):
                LOGGER.info("Önceden eğitilmiş model yüklendi: %s", path)
                return payload["predictor"]
            LOGGER.warning("Model dosyası beklenen biçimde değil: %s", path)
        except Exception:
            LOGGER.exception("Model dosyası okunamadı: %s", path)
        return None

    for path in candidates:
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        if path.is_file():
            predictor = load_artifact(path)
            if predictor is not None:
                if path.resolve() != cache_path.resolve():
                    try:
                        import shutil

                        cache_path.parent.mkdir(parents=True, exist_ok=True)
                        temporary_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
                        shutil.copy2(path, temporary_path)
                        temporary_path.replace(cache_path)
                    except OSError:
                        LOGGER.warning("Model /tmp önbelleğine kopyalanamadı.", exc_info=True)
                return predictor

    if release_url:
        temporary_path = cache_path.with_suffix(cache_path.suffix + ".download")
        try:
            from urllib.request import Request, urlopen

            cache_path.parent.mkdir(parents=True, exist_ok=True)
            request = Request(release_url, headers={"User-Agent": "z-kahin-model-loader/1.0"})
            with urlopen(request, timeout=8) as response, temporary_path.open("wb") as output:
                output.write(response.read())
            predictor = load_artifact(temporary_path)
            if predictor is not None:
                temporary_path.replace(cache_path)
                LOGGER.info("Model GitHub Releases üzerinden indirildi.")
                return predictor
            temporary_path.unlink(missing_ok=True)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            LOGGER.warning("GitHub Releases model indirmesi başarısız: %s", release_url, exc_info=True)

    raise FileNotFoundError(
        "Model dosyası bulunamadı, lütfen export_model.py çalıştırın ve dosyayı repoya ekleyin."
    )

async def post_init(application: Any) -> None:
    """Load the cached predictor or train once without blocking the event loop."""
    try:
        predictor = await asyncio.to_thread(load_or_train_predictor)
    except Exception:
        LOGGER.exception("Z-Kahin modelleri yüklenemedi.")
        raise
    application.bot_data["predictor"] = predictor


def build_application(token: str) -> Any:
    """Build the Telegram application with all bot handlers."""
    from telegram.ext import Application, CommandHandler

    application = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("tahmin", prediction_command))
    application.add_handler(CommandHandler("value", value_command))
    application.add_handler(CommandHandler("value_ou", value_ou_command))
    application.add_handler(CommandHandler("yardim", help_command))
    application.add_handler(CommandHandler("hakkinda", about_command))
    return application


def create_health_app() -> Any:
    """Create the minimal HTTP app used by Hugging Face Spaces health checks."""
    from flask import Flask

    app = Flask("z_kahin_health")

    @app.get("/")
    @app.get("/health")
    def health_check() -> tuple[str, int, dict[str, str]]:
        return "OK", 200, {"Content-Type": "text/plain; charset=utf-8"}

    return app


def _run_telegram_polling(application: Any) -> None:
    """Run Telegram polling in a background thread without installing signal handlers."""
    try:
        application.run_polling(
            allowed_updates=["message"],
            stop_signals=None,
        )
    except Exception:
        LOGGER.exception("Telegram polling thread'i beklenmeyen şekilde sonlandı.")


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN ortam değişkeni tanımlı değil. "
            "BotFather token'ını bu değişkene kaydet."
        )

    try:
        from telegram.ext import Application
    except ImportError as exc:
        raise SystemExit(
            "python-telegram-bot kurulu değil. "
            "Kurulum: python -m pip install -r requirements.txt"
        ) from exc

    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    application = build_application(token)
    polling_thread = Thread(
        target=_run_telegram_polling,
        args=(application,),
        name="telegram-polling",
        daemon=True,
    )
    polling_thread.start()

    host = os.environ.get("HTTP_HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "7860"))
    health_app = create_health_app()
    LOGGER.info(
        "HTTP sağlık sunucusu başlatılıyor: http://%s:%s (/, /health)",
        host,
        port,
    )
    try:
        health_app.run(
            host=host,
            port=port,
            threaded=True,
            use_reloader=False,
        )
    except KeyboardInterrupt:
        LOGGER.info("HTTP sağlık sunucusu kapatılıyor.")


if __name__ == "__main__":
    main()
