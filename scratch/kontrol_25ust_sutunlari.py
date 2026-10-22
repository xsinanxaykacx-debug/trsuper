import pandas as pd

path = "data/csv/DATA.csv"
df = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig", dtype=str)

df["Tarih_parsed"] = pd.to_datetime(
    df["Tarih"], format="%d-%m-%Y", errors="coerce"
)
df["Yil"] = df["Tarih_parsed"].dt.year

print("=== VERI SETININ YILLARA GORE MAC SAYISI ===")
print(df.groupby("Yil", dropna=False).size().to_string())

print("\n=== 2,5 / 2.5 ORAN SUTUNLARI ===")

cols = [
    c for c in df.columns
    if "2,5" in c.lower() or "2.5" in c.lower()
]

for c in cols:
    nonempty = df[c].notna() & df[c].astype(str).str.strip().ne("")
    print("\nSUTUN:", c)
    print("Dolu satir:", int(nonempty.sum()))
    print(
        "Yillara gore doluluk:",
        df.loc[nonempty].groupby("Yil").size().to_dict()
    )
    print(
        "Ornek degerler:",
        df.loc[nonempty, c].drop_duplicates().head(8).tolist()
    )

print("\n=== KULLANILAN 2,5 UST ORANININ YILLARA GORE DOLULUGU ===")

target = "AÜ_2,5_Gol_|_Üst"

if target in df.columns:
    odds = df[target].astype(str).str.strip()
    normalized = odds.str.replace(",", ".", regex=False)
    valid = normalized.str.match(r"^\d+(\.\d+)?$", na=False)
    print(df.loc[valid].groupby("Yil").size().to_string())
else:
    print("Beklenen sutun bulunamadi:", target)
