"""Vercel serverless endpoint for Telegram webhook updates.

Configure TELEGRAM_BOT_TOKEN and WEBHOOK_URL in the Vercel project settings.
ZKAHIN_CACHE_PATH defaults to /tmp/zkahin_bot_model.pkl on Vercel.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Set this before importing telegram_bot so its default cache path is /tmp.
os.environ.setdefault("ZKAHIN_CACHE_PATH", "/tmp/zkahin_bot_model.pkl")

from telegram import Bot, Update
from src.telegram_bot import build_application, load_or_train_predictor

LOGGER = logging.getLogger("zkahin.vercel")
_PREDICTOR: Any = None
_PREDICTOR_LOCK = threading.Lock()


async def _register_webhook() -> bool:
    """Register the deployed Vercel endpoint with Telegram."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    webhook_url = os.environ.get("WEBHOOK_URL", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is not configured")
    if not webhook_url.startswith("https://"):
        raise RuntimeError("WEBHOOK_URL must be the complete https://.../api/webhook URL")
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET") or None
    async with Bot(token=token) as bot:
        return await bot.set_webhook(
            url=webhook_url,
            secret_token=secret,
            allowed_updates=["message"],
        )


def get_predictor() -> Any:
    """Load once per warm serverless instance; persist cache only in /tmp."""
    global _PREDICTOR
    if _PREDICTOR is not None:
        return _PREDICTOR
    with _PREDICTOR_LOCK:
        if _PREDICTOR is None:
            cache_path = Path(os.environ.get(
                "ZKAHIN_CACHE_PATH", "/tmp/zkahin_bot_model.pkl"
            ))
            _PREDICTOR = load_or_train_predictor(cache_path=cache_path)
    return _PREDICTOR


async def _process_telegram_update(payload: dict[str, Any]) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is not configured")

    application = build_application(token)
    started = False
    try:
        await application.initialize()
        application.bot_data["predictor"] = await asyncio.to_thread(get_predictor)
        await application.start()
        started = True
        update = Update.de_json(payload, application.bot)
        if update is not None:
            await application.process_update(update)
    finally:
        if started:
            await application.stop()
        await application.shutdown()


class handler(BaseHTTPRequestHandler):
    """Vercel Python runtime handler."""

    def _respond(self, status: int, body: dict[str, str]) -> None:
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        # Visiting the endpoint once after deployment registers Telegram's webhook.
        try:
            registered = asyncio.run(_register_webhook())
        except Exception:
            LOGGER.exception("Telegram webhook registration failed")
            self._respond(500, {"error": "webhook registration failed"})
            return
        self._respond(
            200,
            {
                "status": "ok",
                "service": "z-kahin-telegram-webhook",
                "webhook_registered": str(bool(registered)).lower(),
            },
        )

    def do_POST(self) -> None:
        expected_secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
        if expected_secret:
            supplied_secret = self.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
            if not supplied_secret or supplied_secret != expected_secret:
                self._respond(403, {"error": "forbidden"})
                return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 1_000_000:
                self._respond(400, {"error": "invalid request body size"})
                return
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                self._respond(400, {"error": "expected a JSON object"})
                return
            asyncio.run(_process_telegram_update(payload))
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            self._respond(400, {"error": "invalid JSON"})
            return
        except Exception:
            LOGGER.exception("Telegram webhook update processing failed")
            self._respond(500, {"error": "update processing failed"})
            return

        self._respond(200, {"ok": "true"})

    def log_message(self, format: str, *args: Any) -> None:
        LOGGER.info("%s - %s", self.address_string(), format % args)
