"""Independent numerical spot checks and a bounded submission ZIP.

Run after the analysis and PDF build: python tools/verify_and_package.py
Only explicit deliverable files are included; local packages/caches are excluded.
"""
import hashlib
import json
from pathlib import Path
import re
import zipfile

import joblib
import numpy as np
import pandas as pd
from pypdf import PdfReader
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"output"
meta=json.loads((OUT/"run_metadata.json").read_text(encoding="utf-8"))
inter=json.loads((OUT/"tables"/"interval_metrics.json").read_text(encoding="utf-8"))
manifest=json.loads((OUT/"report_manifest.json").read_text(encoding="utf-8"))
checks=[]


def check(condition,description):
    if not condition: raise AssertionError(description)
    checks.append(description)


sample=pd.read_csv(OUT/"tables"/"analysis_sample.csv")
split=pd.read_csv(OUT/"tables"/"split_manifest.csv")
pred=pd.read_csv(OUT/"tables"/"test_predictions.csv")
result=pd.read_csv(OUT/"tables"/"model_metrics.csv").set_index("model")
bundle=joblib.load(OUT/"models"/"ols_bundle.joblib")
features=meta["input_features"]
check(len(features)==20 and "id" not in features and "FloodProbability" not in features,"20 original predictors, excluding id and target")
check(10<=len(features)<=20 and 13<len(features)<40,"Both assignment feature-count requirements satisfied")
compile((ROOT/"5113056021_hw2.py").read_text(encoding="utf-8"),"5113056021_hw2.py","exec")
checks.append("Current main program passes Python syntax compilation")
check(len(sample)==50000 and len(split)==50000,"50,000 sampled rows recorded")
check(split.id.is_unique and set(split.id)==set(sample.id),"Every sampled row has exactly one split")
check(split.groupby("split").size().to_dict()=={"calibration":8000,"proper_train":32000,"test":10000},"32,000 / 8,000 / 10,000 disjoint split sizes")
test_ids=set(split.loc[split.split=="test","id"])
check(test_ids==set(pred.id),"Predictions contain exactly the held-out test ids")
joined=pred.merge(sample[["id","FloodProbability"]],on="id",validate="one_to_one")
check(np.allclose(joined.actual,joined.FloodProbability),"Reported test targets match source sample")
rmse=float(np.sqrt(np.mean((pred.actual-pred.prediction)**2)))
r2=float(1-np.sum((pred.actual-pred.prediction)**2)/np.sum((pred.actual-pred.actual.mean())**2))
check(np.isclose(rmse,result.loc["OLS_selected","RMSE"],rtol=1e-12),"OLS RMSE independently recomputed from saved predictions")
check(np.isclose(r2,result.loc["OLS_selected","R2"],rtol=1e-12),"OLS R2 independently recomputed from saved predictions")
check(np.all(pred.conformal_lower<=pred.prediction) and np.all(pred.prediction<=pred.conformal_upper),"Prediction intervals contain each point prediction")
coverage=float(((pred.actual>=pred.conformal_lower)&(pred.actual<=pred.conformal_upper)).mean())
check(np.isclose(coverage,inter["conformal_coverage"]),"Conformal test coverage independently recomputed")
cal=sample.merge(split.loc[split.split=="calibration",["id"]],on="id",validate="one_to_one")
resid=np.abs(cal.FloodProbability-bundle["pipeline"].predict(cal[features]))
q=float(np.sort(resid)[7600])
check(np.isclose(q,inter["conformal_q"],rtol=1e-12),"Finite-sample corrected 7,601st calibration residual verified")
new=pd.read_csv(ROOT/"data"/"new_samples.csv")
newpred=pd.read_csv(OUT/"new_predictions.csv")
check(np.allclose(bundle["pipeline"].predict(new[features]),newpred.prediction),"Serialized model reload reproduces five deployment examples")
check(hashlib.sha256((ROOT/"data"/"train.csv").read_bytes()).hexdigest()==meta["source_sha256"],"Source train.csv SHA-256 matches metadata")
check(len(list((OUT/"figures").glob("*.png")))==8,"Eight expected analytical figures present")
report=PdfReader(ROOT/manifest["report_file"])
text="\n".join(page.extract_text() or "" for page in report.pages)
check(len(report.pages)==manifest["combined_pages"],"Combined report page count matches manifest")
check(all(term in text for term in ["Business Understanding","Data Understanding","Data Preparation","Modeling","Evaluation","Deployment","NotebookLM 摘要","GPT 輔助內容"]),"Six CRISP-DM stages and separately marked AI sections present")
check("�" not in text,"PDF text extraction has no Unicode replacement characters")
ranking=pd.read_csv(OUT/"tables"/"feature_ranking.csv")
selection=pd.read_csv(OUT/"tables"/"feature_selection_cv.csv")
check(int(ranking.kbest14_selected.sum())==14 and int(ranking.rfe14_selected.sum())==14,
      "Both fixed 14-feature selection methods actually retain exactly 14 predictors")
