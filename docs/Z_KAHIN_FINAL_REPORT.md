# Z-Kâhin — Nihai Araştırma Raporu

**Durum:** Araştırma kapatıldı; mevcut sonuçlar altında doğrulanmış bahis avantajı bulunamadı.  
**Depo:** https://github.com/xsinanxaykacx-debug/trsuper  
**Son rapor tarihi:** 22 Ekim 2026

---

## 1. Yönetici özeti

Z-Kâhin projesinin amacı, futbol maçları için geçmiş verilerden tahmin üretmenin ötesine geçerek, bu tahminlerin bahis piyasasında maliyetler ve belirsizlik hesaba katıldığında sürdürülebilir bir avantaja dönüşüp dönüşmediğini sınamaktı.

Araştırma boyunca tarihsel maç sonuçları, bahis oranları, takım gücü ve form özellikleri incelendi; makine öğrenmesi modelleri ve birden fazla bahis/kasa yönetimi yaklaşımı test edildi. Mevcut deneylerde **bağımsız doğrulamayla desteklenmiş, genellenebilir ve istatistiksel olarak güvenilir bir kârlı bahis stratejisi doğrulanamadı.**

Bu, projenin başarısız olduğu anlamına gelmez. Araştırmanın önemli çıktısı, tahmin performansı ile bahis kârlılığının farklı problemler olduğunu ortaya koyması ve geçmiş veride görülen olumlu sonuçların tek başına gerçek bir avantaj kanıtı sayılamayacağını göstermesidir.

## 2. Veri ve modelleme yaklaşımı

### Veri

- Araştırmanın erken aşamalarında yaklaşık **180.000 maçlık** tarihsel veri havuzu kullanıldı.
- Depodaki daha sonraki takım/market örüntüsü analizlerinde kullanılan **data/csv/DATA.csv** dosyası ayrı bir veri kesitidir: README'de **7.422 maç ve 353 sütun** olarak belgelenmiştir.
- Bu iki sayı farklı veri kapsamlarını temsil eder; aynı veri dosyasının satır sayıları gibi değerlendirilmemelidir.
- Maç sonuçları, oranlar ve market etiketleri veri kalite kontrollerinden geçirildi. Eksik veya tutarsız değerleri sırf daha iyi sonuç almak için tahminle doldurmak yerine, ilgili analizlerde dışlama ve tutarlılık kontrolleri tercih edildi.

### Özellikler ve modeller

Araştırmanın modelleme hattında aşağıdaki yaklaşım ve özellik aileleri yer aldı:

- **XGBoost** sınıflandırma modeli; hiperparametre araması için **Optuna** kullanıldığı belirtilen deneyler.
- **Elo** tabanlı takım gücü ve iki takım arasındaki güç farkı.
- Son 5 ve 10 maçtan türetilen **form** özellikleri; puan, atılan gol ve yenilen gol gibi göstergeler.
- Dinlenme süresi ve momentum özellikleri.
- Model çıktılarının bahis oranlarıyla birleştirilerek beklenen değer (EV) adaylarının değerlendirilmesi.

Proje konuşmalarında Z-Kâhin'in tahmin kalitesi için **LogLoss 0,68** değeri olumlu bir gösterge olarak raporlandı. Bu raporda, ilgili deneyin tam veri bölümü, hedef değişkeni ve karşılaştırma tablosu tek bir doğrulanabilir metrik kaydı halinde bulunmadığından, 0,68 değeri bağlamından kopuk evrensel performans garantisi olarak yorumlanmamalıdır. LogLoss'un anlamı, hangi test örnekleminde ve hangi kıyas çizgisine karşı ölçüldüğüne bağlıdır.

## 3. Denenen stratejiler ve sonuç

### Value Bet

Model olasılıkları ile piyasanın oranlarından türetilen örtük olasılıklar karşılaştırılarak, tahmini beklenen değeri pozitif görünen seçimler arandı. Modelin bir olasılığı yüksek doğrulukla tahmin etmesi, bu olasılığın piyasa fiyatından sistematik olarak daha iyi olduğu anlamına gelmez.

**Sonuç:** İncelenen kurallar ve tarihsel dönemler kapsamında güvenilir, bağımsız doğrulaması yapılmış bir pozitif EV avantajı ortaya konamadı. Tahmini EV eşiğini geçen bahisler, gerçek EV'nin pozitif olduğunu kendi başına kanıtlamaz; kalibrasyon hatası, oran marjı, veri seçimi ve örneklem belirsizliği bu farkı ortadan kaldırabilir.

### Kelly ve Flat Bet

Sermayeyi bahisler arasında paylaştırmak için Kelly tipi kasa yönetimi ve sabit tutarlı bahis yaklaşımları ele alındı.

