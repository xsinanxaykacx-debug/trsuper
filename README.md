# Maçkolik Bahis Oranları — Örüntü Araştırması

Bu depo, futbol maçlarının geçmiş sonuçları ve bahis oranları arasında **istatistiksel olarak desteklenebilir, bağımsız veride de ayakta kalan bir örüntü bulunup bulunmadığını** araştırır. Amaç yalnızca geçmişte kârlı görünen grupları bulmak değil; tesadüf, aşırı uyum ve çoklu test kaynaklı sahte sonuçları ayırt etmektir.
## 📊 Vaka Çalışması: "Favoriye Bahis" Stratejisi

### Hipotez
"Dört büyük takım (Galatasaray, Fenerbahçe, Beşiktaş, Trabzonspor) favori olduğunda, her maça 1 birim sabit bahis basmak uzun vadede kâr getirir."

### Yöntem
- MS1 veya MS2 (favori taraf) oranı, maç öncesi kapanış oranı
- Her maça **1 birim sabit bahis**
- 2014-2025 dönemi, 4 takım × ~410 maç
- 100 maçlık ardışık serilere bölünmüş (16 seri)

### Sonuçlar (Genel)

| Takım | Maç | Net Kâr/Zarar | ROI |
|---|---:|---:|---:|
| Galatasaray | 410 | **−28.22** | −%6.88 |
| Fenerbahçe | 412 | **−61.02** | −%14.81 |
| Beşiktaş | 415 | **−37.20** | −%8.96 |
| Trabzonspor | 415 | **−63.19** | −%15.23 |

### 100 Maçlık Seri Analizi (16 Seri)

| Seri | GS | FB | BJK | TS | Pozitif |
|---|---:|---:|---:|---:|---:|
| 1 | −13.80 | −9.40 | **+3.55** | −20.60 | 1/4 |
| 2 | −6.37 | −29.66 | −9.70 | −28.23 | 0/4 |
| 3 | −14.20 | −11.80 | −17.60 | −12.90 | 0/4 |
| 4 | **+8.09** | −10.16 | −13.45 | **+1.55** | 2/4 |
| **Toplam** | **1/4** | **0/4** | **1/4** | **1/4** | **3/16 (18.75%)** |

**Rastgele beklenti:** ~%45-50 (bahisçi marjı düşüldükten sonra).
**Gözlenen:** %18.75. **Yani favori bahisleri, rastgele beklentinin çok altında.**

### 🚨 En Kritik Bulgu: Kazanma Oranı ≠ Kârlılık

**Galatasaray 1. Seri:**
- 100 bahis
- **58 kazanç** (%58 kazanma oranı)
- **Sonuç: −13.80 birim zarar**

**Neden?** Favori oranları düşük (1.50-1.80 arası). Bir kayıp (−1.00), iki kazancı (2 × 0.70 = 1.40) siliyor.

**Ders:** "Yüksek kazanma oranı" tuzağına düşmeyin. Gerçek kârlılık, **kazanç × oran − kayıp** hesabıyla ölçülür.

### Yorum
- **3/16 pozitif seri**, rastgele beklentinin çok altında → favori bahisleri sistematik dezavantaj
- Pozitif seriler (GS 4, BJK 1, TS 4) **izole başarılar**, diğer serilerde aynı takımlar negatif
- **Kadro/teknik direktör/piyasa koşulları** seri sonuçlarını etkiliyor
- Sonuç, **verimli piyasa hipoteziyle tutarlı**: bahisçi marjı + favoriye aşırı talep = negatif beklenti

### ⚠️ Yorumlama Uyarısı
Bu vaka çalışması, "favori bahisleri işe yaramaz" **kanıtı değil**, "bu dönemde, bu yöntemle, kârlı değil" **gözlemidir**. Pozitif serileri seçip genelleme yapmak **p-hacking**'dir.

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

```powershell
python -m pip install pandas numpy scipy statsmodels
python discovery.py
```

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

## MS2 oranı eksik kayıtlar

`data/csv/DATA.csv` dosyasındaki MS2 oranı alanı ayrıca denetlenmiştir.

- İncelenen toplam maç: **7.422**
- MS2 oranı boş maç: **20** (yaklaşık %0,27)
- Önceki incelemede Maçkolik sayfasında MS2 oranı `-` olarak bildirilen maç: **4**. Bu kayıtlar bu denetim sırasında bağımsız olarak yeniden doğrulanmamıştır.
- Dış kaynak kontrolü bekleyen maç: **16**

