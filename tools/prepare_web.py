"""Recompute demo results from the fixed samples included with the website.

The published samples are the canonical inputs; full source downloads are not
required. Run from the project root: python tools/prepare_web.py
"""
import importlib.util
import json
from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'web/dist'
spec=importlib.util.spec_from_file_location('analysis_engine',WEB/'analysis.py')
engine=importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
def main():
    summary={}
    for name,target,excluded in [('flood','FloodProbability',['id']),('housing','price',['id','date'])]:
        path=WEB/f'data/{name}_sample.csv'
        result=json.loads(engine.run_analysis(path.read_text(encoding='utf-8'),target,excluded))
        result['dataset_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        result['mode']='預先計算示範；重新分析使用相同程式與樣本'
        (WEB/f'data/{name}_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        summary[name]={k:result[k] for k in ['original_features','selected_features','metrics','interval','notices','dataset_sha256']}
        print(name,json.dumps(summary[name],ensure_ascii=False))
    summary['startups']=json.loads(engine.run_analysis((ROOT/'data/50_Startups.csv').read_text(),'Profit',[]))
    (ROOT/'output').mkdir(exist_ok=True)
    (ROOT/'output/web_validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':
    main()
