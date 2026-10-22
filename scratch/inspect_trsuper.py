# inspect_trsuper.py — v4: salt okuma, model egitmez, veri dosyalarini degistirmez
from pathlib import Path
from collections import Counter
import csv, io, re, warnings
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning)

ROOT     = Path(r"C:\Users\bzdye\Downloads\trsuper")
REPORT   = ROOT / "_inspection_report.txt"
DELIM_SAMPLE_LINES = 500
DELIM_SAMPLE_BYTES = 1_000_000
DATE_CHUNK = 500_000
SAMPLE_ROWS = 5
VERIFY_SAMPLE_ROWS = 3
VERIFY_MAX_COLS = 30          # tam satir basarken sutun tavani
VERIFY_CELL_MAX = 24          # tek hucre max karakter
ENCODINGS  = ["utf-8-sig", "utf-8", "cp1254", "latin1"]
SEPARATORS = [",", ";", "\t", "|"]

lines = []
def log(s=""):
    print(s); lines.append(str(s))

# ---------- 1) Aday okuma skorlamasi ----------
def try_read_sample(path, enc):
    try:
        with open(path, "r", encoding=enc, newline="") as f:
            return f.read(DELIM_SAMPLE_BYTES)
    except Exception:
        return None

def score_delimiter(text, sep):
    if not text: return None
    try:
        reader = csv.reader(io.StringIO(text), delimiter=sep)
        rows = []
        for i, r in enumerate(reader):
            if i >= DELIM_SAMPLE_LINES: break
            rows.append(r)
    except Exception:
        return None
    if len(rows) < 2: return None
    header, data = rows[0], rows[1:]
    if not data: return None

    ncols_list = [len(r) for r in data]
    mode_ncols, mode_count = Counter(ncols_list).most_common(1)[0]
    if mode_ncols < 2: return None
    consist_ratio = mode_count / len(ncols_list)

    header_text_ratio = sum(
        1 for c in header
        if c.strip() and not re.fullmatch(r"-?\d+([.,]\d+)?", c.strip())
    ) / max(len(header), 1)
    header_ok = header_text_ratio > 0.7
    header_matches_data = len(header) == mode_ncols

    n = min(200, len(data))
    type_profile = []
    for j in range(mode_ncols):
        vals = [r[j] for r in data[:n] if len(r) > j and r[j].strip()]
        if not vals:
            type_profile.append("empty"); continue
        num = date = 0
        for v in vals:
            vv = v.strip().replace(",", ".")
            try:
                float(vv); num += 1; continue
            except Exception:
                pass
            if re.search(r"[-/.:]", v) and not re.fullmatch(r"-?\d+(\.\d+)?", v):
                d = pd.to_datetime(v, errors="coerce", dayfirst=True)
                if pd.notna(d): date += 1
        tot = len(vals)
        if num / tot > 0.85: type_profile.append("num")
        elif date / tot > 0.6: type_profile.append("date")
        else: type_profile.append("txt")
    n_types = len(set(type_profile) - {"empty"})

    uniq_counts = [len({r[j] for r in data[:n] if len(r) > j}) for j in range(mode_ncols)]
    has_low_card  = any(u <= 10 for u in uniq_counts)
    has_high_card = any(u >= 50 for u in uniq_counts)
    date_like_cols = sum(1 for t in type_profile if t == "date")

    total_cells = sum(len(r) for r in data)
    filled = sum(1 for r in data for c in r if c.strip()) / max(total_cells, 1)

    score = 0.0
    if mode_ncols >= 3:  score += 3
    if mode_ncols >= 5:  score += 1
    if mode_ncols >= 10: score += 1
    if consist_ratio > 0.95: score += 3
    if header_ok: score += 2
    if header_matches_data: score += 2
    if n_types >= 2: score += 2
    if n_types >= 3: score += 1
    if has_low_card:  score += 1
    if has_high_card: score += 1
    if date_like_cols > 0: score += 2
    if filled > 0.85: score += 1

    return {
        "sep": sep, "enc": None, "score": score,
        "ncols": mode_ncols, "consist_ratio": consist_ratio,
        "header_ok": header_ok, "header_matches_data": header_matches_data,
        "n_types": n_types, "type_profile": type_profile,
        "has_low_card": has_low_card, "has_high_card": has_high_card,
        "date_like_cols": date_like_cols, "filled": filled,
        "full_header": header, "sample_rows_full": data[:VERIFY_SAMPLE_ROWS],
        "bad_chars": 0,
    }

