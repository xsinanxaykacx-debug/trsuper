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
