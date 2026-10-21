# DATA.csv — Veri Kalitesi Denetim Raporu

- **Toplam satır:** 7422
- **Toplam sütun:** 353
- **Kaynak dosya:** data/csv/DATA.csv

## 1. Lig ve Sezon Sınıflandırması

- Sezonu belirlenemeyen satır sayısı: **0**
- Tespit edilen benzersiz lig sayısı: **10**
- Tespit edilen benzersiz sezon sayısı: **13**

## 2. Skor ve Sonuç (MS) Tutarlılığı

- **Skoru ayrıştırılabilen satır sayısı:** 7422
- **MS değeri geçerli (1/X/2) olan satır sayısı:** 7422
- **MS değeri eksik olan satır sayısı:** 0
- **Geçersiz MS değerine sahip satır sayısı:** **0**
- **Skor ve MS karşılaştırması yapılabilen maç sayısı:** 7422
- **Skor ile MS sütunu uyuşmayan maç sayısı:** **0**

**Skor kategorileri (birbirini dışlayan):**
- Skoru boş olan satır sayısı: 0
- İptal/ertelenen/hükmen ifadesi içeren skor sayısı: 0
- Tanınmayan/geçersiz formattaki skor sayısı: 0

## 3. Oran Sütunları ve Doluluk

- **Tespit edilen market/oran sütunu sayısı:** 296
- Sütun seçimi: adında | karakteri bulunan ve İSTATİSTİK/ISTATISTIK ile başlamayan sütunlar.

### Tüm market/oran sütunlarının doluluğu

