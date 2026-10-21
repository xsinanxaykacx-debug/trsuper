# Maçkolik Bahis Oranları — Örüntü Araştırması

Bu depo, futbol maçlarının geçmiş sonuçları ve bahis oranları arasında **istatistiksel olarak desteklenebilir, bağımsız veride de ayakta kalan bir örüntü bulunup bulunmadığını** araştırır. Amaç yalnızca geçmişte kârlı görünen grupları bulmak değil; tesadüf, aşırı uyum ve çoklu test kaynaklı sahte sonuçları ayırt etmektir.

## Araştırmanın güncel sonucu

> **Nihai karar: Mevcut analizlerde bağımsız doğrulamayla desteklenmiş, genellenebilir kârlı bir bahis örüntüsü bulunmadı.**

En son örüntü keşif çalışması; lig ailesi, haftanın günü, market ve oran bandı kombinasyonlarını inceledi. Genel raporda en az 30 maç içeren **534 örüntü** değerlendirildi. Tüm dönem verisinde pozitif getiri (ROI) ve en az 60 maç koşuluyla **16 aday** öne çıktı. Ancak bu, 16 adayın kârlı olduğu anlamına gelmez.

- Erken dönem (2013–2020) ile geç dönem (2021–2025) karşılaştırmasında **16 adayın 13'ünde ROI işareti değişti**.
- Adaylar tüm dönem verisi incelendikten sonra seçildiği için 2021–2025, bu adaylar açısından bağımsız ve kör bir doğrulama seti değildir.
- pattern_discovery_v2 kapsamındaki 534 örüntü için FDR çoklu karşılaştırma düzeltmesi **henüz hesaplanıp doğrulanmış değildir**. Bu nedenle bu analiz için “FDR'den geçen aday sayısı sıfır” denmemektedir.
- Daha önceki ayrı discovery.py çalışmasında 45 test için Benjamini–Hochberg FDR düzeltmesinden geçen aday bulunmadı.

**Yorum:** Geçmiş veride pozitif ROI görmek tek başına bir bahis avantajını kanıtlamaz. Mevcut bulgular güvenilir bir avantajı göstermiyor; ancak tüm olası stratejilerin kârsız olduğunu da kanıtlamıyor.

Ayrıntılı değerlendirme: [docs/discovery_notes.md](docs/discovery_notes.md).

## Veri