check(int(selection.loc[selection.cv_rmse.idxmin(),"k"])==meta["selected_k"],
      "Final feature count agrees with the lowest training CV RMSE")
bodytext="\n".join(page.extract_text() or "" for page in report.pages[:manifest["report_pages"]])
if manifest["notebooklm_complete"]:
    nb=json.loads((ROOT/"notebooklm_result.json").read_text(encoding="utf-8"))
    nb_chars=len(re.findall(r"[\u3400-\u9fff]",nb["summary"]))
    check(nb_chars>=100,"Actual NotebookLM summary contains at least 100 Chinese characters")
    check(nb["verified_in_notebooklm"] and len(nb["sources"])>=1 and all(s["imported"] for s in nb["sources"]),
          "NotebookLM result records verified output and successfully imported sources")
    check((ROOT/"notebooklm_raw.txt").stat().st_size>500,"NotebookLM original prompts and responses preserved")
    check(re.sub(r"\s+","",nb["summary"]) in re.sub(r"\s+","",bodytext),"Complete NotebookLM summary appears in the report body")
    check("尚未完成：NotebookLM" not in bodytext and "實際研究摘要仍待登入" not in (ROOT/"README.md").read_text(encoding="utf-8"),
          "Current report and README have no obsolete NotebookLM pending status")

web=json.loads((OUT/"chatgpt_screenshots.json").read_text(encoding="utf-8"))
check(web["verified_in_browser"] and web["conversation_url"].startswith("https://chatgpt.com/c/"),
      "Screenshot appendix records a real ChatGPT web conversation")
check(len(web["screenshots"])>=3 and all((ROOT/p).exists() for p in web["screenshots"]),
      "All captured ChatGPT browser images are present")
check(len(PdfReader(ROOT/"5113056021_gpt_conversation.pdf").pages)==len(web["screenshots"]),
      "Screenshot PDF contains one image page per captured browser image")
for page,relative in zip(PdfReader(ROOT/"5113056021_gpt_conversation.pdf").pages,web["screenshots"]):
    page_images=[obj.get_object() for obj in page["/Resources"]["/XObject"].values()
                 if obj.get_object().get("/Subtype")=="/Image"]
    with Image.open(ROOT/relative) as original:
        if len(page_images)!=1:
            raise AssertionError("Expected one screenshot image per page: "+relative)
        embedded=page_images[0]
        decoded=embedded.get_data()
        # pypdf's page.images helper re-encodes extracted JPEGs. Compare the
        # actual PDF stream to the original JPEG, which ReportLab embeds intact.
        exact=decoded==(ROOT/relative).read_bytes() if original.format=="JPEG" else decoded==original.convert("RGB").tobytes()
        if not exact or (embedded["/Width"],embedded["/Height"])!=original.size:
            raise AssertionError("Screenshot pixels differ in PDF: "+relative)
checks.append("All screenshot pixels are preserved unchanged in the PDF appendix")

compliance=[
    ("Kaggle 資料來源與連結","已完成","data/train.csv、sources.md；報告第 1、13 節"),
    ("資料特徵數","已完成","排除 id 與目標後有 20 個特徵，同時落在 10–20 及 14–39 的範圍"),
    ("線性回歸預測","已完成","5113056021_hw2.py；主要模型 OLS20"),
    ("特徵選擇","已完成","SelectKBest 五折比較 k=14–20，另建立 KBest14、RFE14"),
    ("模型評估","已完成","10,000 筆測試資料；MAE、MSE、RMSE、R²、調整 R²"),
    ("預測圖與區間","已完成","output/figures/06_prediction_intervals.png；另存平均 CI、OLS PI"),
    ("CRISP-DM 六階段","已完成","報告第 1–11 節，包含模型儲存及新資料預測"),
    ("GPT 對話 PDF","部分完成","已附本次 ChatGPT 網頁技術問答截圖；先前 Codex 協作對話未收錄，未達所有對話的完整範圍"),
    ("NotebookLM 研究摘要","已完成" if manifest["notebooklm_complete"] else "未完成",
     f"摘要 {manifest.get('notebooklm_summary_chinese_characters',0)} 個中文字；附原始回覆、引用及筆記本網址"),
    ("GPT 輔助內容與 NotebookLM 摘要","已完成","報告第 12 節分別說明"),
    ("網路解法比較","已完成","參考 Kaggle 對稱特徵工程，比較 OLS、Ridge、HistGB 及加入總和的結果"),
    ("Kaggle 名次或預測評估","已完成","本次沒有參賽；結果以測試指標及預測圖呈現"),
    ("主程式、PDF 與 ZIP","已完成","5113056021_hw2.py；5113056021_hw2_report.pdf；5113056021_hw2.zip"),
    ("GitHub／Colab 連結","選填／未建立","原作業將此列為 optional；已附 README 流程與結果"),
]
checklist=["# 繳交項目整理","\n以下依作業說明整理本次完成的內容與檔案位置。",
           "\n| 作業項目 | 完成情形 | 內容與檔案位置 |","|---|---|---|"]
