import pandas as pd
import numpy as np
from pathlib import Path

def load_global_data() -> pd.DataFrame:
    # Dosyayı hem data/csv içinde hem de ana dizinde ara
    paths_to_try = [
        Path("data/csv/180k.csv"),
        Path("180k.csv"),
        Path("data/csv/180k.xlsx"),
        Path("180k.xlsx")
    ]
    
    filepath = None
    for p in paths_to_try:
        if p.exists():
            filepath = p
            break
            
    if filepath is None:
        raise FileNotFoundError("180k dosyasi bulunamadi! Lutfen dosyayi projenin icine (data/csv/ veya ana dizin) koyun.")
        
    print(f"Devasa veri seti okunuyor: {filepath}")
    
    if filepath.suffix == '.csv':
        df = pd.read_csv(filepath, encoding="utf-8-sig", low_memory=False)
    else:
        df = pd.read_excel(filepath)
    
    # 1. İsim Eşleştirmeleri
    df = df.rename(columns={
        "TARİH": "Tarih",
        "EV": "Ev_Sahibi",
        "DEP": "Deplasman",
        "MS1": "_odd_H",
        "MSX": "_odd_D",
        "MS2": "_odd_A"
    })
    
    # 2. Tarih Formatı (Gün.Ay.Yıl)
    df["_date"] = pd.to_datetime(df["Tarih"], dayfirst=True, errors="coerce")
    
    # 3. Sezon Hesaplama (Ağustos-Temmuz mantığı)
    df["_season"] = df["_date"].apply(lambda d: f"{d.year}/{d.year+1}" if d.month >= 7 else f"{d.year-1}/{d.year}" if pd.notna(d) else None)
    df["Lig/Sezon"] = "Dunya " + df["_season"].astype(str)
    
    # 4. Skorlar ve Hedef (y)
    df["MSE"] = pd.to_numeric(df["MSE"], errors="coerce")
    df["MSD"] = pd.to_numeric(df["MSD"], errors="coerce")
    
    conditions = [(df["MSE"] > df["MSD"]), (df["MSE"] == df["MSD"]), (df["MSE"] < df["MSD"])]
    df["_y"] = np.select(conditions, ["H", "D", "A"], default=None)
    
    # 5. Oranları Temizle (Virgül -> Nokta)
    def clean_odds(s):
        return pd.to_numeric(s.astype(str).str.replace(",", ".", regex=False).str.strip(), errors="coerce")
    
    df["_odd_H"] = clean_odds(df["_odd_H"])
    df["_odd_D"] = clean_odds(df["_odd_D"])
    df["_odd_A"] = clean_odds(df["_odd_A"])
    
    # 6. Benzersiz ID Üretimi (Çakışmaması için 20 Milyon'dan başlasın)
    df["_id"] = np.arange(20000000, 20000000 + len(df))
    
    # Temizlik: Hedefi veya oranı olmayan maçları at
    df = df.dropna(subset=["_date", "_season", "_y", "_odd_H", "_odd_D", "_odd_A"])
    
    print(f"Basarili: {len(df)} mac yuklendi.")
    if len(df) > 0:
        print(f"Sezon araligi: {df['_season'].min()} - {df['_season'].max()}")
    
    cols = ["_id", "_date", "_season", "Lig/Sezon", "Ev_Sahibi", "Deplasman", "MSE", "MSD", "_y", "_odd_H", "_odd_D", "_odd_A"]
    return df[cols].reset_index(drop=True)