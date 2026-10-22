# -*- coding: utf-8 -*-
# archive_manifest.py — v1.6 arşiv manifesti (FINAL v4)
# ============================================================
# SALT OKUNUR (hedef dosyalar): hiçbir hedef CSV veya .py değiştirilmez.
# TEK YAZMA: archive_manifest.txt (yeni dosya).
#
# İki mod:
#   1) python .\archive_manifest.py              → manifest üret
#   2) python .\archive_manifest.py --verify     → archive_v16/ ile
#                                                   hash + satır + sütun
#                                                   doğrulaması
#
# FIX v2:
#   - archive_v16/ yoksa verify → açıkça ">>> VERIFY: FAIL"
#   - produce_manifest: CSV okunamazsa status = CSV_READ_FAIL
# FIX v3:
#   - produce_manifest sonuna ">>> MANIFEST: PASS/FAIL" eklendi
# FIX v4:
#   - log() tek argümanlı olduğu için ">>> MANIFEST:" satırı
#     f-string ile düzeltildi (v3'te TypeError veriyordu)
# ============================================================

from pathlib import Path
import hashlib, time, sys
import pandas as pd

ROOT = Path(r"C:\Users\bzdye\Downloads\trsuper")
ARCH = ROOT / "archive_v16"
OUT  = ROOT / "archive_manifest.txt"

TARGETS = [
    ROOT / "model_v1_6.py",
    ROOT / "walkforward_v16_exact.csv",
    ROOT / "v16_per_match_predictions.csv",
    ROOT / "v16_error_segments.csv",
    ROOT / "features_v1.csv",
]

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def csv_shape(p):
    try:
        df = pd.read_csv(p, low_memory=False)
        return (len(df), df.shape[1], list(df.columns))
    except Exception as e:
        return (None, None, [f"ERROR: {e}"])