- **Flat Bet**, her bahiste benzer tutar riske atarak bahis büyüklüğünün değişkenliğini azaltır; tahminin kendisinde bir avantaj yaratmaz.
- **Kelly**, doğru olasılık ve oran varsayımları altında sermaye büyümesini hedefler. Olasılık tahminleri hatalıysa veya gerçek avantaj yoksa, yüksek bahis büyüklüğü kayıpları büyütebilir.
- Hiçbir kasa yönetimi yöntemi, negatif beklenen değeri pozitif beklenen değere dönüştürmez.

**Sonuç:** Sermaye dağıtım kuralı tek başına kârlılık sağlamadı. Kasa eğrisini yönetmek ile tahmin/piyasa farkından gerçek bir avantaj üretmek birbirinden ayrı konulardır.

### Haftalık Kâr Al (Take Profit)

Haftalık hedefe ulaşıldığında kârı kapatıp kasayı sıfırlama yaklaşımı test edildi. Kaydedilen simülasyonda 87 hafta vardı: 10 hafta kâr alma eşiğine ulaştı, 60 hafta zarar durdurma ile kapandı ve 17 hafta iki eşikten hiçbirine ulaşmadı. Toplam net sonuç **−2.331,38 birim** olarak raporlandı.

**Başarısızlık nedeni:** Kâr alma ve zarar durdurma kuralları sonuçların zamanlamasını değiştirir, ancak bahislerin beklenen değerini otomatik olarak iyileştirmez. Ayrıca eşiğe ulaşmayan haftaları “kasada 100–199 birim kaldı” gibi kesin bir sonuçla eşitlemek doğru değildir; bu haftaların gerçek son kasası ayrı değerlendirilmelidir.

### Zirveyi Takip Et (Trailing Stop)

Model C ile 2018/2019 ve 2019/2020 sezonları tek kronolojik akışta test edildi. Modelin eğitim dönemi 2012/2013–2017/2018 olarak sabitlendi; bahis seçiminde tahmini EV eşiği 0,05, bahis büyüklüğünde kasanın %20'si kullanıldı. Kasa zirvesinden %25 gerileme veya zirve oluşmadan 50 birimin altına düşme durumunda seans kapatıldı.

Kaydedilen simülasyon çıktısı:

| Gösterge | Sonuç |
|---|---:|
| Açılan seans | 473 |
| Zirveden %25 düşüşle kapanan seans | 300 |
| Bu 300 seans içinde kârla kapanan | 95 |
| Kâr etmeyen/başabaş kapanan trailing seansı | 205 |
| 50 birimin altındaki stop-loss kapanışı | 172 |
| Test sonunda açık kalan seans | 1 |
| Görülen en yüksek kasa zirvesi | 1.442,97 birim |
| Pozitif trailing çıkışlarından raporlanan kâr toplamı | +4.385,38 birim |
| Kapanan seansların toplam net sonucu | −9.254,22 birim |
| Son açık seansın kasası | 152,66 birim |
| Son açık seansın net sonucu | +52,66 birim |
| Tüm seans sonuçlarının toplam neti | **−9.201,56 birim** |
| Seans başına 100 birim varsayımıyla toplam sermaye tahsisi | 47.300 birim |
| Tahsisler dâhil hesaplanan toplam değer | 38.098,44 birim |
| Toplam tahsise göre net getiri | yaklaşık **−%19,45** |

**Önemli muhasebe notu:** Her kapanıştan sonra kasanın 100 birime sıfırlanması, simülasyonda yeni bir 100 birimlik sermaye tahsisi varsayar. Dolayısıyla sonuç tek bir 100 birimlik kasanın hiç ek sermaye almadan bileşik büyümesi değildir. Toplam net sonuç, her seansın kendi 100 birimlik başlangıcına göre kâr/zararlarının toplamıdır. Yalnızca pozitif trailing çıkışlarından elde edilen +4.385,38 birim, zarar eden seansları mahsup etmediği için stratejinin genel kârlılık göstergesi olarak kullanılamaz.

**Sonuç:** Zirve takibi bu testte zararı engellemedi. Stop seviyeleri kâr garantisi vermez; özellikle ilk zirve 100 birimin biraz üstündeyse, zirveden %25 gerileme seansı başlangıç sermayesinin altında kapatabilir.

## 4. Bilimsel değerlendirme: marj, EV ve piyasa

Bahis şirketlerinin oranları genellikle **overround** olarak bilinen marjı içerir. Aynı markette oranlardan hesaplanan örtük olasılıkların toplamının 1'i aşması, bahisçinin tüm sonuçlara eşit ve uygun biçimde bahis dağıtması durumunda bile maliyet dezavantajı doğurabilir.

Bununla birlikte, şu iki ifade birbirinden ayrılmalıdır:

