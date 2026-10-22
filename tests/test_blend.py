import unittest
import numpy as np
from src.blend import fit_blend,apply_blend

class BlendTests(unittest.TestCase):
    def test_weights_and_blend(self):
        y=np.array(["H","D","A","H","D","A"])
        p1=np.array([[.7,.2,.1],[.2,.7,.1],[.1,.2,.7],[.6,.3,.1],[.2,.6,.2],[.1,.2,.7]])
        p2=np.full((6,3),1/3)
        weights=fit_blend({"good":p1,"flat":p2},y)
        self.assertAlmostEqual(sum(weights.values()),1.0,places=8)
        self.assertTrue(all(0<=v<=1 for v in weights.values()))
        p=apply_blend({"good":p1,"flat":p2},weights)
        self.assertTrue(np.allclose(p.sum(axis=1),1))

if __name__=="__main__": unittest.main()
