"""Train all Z-Kahin classifiers and export the deployment artifact.

Run from the repository root:
    python -m src.export_model

The artifact format intentionally matches src.telegram_bot.load_or_train_predictor.
The historical source data must exist at data/csv/180k.pkl or data/csv/180k.xlsx.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import joblib

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.telegram_bot import CACHE_VERSION, ZKahinPredictor
from src.load_global import PICKLE_PATH, XLSX_PATH

OUTPUT_PATH = ROOT / "models" / "zkahin_bot_model.pkl"


def main() -> int:
    logging.basicConfig(
        level="INFO",
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if not PICKLE_PATH.is_file() and not XLSX_PATH.is_file():
        print(
            "HATA: 180k veri kaynağı bulunamadı. "
            f"Beklenen dosyalardan biri: {PICKLE_PATH} veya {XLSX_PATH}",
            file=sys.stderr,
        )
        return 2

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = OUTPUT_PATH.with_suffix(OUTPUT_PATH.suffix + ".tmp")

    predictor = ZKahinPredictor()
    predictor.load_and_train()

    if not (
        predictor.model_1x2 is not None
        and predictor.model_1x2_odds is not None
        and predictor.model_ou25 is not None
    ):
        raise RuntimeError("Üç modelin tamamı eğitilmedi; dışa aktarma durduruldu.")

    payload = {
        "cache_version": CACHE_VERSION,
        "predictor": predictor,
    }
    joblib.dump(payload, temporary_path, compress=3)
    temporary_path.replace(OUTPUT_PATH)

    size_bytes = OUTPUT_PATH.stat().st_size
    print(f"Model dosyası: {OUTPUT_PATH}")
    print(f"Dosya boyutu: {size_bytes:,} bayt ({size_bytes / (1024 * 1024):.2f} MiB)")
    print("Eğitilen modeller: 1X2 (oransız), 1X2 (oranlı), Alt/Üst 2.5")
    if size_bytes >= 100 * 1024 * 1024:
        print("UYARI: Dosya 100 MiB sınırını aşıyor; repoya commit etmeyin.")
    else:
        print("Boyut kontrolü: 100 MiB altında; GitHub Release asset'i olarak kullanılabilir.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
