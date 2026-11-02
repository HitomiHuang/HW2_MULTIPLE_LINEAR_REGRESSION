"""Package the new, actually obtained NotebookLM response and its source evidence."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import re

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'output/evidence/notebooklm_revision'
previous = json.loads((ROOT / 'notebooklm_result.json').read_text(encoding='utf-8'))
prompts = json.loads((EVIDENCE / 'research_prompts.json').read_text(encoding='utf-8'))
raw = (EVIDENCE / 'final_response.txt').read_text(encoding='utf-8')
paragraphs = [p.strip() for p in raw.split('\n\n') if p.strip() and not p.startswith('# ')]
assert len(paragraphs) == 3
paragraph_sources = [['N1', 'N2', 'N7', 'N9'], ['N3', 'N4', 'N8', 'N10'], ['N2', 'N6', 'N9']]
summary = '\n\n'.join(p + ' 〔' + '、'.join(ids) + '〕' for p, ids in zip(paragraphs, paragraph_sources))
count = len(re.findall(r'[\u4e00-\u9fff]', '\n\n'.join(paragraphs)))
assert count > 100
sources = previous['sources'] + [
    {'id': 'N7', 'title': 'Kaggle：House Sales in King County, USA', 'url': 'https://www.kaggle.com/datasets/harlfoxem/housesalesprediction', 'imported': True},
] + [dict(s, imported=True) for s in prompts['sources_discovered']]
record = {
    'verified_in_notebooklm': True,
    'notebook_title': 'HW2 多元線性回歸：洪水分數與房價研究',
    'saved_note_title': 'NotebookLM 摘要｜洪水與房價多元線性回歸',
    'retrieved_date': datetime.now(ZoneInfo('Asia/Taipei')).strftime('%Y-%m-%d'),
    'method': 'Used NotebookLM Fast Research on the web, reviewed results, imported three university teaching sources and the King County source, excluded the previous saved note, requested a new cited synthesis, clarified scope in a follow-up, and saved the final response as a note.',
    'selected_web_sources': 10,
    'newly_imported_web_sources': 4,
    'summary': summary,
    'summary_exact_clipboard': raw,
    'chinese_characters_excluding_citations': count,
    'summary_editing': 'Removed the Markdown heading and grouped the original inline citations into source-level N references. Summary wording is unchanged.',
    'paragraph_source_ids': paragraph_sources,
    'sources': sources,
    'raw_response_file': 'output/evidence/notebooklm_revision/final_response.txt',
    'prompts_file': 'output/evidence/notebooklm_revision/research_prompts.json',
    'evidence_privacy': 'The public record excludes Google account identifiers, private notebook URLs and browser screenshots. Original browser evidence remains in the local temporary evidence folder.',
}
(EVIDENCE / 'research_result.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
links = '\n'.join('- [' + s['id'] + '] [' + s['title'] + '](' + s['url'] + ')' for s in sources)
note = f'''# NotebookLM 研究筆記

研究日期：{record['retrieved_date']}。

本次在 NotebookLM 使用 Fast Research 搜尋多元線性回歸、特徵選擇、Pipeline、交叉驗證與預測區間解法。檢視搜尋結果後，選入 UBC、BYU 與 South Carolina 三份大學教材，另加入 Kaggle King County 房價資料背景，與原有六份網路來源合併研究。舊的洪水摘要記事未勾選為本次研究來源。

## NotebookLM 摘要

{summary}

摘要原文字數：{count} 個中文字（不含引用編號）。正文未改寫，只移除 Markdown 標題並整理引用編號。

## 研究與採用方式

先請 NotebookLM 根據十份已勾選的網路來源產生摘要，再追問釐清特徵工程尚未在本作業驗證，以及平均 CI／單筆 PI 須在相同模型與條件下比較。最終回覆已存為「{record['saved_note_title']}」記事。

報告在資料背景、Pipeline 防洩漏、特徵選擇與預測區間的採用段落，標示「NotebookLM 摘要」及 N 編號。列總和與跨欄排序保留為待驗證改進，不作為已完成實驗。

報告另以「GPT 輔助內容」及 G1–G6 編號標示此次 ChatGPT 問答的採用位置，與 NotebookLM 研究來源分別對照。

## 閱讀來源

{links}

## 研究記錄

- [研究摘要與來源記錄](output/evidence/notebooklm_revision/research_result.json)
- [兩輪提問](output/evidence/notebooklm_revision/research_prompts.json)
- [NotebookLM 最終原文](output/evidence/notebooklm_revision/final_response.txt)

公開研究記錄保留提問、回覆與網路來源，原始瀏覽器畫面及私人筆記本資訊保存在本機。
'''
(ROOT / 'notebooklm_research.md').write_text(note, encoding='utf-8')
print(json.dumps({'selected_sources': len(sources), 'chinese_characters': count}, ensure_ascii=False))