checklist.extend(f"| {a} | {b} | {c} |" for a,b,c in compliance)
checklist.extend(["\n## 作業說明",
                  "- 我使用 NotebookLM 閱讀六個來源，將摘要、完整提問與回覆分別存檔。" if manifest["notebooklm_complete"] else "- NotebookLM 研究摘要尚未完成。",
                  "- PDF 附錄改為本次 ChatGPT 網頁技術問答截圖；此版未包含先前協作對話的全文。",
                  "- 特徵選擇最後保留 20 欄，是因為交叉驗證誤差最低；另有 14 欄模型作為比較。",
                  "- 資料為合成資料，結果主要用來練習模型比較。若要應用到實際洪災預測，還需要實測資料進一步評估。"])
(ROOT/"COMPLIANCE_CHECKLIST.md").write_text("\n".join(checklist),encoding="utf-8")

status="程式、報告與研究摘要已完成檢查。" if manifest["notebooklm_complete"] else "程式分析已完成，NotebookLM 研究摘要尚未完成。"
lines=["# 程式執行與結果檢查",f"\n{status}","\n我使用檢查程式確認資料分組、預測數值及儲存模型的結果，以下列出執行紀錄。","\n## 資料與計算結果"]
lines.extend("- "+s for s in checks)
lines.extend(["\n## 分析時需要留意的地方","- 資料為合成資料，本次主要比較相似分布下的預測結果。",
              "- 交叉驗證用來選擇模型設定，最後再以保留測試資料計算誤差。",
              "- Conformal 預測區間需要校準與新資料可交換的前提。",
              "- 係數表示條件關聯，不能直接當成因果效果。",
              "\n## 報告排版","- PDF 已轉成圖片檢查文字、表格及圖表的位置。"])
if not manifest["notebooklm_complete"]:
    lines.extend(["\n## 指定繳交項目的缺件","- 尚未取得 NotebookLM 登入後的實際研究摘要。報告已明確標示，不可將目前壓縮檔視為全部要求完成。"])
(ROOT/"VALIDATION.md").write_text("\n".join(lines),encoding="utf-8")

files=[ROOT/name for name in ["5113056021_hw2.py","5113056021_hw2_report.pdf","5113056021_gpt_conversation.pdf",
    "README.md","requirements.txt","sources.md","notebooklm_research.md","VALIDATION.md","DATA_LICENSE.md","COMPLIANCE_CHECKLIST.md",
    "report_source.txt"]]
files.extend(sorted((ROOT/"tools").glob("*.py")))
files.extend(ROOT/"data"/name for name in ["train.csv","flood.csv","new_samples.csv"])
files.extend(sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "conversation_overview.json"))
if (ROOT/"notebooklm_result.json").exists():files.append(ROOT/"notebooklm_result.json")
if (ROOT/"notebooklm_raw.txt").exists():files.append(ROOT/"notebooklm_raw.txt")
if (ROOT/"notebooklm_dom.txt").exists():files.append(ROOT/"notebooklm_dom.txt")
sha={str(p.relative_to(ROOT)).replace("\\","/"):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(ROOT/"submission_manifest.json").write_text(json.dumps({"notebooklm_complete":manifest["notebooklm_complete"],"files":sha},ensure_ascii=False,indent=2),encoding="utf-8")
files.append(ROOT/"submission_manifest.json")
dest=ROOT/"5113056021_hw2.zip"
with zipfile.ZipFile(dest,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for path in files:archive.write(path,"5113056021_hw2/"+path.relative_to(ROOT).as_posix())
with zipfile.ZipFile(dest) as archive:
    check(archive.testzip() is None,"ZIP CRC integrity passed")
    check(len(archive.namelist())==len(files),"ZIP contains all explicit deliverables")
    check(not any(part in name.split("/") for name in archive.namelist() for part in [".deps","tmp",".git","__pycache__"]),
          "ZIP excludes local packages, caches and Git internals")
    for relative,digest in sha.items():
        if hashlib.sha256(archive.read("5113056021_hw2/"+relative)).hexdigest()!=digest:
            raise AssertionError("ZIP content hash mismatch: "+relative)
    checks.append("Every packaged deliverable matches its SHA-256 manifest")
print(json.dumps({"checks_passed":len(checks),"zip":str(dest),"files":len(files),"size_mb":round(dest.stat().st_size/1e6,2),"notebooklm_complete":manifest["notebooklm_complete"]},indent=2))
