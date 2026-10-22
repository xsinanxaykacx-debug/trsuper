import unittest
import pandas as pd
from src.load import season_normalize, to_numeric

class LoadTests(unittest.TestCase):
    def test_season_normalization(self):
        self.assertEqual(season_normalize("2013/14"),"2013/2014")
        self.assertEqual(season_normalize("2013/2014"),"2013/2014")
    def test_comma_decimal(self):
        values=to_numeric(pd.Series(["1,50","2.20","bad"]))
        self.assertAlmostEqual(values.iloc[0],1.5)
        self.assertAlmostEqual(values.iloc[1],2.2)
        self.assertTrue(pd.isna(values.iloc[2]))

if __name__=="__main__": unittest.main()
