# Maçkolik Bahis Oranları — Örüntü Araştırması

Bu depo, futbol maçlarının geçmiş sonuçları ve bahis oranları arasında **istatistiksel olarak desteklenebilir, bağımsız veride de ayakta kalan bir örüntü bulunup bulunmadığını** araştırır. Amaç yalnızca geçmişte kârlı görünen grupları bulmak değil; tesadüf, aşırı uyum ve çoklu test kaynaklı sahte sonuçları ayırt etmektir.

## İçindekiler

- [🎯 Yönetici Özeti](#-yönetici-özeti)
- [📋 Araştırma Zaman Çizelgesi — 17 Test/Araştırma Akışı](#-araştırma-zaman-çizelgesi--17-testaraştırma-akışı)
- [🔬 Öne Çıkan Bulgular](#-öne-çıkan-bulgular)
  - [🚨 Kazanma oranı ≠ kârlılık](#-kazanma-oranı--kârlılık)
  - [🎲 MS2 bootstrap = yazı tura](#-ms2-bootstrap--yazı-tura)
  - [🌊 Yüksek oran zamanla kötüleşiyor](#-yüksek-oran-zamanla-kötüleşiyor)
  - [💀 Kasa simülasyonu yıkım](#-kasa-simülasyonu-yıkım)
  - [🔍 Galatasaray en yakın sonuç](#-galatasaray-en-yakın-sonuç)
  - [📅 TG format değişimi](#-tg-format-değişimi)
- [🧪 Metodolojik Çerçeve](#-metodolojik-çerçeve)
- [📊 Vaka Çalışması: Favoriye Bahis](#-vaka-çalışması-favoriye-bahis-stratejisi)
- [Araştırmanın güncel sonucu](#araştırmanın-güncel-sonucu)
- [Veri](#veri)
- [Mevcut araştırmalar ve raporlar](#mevcut-araştırmalar-ve-raporlar)
- [Sorumlu yorumlama](#sorumlu-yorumlama)
- [🏆 Nihai Kapanış](#-nihai-kapanış)

## 🎯 Yönetici Özeti

Bu depo, Maçkolik tarihsel maç sonuçları ve oran verilerinde tekrarlanabilir bir bahis avantajı bulunup bulunmadığını araştırır. Şu ana kadarki testlerde **bağımsız doğrulamayla desteklenmiş, genellenebilir ve istatistiksel olarak güvenilir bir kârlı strateji bulunmadı.**

| Ana gösterge | Bulgular |
|---|---|
| Araştırma akışları | 17 test/analiz başlığı; bunlar 17 bağımsız deney veya bağımsız örneklem anlamına gelmez |
| Örüntü keşfi v2 | En az 30 maç içeren 534 örüntü incelendi; 16 aday tüm dönem ROI'si ve örneklem eşiğiyle öne çıktı |
| Erken/geç dönem istikrarı | 16 adayın 13'ünde ROI işareti değişti; aday seçimi tüm dönem verisine baktığı için bu kör doğrulama değildir |
| Önceki 45 testlik çalışma | Benjamini–Hochberg FDR düzeltmesinden geçen aday: 0 |
| TG 4 kategori testi | 137 adaydan FDR q < 0,05 koşulunu sağlayan: 0 |
| MS2 düşük oran bootstrap kontrolü | ROI yaklaşık +%0,07; %95 aralık sıfırı içeriyor |
| Yüksek oran stratejileri, 2023–2025 | Strateji A ROI −%45,26; Strateji B ROI −%37,12; iki aralığın da üst sınırı sıfırın altında |
| Doğrulanmış kârlı strateji | 0 |

**Karar:** Mevcut sonuçlar gerçek parayla uygulanması önerilebilecek doğrulanmış bir avantaj göstermiyor. Bu, her olası stratejinin kârsız olduğunun evrensel kanıtı değildir; yalnızca incelenen veri, filtreler ve yöntemlerle avantaj doğrulanamadı.

## 📋 Araştırma Zaman Çizelgesi — 17 Test

Bu tablo, depoda izlenen 17 test/analiz akışını özetler. Akışların bazıları aynı maçları, dönemleri veya adayları yeniden kullanır; **17 başlık, 17 bağımsız deney veya 17 bağımsız doğrulama örneklemi demek değildir.**

| # | Analiz | Test/örneklem kapsamı | Düzeltme / yöntem | Sonuç |
|---:|---|---:|---|---|
| 1 | İlk 1X2 + KG + 2,5 Alt/Üst taraması | 45 test | Benjamini–Hochberg FDR | Geçen aday: 0 |
| 2 | pattern_discovery_v2 örüntü taraması | 534 örüntü | Dönem karşılaştırması | 16 aday öne çıktı; 13/16 adayda ROI işareti dönemler arasında değişti |
| 3 | Spesifik oran × gün kombinasyonları | 2.161 test | Keşifsel; tam çoklu-test düzeltmesi yok | Dönem kararlılığı zayıf; bağımsız doğrulama değildir |
| 4 | Toplam Gol (TG) 4 kategori | 137 aday | Benjamini–Hochberg FDR | Geçen aday: 0 |
| 5 | TG birleşik analiz | 8 aday/test | FDR | Geçen aday: 0 |
| 6 | TG blok duyarlılık | 32 senaryo (4 blok uzunluğu × testler) | Hareketli blok bootstrap | Güven aralıkları sıfırı içerdi; avantaj doğrulanmadı |
| 7 | Dört büyük takım — favori stratejisi | 4 takım; 16 adet 100 maçlık seri | Sabit bahis, seri analizi | 3/16 seri pozitif |
| 8 | Dört büyük takım — MS banko/kasa | 4 takım | 100 birim başlangıç, sabit 1 birim | Dört takımın tarihsel ROI'si negatif; 2025'e kadar kasa tükenmedi |
| 9 | Yüksek oran A/B | 2 strateji | Bootstrap güven aralığı | Genel ROI ve güven aralıkları negatif |
| 10 | Takım bazlı ileri test | 4 takım | Holm düzeltmesi | Düzeltilmiş anlamlı sonuç: 0 |
| 11 | Takım seçimi düzeltmesi | 12 karşılaştırma | Holm düzeltmesi | Galatasaray'ın görünen artısı güven aralığıyla doğrulanmadı |
| 12 | Galatasaray leave-one-year-out | 7 senaryo | Duyarlılık kontrolü | Sonuç seçilen dönemlere duyarlı; doğrulama değil |
| 13 | Galatasaray kâr yoğunlaşması | En yüksek kazançların etkisi | Yoğunlaşma kontrolü | En iyi kazançları çıkarınca sonuç belirgin değişiyor |
| 14 | Yüksek oran kırılımı | Yıl × oran × market | Alt grup analizi | Küçük alt gruplar keşifsel; doğrulanmış pozitif grup yok |
| 15 | Yüksek oran kronolojik doğrulaması | 2014–2022 / 2023–2025 | Zaman sıralı tarihsel test | Her iki strateji de zaman dışı dönemde kötüleşti |
| 16 | MS2 eksik oran denetimi | 7.422 maç; 20 boş MS2 | Veri kalite kontrolü | Eksik oranlar raporlandı; tahminle doldurulmadı |
| 17 | Skor/MS/maç ID veri kalite kontrolleri | 7.422 satırlık ana CSV | Tutarlılık ve benzersizlik kontrolleri | Mevcut raporda uyuşmazlık/tekrar bildirilmedi |

Ayrıntılar için ilgili bölüm ve raporlara bakın. Bu tablo bir yönetim özeti niteliğindedir; her satırın bağımsız bir veri kümesi kullandığı veya aynı düzeyde kanıt ürettiği anlamına gelmez.

## 🔬 Öne Çıkan Bulgular

### 🚨 Kazanma oranı ≠ kârlılık

| Takım | Kazanma oranı | ROI |
|---|---:|---:|
| Galatasaray | %64,88 | −%6,88 |
| Beşiktaş | %59,76 | −%8,96 |
| Fenerbahçe | %60,44 | −%14,81 |
| Trabzonspor | %51,33 | −%15,23 |

Favori oranları düşük olduğunda birkaç kayıp, çok sayıda kazancın getirisini silebilir. Başarı; kazanma yüzdesiyle değil, oranlar, net kâr/zarar ve yatırılan toplam tutara göre ROI ile ölçülmelidir.

### 🎲 MS2 bootstrap = yazı tura

Düşük oranlı MS2 alt grubunda 2023 sonrası 378 bahis için nokta ROI'si yaklaşık **+%0,07** idi. Hareketli blok uzunluğu 1, 10, 20 ve 40 için %95 güven aralıklarının tümü sıfırı içerdi; bootstrap tekrarlarının pozitif sonuç veren oranı yaklaşık %50–52 aralığındaydı. Bu, pozitif avantaj kanıtı değil, yazı-tura benzeri belirsizliktir. Başka bir MS2 kasa simülasyonunda 555 bahis ve −%17,89 ROI görülmüştür; bunlar farklı analizlerdir.

| Blok uzunluğu | ROI %95 güven aralığı | Pozitif bootstrap oranı |
|---:|---:|---:|
| 1 | −%11,27 – +%11,24 | %50,95 |
| 10 | −%8,90 – +%8,80 | %50,28 |
| 20 | −%9,32 – +%8,79 | %50,48 |
| 40 | −%9,85 – +%8,38 | %52,36 |

### 🌊 Yüksek oran zamanla kötüleşiyor

| Strateji | Geliştirme 2014–2022 | Zaman dışı tarihsel test 2023–2025 | Test dönemi %95 bootstrap aralığı |
|---|---:|---:|---:|
| A — Favorinin tersi MS1/MS2 | −%28,70 | −%45,26 | −%61,23 – −%28,68 |
| B — MS1/MSX/MS2 içinden en yüksek oran | −%17,47 | −%37,12 | −%54,27 – −%19,14 |

İki stratejinin de zaman dışı tarihsel testte ROI'si kötüleşti ve güven aralığının üst sınırı sıfırın altında kaldı. Bu test geçmişte ayrılmış bir dönemdir; canlı ileriye dönük deney değildir.

### 💀 Kasa simülasyonu yıkım

| Strateji | Başlangıç kasası | Simülasyonda oynanan bahis | Son kasa | Kasa duruş tarihi |
|---|---:|---:|---:|---|
| A — Favorinin tersi | 100 birim | 372 | 0,25 birim | 28.01.2019 |
| B — En yüksek MS1/MSX/MS2 oranı | 100 birim | 530 | 0,25 birim | 02.01.2021 |

Bu sonuçlar, sabit 1 birim bahisle geçmiş maçların kronolojik olarak oynandığı varsayımına dayanır. Dört büyük takımın düşük oranlı favori simülasyonu ayrı bir çalışmadır; o simülasyonda 2025'e kadar kasa tükenmedi, ancak dört takımın da toplam ROI'si negatifti.

### 🔍 Galatasaray en yakın sonuç

Bir takım seçimi/çoklu karşılaştırma analizinde Galatasaray için n=96 ve nokta ROI +%8,81 raporlandı; %95 güven aralığı −%1,01 ile +%17,93 arasındaydı ve Holm p değeri 0,158 idi. En yüksek 10 kazancın etkisi ve yıllar arası duyarlılık ayrıca incelendi; bu sonuç doğrulanmış avantaj değildir.

Ayrı takım bazlı ileri testte Galatasaray 100 bahis için +%4,46 ROI gösterdi; %95 güven aralığı −%5,91 ile +%14,86, Holm-düzeltilmiş p değeri 0,8007 idi. İki sonuç farklı analizlere aittir; hiçbiri “Galatasaray'a bahis yap” önerisi olarak yorumlanmamalıdır.

### 📅 TG format değişimi

Toplam Gol (TG) sonuç kategorilerinin adlandırması/dönem kapsamı değişmiş görünüyor; dönemleri eşleştirmeden kategorileri doğrudan kıyaslamak hatalı olabilir:

| Dönem | TG kategorileri |
|---|---|
| 2014–2019 | 0–1, 2–3, 4–6, 7+ |
| 2020–2025 | 0–1, 2–3, 4–5, 6+ |

2014–2019 dönemindeki oran/sonuç analizinde 0–1 ROI −%18,03; 2–3 −%18,67; 4–6 −%24,23; 7+ −%70,46 olarak raporlandı. 137 adayın hiçbirinde FDR q < 0,05 koşulu sağlanmadı. Geç dönem kategorileri farklı olduğundan 4–6 ile 4–5 veya 7+ ile 6+ doğrudan eşdeğer kabul edilmemelidir.

Ayrı bir veri şeması sorunu olarak 2,5 Alt/Üst sütunları da dönemsel olarak değişiyor: eski AÜ_2,5_Gol sütunlarında geçerli oranlar 11.01.2014–26.08.2019, yeni 2,5_Alt/Üst sütunlarında ise 30.08.2019–28.12.2025 aralığında bulunuyor. İki sütun grubunun aynı maçta birlikte dolu olduğu kayıt sayısı 0; bu seriler kaynak ve anlam eşdeğerliği doğrulanmadan birleştirilmemelidir.

## 🧪 Metodolojik Çerçeve

| İlke | Uygulama ve sınır |
|---|---|
| Veri bütünlüğü | Ham CSV sonuçları iyileştirmek için değiştirilmez; eksik oranlar tahminle doldurulmaz. |
| Skor ve kimlik kontrolleri | Skor–market tutarlılığı ve tekrar eden maç kimlikleri ayrı denetlenir; sonuçlar yalnızca ilgili veri sürümü için geçerlidir. |
| Sabit bahis | Rapor farklı bir kural belirtmedikçe geçerli her bahis için 1 birim. |
| ROI | Toplam net kâr/zarar ÷ toplam bahis tutarı. Kazanma oranı tek başına yeterli değildir. |
| Belirsizlik | Uygun analizlerde %95 güven aralığı ve bootstrap duyarlılığı kullanılır; aralık sıfırı içeriyorsa pozitif getiri doğrulanmış sayılmaz. |
| Çoklu karşılaştırma | Uygun çalışmalarda Benjamini–Hochberg FDR veya Holm düzeltmesi kullanılır. Bir analizdeki düzeltme başka analizlere otomatik olarak uygulanmış sayılmaz. |
| Bootstrap sınırı | Gerçekleşmiş kâr/zararı yeniden örnekleyerek belirsizliği inceler; aday seçimi yanlılığını ortadan kaldırmaz ve gelecek kârını garanti etmez. |
| Kronolojik test | 2014–2022 geliştirme ve 2023–2025 zaman dışı tarihsel dönem ayrımı, canlı ileriye dönük testle aynı değildir. |
| Bağımsızlık | Aynı maçları, dönemi veya adayları kullanan raporlar bağımsız doğrulama olarak sayılmaz. |
| Dürüst raporlama | Negatif ve belirsiz sonuçlar da raporlanır; pozitif nokta ROI tek başına strateji kanıtı değildir. |
| Seçim yanlılığı | Çok sayıda gruptan en iyi görüneni sonradan seçmek p-hacking riskini artırır. |

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

### MS1 / MSX / MS2 Haftanın Günü Araştırması

- Yeni analiz betiği: `analiz_haftanin_gunu_ms1x2.py`
- Sonuç klasörü: `data/pattern_discovery_ms1x2/`
- Marketler: MS1 (ev sahibi), MSX (beraberlik), MS2 (deplasman).
- Tarama: lig, haftanın günü, market ve 0,10 genişliğinde oran bandı; 1,00 dahil, 5,00 hariç.
- Asgari örneklem: örüntü başına 30 maç; aday incelemesinde en az 60 maç.
- Raporlar: market kapsamı, haftanın gününe göre genel performans, test edilen örüntüler, adaylar ve sezon ayrıntıları.
- Çoklu testler için Benjamini–Hochberg FDR düzeltmesi uygulanır. Aday koşulları pozitif ROI, ROI için yaklaşık %95 güven aralığının alt sınırının sıfırın üzerinde olması, FDR q < 0,05 ve erken/geç dönemlerde yeterli örneklemle pozitif ROI gerektirir.

**Çalıştırma:** depo kök dizininde `python analiz_haftanin_gunu_ms1x2.py`.

**Önemli sınırlama:** 2014–2019 ve 2020–2025 dönemleri yalnızca istikrarı inceleyen tanısal dönemlerdir; bu dönem karşılaştırması bağımsız kör doğrulama değildir. 2020–2025 verisi önceki keşiflerde de incelendiği için out-of-sample doğrulama olarak sunulmaz. Betik keşif amaçlıdır; aday çıkması bile gelecekte kâr veya bahis avantajı garantisi vermez.

### MS2 oranı eksik kayıtlar

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

### Dört Büyük Takım — MS Favorisi ve Kasa Simülasyonu

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

### 2026–2027 İçin 100 Birimlik Kasa İleri Testi

Düşük MS1/MS2 oranını seçen stratejinin Galatasaray seçimi ve dört büyük takım birleşik portföyü için tarihsel sonuçları, 100 bahislik aritmetik senaryo ve 2026–2027 ileriye dönük test protokolü ayrı raporda yer alır.

- [100 birim kasa ve ileriye dönük test raporu](data/bankroll_ruin_simulation/dort_buyuk_unique/gercek_takim_secimi/2026_2027_100_birim_ileri_test.md)

**Önemli:** Galatasaray örneklemindeki +%8,81 tarihsel ROI'nin yaklaşık %95 belirsizlik aralığı sıfırı içerir. 108,81 birim, bu tarihsel nokta ROI'sinin 100 bahiste aynen tekrarlandığı varsayımına dayanan aritmetik senaryodur; kâr beklentisi veya garanti değildir. Dört büyük takımın birleşik örnekleminde tarihsel ROI -%3,07'dir. 2026–2027 sonuçları önceden sabitlenmiş kuralla ileriye dönük test edilmelidir.

### Dört Büyük Takım — Yüksek Oran Stratejileri

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

## Mevcut araştırmalar ve raporlar

### Haftanın Günü Bazlı 2,5 Alt/Üst ve KG Var/Yok Araştırmaları

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

### Depodaki Ek Araştırma Dosyaları

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

## Sorumlu yorumlama

Bu depo istatistiksel araştırma amaçlıdır; bahis tavsiyesi veya kâr garantisi sunmaz. Geçmiş performans gelecekteki sonuçları garanti etmez. “Avantaj bulunamadı” ifadesi, incelenen veri ve yöntemlerle yeterli kanıt elde edilemediği anlamına gelir; tüm olası stratejiler hakkında evrensel bir hüküm değildir.

## 🏆 Nihai Kapanış

> **17 analiz/test akışı ve çok sayıda örüntü taraması sonucunda, mevcut veriyle bağımsız doğrulamayla desteklenmiş kârlı bir bahis avantajı gösterilemedi.**

MS2 bootstrap sonuçları sıfır etrafında belirsiz; yüksek oran stratejileri 2023–2025 tarihsel testinde daha kötü performans gösterdi; TG kategori ve 2,5 Alt/Üst sütunlarının dönemsel şema farkları dikkate alınmalı. Bu bulgular tüm olası stratejilerin kârsız olduğunu kanıtlamaz, ancak mevcut stratejilerin kârlı olduğu iddiasını da desteklemez.

Yeni bir çalışma başlatılırsa hipotez, veri aralığı, aday seçme kuralı, örneklem eşiği ve istatistiksel testler sonuçlar görülmeden önce sabitlenmeli; doğrulama için keşifte kullanılmamış veri ayrılmalıdır.

**Bu depo araştırma ve yöntem denetimi içindir; bahis tavsiyesi, kazanç garantisi veya gelecekteki sonuçların tahmini değildir.**
