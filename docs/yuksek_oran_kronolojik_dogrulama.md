# Dört Büyük Takım — Yüksek Oran Stratejileri: Kronolojik Doğrulama

## Amaç

Dört büyük Türk futbol takımının maçlarında iki yüksek oran stratejisinin geçmiş performansını, geliştirme dönemi ile daha sonraki zaman dışı dönem arasında karşılaştırmak.

- **Strateji A — Favorinin tersi (MS1/MS2):** Ev sahibi galibiyeti (MS1) ile deplasman galibiyeti (MS2) oranlarından yüksek olanı seç.
- **Strateji B — En yüksek MS1/MSX/MS2 oranı:** Üç sonuç marketinden en yüksek oranı seç.
- Her bahis için sabit 1 birim.
- Dönemler: geliştirme 2014–2022; zaman dışı tarihsel test 2023–2025.
- Güven aralıkları: 20.000 tekrarlı, 5 bahislik dairesel hareketli blok bootstrap. Bunlar yaklaşık tarihsel belirsizlik aralıklarıdır; tek başına gelecekte kârlılık garantisi sağlamaz.

## Genel sonuçlar

| Strateji | Dönem | Bahis | Kazandı | Kaybetti | Kazanma oranı | Ortalama oran | Net kâr/zarar | ROI | ROI %95 bootstrap alt | ROI %95 bootstrap üst |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A — Favorinin tersi MS1/MS2 | 2014–2022 geliştirme | 768 | 172 | 596 | %22,40 | 3,35 | -220,42 | -%28,70 | -%38,20 | -%19,08 |
| A — Favorinin tersi MS1/MS2 | 2023–2025 zaman dışı test | 217 | 38 | 179 | %17,51 | 3,49 | -98,21 | -%45,26 | -%61,23 | -%28,68 |
| B — En yüksek MS1/MSX/MS2 | 2014–2022 geliştirme | 743 | 179 | 564 | %24,09 | 3,56 | -129,82 | -%17,47 | -%28,04 | -%6,94 |
| B — En yüksek MS1/MSX/MS2 | 2023–2025 zaman dışı test | 215 | 40 | 175 | %18,60 | 3,68 | -79,81 | -%37,12 | -%54,27 | -%19,14 |

## 2023–2025 market × oran grupları

Yalnızca en az 30 bahis içeren gruplar aşağıda gösterilmiştir. Bu eşik, sonuçları doğrulanmış yapmaz; özellikle 30–67 bahislik gruplar keşifsel kabul edilmelidir.

| Strateji | Market | Oran bandı | Bahis | Kazandı | Kazanma oranı | Ortalama oran | Net kâr/zarar | ROI | ROI %95 bootstrap alt | ROI %95 bootstrap üst |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| B — En yüksek oran | MSX (beraberlik) | 3,00–3,49 | 67 | 19 | %28,36 | 3,17 | -7,18 | -%10,72 | -%46,49 | +%25,99 |
| A — Favorinin tersi | MS1 | 2,50–2,99 | 36 | 10 | %27,78 | 2,75 | -9,02 | -%25,06 | -%55,19 | +%4,86 |
| A — Favorinin tersi | MS2 | 4,00–4,99 | 36 | 5 | %13,89 | 4,47 | -14,42 | -%40,06 | -%88,86 | +%10,50 |
| B — En yüksek oran | MS2 | 4,00–4,99 | 36 | 5 | %13,89 | 4,47 | -14,42 | -%40,06 | -%88,86 | +%10,08 |
| A — Favorinin tersi | MS1 | 4,00–4,99 | 30 | 1 | %3,33 | 4,46 | -25,43 | -%84,77 | -%100,00 | -%54,30 |

## Yorum ve karar

1. Her iki stratejinin de 2023–2025 ROI'si negatif; iki genel stratejinin bootstrap güven aralıklarının üst sınırı bile sıfırın altında.
2. Strateji A'nın ROI'si geliştirme dönemindeki -%28,70 seviyesinden zaman dışı dönemde -%45,26'ya gerilemiş.
3. Strateji B'nin ROI'si geliştirme dönemindeki -%17,47 seviyesinden zaman dışı dönemde -%37,12'ye gerilemiş.
4. Beraberlik ve oran bandı alt gruplarının hiçbiri doğrulanmış kârlılık göstermiyor. Beraberlik grubunun güven aralığı sıfırı kapsıyor ve örneklemi yalnızca 67 bahis.
5. **Karar:** Bu testte, önceden tanımlanan iki yüksek oran stratejisinden hiçbiri bahis avantajı göstermedi. Mevcut bulgulara dayanarak gerçek parayla uygulanması önerilmez.

## Sınırlamalar

- 2023–2025 dönemi, geçmiş verinin kronolojik olarak ayrılmış test bölümüdür; canlı ve ileriye dönük bir deney değildir.
- Stratejiler ve alt gruplar geçmiş sonuçlar görüldükten sonra incelenmiş olabileceği için çoklu karşılaştırma ve seçim yanlılığı riski vardır.
- Blok bootstrap, bahis dizisindeki kısa dönem bağımlılığı yaklaşık olarak ele alır; burada kullanılan bloklar seçili grubun bahis sırası üzerinde dairesel örneklenmiştir. Takvimdeki tüm maçların ortak bağımlılık yapısını tam modellemez.
- Sonuçlar yalnızca tanımlanan veri, filtreler ve dönemler için geçerlidir; bütün bahis stratejilerinin kârsız olduğunu kanıtlamaz.

## Yeniden üretim

Analiz betiği: [analiz_dort_buyuk_yuksek_oran_dogrulama.py](../analiz_dort_buyuk_yuksek_oran_dogrulama.py)

Betiğin yerel çıktıları `data/bankroll_ruin_simulation/dort_buyuk_unique/yuksek_oran_karsilastirmasi` klasörüne yazılır.
