import pandas as pd
import time

print("Excel okunuyor... (BU ISLEM 5-10 DAKIKA SURECEK, LUTFEN KAPATMAYIN)")
start_time = time.time()

df = pd.read_excel("data/csv/180k.xlsx")
print(f"Excel basariyla okundu! Toplam satir: {len(df)}")
print(f"Okuma suresi: {time.time() - start_time:.1f} saniye")

print("CSV'ye yaziliyor...")
df.to_csv("data/csv/180k.csv", index=False, encoding="utf-8-sig")

print(f"ISLEM BITTI! {len(df)} mac basariyla 180k.csv dosyasina yazildi.")