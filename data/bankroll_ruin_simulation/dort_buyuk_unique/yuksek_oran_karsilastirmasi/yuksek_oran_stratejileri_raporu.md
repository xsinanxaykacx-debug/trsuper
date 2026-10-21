# Dört Büyük Takım — Yüksek Oran Stratejileri

## Yöntem

- Ortak havuz: dört büyük takımın en az birinin oynadığı, skoru okunabilen ve üç oranın da 1,00 dahil–5,00 hariç geçerli olduğu 992 maç.
- A: MS1/MS2 arasında daha yüksek oranlı taraf; eşit MS1/MS2 oranında bahis yok.
- B: MS1/MSX/MS2 arasında en yüksek oran; en yüksek oran eşitliğinde bahis yok.
- Her bahis 1 birim, başlangıç kasası 100 birim. Tarih sıralı hareketli blok bootstrap: blok 5, 20.000 tekrar.

## Sonuç

| Strateji | Bahis | Kazandı | Kaybetti | Kazanma % | Net K/Z | ROI % | ROI %95 alt | ROI %95 üst | Teorik son kasa | 100 birimle oynanan | Gerçek son kasa | Maks. düşüş % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A_Favorinin_Tersi_MS1_MS2 | 985 | 210 | 775 | 21.32 | -318.63 | -32.35 | -40.81 | -23.92 | -218.63 | 372 | 0.25 | 99.75 |
| B_MS1_MSX_MS2_En_Yuksek_Oran | 958 | 219 | 739 | 22.86 | -209.63 | -21.88 | -30.90 | -12.72 | -109.63 | 530 | 0.25 | 99.78 |

## Önemli notlar

- Teorik son kasa, tüm tarihsel bahislerin net sonucunu 100 birime ekler; kasa sıfırın altına inse bile tüm bahisleri oynanmış varsayar.
- Gerçek son kasa simülasyonunda kasa 1 birimin altına düştüğünde yeni bahis açılmaz.
- Yüksek oran, yüksek kâr garantisi değildir. ROI güven aralığı sıfırı içeriyorsa pozitif avantaj için yeterli kanıt yoktur.
- İki strateji aynı ortak maç havuzunu kullanır; eşit oran kuralları nedeniyle bahis adetleri farklı olabilir.

## Dosyalar

- yuksek_oran_stratejileri_ozet.csv: karşılaştırmalı özet.
- yuksek_oran_stratejileri_bahis_detay.csv: her bahis ve sonucu.
- ortak_mac_havuzu.csv: ortak maç ve oran havuzu.
