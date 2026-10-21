# Yüksek Oran Stratejileri — Kronolojik Dönem Dışı Doğrulama

## Önceden tanımlanan dönem ayrımı

- Geliştirme/keşif dönemi: 2014–2022.
- Zaman dışı kontrol dönemi: 2023–2025.
- Bu ayrım, mevcut strateji kuralını değiştirmeden geçmişin daha sonraki yıllarında performansın tekrarlanıp tekrarlanmadığını inceler.
- Bu test gerçek anlamda geleceğe dönük canlı bahis testi değildir; aynı tarihsel veri içinde kronolojik kontrol olarak değerlendirilmelidir.
- %95 aralık, kâr/zarar dizisine blok uzunluğu 5 olan 20.000 tekrarlı hareketli blok bootstrap ile hesaplanmıştır. Kısa dönem ve az bahisli alt gruplarda aralıklar belirsizdir.

## Dönem sonuçları

                    Strateji                     Donem  Bahis_Sayisi  Kazandi  Kaybetti  Kazanma_Orani_%  Ortalama_Oran  Toplam_Kar_Zarar      ROI_%  ROI_Bootstrap_%95_Alt  ROI_Bootstrap_%95_Ust
   A_Favorinin_Tersi_MS1_MS2      GELISTIRME_2014_2022           768      172       596        22.395833       3.352187           -220.42 -28.700521             -38.204460             -19.081576
   A_Favorinin_Tersi_MS1_MS2 ZAMAN_DISI_TEST_2023_2025           217       38       179        17.511521       3.492673            -98.21 -45.258065             -61.226152             -28.681797
B_MS1_MSX_MS2_En_Yuksek_Oran      GELISTIRME_2014_2022           743      179       564        24.091521       3.558264           -129.82 -17.472409             -28.041790              -6.944684
B_MS1_MSX_MS2_En_Yuksek_Oran ZAMAN_DISI_TEST_2023_2025           215       40       175        18.604651       3.678698            -79.81 -37.120930             -54.265116             -19.144186

## 2023–2025 dönem dışı kontrolü

                    Strateji                     Donem  Bahis_Sayisi  Kazandi  Kaybetti  Kazanma_Orani_%  Ortalama_Oran  Toplam_Kar_Zarar      ROI_%  ROI_Bootstrap_%95_Alt  ROI_Bootstrap_%95_Ust
   A_Favorinin_Tersi_MS1_MS2 ZAMAN_DISI_TEST_2023_2025           217       38       179        17.511521       3.492673            -98.21 -45.258065             -61.226152             -28.681797
B_MS1_MSX_MS2_En_Yuksek_Oran ZAMAN_DISI_TEST_2023_2025           215       40       175        18.604651       3.678698            -79.81 -37.120930             -54.265116             -19.144186

