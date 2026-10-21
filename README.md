# Ma├ğkolik Bahis Oranlar─▒ ÔÇö ├ûr├╝nt├╝ Ara┼şt─▒rmas─▒

Bu depo, futbol ma├ğlar─▒n─▒n ge├ğmi┼ş sonu├ğlar─▒ ve bahis oranlar─▒ aras─▒nda **istatistiksel olarak desteklenebilir, ba─ş─▒ms─▒z veride de ayakta kalan bir ├Âr├╝nt├╝ bulunup bulunmad─▒─ş─▒n─▒** ara┼şt─▒r─▒r. Ama├ğ yaln─▒zca ge├ğmi┼şte k├órl─▒ g├Âr├╝nen gruplar─▒ bulmak de─şil; tesad├╝f, a┼ş─▒r─▒ uyum ve ├ğoklu test kaynakl─▒ sahte sonu├ğlar─▒ ay─▒rt etmektir.

## Ara┼şt─▒rman─▒n g├╝ncel sonucu

> **Nihai karar: Mevcut analizlerde ba─ş─▒ms─▒z do─şrulamayla desteklenmi┼ş, genellenebilir k├órl─▒ bir bahis ├Âr├╝nt├╝s├╝ bulunmad─▒.**

En son ├Âr├╝nt├╝ ke┼şif ├ğal─▒┼şmas─▒; lig ailesi, haftan─▒n g├╝n├╝, market ve oran band─▒ kombinasyonlar─▒n─▒ inceledi. Genel raporda en az 30 ma├ğ i├ğeren **534 ├Âr├╝nt├╝** de─şerlendirildi. T├╝m d├Ânem verisinde pozitif getiri (ROI) ve en az 60 ma├ğ ko┼şuluyla **16 aday** ├Âne ├ğ─▒kt─▒. Ancak bu, 16 aday─▒n k├órl─▒ oldu─şu anlam─▒na gelmez.

- Erken d├Ânem (2013ÔÇô2020) ile ge├ğ d├Ânem (2021ÔÇô2025) kar┼ş─▒la┼şt─▒rmas─▒nda **16 aday─▒n 13'├╝nde ROI i┼şareti de─şi┼şti**.
- Adaylar t├╝m d├Ânem verisi incelendikten sonra se├ğildi─şi i├ğin 2021ÔÇô2025, bu adaylar a├ğ─▒s─▒ndan ba─ş─▒ms─▒z ve k├Âr bir do─şrulama seti de─şildir.
- pattern_discovery_v2 kapsam─▒ndaki 534 ├Âr├╝nt├╝ i├ğin FDR ├ğoklu kar┼ş─▒la┼şt─▒rma d├╝zeltmesi **hen├╝z hesaplan─▒p do─şrulanm─▒┼ş de─şildir**. Bu nedenle bu analiz i├ğin ÔÇ£FDR'den ge├ğen aday say─▒s─▒ s─▒f─▒rÔÇØ denmemektedir.
- Daha ├Ânceki ayr─▒ discovery.py ├ğal─▒┼şmas─▒nda 45 test i├ğin BenjaminiÔÇôHochberg FDR d├╝zeltmesinden ge├ğen aday bulunmad─▒.

**Yorum:** Ge├ğmi┼ş veride pozitif ROI g├Ârmek tek ba┼ş─▒na bir bahis avantaj─▒n─▒ kan─▒tlamaz. Mevcut bulgular g├╝venilir bir avantaj─▒ g├Âstermiyor; ancak t├╝m olas─▒ stratejilerin k├órs─▒z oldu─şunu da kan─▒tlam─▒yor.

Ayr─▒nt─▒l─▒ de─şerlendirme: [docs/discovery_notes.md](docs/discovery_notes.md).

## Veri

