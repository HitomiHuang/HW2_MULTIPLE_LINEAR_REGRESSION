"""Generate deterministic browser samples and results using the shared engine."""
import importlib.util
import json
from pathlib import Path
import hashlib
import shutil
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'web/dist'
spec=importlib.util.spec_from_file_location('analysis_engine',WEB/'analysis.py')
engine=importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
def main():
    flood=pd.read_csv(ROOT/'output/tables/analysis_sample.csv').sample(4000,random_state=42)
    flood.to_csv(WEB/'data/flood_sample.csv',index=False)
    housing=pd.read_csv(ROOT/'data/kc_house_data.csv').drop(columns=['Unnamed: 0'],errors='ignore')
    housing.sample(4000,random_state=42).to_csv(WEB/'data/housing_sample.csv',index=False)
    shutil.copy2(ROOT/'data/50_Startups.csv',WEB/'data/50_Startups.csv')
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
    (ROOT/'output/web_validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    notebook=json.loads((ROOT/'notebooklm_result.json').read_text(encoding='utf-8'))
    (WEB/'data/notebooklm.json').write_text(json.dumps(notebook,ensure_ascii=False),encoding='utf-8')
if __name__=='__main__':
    main()
