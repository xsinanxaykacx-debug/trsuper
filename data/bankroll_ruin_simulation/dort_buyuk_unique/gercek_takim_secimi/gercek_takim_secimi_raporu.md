# Dört Büyük Takım — Gerçek Seçilen Takım Analizi

- Kaynak: `data\bankroll_ruin_simulation\dort_buyuk_unique\benzersiz_mac_bahis_detay.csv`
- Tarih filtresi: 2023-01-01 ve sonrası
- Strateji: `DUSUK_ORAN_MS1_MS2`
- Bahis birimi: kaynak `Kar_Zarar` sütunundaki birim
- Bootstrap tekrar sayısı: 10,000
- Hareketli blok uzunluğu: 10
- Analize giren dört büyük takım seçimi: 353

## Sonuçlar

         Grup_Turu                   Takim  Bahis_Sayisi  Toplam_Kar  ROI_Yuzde  Bootstrap_CI95_Alt  Bootstrap_CI95_Ust  MDD_Birim  Tek_Yonlu_T_P  Holm_Duzeltilmis_P  Guclu_Kanit
      TAKIM_TOPLAM             Galatasaray            96        8.46     8.8125             -0.1771             17.8961       2.49       0.039472             0.15789        False
       TAKIM_TARAF        Galatasaray - Ev            50        1.34     2.6800             -8.4005             14.3000       3.42       0.335472                 NaN        False
       TAKIM_TARAF Galatasaray - Deplasman            46        7.12    15.4783             -0.6087             30.3049       2.22       0.025931                 NaN        False
      TAKIM_TOPLAM              Fenerbahçe           101       -3.37    -3.3366            -10.7030              3.9901       6.77       0.716319             1.00000        False
       TAKIM_TARAF         Fenerbahçe - Ev            49       -6.47   -13.2041            -23.6939             -3.2852       6.57       0.963227                 NaN        False
       TAKIM_TARAF  Fenerbahçe - Deplasman            52        3.10     5.9615             -7.9615             19.3082       4.49       0.252800                 NaN        False
      TAKIM_TOPLAM                Beşiktaş            88      -17.05   -19.3750            -35.3301             -3.8068      21.69       0.986810             1.00000        False
       TAKIM_TARAF           Beşiktaş - Ev            44       -7.89   -17.9318            -32.5006             -5.5682       9.57       0.950477                 NaN        False
       TAKIM_TARAF    Beşiktaş - Deplasman            44       -9.16   -20.8182            -48.0920              7.0920      13.24       0.933692                 NaN        False
      TAKIM_TOPLAM             Trabzonspor            68        1.13     1.6618             -7.2945             11.3235       3.00       0.431273             1.00000        False
       TAKIM_TARAF        Trabzonspor - Ev            46        1.08     2.3478             -9.5658             13.7826       2.79       0.410703                 NaN        False
       TAKIM_TARAF Trabzonspor - Deplasman            22        0.05     0.2273            -17.7727             18.5909       4.00       0.495640                 NaN        False
DORT_BUYUK_PORTFOY       Dört büyük toplam           353      -10.83    -3.0680             -9.3825              3.4307      20.11       0.804602                 NaN        False

## Değerlendirme

Dört ana takım testinde, %95 blok-bootstrap ROI güven aralığının alt sınırı sıfırın üzerinde olan ve Holm düzeltmeli tek yönlü t-test p değeri 0,05'in altında kalan bir takım yok. Bu veriyle doğrulanmış bir avantaj iddiası desteklenmiyor.

## Yöntem ve sınırlamalar

- Takım, bahis yapılan taraf üzerinden belirlenmiştir: MS1 ev sahibi; MS2 deplasman.
- Geçersiz bahisler, oranı 1 veya daha düşük olanlar ve kâr-zararı eksik satırlar dışarıda bırakılmıştır.
- Güven aralığı kronolojik sıralı kâr-zarar dizisi üzerinde dairesel hareketli blok bootstrap ile hesaplanmıştır.
- Tek yönlü t-test p değerleri zaman bağımlılığını modellemez; bootstrap güven aralığından bağımsız bir kanıt gibi yorumlanmamalıdır.
- Holm düzeltmesi dört takımın ana karşılaştırmasına uygulanmıştır. Ev/deplasman kırılımları keşif amaçlıdır.
- MDD, sıfır başlangıç kârından hesaplanan azami düşüşün bahis birimi cinsinden büyüklüğüdür; yüzde bankroll düşüşü değildir.

## Dosyalar

- Sonuç tablosu: `data\bankroll_ruin_simulation\dort_buyuk_unique\gercek_takim_secimi\gercek_takim_secimi_sonuclari.csv`
- Analize giren bahisler: `data\bankroll_ruin_simulation\dort_buyuk_unique\gercek_takim_secimi\analize_giren_bahisler.csv`