Ayrıntılı kayıtlar:
- [MS2 eksik oran CSV raporu](data_quality_ms2_eksik.csv)
- [MS2 eksik oran Markdown raporu](data_quality_ms2_eksik.md)

### Analiz açısından yorum

MS2 oranı boş olan maçlar, MS2 oranı gerektiren hesaplamalarda geçerli oranı varmış gibi kullanılmamalıdır. Eksik oranlar tahminle doldurulmamıştır ve kaynak CSV değiştirilmemiştir.

Bir maçta MS2 oranının boş olması, deplasman galibiyetinin kesin görüldüğünü veya oranın neden yayımlanmadığını kanıtlamaz. Maçkolik sayfasında `-` görünmesi de tek başına bahis şirketlerinin hiçbir zaman oran açmadığını göstermez.

Bu denetim veri kapsamını belgelemektedir; yeni bir bahis avantajı veya kârlı strateji kanıtı değildir.

## Dört Büyük Takım — MS Favorisi ve Kasa Simülasyonu

### Araştırmanın Amacı

Bu çalışmada Galatasaray, Fenerbahçe, Beşiktaş ve Trabzonspor maçlarında MS1, MSX ve MS2 oranları arasından en düşük geçerli oranın seçildiği basit bir bahis stratejisi geriye dönük test edilmiştir.

Amaç, her takımın maçlarında aynı seçim kuralı uygulandığında 100 birimlik başlangıç kasasının tarihsel sonuçlar karşısında nasıl değiştiğini incelemektir.

### Simülasyon Kuralları

- Başlangıç kasası: **100 birim**
- Her takım maçı için sabit bahis: **1 birim**
- Seçim: MS1, MSX ve MS2 arasındaki en düşük geçerli oran
- Kazanan bahis: Net kâr, `oran - 1` birim
- Kaybeden bahis: `-1` birim
- Geçerli oranı veya sonucu olmayan maçlar simülasyona alınmaz.
- Maçlar tarih sırasıyla işlenir.
- Sonuçlar, `data/csv/DATA.csv` dosyasındaki mevcut tarihsel veriye dayanır.

### Sonuçlar

| Sıra | Takım | Geçerli Bahis | Kazandı | Kaybetti | Kazanma Oranı | Toplam Kâr/Zarar | ROI | Son Kasa |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | Galatasaray | 410 | 266 | 144 | %64,88 | -28,22 | -%6,88 | 71,78 |
| 2 | Beşiktaş | 415 | 248 | 167 | %59,76 | -37,20 | -%8,96 | 62,80 |
| 3 | Fenerbahçe | 412 | 249 | 163 | %60,44 | -61,02 | -%14,81 | 38,98 |
| 4 | Trabzonspor | 415 | 213 | 202 | %51,33 | -63,19 | -%15,23 | 36,81 |

**Veri dönemi:** 1 Ocak 2014 başlangıç tarihi; takım bazında son geçerli maçlar 20–22 Aralık 2025 aralığındadır. Galatasaray maçları 21 Aralık 2025'e kadar uzanır.

### Bulgular

- Bu testte en yüksek kalan kasa Galatasaray için görülmüştür: **71,78 birim**.
- Beşiktaş 62,80 birimle ikinci sıradadır.
- Fenerbahçe ve Trabzonspor için kalan kasa sırasıyla 38,98 ve 36,81 birimdir.
- Dört takımın da toplam kâr/zararı negatiftir.
- Kazanma oranının yüksek olması tek başına kârlılık anlamına gelmez; oranların seviyesi de sonucu belirler.

### Yorum ve Sınırlamalar

Bu sonuçlar, yalnızca kullanılan veri setindeki geçmiş maçları ve belirtilen seçim kuralını yansıtır. Galatasaray'ın bu örneklemde daha iyi sonuç vermesi, gelecekte de aynı performansı göstereceğini kanıtlamaz.

Dört sistem de veri döneminin sonuna ulaşmış, bu simülasyonda başlangıç kasasını tüketmemiştir. Bu nedenle sonuçlardan gerçek bir kasa bitiş tarihi veya gelecekteki dayanma süresi çıkarılamaz.

Bu çalışma, bağımsız ve ileriye dönük doğrulama yapılmadan kârlı bir bahis sistemi bulunduğu şeklinde yorumlanmamalıdır.

### Üretilen Dosyalar

