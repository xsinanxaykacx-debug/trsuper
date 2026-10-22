import unittest
import numpy as np
from src.evaluate import log_loss,brier_score,accuracy,ece

class EvaluateTests(unittest.TestCase):
    def test_metrics_match_manual_example(self):
        y=np.array(["H","D"])
        p=np.array([[.8,.1,.1],[.2,.6,.2]])
        expected_ll=-(np.log(.8)+np.log(.6))/2
        expected_brier=(((.8-1)**2+(.1-0)**2+(.1-0)**2)+((.2-0)**2+(.6-1)**2+(.2-0)**2))/2
        self.assertAlmostEqual(log_loss(y,p),expected_ll,places=12)
        self.assertAlmostEqual(brier_score(y,p),expected_brier,places=12)
        self.assertEqual(accuracy(y,p),1.0)
        self.assertGreaterEqual(ece(y,p),0.0)

if __name__=="__main__": unittest.main()
