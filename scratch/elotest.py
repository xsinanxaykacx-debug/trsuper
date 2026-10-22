class Oyuncu:
    def __init__(self, isim, ilk_elo):
        self.isim = isim
        self.elo = ilk_elo

    def __repr__(self):
        return f"{self.isim}: {self.elo:.2f}"

class Takim:
    def __init__(self, isim, oyuncu_isimleri):
        self.isim = isim
        # Sezon başı 100 puan ilk 11'deki oyunculara eşit bölünür (Her biri 100 / 11 = 9.09)
        baslangic_elo = 100.0 / 11
        self.oyuncular = {isim: Oyuncu(isim, baslangic_elo) for isim in oyuncu_isimleri}

    def mac_isle(self, sonuc, gol_atanlar=None, asist_yapanlar=None, kaleci=None, gol_yedi=False, kirmizi_kartlar=None, sari_kartlar=None):
        if gol_atanlar is None: gol_atanlar = []
        if asist_yapanlar is None: asist_yapanlar = []
        if kirmizi_kartlar is None: kirmizi_kartlar = []
        if sari_kartlar is None: sari_kartlar = []

        # 1. Kart Cezalarının Hesaplanması (Puan alınsın/alınmasın her koşulda kendi ELO'sundan düşer)
        for oyuncu_isim in kirmizi_kartlar:
            if oyuncu_isim in self.oyuncular:
                self.oyuncular[oyuncu_isim].elo *= 0.90 # %10 düşüş
                
        for oyuncu_isim in sari_kartlar:
            if oyuncu_isim in self.oyuncular:
                self.oyuncular[oyuncu_isim].elo *= 0.95 # %5 düşüş

        # 2. Maç Sonucu Puan Değişimi
        if sonuc == "G":
            toplam_dagitilacak = 3.0
        elif sonuc == "B":
            toplam_dagitilacak = 1.0
        elif sonuc == "M":
            toplam_dagitilacak = -3.0
        else:
            toplam_dagitilacak = 0.0

        # Galibiyet veya Beraberlik durumunda puan ekleme mantığı
        if toplam_dagitilacak > 0:
            paylar = {}
            toplam_pay = 0
            
            for isim in self.oyuncular:
                pay = 1.0 # Baz pay
                
                # Gol atanlara %10 fazla pay
                if isim in gol_atanlar:
                    pay += 0.10
                # Asist yapanlara %5 fazla pay
                if isim in asist_yapanlar:
                    pay += 0.05
                # Gol yemeyen kaleciye %10 fazla pay
                if isim == kaleci and not gol_yedi:
                    pay += 0.10
                    
                paylar[isim] = pay
                toplam_pay += pay

            # Dağıtılacak puanı paylara göre bölüştürme
            for isim, pay in paylar.items():
                kazanilan_elo = (pay / toplam_pay) * toplam_dagitilacak
                self.oyuncular[isim].elo += kazanilan_elo

        # Mağlubiyet durumunda 3 puan takımdan eşit olarak eksiltilir (-3 / 11)
        elif toplam_dagitilacak < 0:
            eksiltme = toplam_dagitilacak / 11
            for isim in self.oyuncular:
                self.oyuncular[isim].elo += eksiltme

    def kadroyu_goster(self):
        print(f"\n--- {self.isim} Güncel ELO Durumu ---")
        toplam = 0
        for o in self.oyuncular.values():
            print(o)
            toplam += o.elo
        print(f"Takım Toplam ELO: {toplam:.2f}")

# ---- SİMÜLASYON TESTİ ----

# 11 Kişilik Örnek Kadro
ilk_11 = ["Muslera", "Nelsson", "Davinson", "Abdulkerim", "Jakobs", "Torreira", "Sara", "Baris", "Mertens", "Yunusemre", "Osimhen"]
galatasaray = Takim("Galatasaray", ilk_11)

# Sezon Başı Durumu
galatasaray.kadroyu_goster()

# Senaryo 1: Maç kazanıldı (3 puan eklenecek). Osimhen gol attı, Sara asist yaptı, Muslera gol yemedi. Torreira sarı kart gördü.
galatasaray.mac_isle(
    sonuc="G",
    gol_atanlar=["Osimhen"],
    asist_yapanlar=["Sara"],
    kaleci="Muslera",
    gol_yedi=False,
    sari_kartlar=["Torreira"]
)
galatasaray.kadroyu_goster()

# Senaryo 2: Maç kaybedildi (-3 puan). Jakobs kırmızı kart gördü.
galatasaray.mac_isle(
    sonuc="M",
    kirmizi_kartlar=["Jakobs"]
)
galatasaray.kadroyu_goster()
