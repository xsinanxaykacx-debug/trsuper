from pathlib import Path
import pandas as pd

root = Path.cwd()
paths = [
    root / "DATA.csv",
    root / "data" / "csv" / "DATA.csv",
    root / "archive_v16" / "v16_per_match_predictions.csv",
]

for path in paths:
    try:
        exists = path.exists()
    except Exception as exc:
        print(f"OKUMA HATASI: {path} — {type(exc).__name__}")
        continue

    if not exists:
        print(f"YOK: {path}")
        continue

    print(f"VAR: {path}")
    try:
        df_auto = pd.read_csv(
            path, sep=None, engine="python", encoding="utf-8-sig", nrows=0
        )
        df_def = pd.read_csv(path, encoding="utf-8-sig", nrows=0)
        print(
            f"sep=None: {len(df_auto.columns)} sutun | "
            f"sep=',': {len(df_def.columns)} sutun"
        )
        print(
            "ID benzeri sutunlar:",
            [repr(c) for c in df_def.columns if "ID" in c.upper()],
        )
        print(f"Dosya boyutu: {path.stat().st_size}")
    except Exception as exc:
        print(f"OKUMA HATASI: {path} — {type(exc).__name__}")

print("BITTI - salt okunur")