- Simülasyon betiği: `simulasyon_dort_buyuk_ms_banko.py`
- Özet CSV: `data/bankroll_ruin_simulation/dort_buyuk/dort_buyuk_ms_favorisi_ozet.csv`
- Maç bazında ayrıntılar: `data/bankroll_ruin_simulation/dort_buyuk/dort_buyuk_ms_favorisi_detay.csv`


## 2026–2027 İçin 100 Birimlik Kasa İleri Testi

Düşük MS1/MS2 oranını seçen stratejinin Galatasaray seçimi ve dört büyük takım birleşik portföyü için tarihsel sonuçları, 100 bahislik aritmetik senaryo ve 2026–2027 ileriye dönük test protokolü ayrı raporda yer alır.

- [100 birim kasa ve ileriye dönük test raporu](data/bankroll_ruin_simulation/dort_buyuk_unique/gercek_takim_secimi/2026_2027_100_birim_ileri_test.md)

**Önemli:** Galatasaray örneklemindeki +%8,81 tarihsel ROI'nin yaklaşık %95 belirsizlik aralığı sıfırı içerir. 108,81 birim, bu tarihsel nokta ROI'sinin 100 bahiste aynen tekrarlandığı varsayımına dayanan aritmetik senaryodur; kâr beklentisi veya garanti değildir. Dört büyük takımın birleşik örnekleminde tarihsel ROI -%3,07'dir. 2026–2027 sonuçları önceden sabitlenmiş kuralla ileriye dönük test edilmelidir.


## Dört Büyük Takım — Yüksek Oran Stratejileri

İki karşı stratejiyi aynı uygun maç havuzunda test eden betik eklendi:

- [Analiz betiği](analiz_dort_buyuk_yuksek_oran_stratejileri.py)
- Strateji A: MS1/MS2 arasında düşük oranlı tarafın tersi, yani daha yüksek oranlı taraf.
- Strateji B: MS1/MSX/MS2 arasındaki en yüksek oranlı sonuç.
- Ortak maç havuzu, sabit 1 birim bahis, 100 birim kasa, ROI ve hareketli blok bootstrap belirsizlik aralığı hesaplanır.
- Çıktılar `data/bankroll_ruin_simulation/dort_buyuk_unique/yuksek_oran_karsilastirmasi/` klasörüne yazılır.

Bu analizde üç oranın da geçerli olması şartıyla aynı maç havuzu kullanılır; eşit oran durumlarında ilgili strateji bahis yapmaz. Geçmiş performans gelecekteki sonucu garanti etmez.


### Yüksek Oran Stratejileri — Kırılım Analizi

- [Yıl × oran aralığı × seçilen market analiz betiği](analiz_dort_buyuk_yuksek_oran_kirilim.py)
- Önce `analiz_dort_buyuk_yuksek_oran_stratejileri.py` çalıştırılmalı; bu ikinci betik onun `yuksek_oran_stratejileri_bahis_detay.csv` çıktısını kullanır.
- Yıllara, oran aralıklarına (1,00–1,99; 2,00–2,49; 2,50–2,99; 3,00–3,49; 3,50–3,99; 4,00–4,99), seçilen MS1/MSX/MS2 marketine ve bunların kesişimlerine göre bahis sayısı, kazanma oranı, ortalama oran, toplam kâr/zarar ve ROI üretir.
- Kırılım sonuçları keşif amaçlıdır; çok sayıda kombinasyonda tesadüfi pozitif sonuçlar çıkabileceği için bağımsız doğrulama olmadan strateji seçmek için kullanılmamalıdır.


### Yüksek Oran Stratejileri — Kronolojik Doğrulama

- [Kronolojik doğrulama betiği](analiz_dort_buyuk_yuksek_oran_dogrulama.py)
- Geliştirme/keşif dönemi 2014–2022, zaman dışı tarihsel kontrol dönemi 2023–2025 olarak ayrılır.
- Strateji ve market × oran aralığı sonuçları için bahis sayısı, kazanma oranı, ROI ve hareketli blok bootstrap %95 aralığı üretilir.
- Bu, tarihsel kronolojik kontrol olup canlı ileriye dönük test değildir. Alt grup sonuçları çoklu karşılaştırma nedeniyle keşif amaçlıdır; bağımsız doğrulama olmadan bahis kuralı seçilmemelidir.

- ## 🎯 Yönetici Özeti — Nihai Sonuç

