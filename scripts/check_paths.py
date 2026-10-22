from pathlib import Path
import pandas as pd

root = Path.cwd()
paths = [
    root / "DATA.csv",
    root / "data" / "csv" / "DATA.csv",
    root / "archive_v16" / "v16_per_match_predictions.csv",
]

for path in paths:
    if path.exists():
        print(f"VAR: {path}")
        df_auto = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig", nrows=0)
        df_def = pd.read_csv(path, encoding="utf-8-sig", nrows=0)
        print(f"sep=None: {len(df_auto.columns)} sutun | sep=',': {len(df_def.columns)} sutun")
        print("ID sutunlari:", [repr(c) for c in df_def.columns if "ID" in c.upper() or "id" in c])
        print(f"Dosya boyutu: {path.stat().st_size}")
    else:
        print(f"YOK: {path}")

print("BITTI - salt okunur")