# ============================================================
# MOD 1: manifest üret
# ============================================================
def produce_manifest():
    lines = []
    def log(s=""):
        print(s); lines.append(str(s))

    log("=" * 78)
    log("v1.6 ARŞİV MANİFESTİ")
    log(f"Üretim zamanı: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 78)
    log("")
    log("KAPSAM: Bu betik hedef dosyaları YALNIZCA OKUR. Tek yazma işlemi")
    log("        bu manifest dosyasıdır (archive_manifest.txt). Hedef")
    log("        dosyaların içeriği değiştirilmez, yeniden adlandırılmaz.")
    log("")

    summary = []
    for p in TARGETS:
        log("")
        log(f"Dosya: {p.name}")
        if not p.exists():
            log(f"  !!! BULUNAMADI: {p}")
            summary.append({"file": p.name, "status": "MISSING",
                            "sha": None, "rows": None, "cols": None})
            continue
        st = p.stat()
        sha = sha256(p)
        log(f"  Boyut       : {st.st_size:,} bytes")
        log(f"  mtime       : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st.st_mtime))}")
        log(f"  SHA256      : {sha}")

        if p.suffix == ".csv":
            rows, cols, colnames = csv_shape(p)
            if rows is None:
                status = "CSV_READ_FAIL"
                log(f"  !!! CSV OKUNAMADI: {colnames[0]}")
                log(f"  Satır × sütun: — × —")
                log(f"  Sütunlar    : —")
                summary.append({"file": p.name, "status": status,
                                "sha": sha, "rows": None, "cols": None})
            else:
                status = "OK"
                log(f"  Satır × sütun: {rows} × {cols}")
                log(f"  Sütunlar    : {colnames}")
                summary.append({"file": p.name, "status": status,
                                "sha": sha, "rows": rows, "cols": cols})
        else:
            summary.append({"file": p.name, "status": "OK",
                            "sha": sha, "rows": None, "cols": None})

    log("")
    log("=" * 78)
    log("ÖZET TABLO (manifest sonrası hızlı kontrol)")
    log("=" * 78)
    log(f"  {'dosya':40s} {'durum':15s} {'satır':>8s} {'sütun':>6s}  sha256[:16]")
    for r in summary:
        sha16 = (r["sha"][:16] + "…") if r["sha"] else "—"
        log(f"  {r['file']:40s} {r['status']:15s} "
            f"{(r['rows'] if r['rows'] is not None else '—'):>8} "
            f"{(r['cols'] if r['cols'] is not None else '—'):>6}  {sha16}")

    log("")
    log("=" * 78)
    log("DONDURULMUŞ REFERANS (v1.6, 5854 fair maç)")
    log("=" * 78)
    log("  RF  LL  : 1.0267     MKT LL  : 0.9927")
    log("  RF  Br  : 0.6154     MKT Br  : 0.5918")
    log("  RF  Acc : 48.61%     MKT Acc : 51.84%")
    log("  n sezon : 10  (2016/17 → 2025/26)")
    log("  n maç   : 5854")

    log("")
    log("=" * 78)
    log("ARŞİVLENEN DENEYLER (hepsi v1.6'ya karşı, aynı 3 kriter)")
    log("=" * 78)
    log("  v1.7  stadium_home_win_rate_prior            FAIL")
    log("  v1.8  referee_home_win_rate_prior            FAIL")
    log("  v1.9  coach_home_win_rate_prior              FAIL")
    log("  v2.0  Platt/Isotonic calibration             FAIL")
    log("  v2.1  stadium + referee                      FAIL (1/3)")
    log("  v2.2  squad_stability_home/away_prior        FAIL (0/3)")

    log("")
    log("=" * 78)
    log("METODOLOJİK NOTLAR")
    log("=" * 78)
    log("  1. RF'nin ayrışmada %27.1 acc alması, 'bağımsız sinyal yok'")
    log("     anlamına gelmez. %95 GA ve rastgele çizgisi karşılaştırması")
    log("     yapılmadan bu yorum yapılmamalı.")
    log("  2. Altı deneyin başarısız olması, mevcut sütunlardan hiçbir")
    log("     bilgi çıkmayacağını KANITLAMAZ. Sadece bu 6 hipotezin bu")
    log("     kriterleri geçemediğini gösterir.")
    log("  3. walkforward_v16_exact.csv, v1.6 ORİJİNALİNİN kanıtı değil;")
    log("     bu kodun yeniden ürettiği değerlerdir. Orijinal kodla")
    log("     birebir aynlık doğrulanmadı.")
    log("  4. BAHİS SİMÜLASYONU KAPALI. 'RF < MKT tek sezonda' gibi bir")
    log("     eşik başarı ölçütü olarak kullanılmaz: tek sezon tesadüf")
    log("     olabilir; LL üstünlüğü tek başına kârlılığı kanıtlamaz.")
    log("     Bahis simülasyonu için kriterler HENÜZ TANIMLI DEĞİL.")
    log("  5. Yeni veri için '0.005 LL katkısı' bir ÖNCELİKLENDİRME")
    log("     HEDEFİDİR, kesin/gerekli eşik değildir. Mevcut sonuçlar")
    log("     bunun ulaşılabilir olduğunu göstermiyor.")

    log("")
    log("=" * 78)
    log("SONRAKİ ADIM (bu manifest dışında)")
    log("=" * 78)
    log("  A) archive_v16/ klasörü oluştur, 5 hedef dosyayı + bu")
    log("     manifesti oraya kopyala.")
    log("  B) Ardından: python .\\archive_manifest.py --verify")
    log("     → kaynak vs arşiv hash + satır + sütun eşleşmesi")

    # === MANIFEST ÜRETİM SONUCU ===
    non_ok = [r for r in summary if r["status"] != "OK"]
    manifest_ok = len(non_ok) == 0
    log("")
    log("=" * 78)
    log("MANIFEST ÜRETİM SONUCU")
    log("=" * 78)
    if manifest_ok:
        log("  Tüm hedef dosyalar OK")
    else:
        log(f"  !!! {len(non_ok)} dosya OK değil:")
        for r in non_ok:
            log(f"       - {r['file']}: {r['status']}")
    log("")
    log(f">>> MANIFEST: {'PASS' if manifest_ok else 'FAIL'}")
    log("")
    log("  NOT: Bu kontrol arşiv doğrulaması DEĞİL — sadece manifest")
    log("       üretiminin temiz olduğunu gösterir. Arşiv doğrulaması")
    log("       ayrı bir adımdır: python .\\archive_manifest.py --verify")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nManifest: {OUT}")

# ============================================================
# MOD 2: verify (archive_v16/ ile kaynak karşılaştırması)
# ============================================================
def verify_archive():
    if not ARCH.exists():
        print("=" * 78)
        print("ARCHIVE VERIFY: archive_v16/ YOK")
        print("=" * 78)
        print(f"  Beklenen konum: {ARCH}")
        print(f"  Önce 5 hedef dosyayı + manifesti oraya kopyala.")
        print("")
        print(">>> VERIFY: FAIL")
        return

    print("=" * 78)
    print("ARCHIVE VERIFY: kaynak vs archive_v16/")
    print("=" * 78)
    print(f"  {'dosya':40s} {'kaynak_sha':>16s} {'arşiv_sha':>16s} "
          f"{'satır':>8s} {'sütun':>6s}  durum")
    all_ok = True

    for p in TARGETS:
        if not p.exists():
            print(f"  {p.name:40s} {'—':>16s} {'—':>16s} {'—':>8s} {'—':>6s}  KAYNAK YOK")
            all_ok = False; continue
        src_sha = sha256(p)
        dst = ARCH / p.name
        if not dst.exists():
            print(f"  {p.name:40s} {src_sha[:16]:>16s} {'—':>16s} {'—':>8s} {'—':>6s}  ARŞİV YOK")
            all_ok = False; continue

        dst_sha = sha256(dst)
        sha_match = (src_sha == dst_sha)
        if not sha_match:
            all_ok = False

        row_info = "—"; col_info = "—"
        if p.suffix == ".csv":
            try:
                src_df = pd.read_csv(p, low_memory=False)
                dst_df = pd.read_csv(dst, low_memory=False)
                row_info = f"{len(src_df)}={len(dst_df)}" if len(src_df) == len(dst_df) \
                           else f"{len(src_df)}≠{len(dst_df)}"
                if len(src_df) != len(dst_df):
                    all_ok = False
                src_cols = list(src_df.columns)
                dst_cols = list(dst_df.columns)
                col_info = f"{len(src_cols)}={len(dst_cols)}" if len(src_cols) == len(dst_cols) \
                           else f"{len(src_cols)}≠{len(dst_cols)}"
                if src_cols != dst_cols:
                    all_ok = False
                    print(f"  {p.name}: SÜTUN ADLARI FARKLI")
                    print(f"    kaynak: {src_cols}")
                    print(f"    arşiv : {dst_cols}")
            except Exception:
                row_info = "okunamadı"; col_info = "okunamadı"
                all_ok = False

        status = "OK" if sha_match else "SHA FARK"
        print(f"  {p.name:40s} {src_sha[:16]:>16s} {dst_sha[:16]:>16s} "
              f"{row_info:>8s} {col_info:>6s}  {status}")

    print("")
    manifest_src = OUT
    manifest_dst = ARCH / OUT.name
    if not manifest_src.exists():
        print(f"  MANIFEST KAYNAĞI YOK: {manifest_src}")
        all_ok = False
    elif not manifest_dst.exists():
        print(f"  MANIFEST ARŞİVDE YOK: {manifest_dst}")
        all_ok = False
    else:
        m_src = sha256(manifest_src)
        m_dst = sha256(manifest_dst)
        match = "OK" if m_src == m_dst else "SHA FARK"
        if m_src != m_dst:
            all_ok = False
        print(f"  manifest kaynak: {m_src[:16]}  arşiv: {m_dst[:16]}  -> {match}")

    print("")
    print(">>> VERIFY:", "PASS" if all_ok else "FAIL")

# ============================================================
if __name__ == "__main__":
    if "--verify" in sys.argv:
        verify_archive()
    else:
        produce_manifest()