"""Create a bounded, reproducible source submission ZIP without nested downloads."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
ROOT=Path(__file__).resolve().parents[1]
root_files=['README.md','requirements.txt','analyze_dataset.py','5113056021_hw2.py',
 '5113056021_hw2_update.pdf','5113056021_hw2_report.pdf','5113056021_gpt_conversation.pdf','5113056021_gpt_conversation_updated.pdf',
 'gpt_conversation.md','gpt_conversation.json','gpt_conversation_updated.json',
 'notebooklm_research.md','notebooklm_result.json','notebooklm_raw.txt','notebooklm_dom.txt',
 'sources.md','DATA_LICENSE.md','COMPLIANCE_CHECKLIST.md','VALIDATION_WEB.md','VALIDATION.md','.gitignore']
files=[ROOT/f for f in root_files]
for folder in ['tests','tools','web/dist','data','output','.github']:
 for p in (ROOT/folder).rglob('*'):
  rel=p.relative_to(ROOT).as_posix()
  if not p.is_file() or '__pycache__' in rel or (rel.startswith('web/dist/downloads/') or rel.startswith('data/kaggle_download/')) or p.suffix in ['.zip','.gz','.pyc','.joblib'] or rel in ['data/train.csv','tools/publish_github.py','web/dist/check.txt']:
   continue
  files.append(p)
files=sorted(set(files))
manifest={'revision':'2026-11-02 revised assignment','primary_program':'analyze_dataset.py','github':'https://github.com/HitomiHuang/HW2_MULTIPLE_LINEAR_REGRESSION',
 'site':'https://hw2-regression-lab-5113056021.ivy819.chatgpt.site','source_files':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
(ROOT/'updated_submission_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
files.append(ROOT/'updated_submission_manifest.json')
archive=ROOT/'5113056021_hw2_updated.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=8) as z:
 for p in files:z.write(p,p.relative_to(ROOT).as_posix())
assert archive.stat().st_size<25*1024*1024,'Static hosting single-file size limit exceeded'
shutil.copy2(archive,ROOT/'web/dist/downloads'/archive.name)
print(json.dumps({'zip':str(archive),'files':len(files),'bytes':archive.stat().st_size},ensure_ascii=False))
