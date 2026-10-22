import numpy as np
import pandas as pd

LABELS=("H","D","A")
def _arrays(y,p):
    y=np.asarray(y,dtype=str); p=np.asarray(p,dtype=float)
    if p.shape!=(len(y),3): raise ValueError("Olasılık matrisi N x 3 olmalı (H,D,A).")
    idx={v:i for i,v in enumerate(LABELS)}
    valid=np.isin(y,LABELS)&np.isfinite(p).all(axis=1)&(p>=0).all(axis=1)&(p.sum(axis=1)>0)
    y,p=y[valid],p[valid]
    p=p/p.sum(axis=1,keepdims=True)
    yi=np.array([idx[v] for v in y],dtype=int)
    return y,p,yi

def log_loss(y,p):
    _,p,yi=_arrays(y,p)
    return float(-np.log(np.clip(p[np.arange(len(yi)),yi],1e-15,1)).mean())

def brier_score(y,p):
    _,p,yi=_arrays(y,p)
    return float(np.mean(np.sum((p-np.eye(3)[yi])**2,axis=1)))

def accuracy(y,p):
    _,p,yi=_arrays(y,p)
    return float(np.mean(np.argmax(p,axis=1)==yi))

def ece(y,p,bins=10):
    y,p,yi=_arrays(y,p); conf=p.max(axis=1); correct=(np.argmax(p,axis=1)==yi)
    edges=np.linspace(0,1,bins+1); result=0.0
    for i in range(bins):
        mask=(conf>=edges[i])&(conf<(edges[i+1] if i<bins-1 else edges[i+1]+1e-12))
        if mask.any(): result += mask.mean()*abs(correct[mask].mean()-conf[mask].mean())
    return float(result)

def metric_row(name,y,p):
    return {"model":name,"n":len(y),"log_loss":log_loss(y,p),"brier":brier_score(y,p),"accuracy":accuracy(y,p),"ece":ece(y,p)}

def per_season(y,p,seasons,name):
    frame=pd.DataFrame({"y":np.asarray(y),"season":np.asarray(seasons)})
    probs=np.asarray(p)
    return pd.DataFrame([{"model":name,"season":season,**metric_row(name,grp.y,probs[grp.index.to_numpy()])} for season,grp in frame.groupby("season",sort=True)])
