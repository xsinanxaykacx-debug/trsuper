# Maçkolik Bahis Oranları — Örüntü Araştırması

Futbol maçlarında bahis oranları ile sonuçlar arasındaki istatistiksel olarak desteklenebilir örüntüleri arayan bir keşif çalışması.

## 📌 Özet

**Sonuç: Null.** 2019/2020 – 2022/2023 döneminde, 9 market ve 45 oran bandı test edildi. Benjamini–Hochberg FDR düzeltmesinden geçen hiçbir aday bulunmadı. En yüksek gözlenen ROI, KG Var marketinin 1,80–2,00 oran bandında +%2,36 oldu (n=148); ancak bu değer istatistiksel olarak anlamsızdı (ham p=0,3781, BH p=1,0). Ayrıntılar için [`docs/RAPOR.md`](docs/RAPOR.md).

> Bu sonuç, piyasanın bütünüyle verimli olduğunu veya başka koşullarda avantaj bulunamayacağını **kanıtlamaz**. Yalnızca bu veri, dönem, marketler ve yöntemle istatistiksel olarak desteklenen bir bahis avantajı bulunamadığını gösterir.

## 🎯 Projenin Amacı

Bu çalışma, "geçmişte kârlı görünen oranları bulmak" değil, **çoklu test düzeltmesi ve istatistiksel doğrulamadan sonra da ayakta kalan bir örüntü var mı?** sorusuna cevap aramaktır. Amaç, tek bir olumlu ROI sonucunu başarı kabul etmek değil, sahte pozitifleri elemektir.

## 📊 Veri

| Özellik | Değer |
|---|---|
| Kaynak | [Maçkolik arşivi](https://arsiv.mackolik.com) |
| Toplam maç | 7.422 |
| Toplam sütun | 353 |
| Dönem | 2013/2014 – 2025/2026 |
| Keşif dönemi | 2019/2020 – 2022/2023 (2.503 maç) |
| Skor-MS uyuşmazlığı | **0** (doğrulandı) |
| Maç_ID tekrarı | **0** (doğrulandı) |

**Not:** Alt/Üst oranları yalnızca 2019/2020 sezonundan itibaren mevcuttur. Bu nedenle tüm analizler bu ortak pencerede yapılmıştır.

## 🔬 Metodoloji

### Test Edilen Marketler
- Maç Sonucu: 1, X, 2
- Karşılıklı Gol: Var, Yok
- 1,5 Alt/Üst: Alt, Üst
- 2,5 Alt/Üst: Alt, Üst

### Oran Bantları
- Dar bantlar: 1.00 – 2.80 arası 0.20'lik dilimler
- Geniş bantlar: 2.80–4.00, 4.00–5.00, 5.00–7.50, 7.50–10.00, 10.00+

### İstatistiksel Kurallar
- **Minimum örneklem:** n ≥ 100
- **Getiri:** Kazanç = oran − 1, Kayıp = −1
- **Çoklu test düzeltmesi:** Benjamini–Hochberg FDR (α = 0.05)
- **Güven aralığı:** Bootstrap (2.000 iterasyon, nominal %95)
- **Test:** Tek yönlü t-testi (H₁: ROI > 0)

### Karar Zinciri
1. Keşif döneminde FDR'den geçmek (q < 0.05)
2. Bootstrap alt GA > 0
3. Doğrulama döneminde aynı kurallarla test
4. Kilitli testte nihai onay

**Hiçbir aday 1. aşamayı geçemediği için 2, 3 ve 4. aşamalar çalıştırılmadı.**

## 📁 Repo Yapısı


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