## Market × oran aralığı × dönem

                    Strateji                     Donem Secilen_Market Oran_Araligi  Bahis_Sayisi  Kazandi  Kaybetti  Kazanma_Orani_%  Ortalama_Oran  Toplam_Kar_Zarar       ROI_%  ROI_Bootstrap_%95_Alt  ROI_Bootstrap_%95_Ust                               Orneklem_Notu
   A_Favorinin_Tersi_MS1_MS2      GELISTIRME_2014_2022              1    2,00-2,49            47       17        30        36.170213       2.384255             -6.38  -13.574468             -39.255851              12.234043 N<100: keşifsel, bağımsız doğrulama gerekir
   A_Favorinin_Tersi_MS1_MS2      GELISTIRME_2014_2022              1    2,50-2,99           114       27        87        23.684211       2.725175            -40.00  -35.087719             -56.359649             -12.760965  N>=100: yine de dönem dışı tekrar aranmalı
   A_Favorinin_Tersi_MS1_MS2      GELISTIRME_2014_2022              1    3,00-3,49           105       26        79        24.761905       3.180286            -21.72  -20.685714             -44.762381               3.600476  N>=100: yine de dönem dışı tekrar aranmalı
   A_Favorinin_Tersi_MS1_MS2      GELISTIRME_2014_2022              1    3,50-3,99            79       13        66        16.455696       3.671519            -31.06  -39.316456             -71.898734              -5.708228 N<100: keşifsel, bağımsız doğrulama gerekir
   A_Favorinin_Tersi_MS1_MS2      GELISTIRME_2014_2022              1    4,00-4,99            76       17        59        22.368421       4.307895             -1.05   -1.381579             -40.394737              38.488487 N<100: keşifsel, bağımsız doğrulama gerekir
   A_Favorinin_Tersi_MS1_MS2      GELISTIRME_2014_2022              2    2,00-2,49            44       18        26        40.909091       2.389773             -0.73   -1.659091             -39.931818              36.681818 N<100: keşifsel, bağımsız doğrulama gerekir
   A_Favorinin_Tersi_MS1_MS2      GELISTIRME_2014_2022              2    2,50-2,99            72       19        53        26.388889       2.703472            -20.18  -28.027778             -50.972222              -4.485417 N<100: keşifsel, bağımsız doğrulama gerekir
   A_Favorinin_Tersi_MS1_MS2      GELISTIRME_2014_2022              2    3,00-3,49            66       15        51        22.727273       3.190455            -18.10  -27.424242             -57.121212               3.409091 N<100: keşifsel, bağımsız doğrulama gerekir
   A_Favorinin_Tersi_MS1_MS2      GELISTIRME_2014_2022              2    3,50-3,99            49        5        44        10.204082       3.734898            -30.80  -62.857143             -92.551020             -32.448980 N<100: keşifsel, bağımsız doğrulama gerekir
   A_Favorinin_Tersi_MS1_MS2      GELISTIRME_2014_2022              2    4,00-4,99           116       15       101        12.931034       4.370603            -50.40  -43.448276             -65.991379             -19.008621  N>=100: yine de dönem dışı tekrar aranmalı
   A_Favorinin_Tersi_MS1_MS2 ZAMAN_DISI_TEST_2023_2025              1    2,00-2,49            13        2        11        15.384615       2.403846             -8.24  -63.384615            -100.000000              -8.538462                             N<30: yorumlama
   A_Favorinin_Tersi_MS1_MS2 ZAMAN_DISI_TEST_2023_2025              1    2,50-2,99            36       10        26        27.777778       2.748889             -9.02  -25.055556             -55.194444               4.861111 N<100: keşifsel, bağımsız doğrulama gerekir
   A_Favorinin_Tersi_MS1_MS2 ZAMAN_DISI_TEST_2023_2025              1    3,00-3,49            14        5         9        35.714286       3.187857              1.52   10.857143             -56.428571              78.285714                             N<30: yorumlama
   A_Favorinin_Tersi_MS1_MS2 ZAMAN_DISI_TEST_2023_2025              1    3,50-3,99            24        1        23         4.166667       3.752917            -20.36  -84.833333            -100.000000             -54.500000                             N<30: yorumlama
   A_Favorinin_Tersi_MS1_MS2 ZAMAN_DISI_TEST_2023_2025              1    4,00-4,99            30        1        29         3.333333       4.458000            -25.43  -84.766667            -100.000000             -54.300000 N<100: keşifsel, bağımsız doğrulama gerekir
   A_Favorinin_Tersi_MS1_MS2 ZAMAN_DISI_TEST_2023_2025              2    2,00-2,49             9        3         6        33.333333       2.401111             -1.78  -19.777778             -74.000000              33.000000                             N<30: yorumlama
   A_Favorinin_Tersi_MS1_MS2 ZAMAN_DISI_TEST_2023_2025              2    2,50-2,99            21        6        15        28.571429       2.690476             -4.26  -20.285714             -73.285714              32.428571                             N<30: yorumlama
   A_Favorinin_Tersi_MS1_MS2 ZAMAN_DISI_TEST_2023_2025              2    3,00-3,49            15        1        14         6.666667       3.294667            -11.83  -78.866667            -100.000000             -36.600000                             N<30: yorumlama
   A_Favorinin_Tersi_MS1_MS2 ZAMAN_DISI_TEST_2023_2025              2    3,50-3,99            19        4        15        21.052632       3.722105             -4.39  -23.105263             -81.473684              53.789474                             N<30: yorumlama
   A_Favorinin_Tersi_MS1_MS2 ZAMAN_DISI_TEST_2023_2025              2    4,00-4,99            36        5        31        13.888889       4.472500            -14.42  -40.055556             -88.861111              10.500000 N<100: keşifsel, bağımsız doğrulama gerekir
