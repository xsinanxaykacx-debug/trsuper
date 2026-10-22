"""Process pending Telegram updates once, then exit.

The script intentionally makes one getUpdates request rather than running a
continuous polling loop. The workflow persists last_update.txt back to GitHub.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from telegram import Update
from src.telegram_bot import build_application, load_or_train_predictor

LOGGER = logging.getLogger("z_kahin.cron")
OFFSET_FILE = ROOT / "last_update.txt"


def read_last_update_id() -> int:
    """Return the last successfully processed update ID, or -1 on first run."""
    try:
        value = OFFSET_FILE.read_text(encoding="utf-8").strip()
        return int(value) if value else -1
    except FileNotFoundError:
        return -1


def write_last_update_id(update_id: int) -> None:
    """Atomically persist the last processed Telegram update ID."""
    OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = OFFSET_FILE.with_suffix(".txt.tmp")
    temporary.write_text(f"{update_id}\n", encoding="utf-8")
    temporary.replace(OFFSET_FILE)


async def run_once() -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN secret/environment variable is missing")

    last_update_id = read_last_update_id()
    # A new installation has no offset: let Telegram return all pending updates.
    offset = last_update_id + 1 if last_update_id >= 0 else None

    application = build_application(token)
    initialized = False
    started = False
    processed_last_id = last_update_id

    try:
        await application.initialize()
        initialized = True

        # The bot's post_init callback is normally invoked by run_polling; this
        # one-shot runner loads the pre-trained model explicitly instead.
        application.bot_data["predictor"] = await asyncio.to_thread(
            load_or_train_predictor
        )

        await application.start()
        started = True

        updates = await application.bot.get_updates(
            offset=offset,
            timeout=0,
            allowed_updates=["message"],
        )
        updates = sorted(updates, key=lambda item: item.update_id)
        LOGGER.info("Telegram bekleyen güncelleme sayısı: %d", len(updates))

        for update in updates:
            # Advance only after PTB has successfully dispatched the update.
            await application.process_update(update)
            processed_last_id = max(processed_last_id, update.update_id)
            LOGGER.info("İşlendi: update_id=%s", update.update_id)

        if processed_last_id > last_update_id:
            write_last_update_id(processed_last_id)
            LOGGER.info("Offset kaydedildi: %s", processed_last_id)
        else:
            LOGGER.info("Yeni güncelleme yok; offset değişmedi.")

        return len(updates)
    finally:
        if started:
            await application.stop()
        if initialized:
            await application.shutdown()


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        count = asyncio.run(run_once())
    except Exception:
        LOGGER.exception("Tek seferlik Telegram çalışması başarısız.")
        return 1
    LOGGER.info("Tamamlandı; işlenen güncelleme sayısı: %d", count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
