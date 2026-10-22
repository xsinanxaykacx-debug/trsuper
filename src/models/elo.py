import numpy as np
from scipy.optimize import minimize_scalar

def elo_probabilities(features, temperature=400.0):
    diff=np.asarray(features["elo_diff"],dtype=float)
    # Elo expected score maps to a 3-way softmax approximation; draw mass is anchored by league history.
    home=1/(1+10**(-diff/max(float(temperature),1e-9)))
    draw=np.clip(np.asarray(features["league_draw_share"],dtype=float),.15,.38)
    p_home=home*(1-draw)+draw*.5
    p_away=(1-home)*(1-draw)+draw*.5
    p=np.column_stack([p_home,np.full(len(home),0.0),p_away])
    p[:,1]=draw
    return p/p.sum(axis=1,keepdims=True)

def tune_temperature(features, y, candidates=(250,300,350,400,450,500,600,700)):
    from src.evaluate import log_loss
    best=(float("inf"),400.0)
    for t in candidates:
        p=elo_probabilities(features,t)
        score=log_loss(y,p)
        if score<best[0]: best=(score,float(t))
    return best[1]