| Sütun | Eksik | Dolu | Eksik % |
|---|---:|---:|---:|
| Maç_Sonucu_|_1 | 0 | 7422 | %0.00 |
| Maç_Sonucu_|_X | 0 | 7422 | %0.00 |
| Maç_Sonucu_|_2 | 20 | 7402 | %0.27 |
| Handikap_|_H1 | 4099 | 3323 | %55.23 |
| Handikap_|_HX | 4099 | 3323 | %55.23 |
| Handikap_|_H2 | 4099 | 3323 | %55.23 |
| IY_1,5_Gol_|_Alt | 4099 | 3323 | %55.23 |
| IY_1,5_Gol_|_Üst | 4099 | 3323 | %55.23 |
| AÜ_1,5_Gol_|_Alt | 4153 | 3269 | %55.96 |
| AÜ_1,5_Gol_|_Üst | 4156 | 3266 | %56.00 |
| AÜ_2,5_Gol_|_Alt | 4097 | 3325 | %55.20 |
| AÜ_2,5_Gol_|_Üst | 4097 | 3325 | %55.20 |
| AÜ_3,5_Gol_|_Alt | 4099 | 3323 | %55.23 |
| AÜ_3,5_Gol_|_Üst | 4099 | 3323 | %55.23 |
| Karşılıklı_Gol_|_Var | 74 | 7348 | %1.00 |
| Karşılıklı_Gol_|_Yok | 74 | 7348 | %1.00 |
| İlk_Yarı_Sonucu_|_İY_1 | 4099 | 3323 | %55.23 |
| İlk_Yarı_Sonucu_|_İY_0 | 4100 | 3322 | %55.24 |
| İlk_Yarı_Sonucu_|_İY_2 | 4099 | 3323 | %55.23 |
| Çifte_Şans_|_1-2 | 754 | 6668 | %10.16 |
| Çifte_Şans_|_X-2 | 357 | 7065 | %4.81 |
| Toplam_Gol_|_0-1 | 4099 | 3323 | %55.23 |
| Toplam_Gol_|_2-3 | 4099 | 3323 | %55.23 |
| Toplam_Gol_|_4-6 | 4099 | 3323 | %55.23 |
| Toplam_Gol_|_7+ | 4099 | 3323 | %55.23 |
| Çifte_Şans_|_1-X | 1304 | 6118 | %17.57 |
| Maç_Sonucu_|_1_-2h | 7384 | 38 | %99.49 |
| Maç_Sonucu_|_2_+2h | 7384 | 38 | %99.49 |
| Maç_Sonucu_|_1_+2h | 7421 | 1 | %99.99 |
| Maç_Sonucu_|_2_-2h | 7421 | 1 | %99.99 |
| Maç_Sonucu_|_1_-1h | 7422 | 0 | %100.00 |
| Maç_Sonucu_|_2_+1h | 7422 | 0 | %100.00 |
| Maç_Sonucu_|_1_+1h | 7422 | 0 | %100.00 |
| Maç_Sonucu_|_2_-1h | 7422 | 0 | %100.00 |
| İlk_Yarı_/_Maç_Sonucu_|_1/1 | 7158 | 264 | %96.44 |
| İlk_Yarı_/_Maç_Sonucu_|_1/X | 7159 | 263 | %96.46 |
| İlk_Yarı_/_Maç_Sonucu_|_1/2 | 7158 | 264 | %96.44 |
| İlk_Yarı_/_Maç_Sonucu_|_X/1 | 7158 | 264 | %96.44 |
| İlk_Yarı_/_Maç_Sonucu_|_X/X | 7159 | 263 | %96.46 |
| İlk_Yarı_/_Maç_Sonucu_|_X/2 | 7158 | 264 | %96.44 |
| İlk_Yarı_/_Maç_Sonucu_|_2/1 | 7158 | 264 | %96.44 |
| İlk_Yarı_/_Maç_Sonucu_|_2/X | 7159 | 263 | %96.46 |
| İlk_Yarı_/_Maç_Sonucu_|_2/2 | 7158 | 264 | %96.44 |
| Maç_Skoru_|_1:0 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_2:0 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_2:1 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_3:0 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_3:1 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_3:2 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_4:0 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_4:1 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_4:2 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_4:3 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_5+:0 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_5+:1 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_5+:2 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_5+:3 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_5+:4 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_0:0 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_1:1 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_2:2 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_3:3 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_4:4 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_5+:5+ | 7285 | 137 | %98.15 |
| Maç_Skoru_|_0:1 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_0:2 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_1:2 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_0:3 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_1:3 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_2:3 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_0:4 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_1:4 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_2:4 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_3:4 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_0:+5 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_1:+5 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_2:+5 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_3:+5 | 7285 | 137 | %98.15 |
| Maç_Skoru_|_4:+5 | 7285 | 137 | %98.15 |
| Handikaplı_Maç_Sonucu_(0:2)_|_1 | 4506 | 2916 | %60.71 |
| Handikaplı_Maç_Sonucu_(0:2)_|_X | 4506 | 2916 | %60.71 |
| Handikaplı_Maç_Sonucu_(0:2)_|_2 | 5036 | 2386 | %67.85 |
| Handikaplı_Maç_Sonucu_(0:1)_|_1 | 3479 | 3943 | %46.87 |
| Handikaplı_Maç_Sonucu_(0:1)_|_X | 3479 | 3943 | %46.87 |
| Handikaplı_Maç_Sonucu_(0:1)_|_2 | 3609 | 3813 | %48.63 |
| Handikaplı_Maç_Sonucu_(1:0)_|_1 | 4088 | 3334 | %55.08 |
| Handikaplı_Maç_Sonucu_(1:0)_|_X | 3594 | 3828 | %48.42 |
| Handikaplı_Maç_Sonucu_(1:0)_|_2 | 3594 | 3828 | %48.42 |
| İlk_Yarı/Maç_Sonucu_|_1/1 | 3451 | 3971 | %46.50 |
| İlk_Yarı/Maç_Sonucu_|_1/X | 3451 | 3971 | %46.50 |
| İlk_Yarı/Maç_Sonucu_|_1/2 | 3451 | 3971 | %46.50 |
| İlk_Yarı/Maç_Sonucu_|_X/1 | 3451 | 3971 | %46.50 |
| İlk_Yarı/Maç_Sonucu_|_X/X | 3451 | 3971 | %46.50 |
| İlk_Yarı/Maç_Sonucu_|_X/2 | 3451 | 3971 | %46.50 |
| İlk_Yarı/Maç_Sonucu_|_2/1 | 3451 | 3971 | %46.50 |
| İlk_Yarı/Maç_Sonucu_|_2/X | 3451 | 3971 | %46.50 |
| İlk_Yarı/Maç_Sonucu_|_2/2 | 3451 | 3971 | %46.50 |
| Maç_Sonucu_ve_(1,5)_Alt/Üst_|_1_ve_Alt | 3472 | 3950 | %46.78 |
| Maç_Sonucu_ve_(1,5)_Alt/Üst_|_X_ve_Alt | 3472 | 3950 | %46.78 |
| Maç_Sonucu_ve_(1,5)_Alt/Üst_|_2_ve_Alt | 3472 | 3950 | %46.78 |
| Maç_Sonucu_ve_(1,5)_Alt/Üst_|_1_ve_Üst | 3472 | 3950 | %46.78 |
| Maç_Sonucu_ve_(1,5)_Alt/Üst_|_X_ve_Üst | 3472 | 3950 | %46.78 |
| Maç_Sonucu_ve_(1,5)_Alt/Üst_|_2_ve_Üst | 3472 | 3950 | %46.78 |
| Maç_Sonucu_ve_(2,5)_Alt/Üst_|_1_ve_Alt | 3441 | 3981 | %46.36 |
| Maç_Sonucu_ve_(2,5)_Alt/Üst_|_X_ve_Alt | 3441 | 3981 | %46.36 |
| Maç_Sonucu_ve_(2,5)_Alt/Üst_|_2_ve_Alt | 3441 | 3981 | %46.36 |
| Maç_Sonucu_ve_(2,5)_Alt/Üst_|_1_ve_Üst | 3441 | 3981 | %46.36 |
| Maç_Sonucu_ve_(2,5)_Alt/Üst_|_X_ve_Üst | 3441 | 3981 | %46.36 |
| Maç_Sonucu_ve_(2,5)_Alt/Üst_|_2_ve_Üst | 3441 | 3981 | %46.36 |
| Maç_Sonucu_ve_(3,5)_Alt/Üst_|_1_ve_Alt | 3491 | 3931 | %47.04 |
| Maç_Sonucu_ve_(3,5)_Alt/Üst_|_X_ve_Alt | 3491 | 3931 | %47.04 |
| Maç_Sonucu_ve_(3,5)_Alt/Üst_|_2_ve_Alt | 3491 | 3931 | %47.04 |
| Maç_Sonucu_ve_(3,5)_Alt/Üst_|_1_ve_Üst | 3491 | 3931 | %47.04 |
| Maç_Sonucu_ve_(3,5)_Alt/Üst_|_X_ve_Üst | 3491 | 3931 | %47.04 |
| Maç_Sonucu_ve_(3,5)_Alt/Üst_|_2_ve_Üst | 3491 | 3931 | %47.04 |
| Maç_Sonucu_ve_(4,5)_Alt/Üst_|_1_ve_Alt | 3588 | 3834 | %48.34 |
| Maç_Sonucu_ve_(4,5)_Alt/Üst_|_X_ve_Alt | 3588 | 3834 | %48.34 |
| Maç_Sonucu_ve_(4,5)_Alt/Üst_|_2_ve_Alt | 3588 | 3834 | %48.34 |
| Maç_Sonucu_ve_(4,5)_Alt/Üst_|_1_ve_Üst | 3588 | 3834 | %48.34 |
| Maç_Sonucu_ve_(4,5)_Alt/Üst_|_X_ve_Üst | 3588 | 3834 | %48.34 |
| Maç_Sonucu_ve_(4,5)_Alt/Üst_|_2_ve_Üst | 3588 | 3834 | %48.34 |
| İlk_Gol_|_1 | 3438 | 3984 | %46.32 |
| İlk_Gol_|_Olmaz | 3438 | 3984 | %46.32 |
| İlk_Gol_|_2 | 3439 | 3983 | %46.34 |
| 1,5_Alt/Üst_|_Alt | 3545 | 3877 | %47.76 |
| 1,5_Alt/Üst_|_Üst | 3727 | 3695 | %50.22 |
| 2,5_Alt/Üst_|_Alt | 3406 | 4016 | %45.89 |
| 2,5_Alt/Üst_|_Üst | 3406 | 4016 | %45.89 |
| 3,5_Alt/Üst_|_Alt | 3420 | 4002 | %46.08 |
| 3,5_Alt/Üst_|_Üst | 3418 | 4004 | %46.05 |
| 4,5_Alt/Üst_|_Alt | 5331 | 2091 | %71.83 |
| 4,5_Alt/Üst_|_Üst | 3724 | 3698 | %50.18 |
| Toplam_Gol_Aralığı_|_0-1_Gol | 3439 | 3983 | %46.34 |
| Toplam_Gol_Aralığı_|_2-3_Gol | 3439 | 3983 | %46.34 |
| Toplam_Gol_Aralığı_|_4-5_Gol | 3439 | 3983 | %46.34 |
| Toplam_Gol_Aralığı_|_6+_Gol | 3439 | 3983 | %46.34 |
| 1._Yarı_Sonucu_|_1 | 3388 | 4034 | %45.65 |
| 1._Yarı_Sonucu_|_X | 3388 | 4034 | %45.65 |
| 1._Yarı_Sonucu_|_2 | 3389 | 4033 | %45.66 |
| 1._Yarı_Çifte_Şans_|_1-X | 3968 | 3454 | %53.46 |
| 1._Yarı_Çifte_Şans_|_1-2 | 3521 | 3901 | %47.44 |
| 1._Yarı_Çifte_Şans_|_X-2 | 3632 | 3790 | %48.94 |
| 2._Yarı_Sonucu_|_1 | 3417 | 4005 | %46.04 |
| 2._Yarı_Sonucu_|_X | 3417 | 4005 | %46.04 |
| 2._Yarı_Sonucu_|_2 | 3418 | 4004 | %46.05 |
| 1._Yarı_0,5_Alt/Üst_|_Alt | 3492 | 3930 | %47.05 |
| 1._Yarı_0,5_Alt/Üst_|_Üst | 3494 | 3928 | %47.08 |
| 1._Yarı_1,5_Alt/Üst_|_Alt | 3395 | 4027 | %45.74 |
| 1._Yarı_1,5_Alt/Üst_|_Üst | 3394 | 4028 | %45.73 |
| 1._Yarı_2,5_Alt/Üst_|_Alt | 5910 | 1512 | %79.63 |
| 1._Yarı_2,5_Alt/Üst_|_Üst | 3715 | 3707 | %50.05 |
| Evsahibi_1,5_Alt/Üst_|_Alt | 3755 | 3667 | %50.59 |
| Evsahibi_1,5_Alt/Üst_|_Üst | 3745 | 3677 | %50.46 |
| Deplasman_1,5_Alt/Üst_|_Alt | 4073 | 3349 | %54.88 |
| Deplasman_1,5_Alt/Üst_|_Üst | 4022 | 3400 | %54.19 |
| Tek/Çift_|_Tek | 3407 | 4015 | %45.90 |
| Tek/Çift_|_Çift | 3407 | 4015 | %45.90 |
| Maç_Skoru_|_1-0 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_2-0 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_2-1 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_3-0 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_3-1 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_3-2 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_4-0 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_4-1 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_4-2 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_5-0 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_5-1 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_6-0 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_0-0 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_1-1 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_2-2 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_3-3 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_0-1 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_0-2 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_1-2 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_0-3 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_1-3 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_2-3 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_0-4 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_1-4 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_2-4 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_0-5 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_1-5 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_0-6 | 3761 | 3661 | %50.67 |
| Maç_Skoru_|_Diğer | 3761 | 3661 | %50.67 |
| Evsahibi_Gol_Yemeden_Kazanır_|_Evet | 7277 | 145 | %98.05 |
| Evsahibi_Gol_Yemeden_Kazanır_|_Hayır | 7281 | 141 | %98.10 |
| Deplasman_Gol_Yemeden_Kazanır_|_Evet | 7280 | 142 | %98.09 |
| Gol_Atacak_Takımlar_|_Yalnız_1 | 5484 | 1938 | %73.89 |
| Gol_Atacak_Takımlar_|_Yalnız_2 | 5484 | 1938 | %73.89 |
| Gol_Atacak_Takımlar_|_Her_İkisi | 5484 | 1938 | %73.89 |
| Gol_Atacak_Takımlar_|_Hiçbiri | 5484 | 1938 | %73.89 |
| Daha_Çok_Gol_Olacak_Yarı_|_1.Y | 3445 | 3977 | %46.42 |
| Daha_Çok_Gol_Olacak_Yarı_|_Eşit | 3445 | 3977 | %46.42 |
| Daha_Çok_Gol_Olacak_Yarı_|_2.Y | 3445 | 3977 | %46.42 |
| Evsahibi_Gol_Yemez_|_Evet | 6037 | 1385 | %81.34 |
| Evsahibi_Gol_Yemez_|_Hayır | 6051 | 1371 | %81.53 |
| Deplasman_Gol_Yemez_|_Evet | 6039 | 1383 | %81.37 |
| Deplasman_Gol_Yemez_|_Hayır | 6092 | 1330 | %82.08 |
| Handikaplı_Maç_Sonucu_(2:0)_|_1 | 6345 | 1077 | %85.49 |
| Handikaplı_Maç_Sonucu_(2:0)_|_X | 5869 | 1553 | %79.08 |
| Handikaplı_Maç_Sonucu_(2:0)_|_2 | 5869 | 1553 | %79.08 |
| Evsahibi_0,5_Alt/Üst_|_Alt | 5187 | 2235 | %69.89 |
| Evsahibi_0,5_Alt/Üst_|_Üst | 5547 | 1875 | %74.74 |
| Deplasman_Gol_Yemeden_Kazanır_|_Hayır | 7308 | 114 | %98.46 |
| 0,5_Alt/Üst_|_Alt | 4036 | 3386 | %54.38 |
| 0,5_Alt/Üst_|_Üst | 7269 | 153 | %97.94 |
| 5,5_Alt/Üst_|_Üst | 6630 | 792 | %89.33 |
| Deplasman_0,5_Alt/Üst_|_Alt | 4704 | 2718 | %63.38 |
| Deplasman_0,5_Alt/Üst_|_Üst | 4822 | 2600 | %64.97 |
| 5,5_Alt/Üst_|_Alt | 7214 | 208 | %97.20 |
| Evsahibi_2,5_Alt/Üst_|_Alt | 5900 | 1522 | %79.49 |
| Evsahibi_2,5_Alt/Üst_|_Üst | 5043 | 2379 | %67.95 |
| (8,5)_Korner_Alt/Üst_|_Alt | 6149 | 1273 | %82.85 |
| (8,5)_Korner_Alt/Üst_|_Üst | 6149 | 1273 | %82.85 |
| (9,5)_Korner_Alt/Üst_|_Alt | 5903 | 1519 | %79.53 |
| (9,5)_Korner_Alt/Üst_|_Üst | 5903 | 1519 | %79.53 |
| (10,5)_Korner_Alt/Üst_|_Alt | 6195 | 1227 | %83.47 |
| (10,5)_Korner_Alt/Üst_|_Üst | 6195 | 1227 | %83.47 |
| 1.Yarı_(4,5)_Korner_Alt/Üst_|_Alt | 5863 | 1559 | %78.99 |
| 1.Yarı_(4,5)_Korner_Alt/Üst_|_Üst | 5863 | 1559 | %78.99 |
| 1.Yarı_(5,5)_Korner_Alt/Üst_|_Alt | 6702 | 720 | %90.30 |
| 1.Yarı_(5,5)_Korner_Alt/Üst_|_Üst | 6702 | 720 | %90.30 |
| En_Çok_Korner_|_1 | 5880 | 1542 | %79.22 |
| En_Çok_Korner_|_X | 5840 | 1582 | %78.68 |
| En_Çok_Korner_|_2 | 5840 | 1582 | %78.68 |
| 1._Yarı_En_Çok_Korner_|_1 | 5843 | 1579 | %78.73 |
| 1._Yarı_En_Çok_Korner_|_X | 5842 | 1580 | %78.71 |
| 1._Yarı_En_Çok_Korner_|_2 | 5842 | 1580 | %78.71 |
| İlk_Korner_|_1 | 5845 | 1577 | %78.75 |
| İlk_Korner_|_Olmaz | 5845 | 1577 | %78.75 |
| İlk_Korner_|_2 | 5845 | 1577 | %78.75 |
| (11,5)_Korner_Alt/Üst_|_Alt | 7351 | 71 | %99.04 |
| (11,5)_Korner_Alt/Üst_|_Üst | 7351 | 71 | %99.04 |
| 1.Yarı_(3,5)_Korner_Alt/Üst_|_Alt | 7010 | 412 | %94.45 |
| 1.Yarı_(3,5)_Korner_Alt/Üst_|_Üst | 7010 | 412 | %94.45 |
| (5,5)_Kart_Alt/Üst_|_Alt | 7195 | 227 | %96.94 |
| (5,5)_Kart_Alt/Üst_|_Üst | 7194 | 228 | %96.93 |
| (6,5)_Kart_Alt/Üst_|_Alt | 7340 | 82 | %98.90 |
| (6,5)_Kart_Alt/Üst_|_Üst | 7339 | 83 | %98.88 |
| (7,5)_Kart_Alt/Üst_|_Alt | 7378 | 44 | %99.41 |
| (7,5)_Kart_Alt/Üst_|_Üst | 7378 | 44 | %99.41 |
| Kırmızı_Kart_|_Var | 7083 | 339 | %95.43 |
| Kırmızı_Kart_|_Yok | 7083 | 339 | %95.43 |
| Deplasman_2,5_Alt/Üst_|_Alt | 6826 | 596 | %91.97 |
| Deplasman_2,5_Alt/Üst_|_Üst | 5190 | 2232 | %69.93 |
| (7,5)_Korner_Alt/Üst_|_Alt | 7328 | 94 | %98.73 |
| (7,5)_Korner_Alt/Üst_|_Üst | 7328 | 94 | %98.73 |
| Toplam_Korner_Aralığı_|_0-8 | 5909 | 1513 | %79.61 |
| Toplam_Korner_Aralığı_|_9-11 | 5909 | 1513 | %79.61 |
| Toplam_Korner_Aralığı_|_12+ | 5909 | 1513 | %79.61 |
| 1._Yarı_Korner_Aralığı_|_0-4 | 5908 | 1514 | %79.60 |
| 1._Yarı_Korner_Aralığı_|_5-6 | 5908 | 1514 | %79.60 |
| 1._Yarı_Korner_Aralığı_|_7+ | 5908 | 1514 | %79.60 |
| (8,5)_Kart_Alt/Üst_|_Alt | 7408 | 14 | %99.81 |
| (8,5)_Kart_Alt/Üst_|_Üst | 7407 | 15 | %99.80 |
| Evsahibi_3,5_Alt/Üst_|_Alt | 7236 | 186 | %97.49 |
| Evsahibi_3,5_Alt/Üst_|_Üst | 7218 | 204 | %97.25 |
| (4,5)_Kart_Alt/Üst_|_Alt | 7097 | 325 | %95.62 |
| (4,5)_Kart_Alt/Üst_|_Üst | 7097 | 325 | %95.62 |
| 1.Yarı_(6,5)_Korner_Alt/Üst_|_Alt | 7396 | 26 | %99.65 |
| 1.Yarı_(6,5)_Korner_Alt/Üst_|_Üst | 7396 | 26 | %99.65 |
| (12,5)_Korner_Alt/Üst_|_Alt | 7420 | 2 | %99.97 |
| (12,5)_Korner_Alt/Üst_|_Üst | 7420 | 2 | %99.97 |
| (3,5)_Kart_Alt/Üst_|_Alt | 7265 | 157 | %97.88 |
| (3,5)_Kart_Alt/Üst_|_Üst | 7265 | 157 | %97.88 |
| (2,5)_Kart_Alt/Üst_|_Alt | 7420 | 2 | %99.97 |
| (2,5)_Kart_Alt/Üst_|_Üst | 7420 | 2 | %99.97 |
| Handikaplı_Maç_Sonucu_(0:3)_|_1 | 7296 | 126 | %98.30 |
| Handikaplı_Maç_Sonucu_(0:3)_|_X | 7296 | 126 | %98.30 |
| Handikaplı_Maç_Sonucu_(0:3)_|_2 | 7296 | 126 | %98.30 |
| Handikaplı_Maç_Sonucu_(3:0)_|_1 | 7401 | 21 | %99.72 |
| Handikaplı_Maç_Sonucu_(3:0)_|_X | 7401 | 21 | %99.72 |
| Handikaplı_Maç_Sonucu_(3:0)_|_2 | 7401 | 21 | %99.72 |
| Deplasman_3,5_Alt/Üst_|_Alt | 7364 | 58 | %99.22 |
| Deplasman_3,5_Alt/Üst_|_Üst | 7355 | 67 | %99.10 |
| Evsahibi_4,5_Alt/Üst_|_Alt | 7418 | 4 | %99.95 |
| Evsahibi_4,5_Alt/Üst_|_Üst | 7418 | 4 | %99.95 |
| Korner_Tek/Çift_|_Tek | 6821 | 601 | %91.90 |
| Korner_Tek/Çift_|_Çift | 6821 | 601 | %91.90 |
| Handikaplı_Maç_Sonucu_(0:4)_|_1 | 7422 | 0 | %100.00 |
| Handikaplı_Maç_Sonucu_(0:4)_|_X | 7422 | 0 | %100.00 |
| Handikaplı_Maç_Sonucu_(0:4)_|_2 | 7422 | 0 | %100.00 |
| 6,5_Alt/Üst_|_Alt | 7422 | 0 | %100.00 |
| 6,5_Alt/Üst_|_Üst | 7422 | 0 | %100.00 |
| (9,5)_Kart_Alt/Üst_|_Alt | 7420 | 2 | %99.97 |
| (9,5)_Kart_Alt/Üst_|_Üst | 7420 | 2 | %99.97 |
| 1.Yarı_(2,5)_Korner_Alt/Üst_|_Alt | 7421 | 1 | %99.99 |
| 1.Yarı_(2,5)_Korner_Alt/Üst_|_Üst | 7421 | 1 | %99.99 |
| Maç_Sonucu_(Uzt._Dahil)_|_1 | 7422 | 0 | %100.00 |
| Maç_Sonucu_(Uzt._Dahil)_|_2 | 7422 | 0 | %100.00 |
| Evsahibi_İki_Yarıda_da_Gol_|_Atar | 7259 | 163 | %97.80 |
| Deplasman_İki_Yarıda_da_Gol_|_Atar | 7259 | 163 | %97.80 |
| Deplasman_İki_Yarıda_da_Gol_|_Atamaz | 7331 | 91 | %98.77 |
| Evsahibi_İki_Yarıda_da_Gol_|_Atamaz | 7283 | 139 | %98.13 |

> **Kapsam notu:** Bu rapor yapısal ön denetimdir. Oranların sayısal olup olmadığı, 0/1.00 gibi geçersiz değerler ve uç değerler ayrıca denetlenmemiştir.
> **Veri güvenliği:** Kaynak CSV salt okunur kullanılır; bu betik ham veriyi değiştirmez.
