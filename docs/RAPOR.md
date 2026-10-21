# Bahis Oranları Keşif Analizi — Sonuç Raporu

## 1. Yönetici Özeti

**Sonuç:** Mevcut testlerde FDR düzeltmesinden geçen aday bulunmadı.

2019/2020–2022/2023 sezonlarını kapsayan keşif çalışmasında 9 market sütunu tanımlanmıştır. Çalıştırma çıktısına göre 45 oran bandı testi değerlendirilmiş ve hiçbir test Benjamini–Hochberg FDR düzeltmesinden geçmemiştir.

`discovery_survivors.csv` ve `discovery_strong_candidates.csv` dosyaları yalnızca sütun başlıklarını içermektedir.

Bu sonuç, incelenen örneklem ve yöntem kapsamında istatistiksel olarak desteklenen bir bahis avantajı bulunmadığını gösterir. Tüm olası dönemlerde, marketlerde veya yöntemlerde avantajın imkânsız olduğunu göstermez.

## 2. Çalışmanın Kapsamı

**İncelenen sezonlar:** 2019/2020, 2020/2021, 2021/2022, 2022/2023

**Marketler:** MS 1, MS X, MS 2, KG Var, KG Yok, 1.5 Alt, 1.5 Üst, 2.5 Alt, 2.5 Üst

Çalıştırma çıktısında skor ayrıştırma sonrasında 2.503 geçerli maç satırı raporlanmıştır. Market bazındaki kullanılabilir örneklemler oran eksikliği ve geçerlilik filtreleri nedeniyle farklıdır:

| Market grubu | Kullanılabilir maç |
|---|---:|
| MS 1 | 2.503 |
| MS X | 2.503 |
| MS 2 | 2.502 |
| KG Var/Yok | 2.494 |
| 2,5 Alt/Üst | 2.462 |
| 1,5 Alt/Üst | 2.305 |

Market grupları arasındaki farklar, ilgili oranların ve karşı market oranlarının geçerlilik koşullarından kaynaklanır.

## 3. İstatistiksel Sonuçlar

| Ölçüt | Sonuç |
|---|---|
| Raporlanan oran bandı testi | 45 |
| FDR düzeltmesinden geçen test | 0 |
| Güçlü aday dosyasındaki veri satırı | 0 |
| Doğrulanmış kârlı strateji | Bulunmadı |

FDR'den geçen aday olmaması nedeniyle mevcut analizden doğrulanmış bir bahis stratejisi çıkarılamaz.

## 4. En Yüksek Gözlenen ROI

| Ölçüt | Değer |
|---|---|
| Market | KG Var |
| Oran bandı | 1,80–2,00 |
| Örneklem | 148 |
| Kazanma oranı | %55,41 |
| Ortalama oran | 1,8505 |
| ROI | +%2,36 |
| Nominal %95 bootstrap güven aralığı | −%12,57 ile +%17,30 |
| Ham tek yönlü p değeri | 0,3781 |
| BH düzeltilmiş p değeri | 1,0000 |

Bu bantta gözlenen ROI pozitiftir; ancak güven aralığı sıfırın altındaki getirileri de kapsar ve p değeri istatistiksel anlamlılık için yeterli değildir. Dolayısıyla bu bulgu kârlılık kanıtı değildir.

Bu örnek, çok sayıda bant incelendiğinde pozitif görünen sonuçların ortaya çıkabileceğini ve yalnızca en yüksek ROI'ye odaklanmanın yanıltıcı olabileceğini gösterir.

## 5. Yöntemsel Sınırlamalar

### 5.1 Geniş Oran Bantları
Yüksek oranlarda 2,80–4,00, 4,00–5,00 ve daha geniş bantlar kullanılır. Aynı bant içindeki oranlar farklı risk ve getiri profillerine sahip olabilir. Bu nedenle bant ortalaması, bant içindeki her oran seviyesinin performansını ayrı ayrı göstermez.

### 5.2 Karşılıklı Oran Filtresi
KG ve Alt/Üst analizlerinde iki tarafın da oranının geçerli olması şartı örneklemi daraltır. Karşılaştırmayı aynı maç kümesinde tutmaya yardımcı olurken oranı eksik maçların analiz dışında kalmasına neden olur.

### 5.3 Çoklu Karşılaştırmalar
Birden fazla market ve oran bandının test edilmesi tesadüfi pozitif bulgu riskini artırır. Benjamini–Hochberg FDR düzeltmesi uygulanmıştır; mevcut sonuçlarda hiçbir test düzeltmeden geçmemiştir.

### 5.4 Nominal Bootstrap Güven Aralıkları
Raporlanan %95 bootstrap aralıkları her test için nominal aralıklardır. Tüm testleri aynı anda kapsayan eşzamanlı güven aralıkları olarak yorumlanmamalıdır.

### 5.5 Örneklem Dışı Doğrulama
Bu çalışma keşif amaçlıdır. Sonuçların başka sezonlara veya gelecekteki maçlara taşınabildiği gösterilmiş değildir. Gelecekte bir aday bulunursa yeni bir doğrulama dönemi önceden belirlenmeli ve keşif verisinden ayrı tutulmalıdır.

## 6. Nihai Karar

1. Mevcut analizde istatistiksel olarak desteklenen bahis avantajı bulunmadı.
2. Pozitif ROI gösteren tekil bantlar, güven aralıkları ve çoklu test sonuçları dikkate alınmadan strateji olarak kabul edilmemelidir.
3. Ham veri ve analiz kodu bu raporu oluşturmak amacıyla değiştirilmemiştir.
4. Yeni testler yapılacaksa hipotezler ve parametreler sonuçlar incelenmeden önce belirlenmeli; keşif ve doğrulama verileri ayrılmalıdır.

**Nihai ifade:** 2019/2020–2022/2023 keşif döneminde, 9 market ve 45 oran bandı test edildi. Benjamini–Hochberg FDR düzeltmesinden geçen aday bulunmadı. En yüksek gözlenen ROI, KG Var marketinin 1,80–2,00 oran bandında +%2,36 oldu (n=148); ancak nominal %95 bootstrap güven aralığı sıfırı kapsadı ve ham p değeri 0,3781 idi. Dolayısıyla mevcut çalışma, istatistiksel olarak desteklenen bir bahis avantajı ortaya koymamıştır. Bu sonuç, piyasanın bütünüyle verimli olduğunu veya başka koşullarda avantaj bulunamayacağını kanıtlamaz.
