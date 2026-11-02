"""HW2 CLI: same engine and samples as the published interactive website.
python analyze_dataset.py --problem flood
python analyze_dataset.py --problem housing
python analyze_dataset.py --input data/50_Startups.csv --target Profit
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('hw2_engine',ROOT/'web/dist/analysis.py')
engine=importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
def main():
    parser=argparse.ArgumentParser(description='雙題目 / 自訂 CSV 多元線性回歸')
    parser.add_argument('--problem',choices=['flood','housing'],default='flood')
    parser.add_argument('--input',help='Local CSV path or public HTTPS CSV URL')
    parser.add_argument('--target')
    parser.add_argument('--exclude',nargs='*',default=None)
    parser.add_argument('--max-rows',type=int,default=4000)
    parser.add_argument('--output',type=Path,default=ROOT/'output/custom_analysis.json')
    args=parser.parse_args()
    defaults={'flood':('FloodProbability',['id']),'housing':('price',['id','date'])}
    if args.input:
        if not args.target:parser.error('--input requires --target')
        if args.input.startswith(('https://','http://')):
            with urlopen(args.input,timeout=30) as response:raw=response.read(10*1024*1024+1)
            if len(raw)>10*1024*1024:parser.error('CSV must not exceed 10 MB')
            text=raw.decode('utf-8-sig')
        else:text=Path(args.input).read_text(encoding='utf-8-sig')
        target=args.target;excluded=args.exclude or []
    else:
        text=(ROOT/f'web/dist/data/{args.problem}_sample.csv').read_text(encoding='utf-8-sig')
        target=args.target or defaults[args.problem][0]
        excluded=args.exclude if args.exclude is not None else defaults[args.problem][1]
    if args.max_rows<30:parser.error('--max-rows must be at least 30')
    result=json.loads(engine.run_analysis(text,target,excluded,max_rows=args.max_rows))
    result['dataset_source']=args.input or args.problem
    result['dataset_sha256']=hashlib.sha256(text.encode()).hexdigest()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'output':str(args.output),'features':result['original_features'],
      'selected':len(result['selected_features']),'metrics':result['metrics'][-1], 'coverage':result['interval']['coverage']},ensure_ascii=False))
if __name__=='__main__':main()
