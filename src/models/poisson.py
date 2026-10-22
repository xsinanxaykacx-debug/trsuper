import numpy as np
from scipy.stats import poisson

def poisson_probabilities(features):
    # Uses only pre-match rolling goals and league priors; capped score grid is normalized.
    home_rate=np.clip(.72 + .23*np.nan_to_num(features["form_h_gf_5"],nan=1.2) + .18*np.nan_to_num(features["form_a_ga_5"],nan=1.2),.2,3.8)
    away_rate=np.clip(.62 + .23*np.nan_to_num(features["form_a_gf_5"],nan=1.0) + .16*np.nan_to_num(features["form_h_ga_5"],nan=1.0),.2,3.5)
    grid=np.arange(7)
    rows=[]
    for lh,la in zip(home_rate,away_rate):
        ph=poisson.pmf(grid,lh); pa=poisson.pmf(grid,la)
        mat=np.outer(ph,pa)
        # Dixon-Coles low-score adjustment with conservative rho; clamp and renormalize.
        rho=-0.06
        mat[0,0]*=max(.1,1-lh*la*rho)
        if len(grid)>1:
            mat[0,1]*=max(.1,1+lh*rho)
            mat[1,0]*=max(.1,1+la*rho)
            mat[1,1]*=max(.1,1-rho)
        mat=mat/mat.sum()
        rows.append([mat[np.tril_indices(7,-1)].sum(), mat.trace(), mat[np.triu_indices(7,1)].sum()])
    p=np.asarray(rows)[:,[2,1,0]] # convert away/draw/home to H,D,A
    return p/p.sum(axis=1,keepdims=True)

def goal_market_probabilities(features):
    home_rate=np.clip(.72 + .23*np.nan_to_num(features["form_h_gf_5"],nan=1.2) + .18*np.nan_to_num(features["form_a_ga_5"],nan=1.2),.2,3.8)
    away_rate=np.clip(.62 + .23*np.nan_to_num(features["form_a_gf_5"],nan=1.0) + .16*np.nan_to_num(features["form_h_ga_5"],nan=1.0),.2,3.5)
    over=[]; btts=[]
    for lh,la in zip(home_rate,away_rate):
        over.append(1-poisson.cdf(2,lh+la))
        btts.append((1-poisson.pmf(0,lh))*(1-poisson.pmf(0,la)))
    return np.asarray(over),np.asarray(btts)
