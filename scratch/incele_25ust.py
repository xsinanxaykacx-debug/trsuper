from pathlib import Path
import pandas as pd
import re

p = Path('data/csv/DATA.csv')
if not p.exists():
    raise FileNotFoundError('Veri dosyasi bulunamadi: ' + str(p.resolve()))

df = pd.read_csv(p, sep=None, engine='python', encoding='utf-8-sig', nrows=5, dtype=str)
print('DOSYA:', p.resolve())
print('ORNEK SATIR SAYISI:', len(df))
print('SUTUN SAYISI:', len(df.columns))

pattern = re.compile(r'tarih|date|gun|weekday|skor|sonuc|tam.?zaman|ms|ft|2[,.]5|25|ust|over|oran|gol|goal|mac', re.I)
print('\n=== ILGILI SUTUNLAR VE ORNEKLER ===')
for col in df.columns:
    if pattern.search(str(col)):
        vals = df[col].dropna().astype(str).head(5).tolist()
        print(repr(col) + ': ' + repr(vals))

print('\n=== TUM SUTUN ADLARI ===')
for i, col in enumerate(df.columns, start=1):
    print(f'{i:03d}. {col}')
