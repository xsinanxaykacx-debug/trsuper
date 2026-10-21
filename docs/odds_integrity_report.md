# Oran Kalitesi ve Maç Bütünlüğü Denetim Raporu
- **Toplam Satır:** 7422
- **Toplam Sütun:** 353

## 1. Maç Kimliği ve Tekrar Kontrolü
- **Maç_ID Sütunu:** Mevcut
- Tekrar eden Maç_ID sayısı: **0**
- Eksik Maç_ID sayısı: **0**
- Birebir aynı olan (tüm sütunları kopya) satır sayısı: **0**

## 2. Oran Sütunlarının Sayısal Doğrulaması
- Toplam `|` içeren sütun sayısı: 296
- **Gerçekten sayısal olan oran sütunu sayısı:** 296
- Tüm oran sütunları başarıyla sayıya dönüştürüldü (Sayısal olmayan metin yok).

## 3. Geçersiz ve Mantıksız Oran Değerleri
| Sütun | 0 Değeri | <= 1.00 | 150+ | 1000+ |
|---|---:|---:|---:|---:|
| `Maç_Skoru_|_5+:4` | 0 | 0 | 22 | 0 |
| `Maç_Skoru_|_4:+5` | 0 | 0 | 74 | 0 |
| `İlk_Yarı/Maç_Sonucu_|_1/2` | 0 | 0 | 1 | 0 |
| `İlk_Yarı/Maç_Sonucu_|_2/1` | 0 | 0 | 1 | 0 |
| `Maç_Sonucu_ve_(4,5)_Alt/Üst_|_1_ve_Üst` | 0 | 0 | 1 | 0 |
| `Maç_Sonucu_ve_(4,5)_Alt/Üst_|_X_ve_Üst` | 0 | 0 | 6 | 0 |
| `Maç_Sonucu_ve_(4,5)_Alt/Üst_|_2_ve_Üst` | 0 | 0 | 1 | 0 |
| `Maç_Skoru_|_2-0` | 0 | 0 | 2 | 0 |
| `Maç_Skoru_|_3-0` | 0 | 0 | 14 | 0 |
| `Maç_Skoru_|_3-1` | 0 | 0 | 4 | 0 |
| `Maç_Skoru_|_3-2` | 0 | 0 | 4 | 0 |
| `Maç_Skoru_|_4-0` | 0 | 0 | 196 | 0 |
| `Maç_Skoru_|_4-1` | 0 | 0 | 82 | 0 |
| `Maç_Skoru_|_4-2` | 0 | 0 | 133 | 0 |
| `Maç_Skoru_|_5-0` | 0 | 0 | 764 | 0 |
| `Maç_Skoru_|_5-1` | 0 | 0 | 690 | 0 |
| `Maç_Skoru_|_6-0` | 0 | 0 | 1153 | 0 |
| `Maç_Skoru_|_3-3` | 0 | 0 | 21 | 0 |
| `Maç_Skoru_|_0-2` | 0 | 0 | 1 | 0 |
| `Maç_Skoru_|_0-3` | 0 | 0 | 75 | 0 |
| `Maç_Skoru_|_1-3` | 0 | 0 | 14 | 0 |
| `Maç_Skoru_|_2-3` | 0 | 0 | 6 | 0 |
| `Maç_Skoru_|_0-4` | 0 | 0 | 567 | 0 |
| `Maç_Skoru_|_1-4` | 0 | 0 | 333 | 0 |
| `Maç_Skoru_|_2-4` | 0 | 0 | 467 | 0 |
| `Maç_Skoru_|_0-5` | 0 | 0 | 1101 | 0 |
| `Maç_Skoru_|_1-5` | 0 | 0 | 1045 | 0 |
| `Maç_Skoru_|_0-6` | 0 | 0 | 1277 | 0 |
| `İlk_Korner_|_Olmaz` | 0 | 0 | 9 | 0 |

## 4. Karşılıklı Market Eksiklikleri (Alt/Üst Farkları)
| Market Çifti | Sadece 1. Taraf Dolu | Sadece 2. Taraf Dolu | Her İkisi Boş | Her İkisi Dolu |
|---|---:|---:|---:|---:|
| `1,5_Alt/Üst vs Alt` | 182 | 0 | 3545 | 3695 |
| `2,5_Alt/Üst vs Alt` | 0 | 0 | 3406 | 4016 |
| `3,5_Alt/Üst vs Alt` | 0 | 2 | 3418 | 4002 |
| `4,5_Alt/Üst vs Alt` | 0 | 1607 | 3724 | 2091 |
| `1._Yarı_2,5_Alt/Üst vs Alt` | 0 | 2195 | 3715 | 1512 |
| `Karşılıklı_Gol vs Var` | 0 | 0 | 74 | 7348 |

> **Yorum:** Eğer "Sadece 1. Taraf Dolu" veya "Sadece 2. Taraf Dolu" sayıları yüksekse, veri kaynağında ciddi bir asimetri (tek taraflı eksiklik) vardır. Bu durum analizde yanlılığa yol açar.
