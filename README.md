# trsuper

Futbol maç verileri ve bahis oranları üzerinde veri kalitesi kontrolleri ile istatistiksel örüntü keşfi için kullanılan çalışma deposu.

## Veri

- Ana CSV: [`data/csv/DATA.csv`](data/csv/DATA.csv)
- Analizler, maç skorlarını ve market oranlarını kullanır.
- Ham veri, keşif analizi sonucuna göre değiştirilmemelidir.

## Son analiz

2019/2020–2022/2023 sezonlarını kapsayan keşif çalışmasında 9 market ve 45 oran bandı testi değerlendirildi. Benjamini–Hochberg FDR düzeltmesinden geçen aday bulunmadı.

Bu sonuç, incelenen veri ve yöntem kapsamında istatistiksel olarak desteklenen bir bahis avantajı ortaya konamadığı anlamına gelir; piyasanın bütünüyle verimli olduğunu veya başka koşullarda avantaj bulunamayacağını kanıtlamaz.

- [Analiz protokolü](docs/protocol.md): market tanımları, oran filtreleri, bantlar ve istatistiksel yöntem.
- [Sonuç raporu](docs/RAPOR.md): test sayısı, öne çıkan ROI ve sınırlamalar.

## Kurulum ve Çalıştırma

Python 3 ve analiz için kullanılan bağımlılıklar gerekir. Yerel çalışma kopyanızda `discovery.py` mevcutsa, depo kök dizininden çalıştırın:

```powershell
python -m pip install pandas numpy scipy statsmodels
python discovery.py
```

Betik ve bağımlılık sürümleri depoda yer almıyorsa, çalıştırma ortamını tamamen yeniden üretilebilir saymayın. Sonuçları karşılaştırmadan önce kullanılan betik sürümünü, parametreleri ve girdi verisini doğrulayın.

## Bilimsel yorumlama

Pozitif ROI tek başına kârlılık kanıtı değildir. Çoklu karşılaştırma düzeltmesi, güven aralıkları ve örneklem büyüklüğü birlikte değerlendirilmelidir. Keşif sonucunda aday bulunmaması, her olası markette veya dönemde avantajın imkânsız olduğunu göstermez.
