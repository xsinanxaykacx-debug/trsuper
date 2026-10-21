# Maçkolik Örüntü Taraması — Analiz Protokolü

**Durum:** Keşif tamamlandı (null sonuç)
**Tarih:** 2026-10-21

## 1. Amaç ve Kapsam
Bu çalışma, futbol maçlarında oran aralıklarına göre sabit birim bahis getirisini keşif amacıyla incelemek için hazırlanmıştır. Amaç, gözlenen getiriyi kârlılık kanıtı olarak kabul etmek değil, istatistiksel olarak desteklenebilecek adayları belirlemektir.

- **Analiz betiği:** discovery.py
- **Girdi verisi:** data/csv/DATA.csv
- **Keşif dönemi:** 2019/2020, 2020/2021, 2021/2022, 2022/2023

## 2. İncelenen Marketler
- Maç Sonucu: 1, X, 2
- Karşılıklı Gol: Var, Yok
- 1,5 Alt/Üst: Alt, Üst
- 2,5 Alt/Üst: Alt, Üst

Betikte tanımlı bir market sütunu veri dosyasında bulunmuyorsa ilgili market atlanır.

## 3. Skor ve Kazanma Koşulları
Maç skorları ev ve deplasman gol sayıları olarak ayrıştırılır. Ayrıştırılamayan skorlar analiz dışı bırakılır.

- MS 1: Ev sahibi golü > deplasman golü
- MS X: Ev sahibi golü = deplasman golü
- MS 2: Ev sahibi golü < deplasman golü
- KG Var: Her iki takım da en az bir gol atar
- KG Yok: Takımlardan en az biri gol atamaz
- Üst: Toplam gol sayısı > gol çizgisi
- Alt: Toplam gol sayısı < gol çizgisi

1,5 ve 2,5 çizgileri tam sayı gol toplamlarında eşitlik oluşturmadığından Alt/Üst koşulları birbirini tamamlar.

## 4. Oran Geçerliliği
Bahis oranının sonlu bir sayısal değer olması ve 1,00'dan büyük olması gerekir. Eksik, geçersiz, sonsuz veya 1,00 ve altındaki oranlar kullanılmaz.

Alt/Üst ve KG Var/Yok marketlerinde, karşı market oranının da mevcut ve geçerli olması zorunlu tutulur. Bu bir kod hatası değil, araştırma tasarımı tercihidir. Bununla birlikte karşı tarafın oranı eksik olan maçlar ilgili market analizinden çıkarılır.

## 5. Oran Bantları
Bantlar alt sınır dahil, üst sınır hariç olacak şekilde oluşturulur.

- 1,00–2,80 arasında çoğunlukla 0,20 genişliğinde bantlar
- 2,80–4,00 (genişlik 1,20)
- 4,00–5,00 (genişlik 1,00)
- 5,00–7,50 ve 7,50–10,00 (genişlik 2,50)
- 10,00 ve üzeri açık uçlu son bant

Bu bantlar eşit genişlikte değildir. Yüksek oranlı bantlar farklı oran seviyelerini aynı grupta birleştirir. Bu durum yerel örüntüleri gizleyebilir ve tek bir banttan elde edilen ROI'nin daha dar bir oran aralığına genellenmesini engeller.

Bir bantta yeterli örneklem bulunmaması, o bantın test sonuçlarına alınmamasına neden olabilir. Bantlar, sonuçlara bakılarak sonradan değiştirilmemelidir.

## 6. Getiri Hesabı
Her bahis için bir birim sabit bahis varsayılır.

- Kazanan bahis net getirisi: oran − 1
- Kaybeden bahis net getirisi: −1

ROI, bahis başına ortalama net getiri olarak hesaplanır. Bu değer komisyon, vergi, limit, oran kayması ve diğer uygulama maliyetlerini içerdiği ayrıca modellenmediği sürece gerçek hayatta elde edilecek net kâr garantisi değildir.

## 7. İstatistiksel Değerlendirme
Her test edilen oran bandı için örneklem büyüklüğü, kazanma oranı, ortalama oran, ROI, nominal %95 bootstrap güven aralığı ve tek yönlü tek örneklem t-testinin p değeri raporlanır.

- Minimum örneklem eşiği: betikte tanımlı MIN_SAMPLE_SIZE
- Bootstrap tekrar sayısı: betikte tanımlı BOOTSTRAP_ITERATIONS
- Çoklu karşılaştırma düzeltmesi: Benjamini–Hochberg FDR
- Alternatif hipotez: ortalama net getirinin sıfırdan büyük olması

Bootstrap güven aralıkları nominaldir; bütün bantlar için eşzamanlı güven aralığı değildir. FDR düzeltmesi çoklu testlerin yanlış keşif riskini kontrol etmeye yardımcı olur ancak veri kalitesi, örneklem seçimi veya modelleme kaynaklı tüm belirsizlikleri ortadan kaldırmaz.

Pozitif ROI tek başına yeterli değildir. Ham p değerinin küçük olması da çoklu test düzeltmesi ve etki büyüklüğü değerlendirilmeden kârlılık iddiasına dayanak oluşturmaz.

## 8. Veri Bütünlüğü ve Yeniden Üretilebilirlik
Ham veri değiştirilmez. Temizleme, skor ayrıştırma ve oran filtreleri analiz betiği içinde uygulanır.

Raporlanan sonuçlar, ilgili betik sürümü, girdi dosyası ve parametrelerle ilişkilendirilmelidir. Veri veya parametreler değişirse yeni çalışma ayrı bir sürüm olarak kaydedilmelidir.

## 9. Yorumlama İlkesi
Bir adayın bulunamaması, incelenen koşullarda istatistiksel olarak desteklenen bir avantaj gösterilemediği anlamına gelir. Hiçbir koşulda avantaj bulunamayacağını kanıtlamaz.

Bir adayın bulunması da tek başına gerçek, sürdürülebilir veya geleceğe taşınabilir kârlılık kanıtı değildir. Bunun için önceden belirlenmiş yöntemle ayrı doğrulama ve örneklem dışı test gerekir.
