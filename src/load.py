import pandas as pd
import numpy as np
from pathlib import Path

def to_numeric_comma(series: pd.Series) -> pd.Series:
    """Türkçe ondalık virgüllü string oranları float'a çevirir."""
    return pd.to_numeric(
        series.astype(str).str.replace(",", ".", regex=False).str.strip(),
        errors="coerce"
    )

def load_data(root_path: Path = Path.cwd()) -> pd.DataFrame:
    csv_path = root_path / "data" / "csv" / "DATA.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Veri dosyasi bulunamadi: {csv_path}")
        
    df = pd.read_csv(csv_path, sep=None, engine="python", encoding="utf-8-sig")
    
    df["_date"] = pd.to_datetime(df["Tarih"], format="%d-%m-%Y", errors="coerce")
    df["_season"] = df["Lig/Sezon"].astype(str).str.extract(r"(\d{4}/\d{4})", expand=False)
    
    df["_odd_H"] = to_numeric_comma(df["Maç_Sonucu_|_1"])
    df["_odd_D"] = to_numeric_comma(df["Maç_Sonucu_|_X"])
    df["_odd_A"] = to_numeric_comma(df["Maç_Sonucu_|_2"])
    
    hg = pd.to_numeric(df["MSE"], errors="coerce")
    ag = pd.to_numeric(df["MSD"], errors="coerce")
    
    conditions = [(hg > ag), (hg == ag), (hg < ag)]
    choices = ["H", "D", "A"]
    df["_y"] = np.select(conditions, choices, default=None)
    
    df = df.dropna(subset=["_date", "_season", "_y"]).reset_index(drop=True)
    df["_id"] = pd.to_numeric(df["Maç_ID"], errors="coerce").astype("int64")
    
    return df

def load_v16_reference(root_path: Path = Path.cwd()) -> pd.DataFrame:
    ref_path = root_path / "archive_v16" / "v16_per_match_predictions.csv"
    if not ref_path.exists():
        raise FileNotFoundError(f"v1.6 referans dosyasi bulunamadi: {ref_path}")
        
    ref_df = pd.read_csv(ref_path, encoding="utf-8-sig")
    ref_df["_id"] = pd.to_numeric(ref_df["match_id"], errors="coerce").astype("int64")
    return ref_df

if __name__ == "__main__":
    df = load_data()
    print(f"Yuklenen mac: {len(df)}")
    print(f"Hedef dagilimi:\n{df['_y'].value_counts()}")
    print(f"Oran doluluk (1X2): {df['_odd_H'].notna().mean()*100:.2f}%")