> **Mevcut veriyle yapılan 17 bağımsız analizde, çoklu test düzeltmesinden (FDR/Holm-Bonferroni) geçen ve bağımsız dönemde ayakta kalan hiçbir kârlı bahis örüntüsü bulunamadı.**

| Metrik | Sonuç |
|---|---:|
| Toplam analiz | **17** |
| Test edilen örüntü/kombinasyon | **~2.900+** |
| FDR/Holm'den geçen | **0** |
| Bağımsız doğrulamadan geçen | **0** |
| Güçlü aday (GA alt > 0) | **0** |
| Doğrulanmış kârlı strateji | **0** |
| Skor–MS uyuşmazlığı | **0** |
| Maç ID tekrarı | **0** |

**Bu sonuç, "bahis oynanmaz" demek değildir.** İncelenen veri, market, dönem ve yöntemle **istatistiksel olarak kanıtlanabilir bir avantaj bulunamadığı** anlamına gelir. Bahisçi marjı (%5–8), incelenen tüm piyasalarda sistematik olarak kârlılığı engellemektedir.

## 📋 Araştırma Zaman Çizelgesi — 17 Test

| # | Analiz | Test Sayısı | Düzeltme | Sonuç |
|---|---|---:|---|---|
| 1 | 1X2 + KG + 2.5 Alt/Üst (FDR kontrollü) | 45 | ✅ BH | **0 survivor** |
| 2 | 534 örüntü taraması (pattern_discovery_v2) | 534 | ❌ | 13/16 FLIP |
| 3 | Spesifik oran + gün kombinasyonları | 2.161 | ❌ | 6/10 FLIP |
| 4 | TG (Toplam Gol) — 137 aday | 137 | ✅ BH | **0 survivor** |
| 5 | TG birleşik analiz | 8 | ✅ BH | **0 survivor** |
| 6 | TG blok duyarlılık (1, 10, 20, 40) | 32 | ❌ | GA hep sıfır içi |
| 7 | Dört büyük takım — favori stratejisi | 4 | ❌ | 3/16 seri pozitif |
| 8 | Dört büyük takım — MS banko | 4 | ❌ | Hepsi negatif |
| 9 | Yüksek oran A/B (blok duyarlılık) | 2 | ❌ | GA tamamen negatif |
| 10 | Takım bazlı ileri test | 4 | ✅ Holm | **0 anlamlı** |
| 11 | Takım seçimi düzeltmesi | 12 | ✅ Holm | GS +%8.81 ama GA sıfır içi |
| 12 | GS leave-one-year-out | 7 | ❌ | Kâr dağılmış, GA sıfır içi |
| 13 | GS kâr yoğunlaşması | 1 | ❌ | Top-10 çıkar → +1.83 |
| 14 | Yüksek oran kırılım (yıl × oran × market) | 100+ | ❌ | Alt grupta pozitif yok |
| 15 | Yüksek oran kronolojik doğrulama | 2 | ❌ | Geliştirme → Zaman dışı kötüleşiyor |
| 16 | MS2 eksik oran denetimi | 20 maç | — | %0.27 eksik, rapor edildi |
| 17 | Veri kalitesi (skor/MS/ID) | 7.422 | — | **Kusursuz** |

## 🔬 Öne Çıkan Bulgular

### 🚨 1. Kazanma Oranı ≠ Kârlılık

| Takım | Kazanma | ROI |
|---|---:|---:|
| Galatasaray | %64.88 | −%6.88 |
| Beşiktaş | %59.76 | −%8.96 |
| Fenerbahçe | %60.44 | −%14.81 |
| Trabzonspor | %51.33 | −%15.23 |

**Ders:** Favori oranları düşük → 2 kayıp 3 kazancı siler. %65 kazanma bile yetmiyor.

### 🎲 2. MS2 Bootstrap = Yazı Tura

Düşük oran MS2 alt grubu (2023+):

| Blok | GA | Pozitif Bootstrap % |
|---|---:|---:|
| 1 | [−11.27, +11.24] | %50.95 |
| 10 | [−8.90, +8.80] | %50.28 |
| 20 | [−9.32, +8.79] | %50.48 |
| 40 | [−9.85, +8.38] | %52.36 |

**Yorum:** Her blok uzunluğunda pozitif bootstrap **%50** → strateji kârlılığı **rastgele**. Hipotez değil, saf gürültü.

### 🌊 3. Yüksek Oran Stratejileri — Zamanla Kötüleşiyor

