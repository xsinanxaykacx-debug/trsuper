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