1. **Desteklenen sonuç:** Bu projede incelenen veri, dönem ve strateji kuralları altında sürdürülebilir, bağımsız doğrulanmış bir bahis avantajı gösterilemedi; denenen kasa yönetimi yöntemleri bu sorunu çözmedi.
2. **Desteklenmeyen evrensel iddia:** “Piyasa/kumarhane her zaman kazanır” veya “hiçbir model hiçbir koşulda pozitif EV bulamaz” ifadesi, bu deneylerden matematiksel olarak kanıtlanamaz.

Overround, bahis şirketinin fiyatlamasına gömülü yapısal bir dezavantajdır; ancak her bir bahisçinin her bir olası seçiminin matematiksel olarak kesin biçimde negatif EV olduğu sonucunu tek başına vermez. Gerçek bir avantaj iddiası; olasılık kalibrasyonu, doğru ve zamanında oran verisi, işlem koşulları, önceden belirlenmiş hipotezler, çoklu test düzeltmeleri ve bağımsız zaman dışı doğrulamayla desteklenmelidir.

Bu projenin savunulabilir bilimsel hükmü şudur:

> **İncelenen stratejilerde piyasa marjını aşan, tekrarlanabilir ve istatistiksel olarak güvenilir bir avantaj doğrulanamadı. Negatif veya belirsiz sonuçları kasa yönetimiyle kâra çevirmek mümkün olmadı. Bu sonuç, tüm olası stratejilerin sonsuza dek başarısız olacağının evrensel kanıtı değildir.**

## 5. En olumlu çıktı: tahmin ve karar desteği

Z-Kâhin'in değerini yalnızca bahis kârıyla ölçmek doğru değildir. Modelleme hattı; tarihsel veriyi düzenleme, maç öncesi özellik üretme, olasılık tahmini, piyasa oranlarını değerlendirme ve hipotezleri kronolojik test etme yönünde kullanışlı bir analiz altyapısı oluşturdu.

LogLoss 0,68 değeri, kendi deney bağlamında raporlanan olumlu bir tahmin metriğidir; tek başına kârlılık, üstün kalibrasyon veya piyasa üzerinde avantaj kanıtı değildir. Tahmin performansı ve ekonomik sonuç ayrı metriklerle değerlendirilmelidir.

**Nihai ürün konumlandırması:** Z-Kâhin'i bir “garantili bahis makinesi” olarak değil, olasılık tahmini ve araştırma için bir **analiz/karar destek aracı** olarak görmek daha doğrudur. Kullanıcıya belirsizliği görünür kılmak, oran ile model tahmini arasındaki farkı ölçmek ve doğrulanmamış örüntüleri elemek, kendi başına anlamlı bir araştırma çıktısıdır.

## 6. Araştırma sınırları ve gelecekte kullanılacak standart

- Geçmiş dönem testi, canlı ileriye dönük performans garantisi değildir.
- Aynı maçları veya aynı adayları kullanan analizler bağımsız doğrulama sayılmaz.
- Çok sayıda market, oran bandı ve alt grup tarandığında tesadüfen iyi görünen sonuçlar oluşabilir.
- Pozitif nokta ROI tek başına yeterli değildir. Örneklem büyüklüğü, belirsizlik aralığı, kalibrasyon, çoklu karşılaştırma ve bağımsız dönem performansı birlikte ele alınmalıdır.
- Tahmin modeli ve bahis kuralı, doğrulama verisi incelendikten sonra sürekli değiştirilirse test kümesi de fiilen eğitim/keşif verisine dönüşür.
- Gelecekte yeni bir araştırma açılırsa hipotezler ve karar eşikleri sonuçlar görülmeden önce sabitlenmeli; ayrı bir zaman dışı test ve mümkünse canlı ileriye dönük kayıt kullanılmalıdır.

## 7. Kapanış kararı

Araştırma kapsamındaki deneyler sonlandırıldı. Mevcut sonuçlara dayanarak gerçek parayla bahis yapılması için doğrulanmış bir strateji önerilmiyor. Yeni bir test yapılmadıkça eşikleri optimize etmeye veya aynı tarihsel veriden yeni bir “kazanan” strateji çıkarmaya devam etmek, seçim yanlılığı ve aşırı uyum riskini artıracaktır.

**Projenin son dersi:** İyi tahmin yapmak ile kârlı fiyat bulmak aynı şey değildir. Bir modelin ürettiği olasılıklar, piyasanın sunduğu fiyatlara karşı bağımsız ve istatistiksel olarak güvenilir bir avantaj göstermedikçe bahis stratejisi kanıtlanmış sayılmaz.

---

*Bu rapor araştırma sonuçlarının özetidir; finansal tavsiye veya gelecekteki sonuçlara ilişkin garanti değildir.*