| ├ûzellik | De─şer |
|---|---|
| Kaynak | [Ma├ğkolik ar┼şivi](https://arsiv.mackolik.com) |
| Ana veri dosyas─▒ | [data/csv/DATA.csv](data/csv/DATA.csv) |
| Ma├ğ say─▒s─▒ | 7.422 |
| S├╝tun say─▒s─▒ | 353 |
| Veri d├Ânemi | 2013/2014ÔÇô2025/2026 |
| ├ûnceki FDR kontroll├╝ ke┼şif penceresi | 2019/2020ÔÇô2022/2023 |
| ├ûnceki ke┼şif penceresindeki ma├ğ say─▒s─▒ | 2.503 |

Veri kalitesi kontrolleri, skor-market uyumu ve tekrar eden ma├ğ kimlikleri gibi konular─▒ kapsar. Ham veri, analiz sonu├ğlar─▒n─▒ iyile┼ştirmek amac─▒yla de─şi┼ştirilmemelidir.

## Son ├Âr├╝nt├╝ ke┼şfi nas─▒l yap─▒ld─▒?

pattern_discovery_v2 ├ğal─▒┼şmas─▒ a┼şa─ş─▒daki boyutlar─▒n kombinasyonlar─▒n─▒ tarad─▒:

- **Lig ailesi**
- **Haftan─▒n g├╝n├╝**
- **Bahis marketi:** MS1/MSX/MS2, KG Var/Yok ve 1,5 / 2,5 / 3,5 / 4,5 Alt-├£st
- **Oran band─▒:** 1,00ÔÇô5,00 aral─▒─ş─▒nda 0,10 geni┼şli─şinde bantlar
- **Genel ├Âr├╝nt├╝ e┼şi─şi:** en az 30 ma├ğ
- **Aday inceleme e┼şi─şi:** pozitif ROI ve en az 60 ma├ğ

Bu e┼şikler ke┼şif gruplar─▒n─▒ tan─▒mlamak i├ğin kullan─▒lm─▒┼şt─▒r; ba─ş─▒ms─▒z do─şrulaman─▒n veya istatistiksel anlaml─▒l─▒─ş─▒n yerine ge├ğmez. ├çok say─▒da kombinasyon tarand─▒─ş─▒nda, yaln─▒zca ┼şans nedeniyle baz─▒ gruplar─▒n y├╝ksek ROI g├Âstermesi beklenebilir.

### D├Ânem kar┼ş─▒la┼şt─▒rmas─▒n─▒n s─▒n─▒r─▒

13/16 adayda ROI i┼şaretinin de─şi┼şmesi, sonu├ğlar─▒n d├Ânemler aras─▒nda kararl─▒ olmad─▒─ş─▒n─▒ d├╝┼ş├╝nd├╝ren bir bulgudur. Ancak adaylar t├╝m d├Ânem verisine bak─▒larak se├ğildi─şinden, bu kar┼ş─▒la┼şt─▒rma tek ba┼ş─▒na tarafs─▒z bir do─şrulama testi de─şildir. Binom testi i├ğin hesaplanan p de─şerleri de bu se├ğim etkisini ortadan kald─▒rmaz.

## ├ûnceki FDR kontroll├╝ ├ğal─▒┼şma

Ayr─▒ bir analiz olan discovery.py, 2019/2020ÔÇô2022/2023 d├Âneminde 9 market ve 45 oran band─▒n─▒ test etti. BenjaminiÔÇôHochberg FDR d├╝zeltmesinden ge├ğen aday olmad─▒. En y├╝ksek g├Âzlenen ROI, KG Var marketinin 1,80ÔÇô2,00 oran band─▒nda +%2,36 idi (n=148); sonu├ğ istatistiksel olarak anlaml─▒ de─şildi (ham p=0,3781; BH-d├╝zeltilmi┼ş p=1,0).

Bu ├Ânceki testin ayr─▒nt─▒lar─▒:
- [Sonu├ğ raporu](docs/RAPOR.md)
- [Analiz protokol├╝](docs/protocol.md)
- [45 testin sonu├ğlar─▒](docs/discovery_results.csv)

**├ûnemli:** ├ûnceki 45 testin FDR sonucu ile sonraki 534 ├Âr├╝nt├╝l├╝k ke┼şif ayn─▒ analiz de─şildir; sonu├ğlar─▒ birbirine kar─▒┼şt─▒r─▒lmamal─▒d─▒r.

## Bilimsel karar ve yeniden ba┼şlama ko┼şullar─▒

Mevcut veriyle ke┼şif ├ğal─▒┼şmas─▒ kapat─▒lm─▒┼şt─▒r. Yeni bir ara┼şt─▒rma ba┼şlat─▒lacaksa:

1. Yeni veya ba─ş─▒ms─▒z bir veri kayna─ş─▒ kullan─▒lmal─▒; m├╝mk├╝nse mevcut analizde incelenmemi┼ş ma├ğlar eklenmelidir.
2. Hipotezler, aday se├ğme kurallar─▒, ├Ârneklem e┼şikleri ve istatistiksel testler sonu├ğlara bak─▒lmadan ├Ânce sabitlenmelidir.
3. ├çoklu kar┼ş─▒la┼şt─▒rma d├╝zeltmesi ├Ânceden belirlenmi┼ş protokole g├Âre uygulanmal─▒d─▒r.
4. Do─şrulama verisi, ke┼şif veya aday se├ğimi s─▒ras─▒nda kullan─▒lmamal─▒d─▒r.
5. Pozitif ROI tek ba┼ş─▒na yeterli say─▒lmamal─▒; ├Ârneklem, belirsizlik aral─▒klar─▒, test sonu├ğlar─▒ ve ba─ş─▒ms─▒z d├Ânem performans─▒ birlikte de─şerlendirilmelidir.

## Depo yap─▒s─▒ ve ├ğal─▒┼şt─▒rma

- data/csv/DATA.csv ÔÇö ana ma├ğ verisi
- docs/RAPOR.md ÔÇö ├Ânceki 45 testlik FDR kontroll├╝ ├ğal─▒┼şma
- docs/protocol.md ÔÇö ├Ânceki ├ğal─▒┼şman─▒n analiz protokol├╝
- docs/discovery_notes.md ÔÇö son ├Âr├╝nt├╝ ke┼şfinin nihai de─şerlendirmesi

Python 3 ve ilgili analiz ba─ş─▒ml─▒l─▒klar─▒ gerekir. Yerel ├ğal─▒┼şma kopyan─▒zda discovery.py mevcutsa, depo k├Âk dizininde ┼şu komutlarla ├ğal─▒┼şt─▒rabilirsiniz:

\`\`\`powershell
python -m pip install pandas numpy scipy statsmodels
python discovery.py
\`\`\`

Betik ve ba─ş─▒ml─▒l─▒k s├╝r├╝mleri depoda yer alm─▒yorsa, ├ğal─▒┼şt─▒rma ortam─▒ b├╝t├╝n├╝yle yeniden ├╝retilebilir kabul edilmemelidir. Sonu├ğlar─▒ kar┼ş─▒la┼şt─▒rmadan ├Ânce kullan─▒lan betik s├╝r├╝m├╝n├╝, parametreleri ve girdi verisini do─şrulay─▒n.

---

## Sorumlu yorumlama

Bu depo istatistiksel ara┼şt─▒rma ama├ğl─▒d─▒r; bahis tavsiyesi veya k├ór garantisi sunmaz. Ge├ğmi┼ş performans gelecekteki sonu├ğlar─▒ garanti etmez. Buradaki ÔÇ£avantaj bulunamad─▒ÔÇØ ifadesi, incelenen veri ve y├Ântemlerle yeterli kan─▒t elde edilemedi─şi anlam─▒na gelir; t├╝m olas─▒ stratejiler hakk─▒nda evrensel bir h├╝k├╝m de─şildir.


## Haftanın Günü Bazlı 2,5 Alt/Üst ve KG Var/Yok Araştırmaları

Bu iki ayrı çalışma, haftanın günü ile bahis oran bandı arasında geçmiş veride kârlı ve istatistiksel olarak desteklenebilir bir ilişki bulunup bulunmadığını araştırır. Sonuçlar bahis tavsiyesi değildir.

### 2,5 Alt/Üst

- Analiz betiği: `analiz_haftanin_gunu_25ust.py`
- Sonuç klasörü: `data/pattern_discovery_v2/`
- İncelenen pazar: 2,5 gol Üst; oran bandı genişliği 0,10.
- Test edilen, en az 30 maç içeren gün/oran bandı kombinasyonu: 29.
- Benjamini–Hochberg FDR düzeltmesinden geçen kombinasyon: 0.
- Koşulları sağlayan doğrulanmış aday: 0.
- En yüksek pozitif ROI görülen bant: Cuma, 1,60–1,69 oran aralığı; 70 maçta yaklaşık +%0,39 ROI. Güven aralığının alt sınırı negatif ve düzeltilmiş p değeri anlamlı değildir.

Eski `AÜ_2,5_Gol_|_Üst` sütunu ile yeni `2,5_Alt/Üst_|_Üst` sütununun veri kaynakları ve dönem devamlılığı ayrıca doğrulanmadan tek bir kesintisiz seri gibi birleştirilmemiştir.

### KG Var / KG Yok

- Analiz betiği: `analiz_haftanin_gunu_kg.py`
- Sonuç klasörü: `data/pattern_discovery_kg/`
- Sonuç etiketleri: `KGVY`; oran sütunları: `Karşılıklı_Gol_|_Var` ve `Karşılıklı_Gol_|_Yok`.
- Veri dönemi: 11 Ocak 2014–28 Aralık 2025.
- Her iki KG pazarında kullanılabilir oran bulunan maç sayısı: 7.348.
- En az 30 maç içeren gün/oran bandı kombinasyonu: 70.
- FDR düzeltmesinden geçen kombinasyon: 0.
- Koşulları sağlayan doğrulanmış aday: 0.
- En yüksek pozitif ROI görülen bant: Cumartesi KG Yok, 2,10–2,19 oran aralığı; 52 maçta yaklaşık +%2,31 ROI. Güven aralığının alt sınırı yaklaşık -%26,88 ve FDR q değeri 1,00 olduğundan bu sonuç kanıtlanmış avantaj sayılmaz.

### Ortak metodolojik karar

Her iki araştırmada da pozitif ROI tek başına yeterli kabul edilmemiştir. Çoklu karşılaştırma düzeltmesi, örneklem büyüklüğü ve ROI belirsizlik aralığı birlikte değerlendirilmiştir. Mevcut testlerde güvenilir ve doğrulanmış bir bahis avantajı bulunamamıştır. Bu sonuç, tüm olası stratejilerin kârsız olduğunu kanıtlamaz.

Sonuç CSV dosyaları test edilen bantları, genel performansı ve aday değerlendirmesini ayrı ayrı saklar. Ham veri üzerinde sonuçları iyileştirmek amacıyla değişiklik yapılmamalıdır.

## Depodaki Ek Araştırma Dosyaları

### Örüntü keşfi

- `discover_patterns.py`: Veri setindeki aday örüntüleri taramak için kullanılan araştırma betiği.
- `incele_25ust.py`: 2,5 üst marketiyle ilgili veri ve sonuç incelemeleri.
- `kontrol_25ust_sutunlari.py`: 2,5 üst veri sütunlarını ve kaynak farklılıklarını kontrol etmek için yardımcı betik.

### Sonuç dosyaları

- `data/pattern_discovery/`: Önceki örüntü keşfi çalışmasının çıktıları.
- `data/pattern_discovery_v2/`: Güncellenmiş örüntü taraması, sezon ve dönem karşılaştırmaları, eşik özetleri ve aday sonuçları.
- `data/pattern_discovery_kg/`: Karşılıklı Gol Var/Yok marketi için haftanın günü ve oran bandı analizleri.

### Bilimsel değerlendirme

Pozitif ROI tek başına güvenilir bahis avantajı kanıtı değildir. Örneklem büyüklüğü, güven aralığı, p-değeri ve çoklu testler için FDR düzeltmesi birlikte değerlendirilmelidir. Mevcut haftanın günü analizlerinde FDR düzeltmesinden geçen doğrulanmış aday bulunmamıştır. Sonuçlar kesin kazanç veya gelecekteki performans garantisi olarak yorumlanmamalıdır.

Ham veri dosyaları, özellikle boyutu büyük olan kaynak veriler, bu araştırma dosyalarının yayımlanması için otomatik olarak eklenmez.