def pick_read_options(path):
    candidates = []
    for enc in ENCODINGS:
        text = try_read_sample(path, enc)
        if not text: continue
        bad_chars = text.count("\ufffd")
        for sep in SEPARATORS:
            r = score_delimiter(text, sep)
            if r is None: continue
            r["enc"] = enc
            r["bad_chars"] = bad_chars
            r["score"] -= min(bad_chars, 50) * 0.2
            candidates.append(r)
    if not candidates:
        return None, []
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[0], candidates

def assess_confidence(best, candidates):
    confidence = "HIGH"
    reasons = []

    if len(candidates) >= 2:
        gap = best["score"] - candidates[1]["score"]
        if gap < 1.0:
            confidence = "LOW"; reasons.append(f"top-2 skor farki cok kucuk ({gap:.2f})")
        elif gap < 3.0 and confidence == "HIGH":
            confidence = "MEDIUM"; reasons.append(f"top-2 skor farki orta ({gap:.2f})")

    if best["score"] < 10:
        confidence = "LOW"; reasons.append(f"mutlak skor dusuk ({best['score']:.2f})")
    elif best["score"] < 13 and confidence == "HIGH":
        confidence = "MEDIUM"; reasons.append(f"mutlak skor orta ({best['score']:.2f})")

    if best["ncols"] < 3:
        confidence = "LOW"; reasons.append("ncols<3")
    if not best["header_ok"]:
        confidence = "LOW"; reasons.append("header metin degil (sayi gibi)")
    if not best["header_matches_data"]:
        confidence = "LOW"; reasons.append("header ve veri sutun sayisi uyusmuyor")
    if best["consist_ratio"] < 0.9:
        confidence = "LOW"; reasons.append(f"satir arasi sutun tutarsiz ({best['consist_ratio']:.2f})")
    if best["bad_chars"] > 0:
        if confidence == "HIGH": confidence = "MEDIUM"
        reasons.append(f"encoding supheli ({best['bad_chars']} replacement char)")

    return confidence, reasons

def _fmt_row(row, max_cols=VERIFY_MAX_COLS, cell_max=VERIFY_CELL_MAX):
    cells = []
    for j, c in enumerate(row[:max_cols]):
        c = str(c)
        if len(c) > cell_max: c = c[:cell_max-1] + "…"
        cells.append(repr(c))
    suffix = f"  … (+{len(row)-max_cols} sutun)" if len(row) > max_cols else ""
    return "[" + ", ".join(cells) + "]" + suffix

# ---------- 2) Sezon: ad + deger dogrulamasi ----------
SEASON_HINTS   = ["sezon", "season", "donem", "dönem", "yil", "year"]
SEASON_EXCLUDE = ["hafta", "week", "round", "tur", "tour", "macno"]
DATE_HINTS     = ["tarih", "date", "zaman", "kickoff", "baslangic", "start"]
WEEK_HINTS     = ["hafta", "week", "round", "tur", "tour"]

def is_season_candidate(name):
    n = str(name).lower()
    if any(x in n for x in SEASON_EXCLUDE): return False
    return any(h in n for h in SEASON_HINTS)

def is_week_col(name):
    return any(h in str(name).lower() for h in WEEK_HINTS)

def is_date_col(name):
    return any(h in str(name).lower() for h in DATE_HINTS)

YEAR_RE  = re.compile(r"^(19|20)\d{2}$")
RANGE_RE = re.compile(r"^(19|20)\d{2}\s*[-/]\s*(19|20)?\d{2}$")

def validate_season_column(series):
    s = series.dropna()
    if len(s) == 0:
        return False, "tamamen bos"
    n_unique = s.nunique()
    if n_unique < 2:
        return False, f"unique={n_unique} (tek deger, sezon degil)"
    if n_unique > 50:
        return False, f"unique={n_unique} (sezon icin cok yuksek)"
    sample_vals = [str(v).strip() for v in pd.unique(s.astype(str))[:30]]
    year_like  = sum(1 for v in sample_vals if YEAR_RE.match(v))
    range_like = sum(1 for v in sample_vals if RANGE_RE.match(v))
    if (year_like + range_like) / len(sample_vals) < 0.7:
        return False, f"deger formati sezon gibi degil (ornek: {sample_vals[:5]})"
    return True, f"unique={n_unique}, format=ok"

