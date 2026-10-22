# dogrulama_testi.py
import pandas as pd
import numpy as np

df = pd.read_csv("data/csv/DATA.csv", encoding="utf-8-sig", dtype=str)
df[["Ev_Gol", "Dep_Gol"]] = df["Skor"].str.extract(r"(\d+)-(\d+)").astype(float)
df["Tarih_P"] = pd.to_datetime(df["Tarih"], format="%d-%m-%Y", errors="coerce")
df["Gun"] = df["Tarih_P"].dt.dayofweek.map({0:"Pazartesi",1:"Salı",2:"Çarşamba",3:"Perşembe",4:"Cuma",5:"Cumartesi",6:"Pazar"})
df["Sezon"] = df["Lig/Sezon"].str.extract(r"(\d{4})/\d{4}", expand=False).astype(float)

# En iyi 10'u sabit olarak tanımla (CSV'den okunabilir ama manuel yazıyorum)
top10 = [
    ("MSX",     2.80, "Perşembe"),
    ("MS2",     9.50, "Pazar"),
    ("MS2",     4.90, "Pazar"),
    ("1.5_ALT", 3.53, "Cumartesi"),
    ("MS2",     2.78, "Cumartesi"),
    ("MS1",     2.65, "Cuma"),
    ("MS2",     2.20, "Çarşamba"),
    ("1.5_ALT", 3.57, "Pazar"),
    ("1.5_ALT", 3.51, "Cumartesi"),
    ("MS1",     2.10, "Çarşamba"),
]

kolonlar = {
    "MS1":"Maç_Sonucu_|_1","MSX":"Maç_Sonucu_|_X","MS2":"Maç_Sonucu_|_2",
    "KG_VAR":"Karşılıklı_Gol_|_Var","KG_YOK":"Karşılıklı_Gol_|_Yok",
    "1.5_ALT":"1,5_Alt/Üst_|_Alt","1.5_UST":"1,5_Alt/Üst_|_Üst",
    "2.5_ALT":"2,5_Alt/Üst_|_Alt","2.5_UST":"2,5_Alt/Üst_|_Üst",
}
kosullar = {
    "MS1": lambda d: d["Ev_Gol"] > d["Dep_Gol"],
    "MSX": lambda d: d["Ev_Gol"] == d["Dep_Gol"],
    "MS2": lambda d: d["Ev_Gol"] < d["Dep_Gol"],
    "KG_VAR": lambda d: (d["Ev_Gol"]>0) & (d["Dep_Gol"]>0),
    "KG_YOK": lambda d: (d["Ev_Gol"]==0) | (d["Dep_Gol"]==0),
    "1.5_ALT": lambda d: (d["Ev_Gol"]+d["Dep_Gol"]) < 1.5,
    "1.5_UST": lambda d: (d["Ev_Gol"]+d["Dep_Gol"]) > 1.5,
    "2.5_ALT": lambda d: (d["Ev_Gol"]+d["Dep_Gol"]) < 2.5,
    "2.5_UST": lambda d: (d["Ev_Gol"]+d["Dep_Gol"]) > 2.5,
}

def to_float(v):
    try: return float(str(v).replace(",", "."))
    except: return np.nan

print(f"{'Market':<10} {'Oran':<6} {'Gün':<12} {'ERKEN ROI':<12} {'GEÇ ROI':<12} {'Flip?'}")
print("-" * 65)

for mkt, oran, gun in top10:
    kol = kolonlar[mkt]
    df[f"{mkt}_Oran"] = df[kol].map(to_float)
    df[f"{mkt}_Kazandi"] = kosullar[mkt](df)
    df[f"{mkt}_Net"] = np.where(df[f"{mkt}_Kazandi"], df[f"{mkt}_Oran"]-1, -1)
    
    # Yakın oran eşleşmesi: ±0.02
    filtre = (
        df[f"{mkt}_Oran"].notna() &
        (df[f"{mkt}_Oran"].between(oran-0.02, oran+0.02)) &
        (df["Gun"] == gun)
    )
    alt = df[filtre]
    
    erken = alt[alt["Sezon"] <= 2020]
    gec = alt[alt["Sezon"] >= 2021]
    
    def roi(x): return (x[f"{mkt}_Net"].mean()*100) if len(x) > 0 else np.nan
    r1, r2 = roi(erken), roi(gec)
    flip = "🔄 FLIP" if pd.notna(r1) and pd.notna(r2) and np.sign(r1) != np.sign(r2) else ""
    print(f"{mkt:<10} {oran:<6} {gun:<12} {r1:>10.2f}% {r2:>10.2f}% {flip}")