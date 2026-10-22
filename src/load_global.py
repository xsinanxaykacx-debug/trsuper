import pandas as pd
import numpy as np
from pathlib import Path
import pickle
import os

def load_global_data() -> pd.DataFrame:
    xlsx_path = Path("data/csv/180k.xlsx")
    pkl_path = Path("data/csv/180k.pkl")
    
    # Eğer daha önce hızlı formata (pkl) çevirdiysek direkt onu oku (0.1 saniye)
    if pkl_path.exists():
        print("Hizli formattan (pkl) okunuyor...")
        with open(pkl_path, "rb") as f:
            return pickle.load(f)
            
    if not xlsx_path.exists():
        raise FileNotFoundError("180k.xlsx bulunamadi!")
        
    print("Excel okunuyor (Sadece bu seferlik, lutfen bekleyin)...")
    df = pd.read_excel(xlsx_path)
    
    # 1. İsim Eşleştirmeleri
    df = df.rename(columns={
        "TARİH": "Tarih",
        "EV": "Ev_Sahibi",
        "DEP": "Deplasman",
        "MS1": "_odd_H",
        "MSX": "_odd_D",
        "MS2": "_odd_A"
    })
    
    # 2. Tarih Formatı
    df["_date"] = pd.to_datetime(df["Tarih"], dayfirst=True, errors="coerce")
    
    # 3. Sezon Hesaplama
    df["_season"] = df["_date"].apply(lambda d: f"{d.year}/{d.year+1}" if d.month >= 7 else f"{d.year-1}/{d.year}" if pd.notna(d) else None)
    df["Lig/Sezon"] = "Dunya " + df["_season"].astype(str)
    
    # 4. Skorlar ve Hedef (y)
    df["MSE"] = pd.to_numeric(df["MSE"], errors="coerce")
    df["MSD"] = pd.to_numeric(df["MSD"], errors="coerce")
    
    conditions = [(df["MSE"] > df["MSD"]), (df["MSE"] == df["MSD"]), (df["MSE"] < df["MSD"])]
    df["_y"] = np.select(conditions, ["H", "D", "A"], default=None)
    
    # 5. Oranları Temizle
    def clean_odds(s):
        return pd.to_numeric(s.astype(str).str.replace(",", ".", regex=False).str.strip(), errors="coerce")
    
    df["_odd_H"] = clean_odds(df["_odd_H"])
    df["_odd_D"] = clean_odds(df["_odd_D"])
    df["_odd_A"] = clean_odds(df["_odd_A"])
    
    # 6. Benzersiz ID
    df["_id"] = np.arange(20000000, 20000000 + len(df))
    
    # Eksik olanları sil (Sadece kesinlikle olması gerekenler)
    df = df.dropna(subset=["_date", "_season", "_y"])
    
    print(f"Basarili: {len(df)} mac yuklendi.")
    
    cols = ["_id", "_date", "_season", "Lig/Sezon", "Ev_Sahibi", "Deplasman", "MSE", "MSD", "_y", "_odd_H", "_odd_D", "_odd_A"]
    df_final = df[cols].reset_index(drop=True)
    
    # Bir sonraki calistirmalar icin Pickle olarak kaydet
    print("Gelecek testler icin hizli formata (pkl) kaydediliyor...")
    with open(pkl_path, "wb") as f:
        pickle.dump(df_final, f)
        
    return df_final