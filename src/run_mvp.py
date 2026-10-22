from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from src.load import load_data,load_reference
from src.features import build_features
from src.models.market import multiplicative,shin
from src.models.elo import elo_probabilities,tune_temperature
from src.models.poisson import poisson_probabilities
from src.blend import fit_blend,apply_blend,fit_isotonic,apply_isotonic
from src.evaluate import metric_row,per_season,log_loss

def normalize_id(value):
    text=str(value).strip()
    try:
        number=float(text)
        if np.isfinite(number) and number.is_integer():
            return str(int(number))
    except (ValueError,TypeError):
        pass
    return text

def run():
    data=load_data()
    ref,schedule=load_reference()
    feat=build_features(data)
    feat["_key"]=feat["match_id"].map(normalize_id)
    ref=ref.copy()
    ref["_key"]=ref["match_id"].map(normalize_id)
    if ref["_key"].duplicated().any():
        raise ValueError("Referans kümesinde normalize edilmiş ID tekrarı var.")
    indexed=feat.set_index("_key",drop=False)
    missing=sorted(set(ref["_key"])-set(indexed.index))
    if missing:
        raise ValueError(f"DATA içinde referans test ID eksik: {len(missing)}; örnek={missing[:5]}")
    test=indexed.loc[ref["_key"]].reset_index(drop=True)
    if len(test)!=5854:
        raise AssertionError(f"Test kümesi değişti: {len(test)}")
    if not np.array_equal(test["y"].astype(str).to_numpy(),ref["y"].astype(str).to_numpy()):
        raise ValueError("DATA sonuçları ile arşiv referans y etiketleri uyuşmuyor.")

    seasons=sorted(feat["season"].astype(str).unique(),key=lambda x:int(x[:4]) if x[:4].isdigit() else 0)
    pretest=[s for s in seasons if s < "2016/2017"]
    if len(pretest)<2:
        raise ValueError("Test öncesinde en az iki validation sezonu bulunamadı.")
    validation=pretest[-2:]
    val_mask=feat["season"].astype(str).isin(validation)&feat["y"].isin(["H","D","A"])
    val=feat.loc[val_mask].reset_index(drop=True)
    if len(val)<100:
        raise ValueError(f"Validation örneklemi yetersiz: {len(val)}")
    valid_y=val["y"].to_numpy()

    val_odds=val[["odd_H","odd_D","odd_A"]].to_numpy(float)
    val_mult=multiplicative(val_odds)
    val_shin=shin(val_odds)
    market_name="multiplicative" if log_loss(valid_y,val_mult)<log_loss(valid_y,val_shin) else "shin"
    odds_all=feat[["odd_H","odd_D","odd_A"]].to_numpy(float)
    all_market=multiplicative(odds_all) if market_name=="multiplicative" else shin(odds_all)
    temperature=tune_temperature(val,valid_y)
    all_elo=elo_probabilities(feat,temperature)
    all_poisson=poisson_probabilities(feat)

    val_idx=np.flatnonzero(val_mask.to_numpy())
    val_probs={"Market":all_market[val_idx],"Elo":all_elo[val_idx],"Poisson":all_poisson[val_idx]}
    weights=fit_blend(val_probs,valid_y)
    blend_val=apply_blend(val_probs,weights)
    calibration="none"
    if len(validation)>=2:
        calibration_fit=val["season"].astype(str).to_numpy()==validation[0]
        calibration_check=val["season"].astype(str).to_numpy()==validation[1]
        if calibration_fit.sum()>=100 and calibration_check.sum()>=50:
            iso=fit_isotonic(blend_val[calibration_fit],valid_y[calibration_fit])
            raw_loss=log_loss(valid_y[calibration_check],blend_val[calibration_check])
            iso_loss=log_loss(valid_y[calibration_check],apply_isotonic(blend_val[calibration_check],iso))
            if iso_loss<raw_loss:
                calibration="isotonic"

    positions={key:i for i,key in enumerate(feat["_key"])}
    test_pos=np.array([positions[k] for k in ref["_key"]],dtype=int)
    models={
        "Market":all_market[test_pos],
        "Elo":all_elo[test_pos],
        "Poisson":all_poisson[test_pos],
    }
    models["Blend"]=apply_blend({name:models[name] for name in weights},weights)
    if calibration=="isotonic":
        calibration_fit=val["season"].astype(str).to_numpy()==validation[0]
        iso=fit_isotonic(blend_val[calibration_fit],valid_y[calibration_fit])
        models["Blend"]=apply_isotonic(models["Blend"],iso)

    labels=ref["y"].astype(str).to_numpy()
    baseline_cols={
        "v1.6 RF":["p_rf_H","p_rf_D","p_rf_A"],
        "Market (v1.6)":["p_mkt_H","p_mkt_D","p_mkt_A"],
    }
    for name,cols in baseline_cols.items():
        if not set(cols).issubset(ref.columns):
            raise ValueError(f"Arşiv baseline olasılıkları eksik: {cols}")
        models[name]=ref[cols].to_numpy(float)
    order=["v1.6 RF","Market (v1.6)","Market","Elo","Poisson","Blend"]
    metrics=pd.DataFrame([metric_row(name,labels,models[name]) for name in order])
    if not (metrics["n"]==5854).all():
        raise AssertionError("Modeller aynı sabit 5854 maçta değerlendirilmeli.")

    report_dir=ROOT/"reports"
    report_dir.mkdir(exist_ok=True)
    comparison=ref[["match_id","season","date","y"]].copy()
    pred_rows=[]
    for name in order:
        p=models[name]
        for j,lab in enumerate(("H","D","A")):
            comparison[f"{name}_p_{lab}"]=p[:,j]
    for i in range(len(ref)):
        row={"match_id":ref.iloc[i]["match_id"],"season":ref.iloc[i]["season"],"date":ref.iloc[i]["date"],"y":labels[i]}
        for j,lab in enumerate(("H","D","A")):
            row[f"p_{lab}"]=models["Blend"][i,j]
        pred_rows.append(row)
    pd.DataFrame(pred_rows).to_csv(report_dir/"per_match_predictions.csv",index=False)
    comparison.to_csv(report_dir/"comparison.csv",index=False)
    pd.concat([per_season(labels,models[name],ref["season"].astype(str),name) for name in order],ignore_index=True).to_csv(report_dir/"per_season_metrics.csv",index=False)

    rf_ll=float(metrics.loc[metrics.model=="v1.6 RF","log_loss"].iloc[0])
    market_ll=float(metrics.loc[metrics.model=="Market (v1.6)","log_loss"].iloc[0])
    blend_ll=float(metrics.loc[metrics.model=="Blend","log_loss"].iloc[0])
    tier1=blend_ll<1.0267
    tier2=blend_ll<0.9927
    status="passed tier 2" if tier2 else "passed tier 1" if tier1 else "below baseline"
    lines=[
        "# Faz 1 MVP sonuçları","",
        f"- Sabit test kümesi: {len(ref)} maç; sezonlar {ref['season'].min()}–{ref['season'].max()}.",
        f"- Validation sezonları: {', '.join(validation)}.",
        f"- Market yöntemi (validation): {market_name}.",
        f"- Elo sıcaklığı (validation): {temperature}.",
        f"- Blend ağırlıkları (validation log loss minimizasyonu): {weights}.",
        f"- Kalibrasyon (validation sezonu dış örnek kontrolü): {calibration}.","",
        "| Model | N | Log loss | Brier | Accuracy | ECE |","|---|---:|---:|---:|---:|---:|"
    ]
    for _,r in metrics.iterrows():
        lines.append(f"| {r['model']} | {int(r['n'])} | {r['log_loss']:.6f} | {r['brier']:.6f} | {r['accuracy']:.4%} | {r['ece']:.6f} |")
    lines += [
        "",f"- Tier 1 (Blend log loss < 1.0267): {'PASS' if tier1 else 'FAIL'} (gerçek: {blend_ll:.6f}).",
        f"- Tier 2 (Blend log loss < 0.9927): {'PASS' if tier2 else 'FAIL'} (gerçek: {blend_ll:.6f}).","",
        "## Sezon bazlı metrikler","",pd.read_csv(report_dir/"per_season_metrics.csv").to_markdown(index=False),"",
        "## Dürüstlük kontrolleri","",
        f"- v1.6 RF ölçülen log loss: {rf_ll:.6f}; referans 1.0267.",
        f"- Arşiv market ölçülen log loss: {market_ll:.6f}; referans 0.9927.",
        "- Bütün modeller aynı sabit 5854 match_id kümesinde ölçüldü.",
        "- Test kümesi model seçimi, ağırlık seçimi ve kalibrasyon için kullanılmadı.",""
    ]
    (report_dir/"mvp_results.md").write_text("\n".join(lines),encoding="utf-8")
    print(metrics.to_string(index=False))
    print(f"Tier 1: {'PASS' if tier1 else 'FAIL'} | Tier 2: {'PASS' if tier2 else 'FAIL'}")
    print("Report: reports/mvp_results.md")
    return status

if __name__=="__main__":
    print("MVP_STATUS="+run())