# ---------- 3) Tarih: tam dosya, dort ayri deger ----------
def scan_date_full(path, sep, enc, col):
    first_row_date = last_row_date = None
    first_valid_date = last_valid_date = None
    min_dt = max_dt = None
    n_total = n_nonnull = n_chunks = 0
    first_chunk_done = False

    for chunk in pd.read_csv(path, sep=sep, encoding=enc, usecols=[col],
                             chunksize=DATE_CHUNK, low_memory=False):
        n_chunks += 1
        n_total += len(chunk)
        s = pd.to_datetime(chunk[col], errors="coerce", dayfirst=True)

        # Dosyanin gercek ilk satirinin tarihi (NaT olsa bile kaydedilir)
        if not first_chunk_done:
            if len(s) > 0:
                first_row_date = s.iloc[0]
            first_chunk_done = True

        # Dosyanin gercek son satirinin tarihi (NaT olsa bile, her chunk'ta guncellenir)
        if len(s) > 0:
            last_row_date = s.iloc[-1]

        valid = s.dropna()
        if len(valid) == 0:
            continue

        if first_valid_date is None:
            first_valid_date = valid.iloc[0]
        last_valid_date = valid.iloc[-1]

        if min_dt is None or valid.min() < min_dt: min_dt = valid.min()
        if max_dt is None or valid.max() > max_dt: max_dt = valid.max()
        n_nonnull += int(s.notna().sum())

    return {"first_row_date": first_row_date, "last_row_date": last_row_date,
            "first_valid_date": first_valid_date, "last_valid_date": last_valid_date,
            "min_dt": min_dt, "max_dt": max_dt,
            "n_total": n_total, "n_nonnull": n_nonnull, "n_chunks": n_chunks}

# ---------- 4) Guvenli min/max ----------
def safe_min_max(s):
    if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
        try: return s.min(), s.max()
        except Exception: return None, None
    return None, None

# =============== ANA AKIS ===============
log("=" * 78); log("TRSUPER VERI INCELEMESI (SALT OKUMA — MODEL YOK)"); log("=" * 78)
log(f"ROOT: {ROOT}  |  Exists: {ROOT.exists()}")
if not ROOT.exists():
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    raise SystemExit(f"Klasor yok: {ROOT}")

all_files = [p for p in ROOT.rglob("*") if p.is_file() and p != REPORT]
csv_files = [p for p in all_files if p.suffix.lower() == ".csv"]
log(f"Toplam dosya: {len(all_files)}  |  CSV: {len(csv_files)}")
for p in all_files:
    log(f"  {p.relative_to(ROOT)}   ({p.stat().st_size/1024:.1f} KB)")

