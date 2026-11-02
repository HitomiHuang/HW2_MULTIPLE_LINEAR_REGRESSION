"""Meaningful numerical and leakage checks for the shared web analysis engine."""
import importlib.util
import json
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'web/dist'
spec=importlib.util.spec_from_file_location('engine',WEB/'analysis.py')
engine=importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
class AnalysisTests(unittest.TestCase):
    def test_demo_metrics_and_intervals_independently(self):
        for key,features in [('flood',20),('housing',18)]:
            with self.subTest(key=key):
                r=json.loads((WEB/f'data/{key}_result.json').read_text(encoding='utf-8'))
                self.assertEqual(r['original_features'],features)
                self.assertTrue(r['assignment_eligible'])
                splits=[set(r['split_rows'][s]) for s in ['train','calibration','test']]
                self.assertEqual(len(set.union(*splits)),4000)
                self.assertTrue(all(not splits[i]&splits[j] for i,j in [(0,1),(0,2),(1,2)]))
                p=pd.DataFrame(r['predictions'])
                rmse=np.sqrt(np.mean((p.actual-p.prediction)**2))
                r2=1-np.sum((p.actual-p.prediction)**2)/np.sum((p.actual-p.actual.mean())**2)
                self.assertAlmostEqual(rmse,r['metrics'][-1]['rmse'])
                self.assertAlmostEqual(r2,r['metrics'][-1]['r2'])
                self.assertAlmostEqual(((p.actual>=p.lower)&(p.actual<=p.upper)).mean(),r['interval']['coverage'])
                self.assertTrue(np.all(p.lower<=p.prediction) and np.all(p.prediction<=p.upper))
                self.assertTrue(np.all((p.ols_pi_upper-p.ols_pi_lower)>=(p.mean_ci_upper-p.mean_ci_lower)))
                df=pd.read_csv(WEB/f'data/{key}_sample.csv')
                np.testing.assert_allclose(p.actual,df.iloc[p.row.to_numpy()-2][r['target']])
                best=min(r['selection'],key=lambda s:s['rmse'])
                self.assertEqual(len(r['selected_features']),best['k'])
    def test_test_and_calibration_labels_do_not_tune_model(self):
        rng=np.random.default_rng(7)
        df=pd.DataFrame(rng.normal(size=(160,4)),columns=list('abcd'))
        df['target']=4*df.a-2*df.b+rng.normal(size=160)
        r=json.loads(engine.run_analysis(df.to_csv(index=False),'target'))
        changed=df.copy()
        changed.loc[np.array(r['split_rows']['test'])-2,'target']+=100000
        s=json.loads(engine.run_analysis(changed.to_csv(index=False),'target'))
        np.testing.assert_allclose([v['coefficient'] for v in r['coefficients']],[v['coefficient'] for v in s['coefficients']])
        self.assertEqual(r['selection'],s['selection'])
        self.assertEqual(r['interval']['q'],s['interval']['q'])
        changed=df.copy()
        changed.loc[np.array(r['split_rows']['calibration'])-2,'target']+=100000
        s=json.loads(engine.run_analysis(changed.to_csv(index=False),'target'))
        self.assertEqual(r['coefficients'],s['coefficients'])
        self.assertEqual(r['selection'],s['selection'])
        self.assertGreater(s['interval']['q'],r['interval']['q'])
    def test_teacher_url_dataset_categorical_and_small_sample(self):
        r=json.loads(engine.run_analysis((ROOT/'data/50_Startups.csv').read_text(),'Profit'))
        self.assertEqual(r['sample_rows'],50)
        self.assertEqual(r['original_features'],4)
        self.assertFalse(r['assignment_eligible'])
        self.assertEqual(r['split'],{'train':21,'calibration':19,'test':10})
        self.assertEqual(r['encoded_features'],5)
        self.assertEqual(r['interval']['rank'],19)
        self.assertTrue(np.isfinite(r['interval']['q']))
    def test_missingness_and_invalid_targets(self):
        rng=np.random.default_rng(8)
        df=pd.DataFrame({'x':rng.normal(size=100),'cat':['a','b']*50,'empty':[np.nan]*100,'target':rng.normal(size=100)})
        df.loc[[1,3,4],'x']=np.nan
        df.loc[8,'target']=np.nan
        r=json.loads(engine.run_analysis(df.to_csv(index=False),'target'))
        self.assertEqual(r['removed_target'],1)
        self.assertIn('empty',r['dropped'])
        for bad in ['a,b\n1,2\n3,4',pd.DataFrame({'x':range(50),'y':[1]*50}).to_csv(index=False)]:
            with self.assertRaises(ValueError):
                engine.run_analysis(bad,'y')
if __name__=='__main__':
    unittest.main(verbosity=2)
