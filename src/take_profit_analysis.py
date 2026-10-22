"""Historical take-profit / stop-loss analysis for the PCT_20 bet ledger.

Run from repository root: python -m src.take_profit_analysis

Caution: this ledger contains only bets reached by the original PCT_20 run.
If a scenario survives beyond its last row, that scenario is right-censored.
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd

LEDGER_PATH = Path("data/csv/aggressive_growth_bet_ledger.csv")
OUTPUT_DIR = Path("data/csv")
STRATEGY = "PCT_20"
INITIAL_BANKROLL = 100.0
FRACTION = 0.20
EPS = 1e-9


def parse_bool(value):
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return None
    value = str(value).strip().lower()
    if value in {"true", "1", "yes", "evet"}:
        return True
    if value in {"false", "0", "no", "hayir", "hayır"}:
        return False
    return None


def load_ledger():
    if not LEDGER_PATH.exists():
        raise FileNotFoundError(
            f"{LEDGER_PATH} bulunamadı. Önce src.aggressive_growth çalıştır."
        )
    df = pd.read_csv(LEDGER_PATH, encoding="utf-8-sig")
    required = {
        "strategy", "bet_number", "_id", "_date", "Ev_Sahibi", "Deplasman",
        "selection", "selected_odds", "won",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Günlükte gerekli sütunlar eksik: {missing}")
    df = df.loc[df["strategy"].astype(str).eq(STRATEGY)].copy()
    if df.empty:
        raise ValueError(f"Günlükte {STRATEGY} stratejisi bulunamadı.")
    df["bet_number"] = pd.to_numeric(df["bet_number"], errors="coerce")
    df["selected_odds"] = pd.to_numeric(df["selected_odds"], errors="coerce")
    df["won"] = df["won"].map(parse_bool)
    df = df.dropna(subset=["bet_number", "selected_odds", "won"]).copy()
    df["bet_number"] = df["bet_number"].astype(int)
    df["won"] = df["won"].astype(bool)
    df = df.sort_values("bet_number").drop_duplicates("bet_number").reset_index(drop=True)
    if (df["selected_odds"] <= 1.0).any():
        raise ValueError("Seçilen oranlarda 1.00 veya altı değer var; veri kontrol edilmeli.")
    return df


def label(row):
    date = str(row.get("_date", "?"))[:10]
    return f"{date} | {row.get('Ev_Sahibi', '?')} - {row.get('Deplasman', '?')}"


def apply_bet(bankroll, row):
    stake = bankroll * FRACTION
    profit = stake * (float(row["selected_odds"]) - 1.0) if bool(row["won"]) else -stake
    return max(0.0, bankroll + profit), profit


def report_loss_runs(df):
    later = df.loc[df["bet_number"] > 67].sort_values("bet_number")
    print("\\n" + "=" * 110)
    print("PCT_20 — 67. BAHİSTEN SONRAKİ ARDIŞIK KAYIPLAR")
    print("=" * 110)
    print(f"67. bahis sonrası kayıt: {len(later):,}; kayıp bahis: {int((~later['won']).sum()):,}")
    runs, current = [], []
    for _, row in later.iterrows():
        if not bool(row["won"]):
            current.append(row)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    if not runs:
        print("Ardışık kayıp serisi bulunmadı.")
        return
    print(f"Ardışık kayıp serisi sayısı: {len(runs)}")
    for i, run in enumerate(runs, 1):
        odds = ", ".join(f"{float(r['selected_odds']):.2f}" for r in run)
        print(f"\\nSeri {i}: {len(run)} kayıp | bahis {int(run[0]['bet_number'])}–{int(run[-1]['bet_number'])} | oranlar: {odds}")
        for r in run:
            print(f"  #{int(r['bet_number']):>4} | {float(r['selected_odds']):.2f} | {r['selection']} | {label(r)}")


def scenario_a(df):
    bankroll, peak, peak_at = INITIAL_BANKROLL, INITIAL_BANKROLL, 0
    placed, reason, stopped = 0, "Günlükteki kayıtlı bahisler bitti.", False
    for _, row in df.iterrows():
        if bankroll <= EPS:
            bankroll, reason, stopped = 0.0, "Kasa sıfırlandı.", True
            break
        bankroll, _ = apply_bet(bankroll, row)
        placed += 1
        if bankroll > peak:
            peak, peak_at = bankroll, placed
        if bankroll >= 500.0:
            reason, stopped = "500 birim hedefinde bahis durduruldu.", True
            break
        if bankroll <= EPS:
            bankroll, reason, stopped = 0.0, "Kasa sıfırlandı.", True
            break
    return {
        "scenario": "A — 500 birimde kâr al", "bets_placed": placed,
        "stop_at_bet": placed if stopped else None, "stop_reason": reason,
        "active_bankroll": bankroll, "withdrawn": 0.0, "total_wealth": bankroll,
        "peak_bankroll": peak, "peak_at_bet": peak_at,
        "net_vs_100": bankroll - INITIAL_BANKROLL,
        "ledger_exhausted": placed >= len(df) and not stopped,
    }


def scenario_b(df):
    bankroll, peak, peak_at = INITIAL_BANKROLL, INITIAL_BANKROLL, 0
    placed, reason, stopped = 0, "Günlükteki kayıtlı bahisler bitti.", False
    for _, row in df.iterrows():
        if bankroll <= EPS:
            bankroll, reason, stopped = 0.0, "Kasa sıfırlandı.", True
            break
        prior_peak = peak
        bankroll, _ = apply_bet(bankroll, row)
        placed += 1
        if bankroll > peak:
            peak, peak_at = bankroll, placed
        elif prior_peak > EPS and bankroll <= prior_peak * 0.70:
            reason = f"Önceki zirve {prior_peak:.2f} birimden %30 düşüşte durduruldu."
            stopped = True
            break
        if bankroll <= EPS:
            bankroll, reason, stopped = 0.0, "Kasa sıfırlandı.", True
            break
    return {
        "scenario": "B — Zirveden %30 düşüşte dur", "bets_placed": placed,
        "stop_at_bet": placed if stopped else None, "stop_reason": reason,
        "active_bankroll": bankroll, "withdrawn": 0.0, "total_wealth": bankroll,
        "peak_bankroll": peak, "peak_at_bet": peak_at,
        "net_vs_100": bankroll - INITIAL_BANKROLL,
        "ledger_exhausted": placed >= len(df) and not stopped,
    }


def scenario_c(df):
    bankroll, withdrawn = INITIAL_BANKROLL, 0.0
    next_profit_milestone = INITIAL_BANKROLL + 100.0
    peak_total, peak_at = INITIAL_BANKROLL, 0
    placed, reason, stopped, records = 0, "Günlükteki kayıtlı bahisler bitti.", False, []
    for _, row in df.iterrows():
        if bankroll <= EPS:
            bankroll, reason, stopped = 0.0, "Aktif kasa sıfırlandı; çekilen para korundu.", True
            break
        before = bankroll
        bankroll, bet_profit = apply_bet(bankroll, row)
        placed += 1
        withdrawal_this_bet = 0.0
        # Every 100 units of cumulative total-wealth profit, secure half (50 units).
        while bankroll + withdrawn + EPS >= next_profit_milestone:
            amount = 50.0
            if bankroll + EPS < amount:
                break
            bankroll -= amount
            withdrawn += amount
            withdrawal_this_bet += amount
            next_profit_milestone += 100.0
        total_wealth = bankroll + withdrawn
        if total_wealth > peak_total:
            peak_total, peak_at = total_wealth, placed
        records.append({
            "bet_number": placed, "match": label(row),
            "selected_odds": float(row["selected_odds"]), "won": bool(row["won"]),
            "bankroll_before": before, "bet_profit": bet_profit,
            "withdrawal_this_bet": withdrawal_this_bet,
            "active_bankroll_after": bankroll, "cumulative_withdrawn": withdrawn,
            "total_wealth_after": total_wealth,
        })
        if bankroll <= EPS:
            bankroll, reason, stopped = 0.0, "Aktif kasa sıfırlandı; çekilen para korundu.", True
            break
    return ({
        "scenario": "C — Her +100 kârda 50 birim çek", "bets_placed": placed,
        "stop_at_bet": placed if stopped else None, "stop_reason": reason,
        "active_bankroll": bankroll, "withdrawn": withdrawn,
        "total_wealth": bankroll + withdrawn, "peak_bankroll": peak_total,
        "peak_at_bet": peak_at, "net_vs_100": bankroll + withdrawn - INITIAL_BANKROLL,
        "ledger_exhausted": placed >= len(df) and not stopped,
    }, records)


def main():
    df = load_ledger()
    print("Take-profit / stop-loss analizi")
    print(f"Girdi: {LEDGER_PATH}")
    print(f"PCT_20 satır: {len(df):,} | bahis aralığı: {df['bet_number'].min()}–{df['bet_number'].max()}")
    print("Senaryolar, yalnızca bu günlükte kayıtlı bahis sırasını kullanır.")
    report_loss_runs(df)

    row67 = df.loc[df["bet_number"].eq(67)]
    if not row67.empty:
        r = row67.iloc[0]
        if "bankroll_after" in df.columns and pd.notna(r.get("bankroll_after")):
            bank67 = float(r["bankroll_after"])
        else:
            bank67 = INITIAL_BANKROLL
            for _, item in df.loc[df["bet_number"].le(67)].iterrows():
                bank67, _ = apply_bet(bank67, item)
        print("\\n67. bahis referansı:")
        print(f"  {label(r)} | oran {float(r['selected_odds']):.2f} | {'Kazandı' if bool(r['won']) else 'Kaybetti'}")
        print(f"  O anda durulsaydı kasa: {bank67:.2f} | net sonuç: {bank67 - INITIAL_BANKROLL:+.2f} birim")

    summaries = [scenario_a(df), scenario_b(df)]
    summary_c, withdrawal_ledger = scenario_c(df)
    summaries.append(summary_c)
    result = pd.DataFrame(summaries)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = OUTPUT_DIR / "take_profit_analysis_results.csv"
    withdrawal_path = OUTPUT_DIR / "take_profit_withdrawal_ledger.csv"
    result.to_csv(summary_path, index=False, encoding="utf-8-sig")
    pd.DataFrame(withdrawal_ledger).to_csv(withdrawal_path, index=False, encoding="utf-8-sig")

    print("\\n" + "=" * 125)
    print("KÂR AL / ZARAR DURDUR SENARYOLARI")
    print("=" * 125)
    cols = ["scenario", "bets_placed", "stop_at_bet", "active_bankroll", "withdrawn",
            "total_wealth", "net_vs_100", "peak_bankroll", "peak_at_bet", "ledger_exhausted"]
    print(result[cols].to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    print("\\nDurdurma nedenleri:")
    for item in summaries:
        print(f"- {item['scenario']}: {item['stop_reason']}")
    print("\\nYorum:")
    print("- ledger_exhausted=True, strateji durmadı; mevcut günlük bitti. Sonuç eksik olabilir.")
    print("- Senaryo C'de çekilen para korunur ve aktif bahis kasasından ayrı raporlanır.")
    print("- 67. bahiste veya zirvede durma, önceden belirlenmiş kural değilse geriye dönük seçimdir.")
    print("- Kâr al kuralının gelecekte kârlılık sağlayacağı bu tarihsel testten çıkarılamaz.")
    print(f"\\nÖzet CSV: {summary_path}")
    print(f"Çekim günlüğü CSV: {withdrawal_path}")


if __name__ == "__main__":
    main()