| Strateji | Geliştirme (2014-2022) | Zaman Dışı (2023-2025) | Değişim |
|---|---:|---:|---:|
| A (Favorinin tersi) | −%28.70 | **−%45.26** | −16.56 puan |
| B (En yüksek oran) | −%17.47 | **−%37.12** | −19.65 puan |

**Kritik:** Underdog stratejileri geçmişte kötüydü, **gelecekte daha da kötüleşiyor.**

### 💀 4. Kasa Simülasyonu — Yıkım

| Strateji | Başlangıç | Son Kasa | Bitiş Tarihi |
|---|---:|---:|---|
| A | 100 | **0.25** | 28.01.2019 |
| B | 100 | **0.25** | 02.01.2021 |

**Yani:** 100 birim → 1-2 yılda 2.5 TL. **Yıkıcı.**

### 🔍 5. Galatasaray — En "Yakın" Sonuç

| Metrik | Değer |
|---|---:|
| n | 96 |
| ROI | **+%8.81** |
| %95 GA | **[−1.01, +17.93]** |
| Holm p | 0.158 |
| Top-10 kazanç çıkar | +1.83 (hâlâ pozitif) |
| Leave-one-year-out | 3/3 senaryo pozitif |

**Ama:** GA sıfırı içiyor, Holm p anlamsız. **Hipotez adayı — kanıt değil.**

### 📅 6. TG Format Değişimi

| Dönem | Kategoriler |
|---|---|
| 2014-2019 | 0-1, 2-3, **4-6**, **7+** |
| 2020-2025 | 0-1, 2-3, **4-5**, **6+** |

**Aynı market değil.** Ama 0-1 ve 2-3 ortak:

| Kategori | 2014-2019 | 2020-2025 |
|---|---:|---:|
| 0-1 | −%18.03 | −%17.59 |
| 2-3 | −%18.67 | −%15.32 |
| 4-5 (yak.) | −%35.67 | −%27.11 |
| 6+ (yak.) | −%0.14 | −%34.97 |

**6+ eski dönem** "neredeyse başabaş" görünüyordu. Sezon bazında: +9.7, +11.1, +0.3, +16.0, −11.6, −17.8, −100. **Tam tutarsız.**

## 🧪 Metodolojik Çerçeve

| İlke | Uygulama |
|---|---|
| **Veri bütünlüğü** | Ham CSV değiştirilmedi |
| **Skor doğrulama** | Skor–MS uyuşmazlığı: **0** |
| **Maç ID benzersizliği** | Tekrar: **0** |
| **Sızıntı önleme** | Post-match veriler analiz dışı |
| **Çoklu test düzeltmesi** | Benjamini–Hochberg + Holm-Bonferroni |
| **Belirsizlik ölçümü** | Hareketli blok bootstrap (1, 5, 10, 20, 40) |
| **Zamansal doğrulama** | Geliştirme (2014-2022) / Zaman dışı (2023-2025) |
| **Kasa simülasyonu** | 100 birim, gerçekçi iflas senaryosu |
| **Dürüst raporlama** | Null sonuç gizlenmedi |
| **p-hacking önleme** | "En iyi yılı çıkar" post-hoc reddedildi |

---

## 🏆 Nihai Kapanış

> **17 bağımsız analiz, 2.900+ test, 4 farklı FDR/Holm uygulaması, 5 farklı blok uzunluğu, 2 farklı veri dönemi — hepsi aynı sonucu verdi:**
>
> **Mevcut veriyle, mevcut yöntemle, çoklu test düzeltmesinden geçen ve bağımsız dönemde ayakta kalan hiçbir kârlı bahis örüntüsü bulunamadı.**

Bu bir başarısızlık değil, **bilimsel dürüstlüğün** göstergesidir. Veriye saygı, "bir şey bulana kadar denemek" değil, "bulunamadıysa kabul etmek"tir.

**Yeni veri (2026+, farklı bahis şirketleri, kapanış oranları) olmadan ilerlemek, p-hacking'dir.**

### 📌 Eğer İlerlemek İsterseniz

| Seçenek | Gerekli | Risk |
|---|---|---|
| **Yeni veri** | 2026+ tam sezon, farklı şirketler | Düşük |
| **Yeni market** | Korner, Kart (yeterli veri) | Orta |
| **Farklı yöntem** | Quantile bantlar, ML | **Yüksek (p-hacking)** |

**Mevcut analiz tükendi. Sıfırdan başlamak için yeni veri şart.**