for path in csv_files:
    log(""); log("=" * 78); log(f"DOSYA: {path.relative_to(ROOT)}"); log("=" * 78)

    best, candidates = pick_read_options(path)
    if best is None:
        log("  !! Hicbir ayrac/kodlama kombinasyonu makul okumadi, atlaniyor."); continue

    log("  Aday okumalar (skora gore, ilk 4):")
    for i, c in enumerate(candidates[:4], 1):
        marker = "*" if c is best else " "
        log(f"   {marker}{i}. sep={c['sep']!r} enc={c['enc']!r} score={c['score']:.2f}  "
            f"ncols={c['ncols']} consist={c['consist_ratio']:.3f} "
            f"header_ok={c['header_ok']} header_match={c['header_matches_data']} "
            f"types={c['n_types']} date_like={c['date_like_cols']} "
            f"filled={c['filled']:.2f} bad_chars={c['bad_chars']}")

    log(""); log("  --- ADAY DOGRULAMA (manuel kontrol) ---")
    log(f"  Secilen aday: sep={best['sep']!r} enc={best['enc']!r} ncols={best['ncols']}  "
        f"(score={best['score']:.2f})")
    log(f"  Baslik satiri (tam): {_fmt_row(best['full_header'])}")
    for i, row in enumerate(best['sample_rows_full'], 1):
        log(f"  Ornek satir {i}    : {_fmt_row(row)}")

    conf, conf_reasons = assess_confidence(best, candidates)
    log(f"  GUVEN: {conf}")
    for r in conf_reasons:
        log(f"    - {r}")
    if conf != "HIGH":
        log("  >>> MANUEL DOGRULAMA GEREKLI: yukaridaki baslik/satirlari gozle kontrol et.")

    warns = []
    if best["ncols"] < 3:               warns.append("ncols<3 — mac tablosu icin cok az")
    if not best["header_ok"]:           warns.append("basliklar sayi gibi — header yok olabilir")
    if not best["header_matches_data"]: warns.append("header ve veri sutun sayisi uyusmuyor")
    if best["consist_ratio"] < 0.95:    warns.append(f"satir arasi sutun sayisi tutarsiz (consist={best['consist_ratio']:.3f})")
    if not best["has_low_card"]:        warns.append("dusuk kardinaliteli sutun yok (sonuc/ev-dep gibi)")
    if not best["has_high_card"]:       warns.append("yuksek kardinaliteli sutun yok (takim adlari gibi)")
    if best["date_like_cols"] == 0:     warns.append("tarih benzeri sutun yok")
    if best["filled"] < 0.85:           warns.append(f"doluluk dusuk ({best['filled']:.2f})")
    if best["bad_chars"] > 5:           warns.append(f"encoding uyumsuzlugu ({best['bad_chars']} replacement char)")
    for w in warns:
        log(f"  UYARI: {w}")

    try:
        df = pd.read_csv(path, sep=best["sep"], encoding=best["enc"], low_memory=False)
    except Exception as e:
        log(f"  !! Pandas okuma hatasi: {e}"); continue

    log(""); log(f"  Shape: {df.shape[0]} satir x {df.shape[1]} sutun")
    log("  Sutunlar (dtype / eksik% / unique / min / max):")
    for col in df.columns:
        mn, mx = safe_min_max(df[col])
        log(f"    {str(col)!r:38s} dtype={str(df[col].dtype):10s} "
            f"miss={df[col].isna().mean()*100:5.1f}%  "
            f"unique={df[col].nunique(dropna=True):>7}  "
            f"min={mn if mn is not None else '-'}  "
            f"max={mx if mx is not None else '-'}")

    # SEZON: ad + deger dogrulamasi
    season_cands = [c for c in df.columns if is_season_candidate(c)]
    week_cols    = [c for c in df.columns if is_week_col(c) and not is_season_candidate(c)]
    log(""); log(f"  Sezon ADAY sutunlari (ada gore): {season_cands}")
    confirmed_seasons, rejected_seasons = [], []
    for sc in season_cands:
        ok, why = validate_season_column(df[sc])
        if ok:
            confirmed_seasons.append(sc)
            log(f"    {sc!r} ONAYLANDI: {why}")
            for k, v in df[sc].value_counts(dropna=False).sort_index().items():
                log(f"      {k!r}: {v}")
        else:
            rejected_seasons.append(sc)
            log(f"    {sc!r} REDDEDILDI: {why}")
    if not confirmed_seasons:
        log("    (Onaylanmis sezon sutunu yok — sezon dagilimi raporda yok)")
    if week_cols:
        log(f"  Sezon benzeri ama HARIC (hafta/week/round): {week_cols}")
        for wc in week_cols:
            log(f"    {wc!r} ilk 10: {df[wc].value_counts(dropna=False).head(10).to_dict()}")

    # TARIH: tam dosya, dort ayri deger
    date_cols = [c for c in df.columns if is_date_col(c)]
    log(""); log(f"  Tarih sutunlari (TAM DOSYA, parcali tarama): {date_cols}")
    for dc in date_cols:
        try:
            r = scan_date_full(path, best["sep"], best["enc"], dc)
        except Exception as e:
            log(f"    {dc!r}: tarama basarisiz ({e})"); continue
        log(f"    {dc!r}:")
        log(f"        ilk_satir_tarihi = {r['first_row_date']}   (NaT ise ilk satir tarihsiz)")
        log(f"        son_satir_tarihi = {r['last_row_date']}    (NaT ise son satir tarihsiz)")
        log(f"        ilk_gecerli      = {r['first_valid_date']}")
        log(f"        son_gecerli      = {r['last_valid_date']}")
        log(f"        global_min       = {r['min_dt']}")
        log(f"        global_max       = {r['max_dt']}")
        log(f"        parse={r['n_nonnull']}/{r['n_total']}  chunks={r['n_chunks']}")
        if (r["first_valid_date"] is not None and r["min_dt"] is not None
                and r["first_valid_date"] != r["min_dt"]):
            log("        NOT: ilk_gecerli != global_min — dosya tarih sirali degil")

    # SONUC / ORAN adaylari — sadece profil
    log(""); log("  Sonuc/oran benzeri sutun profilleri (yorum sizin):")
    for col in df.columns:
        c = str(col).lower().strip()
        tags = ("result" in c or "sonuc" in c or "odds" in c or "oran" in c
                or c in {"ms1","msx","ms2","1","x","2","ftr","htr"}
                or c.startswith("ms") or c.startswith("odds") or c.startswith("oran"))
        if not tags: continue
        s = df[col]; mn, mx = safe_min_max(s)
        log(f"    {str(col)!r:24s} dtype={s.dtype}  "
            f"min={mn if mn is not None else '-'}  "
            f"max={mx if mx is not None else '-'}  "
            f"top5={s.value_counts(dropna=False).head(5).to_dict()}")

    log(""); log(f"  Ornek satirlar (ilk {SAMPLE_ROWS}):")
    log(df.head(SAMPLE_ROWS).to_string())

REPORT.write_text("\n".join(lines), encoding="utf-8")
print(f"\nRapor yazildi: {REPORT}")