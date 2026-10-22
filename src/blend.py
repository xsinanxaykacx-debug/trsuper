import numpy as np
from scipy.optimize import minimize
from sklearn.isotonic import IsotonicRegression
from src.evaluate import log_loss

def fit_blend(probabilities, y):
    # Inputs are N x 3 matrices in identical row order; weights are nonnegative and sum to one.
    names=list(probabilities)
    mats=[np.asarray(probabilities[n],dtype=float) for n in names]
    if not mats or any(m.shape!=(len(y),3) for m in mats): raise ValueError("Blend matrisleri aynı N x 3 boyutta olmalı.")
    def objective(w):
        p=sum(wi*m for wi,m in zip(w,mats))
        return log_loss(y,p)
    result=minimize(objective,np.full(len(mats),1/len(mats)),method="SLSQP",bounds=[(0,1)]*len(mats),constraints={"type":"eq","fun":lambda w:w.sum()-1},options={"maxiter":1000,"ftol":1e-10})
    weights=np.clip(result.x,0,1); weights=weights/weights.sum()
    return dict(zip(names,weights.tolist()))

def apply_blend(probabilities, weights):
    p=sum(float(weights[k])*np.asarray(probabilities[k],dtype=float) for k in weights)
    return p/p.sum(axis=1,keepdims=True)

def fit_isotonic(p,y):
    p=np.asarray(p,dtype=float); y=np.asarray(y,dtype=str)
    models=[]
    for j,label in enumerate(("H","D","A")):
        model=IsotonicRegression(out_of_bounds="clip")
        model.fit(p[:,j],(y==label).astype(float))
        models.append(model)
    return models

def apply_isotonic(p,models):
    q=np.column_stack([m.predict(np.asarray(p)[:,i]) for i,m in enumerate(models)])
    q=np.clip(q,1e-8,1)
    return q/q.sum(axis=1,keepdims=True)
