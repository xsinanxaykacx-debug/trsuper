import numpy as np

def multiplicative(odds):
    odds=np.asarray(odds,dtype=float)
    valid=np.isfinite(odds).all(axis=1)&(odds>1).all(axis=1)
    p=np.full_like(odds,np.nan,dtype=float)
    inv=1/odds[valid]
    p[valid]=inv/inv.sum(axis=1,keepdims=True)
    return p

def shin(odds):
    odds=np.asarray(odds,dtype=float)
    p=multiplicative(odds)
    for i,row in enumerate(odds):
        if not np.isfinite(row).all() or (row<=1).any(): continue
        q=1/row; total=q.sum()
        if total<=1: continue
        lo,hi=0.0,min(0.999999,(total-1)/(total))
        for _ in range(80):
            z=(lo+hi)/2
            den=2*(1-z)
            probs=(np.sqrt(z*z+4*(1-z)*q*q/total)-z)/den
            if probs.sum()>1: lo=z
            else: hi=z
        p[i]=probs/probs.sum()
    return p