| Özellik | Değer |
|---|---|
| Kaynak | [Maçkolik arşivi](https://arsiv.mackolik.com) |
| Ana veri dosyası | [data/csv/DATA.csv](data/csv/DATA.csv) |
| Maç sayısı | 7.422 |
| Sütun sayısı | 353 |
| Veri dönemi | 2013/2014–2025/2026 |
| Önceki FDR kontrollü keşif penceresi | 2019/2020–2022/2023 |
| Önceki keşif penceresindeki maç sayısı | 2.503 |

Veri kalitesi kontrolleri, skor-market uyumu ve tekrar eden maç kimlikleri gibi konuları kapsar. Ham veri, analiz sonuçlarını iyileştirmek amacıyla değiştirilmemelidir.

## Son örüntü keşfi nasıl yapıldı?

pattern_discovery_v2 çalışması aşağıdaki boyutların kombinasyonlarını taradı:

- **Lig ailesi**
- **Haftanın günü**
- **Bahis marketi:** MS1/MSX/MS2, KG Var/Yok ve 1,5 / 2,5 / 3,5 / 4,5 Alt-Üst
- **Oran bandı:** 1,00–5,00 aralığında 0,10 genişliğinde bantlar
- **Genel örüntü eşiği:** en az 30 maç
- **Aday inceleme eşiği:** pozitif ROI ve en az 60 maç

Bu eşikler keşif gruplarını tanımlamak için kullanılmıştır; bağımsız doğrulamanın veya istatistiksel anlamlılığın yerine geçmez. Çok sayıda kombinasyon tarandığında, yalnızca şans nedeniyle bazı grupların yüksek ROI göstermesi beklenebilir.

### Dönem karşılaştırmasının sınırı

13/16 adayda ROI işaretinin değişmesi, sonuçların dönemler arasında kararlı olmadığını düşündüren bir bulgudur. Ancak adaylar tüm dönem verisine bakılarak seçildiğinden, bu karşılaştırma tek başına tarafsız bir doğrulama testi değildir. Binom testi için hesaplanan p değerleri de bu seçim etkisini ortadan kaldırmaz.

## Önceki FDR kontrollü çalışma

Ayrı bir analiz olan discovery.py, 2019/2020–2022/2023 döneminde 9 market ve 45 oran bandını test etti. Benjamini–Hochberg FDR düzeltmesinden geçen aday olmadı. En yüksek gözlenen ROI, KG Var marketinin 1,80–2,00 oran bandında +%2,36 idi (n=148); sonuç istatistiksel olarak anlamlı değildi (ham p=0,3781; BH-düzeltilmiş p=1,0).

Bu önceki testin ayrıntıları:
- [Sonuç raporu](docs/RAPOR.md)
- [Analiz protokolü](docs/protocol.md)
- [45 testin sonuçları](docs/discovery_results.csv)

**Önemli:** Önceki 45 testin FDR sonucu ile sonraki 534 örüntülük keşif aynı analiz değildir; sonuçları birbirine karıştırılmamalıdır.

## Bilimsel karar ve yeniden başlama koşulları

Mevcut veriyle keşif çalışması kapatılmıştır. Yeni bir araştırma başlatılacaksa:

1. Yeni veya bağımsız bir veri kaynağı kullanılmalı; mümkünse mevcut analizde incelenmemiş maçlar eklenmelidir.
2. Hipotezler, aday seçme kuralları, örneklem eşikleri ve istatistiksel testler sonuçlara bakılmadan önce sabitlenmelidir.
3. Çoklu karşılaştırma düzeltmesi önceden belirlenmiş protokole göre uygulanmalıdır.
4. Doğrulama verisi, keşif veya aday seçimi sırasında kullanılmamalıdır.
5. Pozitif ROI tek başına yeterli sayılmamalı; örneklem, belirsizlik aralıkları, test sonuçları ve bağımsız dönem performansı birlikte değerlendirilmelidir.

## Depo yapısı ve çalıştırma

- data/csv/DATA.csv — ana maç verisi
- docs/RAPOR.md — önceki 45 testlik FDR kontrollü çalışma
- docs/protocol.md — önceki çalışmanın analiz protokolü
- docs/discovery_notes.md — son örüntü keşfinin nihai değerlendirmesi

Python 3 ve ilgili analiz bağımlılıkları gerekir. Yerel çalışma kopyanızda discovery.py mevcutsa, depo kök dizininde şu komutlarla çalıştırabilirsiniz:

\`\`\`powershell
python -m pip install pandas numpy scipy statsmodels
python discovery.py
\`\`\`

Betik ve bağımlılık sürümleri depoda yer almıyorsa, çalıştırma ortamı bütünüyle yeniden üretilebilir kabul edilmemelidir. Sonuçları karşılaştırmadan önce kullanılan betik sürümünü, parametreleri ve girdi verisini doğrulayın.

---

## Sorumlu yorumlama

Bu depo istatistiksel araştırma amaçlıdır; bahis tavsiyesi veya kâr garantisi sunmaz. Geçmiş performans gelecekteki sonuçları garanti etmez. Buradaki “avantaj bulunamadı” ifadesi, incelenen veri ve yöntemlerle yeterli kanıt elde edilemediği anlamına gelir; tüm olası stratejiler hakkında evrensel bir hüküm değildir.

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

## MS1 / MSX / MS2 Haftanın Günü Araştırması

- Yeni analiz betiği: `analiz_haftanin_gunu_ms1x2.py`
- Sonuç klasörü: `data/pattern_discovery_ms1x2/`
- Marketler: MS1 (ev sahibi), MSX (beraberlik), MS2 (deplasman).
- Tarama: lig, haftanın günü, market ve 0,10 genişliğinde oran bandı; 1,00 dahil, 5,00 hariç.
- Asgari örneklem: örüntü başına 30 maç; aday incelemesinde en az 60 maç.
- Raporlar: market kapsamı, haftanın gününe göre genel performans, test edilen örüntüler, adaylar ve sezon ayrıntıları.
- Çoklu testler için Benjamini–Hochberg FDR düzeltmesi uygulanır. Aday koşulları pozitif ROI, ROI için yaklaşık %95 güven aralığının alt sınırının sıfırın üzerinde olması, FDR q < 0,05 ve erken/geç dönemlerde yeterli örneklemle pozitif ROI gerektirir.

**Çalıştırma:** depo kök dizininde `python analiz_haftanin_gunu_ms1x2.py`.

**Önemli sınırlama:** 2014–2019 ve 2020–2025 dönemleri yalnızca istikrarı inceleyen tanısal dönemlerdir; bu dönem karşılaştırması bağımsız kör doğrulama değildir. 2020–2025 verisi önceki keşiflerde de incelendiği için out-of-sample doğrulama olarak sunulmaz. Betik keşif amaçlıdır; aday çıkması bile gelecekte kâr veya bahis avantajı garantisi vermez.