B_MS1_MSX_MS2_En_Yuksek_Oran      GELISTIRME_2014_2022              1    2,50-2,99             3        0         3         0.000000       2.816667             -3.00 -100.000000            -100.000000            -100.000000                             N<30: yorumlama
B_MS1_MSX_MS2_En_Yuksek_Oran      GELISTIRME_2014_2022              1    3,00-3,49            36        9        27        25.000000       3.261944             -6.82  -18.944444             -63.944444              33.833333 N<100: keşifsel, bağımsız doğrulama gerekir
B_MS1_MSX_MS2_En_Yuksek_Oran      GELISTIRME_2014_2022              1    3,50-3,99            74       13        61        17.567568       3.678378            -26.06  -35.216216             -65.743581               0.040541 N<100: keşifsel, bağımsız doğrulama gerekir
B_MS1_MSX_MS2_En_Yuksek_Oran      GELISTIRME_2014_2022              1    4,00-4,99            76       17        59        22.368421       4.307895             -1.05   -1.381579             -40.921053              38.093750 N<100: keşifsel, bağımsız doğrulama gerekir
B_MS1_MSX_MS2_En_Yuksek_Oran      GELISTIRME_2014_2022              2    2,50-2,99             2        2         0       100.000000       2.925000              3.85  192.500000             192.500000             192.500000                             N<30: yorumlama
B_MS1_MSX_MS2_En_Yuksek_Oran      GELISTIRME_2014_2022              2    3,00-3,49            25        7        18        28.000000       3.269200             -2.10   -8.400000             -73.200000              56.800000                             N<30: yorumlama
B_MS1_MSX_MS2_En_Yuksek_Oran      GELISTIRME_2014_2022              2    3,50-3,99            48        5        43        10.416667       3.739792            -29.80  -62.083333             -92.395833             -30.937500 N<100: keşifsel, bağımsız doğrulama gerekir
B_MS1_MSX_MS2_En_Yuksek_Oran      GELISTIRME_2014_2022              2    4,00-4,99           116       15       101        12.931034       4.370603            -50.40  -43.448276             -66.422414             -19.396552  N>=100: yine de dönem dışı tekrar aranmalı
B_MS1_MSX_MS2_En_Yuksek_Oran      GELISTIRME_2014_2022              X    2,50-2,99            49       14        35        28.571429       2.891429             -8.33  -17.000000             -52.551020              19.000510 N<100: keşifsel, bağımsız doğrulama gerekir
B_MS1_MSX_MS2_En_Yuksek_Oran      GELISTIRME_2014_2022              X    3,00-3,49           300       96       204        32.000000       3.175933              4.29    1.430000             -15.316750              17.780167  N>=100: yine de dönem dışı tekrar aranmalı
B_MS1_MSX_MS2_En_Yuksek_Oran      GELISTIRME_2014_2022              X    3,50-3,99            14        1        13         7.142857       3.555000            -10.40  -74.285714            -100.000000             -22.857143                             N<30: yorumlama
B_MS1_MSX_MS2_En_Yuksek_Oran ZAMAN_DISI_TEST_2023_2025              1    3,00-3,49             8        1         7        12.500000       3.262500             -4.95  -61.875000            -100.000000             -23.750000                             N<30: yorumlama
B_MS1_MSX_MS2_En_Yuksek_Oran ZAMAN_DISI_TEST_2023_2025              1    3,50-3,99            23        1        22         4.347826       3.753043            -19.36  -84.173913            -100.000000             -52.521739                             N<30: yorumlama
B_MS1_MSX_MS2_En_Yuksek_Oran ZAMAN_DISI_TEST_2023_2025              1    4,00-4,99            29        1        28         3.448276       4.468966            -24.43  -84.241379            -100.000000             -52.724138                             N<30: yorumlama
B_MS1_MSX_MS2_En_Yuksek_Oran ZAMAN_DISI_TEST_2023_2025              2    2,50-2,99             1        1         0       100.000000       2.990000              1.99  199.000000                    NaN                    NaN                             N<30: yorumlama
B_MS1_MSX_MS2_En_Yuksek_Oran ZAMAN_DISI_TEST_2023_2025              2    3,00-3,49            10        1         9        10.000000       3.339000             -6.83  -68.300000            -100.000000             -36.600000                             N<30: yorumlama
B_MS1_MSX_MS2_En_Yuksek_Oran ZAMAN_DISI_TEST_2023_2025              2    3,50-3,99            16        4        12        25.000000       3.740625             -1.39   -8.687500             -77.437500              62.250000                             N<30: yorumlama
B_MS1_MSX_MS2_En_Yuksek_Oran ZAMAN_DISI_TEST_2023_2025              2    4,00-4,99            36        5        31        13.888889       4.472500            -14.42  -40.055556             -88.861111              10.083333 N<100: keşifsel, bağımsız doğrulama gerekir
B_MS1_MSX_MS2_En_Yuksek_Oran ZAMAN_DISI_TEST_2023_2025              X    2,50-2,99            17        5        12        29.411765       2.925882             -2.35  -13.823529             -66.352941              39.823529                             N<30: yorumlama
B_MS1_MSX_MS2_En_Yuksek_Oran ZAMAN_DISI_TEST_2023_2025              X    3,00-3,49            67       19        48        28.358209       3.166716             -7.18  -10.716418             -46.492910              25.985075 N<100: keşifsel, bağımsız doğrulama gerekir
B_MS1_MSX_MS2_En_Yuksek_Oran ZAMAN_DISI_TEST_2023_2025              X    3,50-3,99             7        2         5        28.571429       3.655714              0.11    1.571429             -49.857143              53.000000                             N<30: yorumlama
B_MS1_MSX_MS2_En_Yuksek_Oran ZAMAN_DISI_TEST_2023_2025              X    4,00-4,99             1        0         1         0.000000       4.160000             -1.00 -100.000000                    NaN                    NaN                             N<30: yorumlama

## Karar kuralı

- Pozitif ROI tek başına yeterli değildir; %95 aralığın alt sınırı da sıfırın üzerinde olmalıdır.
- Çok sayıda alt grup karşılaştırıldığı için en iyi görünen alt grup, bağımsız doğrulama olmadan seçilmemelidir.
- 2014–2022 iyi, 2023–2025 kötü ise strateji istikrarlı kabul edilmemelidir.
- Bu rapor bahis önerisi değildir; tarihsel sonuçların sağlamlığını kontrol eder.
