# EPL ana eğitim hattına entegrasyon planı

## Amaç ve kapsam

EPL CSV'sini mevcut veri hattına kontrollü biçimde eklemek. Bu PR yalnızca plan dokümanıdır; `src/run_mvp.py`, model kodları, ham veri ve `archive_v16/` değiştirilmez.

## Mevcut akış

- `src.load.load_data()`: mevcut ana veri kümesini yükler ve `_date`, `_season`, `_y`, oranlar ve `_id` alanlarını hazırlar.
- `src.load_epl.load_epl_data()`: EPL CSV'sini aynı temel şemaya dönüştürür. Loader PR #2 henüz `main` üzerinde yoksa önce merge edilmelidir.
- `src/run_mvp.py`: v1.6'nın sabit 5.854 maçlık referans değerlendirmesini sürdürür. Bu benchmark EPL entegrasyonu nedeniyle sessizce değişmemelidir.

## Önerilen birleştirme akışı

1. Ana veriyi `load_data()` ile yükle.
2. EPL'yi `load_epl_data(epl_csv_path, existing_ids=main_df["_id"])` ile yükle.
3. İki veri kümesinin gerekli sütun ve veri tiplerini doğrula.
4. `pd.concat([main_df, epl_df], ignore_index=True)` ile birleştir.
5. Birleşik tabloda `_id` benzersizliğini, `_y ∈ {H,D,A}` olmasını, skor-sonuç tutarlılığını ve geçerli tarihleri doğrula.
6. `_date` üzerinden kronolojik sırala; özellikleri zaman sızıntısı olmadan yeniden hesapla.
7. Eğitim/validasyon/test ayrımını açıkça yapılandır. Eski v1.6 benchmark'ını ve yeni EPL değerlendirmesini ayrı raporla.

İlk uygulama adımı için birleştirme mantığını doğrudan `run_mvp.py` içine gömmek yerine ayrı bir yardımcı fonksiyon (ör. `src/data.py::load_combined_data`) tercih edilir.

## Önemli tasarım riskleri

### Ligler arası özellik sızıntısı
EPL ve Türkiye ligi arasında doğrudan maç yoktur. Elo, form, dinlenme ve H2H geçmişleri lig kapsamına göre ayrılmalı; aynı takım adı farklı liglerde tek takım kimliği sayılmamalı. Özellik motoru lig anahtarını dikkate almıyorsa birleşik veri üzerinde çalıştırılmadan önce bu konu çözülmeli.

### Zaman sızıntısı
Her maçın özellikleri yalnızca o maçtan önceki sonuçları kullanmalı. Aynı gündeki maçlar için gelecekte oynanan maçın sonucunun daha erken maç özelliklerine girmesini önleyecek grup işleme veya kesin maç sırası kullanılmalı. EPL sezonu Ağustos–Temmuz olarak tanımlanmalı.

### ID ve şema
Mevcut ID'ler korunmalı; EPL'nin negatif ID'leri mevcut tüm `_id` değerleriyle çakışmamalı. Birleştirme sonrasında benzersizlik kontrolü zorunlu olmalı. Tarihler datetime, oranlar sayısal float olmalı.

### Eksik oranlar ve adil metrik
Eksik oranlara yapay değer atanmayacak. Market modeli geçersiz olasılık üretebileceğinden metrikler, karşılaştırılan tüm modellerin geçerli tahmin ürettiği ortak `valid_mask` üzerinde hesaplanmalı. Her model için N ve ortak örneklem N'si raporlanmalı.

### Benchmark disiplini
- Sabit 5.854 maçlık v1.6 referans örneklemi değişmemeli.
- EPL üzerinde ayrıca kronolojik holdout değerlendirmesi yapılmalı.
- Model/Blend ağırlıkları yalnızca validasyon verisiyle seçilmeli; test verisi eşik veya ağırlık ayarı için kullanılmamalı.

## Önerilen API taslağı

```python
def load_combined_data(main_root, epl_csv_path):
    main_df = load_data(main_root)
    epl_df = load_epl_data(epl_csv_path, existing_ids=main_df["_id"])
    # validate_schema(main_df, epl_df)
    combined = pd.concat([main_df, epl_df], ignore_index=True)
    # validate_unique_ids_targets_and_scores(combined)
    return combined.sort_values(["_date", "_id"]).reset_index(drop=True)
```

Bu yalnızca taslaktır; bu PR'da uygulanabilir kod olarak eklenmiyor.

## Kabul kriterleri

- [ ] EPL loader PR #2 `main` dalına merge edilmiş olmalı.
- [ ] Ham CSV ve `archive_v16/` değişmeden kalmalı.
- [ ] Gerekli şema ve veri tipleri doğrulanmalı.
- [ ] `_id` benzersiz, hedef değerleri yalnızca H/D/A ve skorlarla tutarlı olmalı.
- [ ] Özellikler kronolojik ve sızıntısız hesaplanmalı; lig geçmişleri karışmamalı.
- [ ] Eksik oranlar açıkça ele alınmalı; karşılaştırmalar ortak geçerli örneklemde yapılmalı.
- [ ] 5.854 maçlık referans benchmark aynı maç ID'leriyle korunmalı.
- [ ] Sentetik EPL testleri ve mevcut test paketi çalıştırılmalı.
- [ ] Rapor; satır sayısı, tarih aralığı, sezon/sonuç dağılımı ve oran kapsamasını göstermeli.

## Bu PR kapsamı dışında

EPL verisini indirmek, CSV'yi depoya eklemek, eğitim kodunu değiştirmek veya `archive_v16/` dosyalarını yeniden üretmek.
