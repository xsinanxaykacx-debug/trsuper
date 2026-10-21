# pattern_discovery_v2 — Keşif Notları ve Nihai Değerlendirme

## Nihai Değerlendirme (2026-10-21)

### Araştırmanın Sonucu

Mevcut `DATA.csv` ve uygulanan analiz yöntemleri kapsamında, bağımsız doğrulamayla desteklenmiş ve genellenebilir kârlı bir bahis örüntüsü bulunamamıştır.

### 16 Pozitif ROI Adayı

- 16 örüntü, tüm veri döneminde pozitif ROI ve en az 60 maç ölçütleriyle seçilmiştir.
- Erken ve geç dönem karşılaştırmasında 13 örüntünün ROI işareti değişmiştir.
- Üç örüntünün iki dönemde de ROI'si pozitiftir; ancak örneklem büyüklükleri ve dönemsel sonuçlar bunları doğrulanmış avantaj olarak sınıflandırmak için yeterli değildir.
- Adaylar tüm dönem verisi incelendikten sonra belirlendiğinden, 2021–2025 bağımsız doğrulama dönemi olarak kullanılamaz.
- Flip oranı (13/16) tek başına istatistiksel anlamlılık veya kârlı avantajın yokluğu için kesin kanıt sayılmamalıdır. Bağımsızlık ve %50 flip varsayımı altında tek yönlü binom p ≈ 0,0106; iki yönlü p ≈ 0,0213. Adaylar tüm dönem verisi incelenerek seçildiği için bu testin varsayımları da doğrudan karşılanmış sayılmaz.

### Çoklu Karşılaştırma

- Önceki `discovery.py` analizinde 45 test için FDR düzeltmesinden geçen aday bulunmamıştır.
- `pattern_discovery_v2` kapsamında raporlanan 534 örüntü için FDR düzeltmesi henüz doğrulanmış değildir. Bu örüntüler hakkında kesin bir survivor sayısı, düzeltme hesaplanmadan belirtilmeyecektir.

### Nihai Karar

Mevcut veri ve mevcut araştırma protokolüyle keşif aşaması kapatılmıştır. Sonuç, tüm olası bahis stratejilerinin kârsız olduğunun kanıtı değil; incelenen yöntemlerle güvenilir bir avantajın gösterilemediğidir.

### Yeniden Başlama Koşulları

1. Yeni veri, mümkünse 2026 sonrası veya bağımsız bir kaynaktan toplanmalıdır.
2. Hipotezler, adaylar, ölçütler ve istatistiksel testler yeni veriye bakılmadan önce sabitlenmelidir.
3. Çoklu karşılaştırma düzeltmesi önceden belirlenmiş protokole göre uygulanmalıdır.
4. Bağımsız doğrulama verisi, keşif ve aday seçimi sırasında kullanılmamalıdır.

### Durum

Mevcut veriyle keşif çalışması kapatıldı. Doğrulanmış kârlı örüntü bulunmadı.

---

## Ek: Önceki Deneylerin Kayıtları

### MIN_SAMPLE Deneyi

`MIN_SAMPLE = 30` filtresi kaldırıldığında 14.929 sezon örüntüsü üretildi; %98,4'ü 30 maçtan az, %90'ı 1–9 maç aralığındaydı. Bu sonuç, düşük örneklemli örüntülerin sayısının çok yüksek olduğunu gösterdi. Filtrenin kaldırılması keşif gürültüsünü artırdığından, genel örüntü raporunda minimum örneklem eşiği korundu.

### Teknik Not: PowerShell Locale Hatası

PowerShell `Export-Csv`, yerel ayarlara bağlı olarak ondalıkları virgülle yazabilir. Bu değerlerin `InvariantCulture` ile yeniden okunması, virgül ondalık ayırıcı olarak yorumlanmadığında hatalı sayılara neden olabilir. Düzeltilmiş dönem karşılaştırması, kaynak Python CSV dosyalarındaki sayıları `InvariantCulture` ile okuyarak oluşturuldu.

İncelenen Python hesaplama mantığında bu inceleme sırasında hata tespit edilmedi. Bu, projenin bütün kodunun kapsamlı biçimde hatasız olduğunun kanıtı değildir.

### Geçerli Referanslar

- `docs/RAPOR.md` — FDR kontrollü 45 test, 0 survivor
- `docs/protocol.md` — analiz protokolü
- `docs/discovery_results.csv` — 45 testin tamamı
