import unittest
import numpy as np
import pandas as pd
from src.models.market import multiplicative,shin
from src.models.elo import elo_probabilities
from src.models.poisson import poisson_probabilities,goal_market_probabilities

class ModelTests(unittest.TestCase):
    def setUp(self):
        self.features=pd.DataFrame({
            "elo_diff":[100,-80,0],"league_draw_share":[.26,.25,.27],
            "form_h_gf_5":[1.5,1.1,1.3],"form_a_ga_5":[1.2,1.4,1.1],
            "form_a_gf_5":[1.0,1.2,1.4],"form_h_ga_5":[1.1,1.5,1.3],
        })
    def test_market_probabilities_normalized(self):
        odds=np.array([[2.0,3.2,4.0],[1.8,3.5,5.0]])
        for p in (multiplicative(odds),shin(odds)):
            self.assertTrue(np.allclose(p.sum(axis=1),1))
            self.assertTrue((p>0).all())
    def test_elo_and_poisson_are_valid_probabilities(self):
        for p in (elo_probabilities(self.features),poisson_probabilities(self.features)):
            self.assertEqual(p.shape,(3,3))
            self.assertTrue(np.isfinite(p).all())
            self.assertTrue(np.allclose(p.sum(axis=1),1))
            self.assertTrue((p>=0).all())
        over,btts=goal_market_probabilities(self.features)
        self.assertTrue(((over>=0)&(over<=1)).all())
        self.assertTrue(((btts>=0)&(btts<=1)).all())

if __name__=="__main__": unittest.main()
