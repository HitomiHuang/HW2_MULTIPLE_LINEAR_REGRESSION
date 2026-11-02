"""Rebuild the Chinese report and its captured ChatGPT web screenshot appendix.

python tools/build_report.py --session-log /path/to/this-session.jsonl
Rebuilds use output/chatgpt_screenshots.json and the original browser PNG files.
The optional session-log argument is retained for command compatibility.
"""
from __future__ import annotations
import argparse
from datetime import datetime
from html import escape
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from matplotlib import get_data_path
from PIL import Image as PILImage
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"output"
WIDTH=A4[0]-36*mm
INK=colors.HexColor("#273445")
BLUE=colors.HexColor("#2864A0")
LIGHT=colors.HexColor("#EDF3F9")
MUTED=colors.HexColor("#5B6878")
FONT_CANDIDATES=[Path("C:/Windows/Fonts/NotoSansTC-VF.ttf"),ROOT/"assets"/"NotoSansTC.ttf",Path("/usr/share/fonts/truetype/noto/NotoSansTC-Regular.ttf")]
for font_path in FONT_CANDIDATES:
    if font_path.exists():
        # Windows ships this variable font at weight 100. Freeze weight 400;
        # ReportLab otherwise embeds the hairline default glyphs.
        from fontTools.ttLib import TTFont as FontToolsFont
        from fontTools.varLib.instancer import instantiateVariableFont
        source_font=FontToolsFont(str(font_path))
        if "fvar" in source_font:
            frozen=ROOT/"tmp"/"fonts"/"NotoSansTC-Regular.ttf"
            frozen.parent.mkdir(parents=True,exist_ok=True)
            if not frozen.exists():
                regular=instantiateVariableFont(source_font,{"wght":400},inplace=False)
                regular.save(str(frozen))
            font_path=frozen
        source_font.close()
        pdfmetrics.registerFont(TTFont("CJK",str(font_path)))
        break
else:
    raise RuntimeError("A Chinese TrueType font is required. Put NotoSansTC.ttf in assets/.")
pdfmetrics.registerFontFamily("CJK",normal="CJK",bold="CJK",italic="CJK",boldItalic="CJK")
pdfmetrics.registerFont(TTFont("MathFallback",str(Path(get_data_path())/"fonts"/"ttf"/"DejaVuSans.ttf")))
STYLES={
    "body":ParagraphStyle("body",fontName="CJK",fontSize=10,leading=16,spaceAfter=7,textColor=INK,wordWrap="CJK"),
    "small":ParagraphStyle("small",fontName="CJK",fontSize=8,leading=12,spaceAfter=5,textColor=MUTED,wordWrap="CJK"),
    "cell":ParagraphStyle("cell",fontName="CJK",fontSize=8.1,leading=12,textColor=INK,wordWrap="CJK"),
    "h1":ParagraphStyle("h1",fontName="CJK",fontSize=19,leading=27,textColor=BLUE,spaceAfter=14,wordWrap="CJK"),
    "h2":ParagraphStyle("h2",fontName="CJK",fontSize=12,leading=18,textColor=BLUE,spaceBefore=6,spaceAfter=7,wordWrap="CJK"),
    "cover":ParagraphStyle("cover",fontName="CJK",fontSize=29,leading=39,textColor=INK,spaceAfter=18,wordWrap="CJK"),
    "kpi":ParagraphStyle("kpi",fontName="CJK",fontSize=21,leading=29,textColor=BLUE,alignment=TA_CENTER),
    "center":ParagraphStyle("center",fontName="CJK",fontSize=9,leading=14,textColor=INK,alignment=TA_CENTER),
}
SOURCE_TEXT=[]


def p(text,style="body",raw=False):
    if not raw: SOURCE_TEXT.append(text)
    markup=text if raw else escape(str(text)).replace("\n","<br/>")
    # These mathematical glyphs are absent from the Chinese font's cmap.
    for char in "ŷ₀ⱼ":
        markup=markup.replace(char,f'<font name="MathFallback">{char}</font>')
    return Paragraph(markup,STYLES[style])


def table(headers,rows,widths=None):
    cells=[[p(h,"cell") for h in headers]]+[[p("" if v is None else str(v),"cell") for v in row] for row in rows]
    t=Table(cells,colWidths=widths or [WIDTH/len(headers)]*len(headers),repeatRows=1,hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),LIGHT),("TEXTCOLOR",(0,0),(-1,0),BLUE),
        ("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),6),
        ("RIGHTPADDING",(0,0),(-1,-1),6),("TOPPADDING",(0,0),(-1,-1),6),
        ("BOTTOMPADDING",(0,0),(-1,-1),6),("LINEBELOW",(0,0),(-1,0),.6,BLUE),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F8FAFC")]),
        ("LINEBELOW",(0,-1),(-1,-1),.3,colors.HexColor("#CBD4DF")),
    ]))
    return t


def image(name,max_height=100*mm):
    path=OUT/"figures"/name
    with PILImage.open(path) as im: w,h=im.size
    scale=min(WIDTH/w,max_height/h)
    SOURCE_TEXT.append(f"[圖：output/figures/{name}]")
    return Image(str(path),width=w*scale,height=h*scale,hAlign="CENTER")


def footer(canvas,doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#CBD4DF"));canvas.setLineWidth(.4)
    canvas.line(18*mm,15*mm,A4[0]-18*mm,15*mm)
    canvas.setFont("CJK",8);canvas.setFillColor(MUTED)
    canvas.drawString(18*mm,10*mm,"5113056021 | HW2 Multiple Linear Regression")
    canvas.drawRightString(A4[0]-18*mm,10*mm,str(doc.page))
    canvas.restoreState()


def doc(path,story):
    SimpleDocTemplate(str(path),pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=17*mm,bottomMargin=22*mm,
        title="5113056021 HW2 多元線性回歸",author="5113056021").build(story,onFirstPage=footer,onLaterPages=footer)


def export_conversation(session_log=None):
    """Build the appendix directly from captured ChatGPT browser images."""
    index=OUT/"chatgpt_screenshots.json"
    if not index.exists():
        raise RuntimeError("Capture the real ChatGPT web conversation before building the PDF.")
    data=json.loads(index.read_text(encoding="utf-8"))
    if not data.get("verified_in_browser") or not data["conversation_url"].startswith("https://chatgpt.com/c/"):
        raise ValueError("A verified ChatGPT web conversation is required.")
    story=[]
    for number,relative in enumerate(data["screenshots"],1):
        if story: story.append(PageBreak())
        story.append(p("附錄：GPT 技術問答截圖","h1"))
        story.append(p(f"網頁畫面 {number} / {len(data['screenshots'])}","small"))
        if number==1:
            story.append(p("以下為本次在 ChatGPT 網頁進行的資料選擇、特徵選擇、預測區間與結論確認問答。", "small"))
            story.append(p("對話網址："+data["conversation_url"],"small"))
        image_path=ROOT/relative
        with PILImage.open(image_path) as screenshot: w,h=screenshot.size
        scale=min(WIDTH/w,218*mm/h)
        story.append(Image(str(image_path),width=w*scale,height=h*scale,hAlign="CENTER"))
        story.append(Spacer(1,6))
        story.append(p("擷取時間（台北）："+data["exported_at"],"small"))
    path=ROOT/"5113056021_gpt_conversation.pdf"
    doc(path,story)
    return path,data


def report(conversation_pdf,conversation):
    meta=json.loads((OUT/"run_metadata.json").read_text(encoding="utf-8"))
    diag=json.loads((OUT/"tables"/"diagnostics.json").read_text(encoding="utf-8"))
    inter=json.loads((OUT/"tables"/"interval_metrics.json").read_text(encoding="utf-8"))
    scores=pd.read_csv(OUT/"tables"/"model_metrics.csv").set_index("model")
    cv=pd.read_csv(OUT/"tables"/"feature_selection_cv.csv")
    rank=pd.read_csv(OUT/"tables"/"feature_ranking.csv")
    coef=pd.read_csv(OUT/"tables"/"ols_coefficients.csv")
    rawcoef=json.loads((OUT/"tables"/"original_unit_equation.json").read_text(encoding="utf-8"))
    desc=pd.read_csv(OUT/"tables"/"training_descriptives.csv",index_col=0)
    ols=scores.loc["OLS_selected"];hgb=scores.loc["HistGB_with_sum"]
    improvement=(ols.RMSE-hgb.RMSE)/ols.RMSE*100
    nb_path=ROOT/"notebooklm_result.json"
    nb=json.loads(nb_path.read_text(encoding="utf-8")) if nb_path.exists() else None
    nb_chars=len(re.findall(r"[\u3400-\u9fff]",nb.get("summary", ""))) if nb else 0
    nb_complete=bool(nb and nb.get("verified_in_notebooklm") and nb_chars>=100
                     and nb.get("notebook_url", "").startswith(("https://notebook.google.com/notebook/", "https://notebooklm.google.com/notebook/"))
                     and any(s.get("imported") and "kaggle.com" in s.get("url", "") for s in nb.get("sources", []))
                     and (ROOT/"notebooklm_raw.txt").exists())
    story=[]

    def page(title):
        if story: story.append(PageBreak())
        story.append(p(title,"h1"))
    def body(text): story.append(p(text))
    def small(text): story.append(p(text,"small"))
    def h(text): story.append(p(text,"h2"))

    story.append(Spacer(1,13*mm));story.append(p("HW2 多元線性回歸\n洪水風險分數預測","cover"))
    body("學號：5113056021　｜　完成日期：2026-10-20")
    body("本次作業使用 Kaggle 洪水資料，依照 CRISP-DM 流程進行資料整理、特徵選擇、多元線性回歸與預測結果分析。")
    story.append(Spacer(1,8*mm))
    kpis=Table([[p(f"{ols.R2:.4f}","kpi"),p(f"{ols.RMSE:.4f}","kpi"),p(f"{inter['conformal_coverage']*100:.2f}%","kpi")],
                [p("測試集 R²","center"),p("測試集 RMSE","center"),p("95% PI 實測覆蓋率","center")]],colWidths=[WIDTH/3]*3)
    kpis.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),LIGHT),("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10)]))
    story.append(kpis);story.append(Spacer(1,8*mm))
    h("摘要")
    body(f"本次從 Kaggle 的 train.csv（1,117,957 筆）隨機抽取 50,000 筆，以 20 個原始特徵預測 FloodProbability。資料分成訓練 32,000 筆、校準 8,000 筆及測試 10,000 筆。我先用五折交叉驗證比較保留 14 至 20 個特徵的結果，再以選出的設定建立多元線性回歸。這組比較以保留 20 個特徵的誤差最低，測試 RMSE 為 {ols.RMSE:.4f}、MAE 為 {ols.MAE:.4f}。")
    body(f"減少至 14 個特徵後，預測誤差增加；Ridge 與 OLS 的結果則幾乎相同。加入特徵總和的 HistGB 將 RMSE 降至 {hgb.RMSE:.4f}，比主要線性模型降低 {improvement:.2f}%。因此，後續會優先保留原始特徵，並比較不同特徵表示對預測的影響。")
    body("由於資料為合成資料，本作業的結果主要用來比較模型與練習分析流程。若要應用到實際洪災預測，仍需要有時間、地點及真實事件紀錄的資料進一步測試。")
    small("資料來源：Kaggle Flood Prediction Dataset。分析工具：Python、scikit-learn、statsmodels。")
    if not nb_complete: small("NotebookLM 研究摘要尚未完成，相關資料整理於第 12 節。")

    page("1｜Business Understanding")
    h("題目選擇與分析目標")
    body("這份資料同時包含環境、人口與基礎設施等評分，欄位數也適合本次作業。我想比較三件事：多個特徵一起使用，能否比單一特徵及平均值預測更準確；刪除部分特徵後，誤差如何變化；加入特徵工程後，非線性模型是否有進一步改善。")
    body("FloodProbability 是連續數值，因此使用回歸模型。資料沒有提供時間欄位，本次不採用自我回歸。我以 RMSE 作為主要比較指標，同時列出 MAE、MSE、R² 與調整 R²，並利用 95% 預測區間呈現個別預測的不確定性。")
    h("資料來源與研究範圍 [1][2]")
    story.append(table(["項目","本作業設定"],[
        ["下載來源","Naiya Khalid：Flood Prediction Dataset，Kaggle，version 2"],
        ["使用檔案","train.csv；1,117,957 筆、22 欄"],
        ["欄位計數","20 個輸入特徵 + FloodProbability 目標 + id 識別碼"],
        ["抽樣","先以 random_state=42 固定抽取 50,000 筆，再切分"],
        ["排除","id 不作為輸入；競賽 test.csv 沒有目標值，不用於計算誤差"],
        ["來源性質","原競賽說明 train/test 由深度學習模型生成，屬合成資料"],
    ],[36*mm,WIDTH-36*mm]))
    h("為何沒有直接用 50,000 筆 flood.csv")
    body("整理資料時，我發現 flood.csv 的 FloodProbability 恰好等於 20 個特徵總和除以 200，逐筆計算的最大差為 0。線性回歸很容易學到這個固定關係，因此我改用同一資料集內較有雜訊的 train.csv 進行主要分析，flood.csv 則只用來說明資料特性。")
    small("資料集介紹中的 50,000 筆是指 flood.csv；本次使用的 train.csv 有 1,117,957 筆。計算特徵數時，已排除 id 與預測目標。原始資料的蒐集方式與地理範圍未有明確記錄。[1]")

    page("2｜Data Understanding")
    body("資料包含 20 個數值型特徵，以下列出欄位名稱、中文說明及訓練資料的統計值。這些欄位是評分，來源沒有提供明確的實測單位，因此解釋係數時，需要留意分數與實際環境條件之間的差異。[1][2]")
    cn=["季風強度","地形與排水","河川管理","森林砍伐","都市化","氣候變遷","水壩品質評分","淤積","農業活動","土地侵占","防災準備不足","排水系統評分","海岸脆弱度","山崩","集水區評分","基礎設施劣化","人口評分","濕地流失","規劃不足","政治因素"]
    rows=[]
    for feature,label in zip(meta["input_features"],cn):
        d=desc.loc[feature]
        rows.append([feature,label,f"{int(d['min'])} - {int(d['max'])}",f"{d['mean']:.2f}"])
    story.append(table(["原始特徵名稱","中文辨識","訓練範圍","平均"],rows,[79*mm,42*mm,29*mm,WIDTH-150*mm]))
    small("表 1 使用 32,000 筆訓練資料計算。50,000 筆分析資料中沒有缺失值，排除 id 後也沒有完全相同的重複列。目標值為浮點數，範圍為 0.285 至 0.725。完整統計表見 training_descriptives.csv。")

    page("3｜資料分布與關聯")
    story.append(image("01_target_distribution.png",70*mm))
    small("圖 1：32,000 筆訓練目標分布，單位為合成分數；集中於 0.5 左右。資料來源：[1][2]，本作業自行計算。")
    story.append(image("02_correlations.png",133*mm))
    body(f"從相關矩陣可以看出，特徵之間的線性相關程度普遍偏低。最大 VIF 為 {diag['max_vif']:.4f}，表示這次模型沒有明顯的多重共線性問題。不過，相關程度低並不代表各欄位的實際作用可以直接由模型判定。")
    small("圖 2：20 × 20 訓練集 Pearson 相關矩陣，色階固定 -1 至 1。資料來源：[1][2]，未使用測試標籤選取欄位。")

    page("4｜Data Preparation")
    h("資料切分")
    story.append(table(["分割","筆數／比例","用途"],[
        ["Proper training","32,000／64%","訓練、五折 CV、特徵與超參數選擇"],
        ["Calibration","8,000／16%","模型固定後，估計 conformal 殘差分位數"],
        ["Test","10,000／20%","設定固定後，一次彙整所有模型及區間評估"],
    ],[39*mm,43*mm,WIDTH-82*mm]))
    body("資料抽樣與切分都固定 seed=42，方便重新執行時取得相同結果。我先保留 20% 作為測試資料，再從剩餘資料中取出 20% 作為校準資料。三組資料的 id 沒有重複，分組結果存於 split_manifest.csv。因為沒有日期及地區欄位，本次採隨機切分，評估範圍限於相似分布的資料。")
    h("資料前處理 [4][5]")
    body("前處理依序使用 SimpleImputer(median)、StandardScaler、SelectKBest / RFE，再接上 LinearRegression。StandardScaler 將各欄轉成平均為 0、標準差為 1 的尺度，讓 RFE 比較不同欄位係數時較一致。這些步驟放在同一個 Pipeline，每一折都只從訓練部分估計轉換規則，再套用到驗證部分，以避免資料洩漏。本次沒有缺失值，補值步驟不會改變資料。")
    body("所有特徵都是數值，不需要類別編碼。我保留原始觀測值，沒有依照測試結果刪除離群值。這次模型的測試預測都落在 0 至 1 之間，但線性回歸本身沒有輸出範圍限制。")
    h("評估量的定義")
    body("MAE = mean(|y - ŷ|)，單位與目標相同；MSE = mean((y - ŷ)²)；RMSE = sqrt(MSE)，較重視大誤差。R² = 1 - SSE/SST，以測試集自身平均作 SST 的中心。")
    body("調整 R² = 1 - (1 - R²)(n - 1)/(n - p - 1)，本報告 n = 10,000，p 為線性模型輸入欄數；僅作描述性比較，不當成測試集上的選模準則。Ridge 的有效自由度與 p 不同，表中數值是相同公式的近似描述；樹模型不填此值。")
    small("同一組交叉驗證同時用來選 k 與 Ridge 的 alpha，因此 CV 分數主要作為選擇設定的依據。本次未使用巢狀交叉驗證，最後仍以沒有參與調整的測試資料評估表現。")

    page("5｜Modeling：特徵選擇")
    body("我使用 SelectKBest 與 RFE 兩種方法。SelectKBest 以 f_regression 計算各欄與目標之間的線性關係分數，再比較保留 14 至 20 欄的五折 CV 結果。RFE 則反覆訓練 OLS，依標準化後係數的大小逐步刪除特徵，直到留下 14 欄。前者分別評分各欄，後者則根據多個欄位一起建模的結果篩選。[4][5]")
    story.append(image("03_feature_selection.png",78*mm))
    rows=[[int(r.k),f"{r.cv_rmse:.6f}",f"{r.cv_std:.6f}"] for r in cv.itertuples()]
    story.append(table(["k","五折平均 RMSE","折間標準差"],rows,[28*mm,75*mm,WIDTH-103*mm]))
    body("由圖與表可看出，特徵數由 14 增加至 20 時，CV RMSE 持續下降。因此，主要線性模型保留全部 20 欄。這個結果顯示，在本次比較的範圍內，被刪除的欄位仍含有預測資訊；固定保留 14 欄的兩種模型，則留到測試階段一起比較。")
    removed=rank.loc[~rank.rfe14_selected,"feature"].tolist()
    small("RFE14 實際移除："+"、".join(removed)+"。固定 14 特徵模型的測試結果另列於第 7 節；完整排名與兩種選擇標記見 feature_ranking.csv。圖中誤差棒為折間標準差，非信賴區間。")

    page("6｜Modeling：OLS 規格與係數")
    body("主要模型為多元線性回歸：ŷ = β₀ + Σ βⱼzⱼ，其中 zⱼ = (xⱼ - 訓練平均) / 訓練標準差。OLS 透過最小化訓練資料的殘差平方和估計係數，讓 20 個特徵共同解釋目標值。對帶截距且沒有正則化的 OLS 而言，標準化只改變係數的單位，不改變預測結果。")
    body(f"轉回原始評分單位後，截距為 {rawcoef['intercept']:.6f}，各欄係數介於 {min(rawcoef['coefficients'].values()):.6f} 至 {max(rawcoef['coefficients'].values()):.6f}。例如 MonsoonIntensity 每增加 1 分，其餘欄位固定，模型預測約增加 {rawcoef['coefficients']['MonsoonIntensity']:.6f}；這是條件關聯。")
    story.append(image("08_coefficients.png",137*mm))
    small("圖 4：標準化係數及 HC3 異質變異穩健 95% 信賴區間，使用 proper training。全部係數、區間、p 值及原單位方程式分別存於 ols_coefficients.csv 與 original_unit_equation.json。")
    body("各欄位的係數很接近，因此我沒有根據微小差距判定哪個因素最重要。HC3 用來估計對異質變異較穩健的標準誤，但無法處理模型遺漏的非線性關係。這些區間是在選定模型後計算，主要用來探索資料中的條件關聯。")

    page("7｜Evaluation：保留測試集")
    body("所有模型都使用相同的 32,000 筆訓練資料與 10,000 筆測試資料。特徵數及 Ridge 參數由訓練階段決定，HistGB 則使用事先設定的參數。以下先檢查主要線性模型，再比較單一特徵、刪欄及非線性模型的差異。")
    labels={"Mean_baseline":"平均值基線","Single_feature_OLS":"單一原始特徵 OLS","SelectKBest14_OLS":"KBest14 OLS","RFE14_OLS":"RFE14 OLS","OLS_selected":"主模型 OLS20","Ridge":"Ridge20","HistGB_raw":"HistGB 原始20","HistGB_with_sum":"HistGB20 + 總和","Sum_feature_OLS":"總和單變量 OLS"}
    rows=[]
    for key,label in labels.items():
        r=scores.loc[key]
        rows.append([label,f"{r.CV_RMSE:.4f}",f"{r.MAE:.4f}",f"{r.MSE:.6f}",f"{r.RMSE:.4f}",f"{r.R2:.4f}"])
    story.append(table(["模型","CV RMSE","MAE","MSE","RMSE","R²"],rows,[49*mm,26*mm,24*mm,29*mm,24*mm,WIDTH-152*mm]))
    story.append(Spacer(1,5*mm));story.append(image("04_model_comparison.png",83*mm))
    body(f"OLS20 的 RMSE 為 {ols.RMSE:.4f}，低於平均值基線的 {scores.loc['Mean_baseline'].RMSE:.4f}，也低於 RFE14 的 {scores.loc['RFE14_OLS'].RMSE:.4f}。調整 R² 為 {ols.Adjusted_R2:.4f}。OLS_all20 與 OLS_selected 相同，是因為特徵選擇最後保留全部 20 欄；Ridge 選出的 alpha 為 1，結果與 OLS 幾乎一致，本次沒有觀察到明顯改善。")
    small("單一原始特徵由訓練資料選出 DamsQuality。『總和單變量 OLS』仍須取得全部 20 個原始輸入，只把它們壓成一個導出欄；不是只蒐集一個原始特徵。其餘調整 R²、訓練誤差與 CV 標準差見 model_metrics.csv。")

    page("8｜預測值與信賴／預測區間")
    story.append(image("05_actual_vs_prediction.png",108*mm))
    body("預測與實際值沿理想對角線分布，但仍有殘差；較高分數附近亦可見偏離。上圖固定抽取 2,500 筆呈現，所有數值指標仍由完整 10,000 筆計算。")
    story.append(table(["區間","名目水準","測試覆蓋率","平均寬度"],[
        ["平均反應 CI","95%","不適用單一觀測",f"{inter['mean_ci_mean_width']:.5f}"],
        ["OLS 單一觀測 PI","95%",f"{inter['ols_pi_coverage']*100:.2f}%",f"{inter['ols_pi_mean_width']:.5f}"],
        ["Split-conformal PI","95%",f"{inter['conformal_coverage']*100:.2f}%",f"{inter['conformal_mean_width']:.5f}"],
    ],[58*mm,29*mm,48*mm,WIDTH-135*mm]))
    body("信賴區間（CI）估計同樣輸入條件下的平均反應 E[Y|X]；預測區間（PI）則對應單一新觀測 Y，還要包含個體殘差，所以通常較寬。表中平均 CI 的寬度約為 0.002，OLS PI 約為 0.078，兩者回答的問題不同。我使用 statsmodels.get_prediction().summary_frame() 同時計算這兩種區間。[6]")
    small("本次沒有 [0,1] 之外的點預測；未裁切區間，保留其原始計算結果。測試覆蓋率與平均寬度為經驗評估，不是額外的選模準則。")

    page("9｜95% 預測區間與覆蓋率")
    story.append(image("06_prediction_intervals.png",105*mm))
    body("圖中取固定隨機的 120 筆測試個案，再依預測值排序；橫軸不是時間。藍色區帶為 95% split-conformal 預測區間，金色點是實際目標。即使模型平均誤差小，單一個案仍需要較寬的預測範圍。")
    h("如何獨立校準 [8]")
    body("主模型以 32,000 筆資料訓練後固定。對 8,000 筆獨立校準資料計算 |y - ŷ|，取 ceil((8,000 + 1) × 0.95) = 7,601 小的殘差。q = 0.040017，因此每筆區間為 [ŷ - q, ŷ + q]。測試資料沒有參與 q 的估計。")
    body("10,000 筆測試資料中，有 9,486 筆實際值落在區間內，覆蓋率為 94.86%。Conformal PI 的平均寬度約為 0.080，略寬於 OLS PI，但本次覆蓋率也較接近設定的 95%。這是同一組測試資料上的比較，仍需觀察其他資料分割下是否有相近結果。")
    body("Split-conformal 不要求殘差服從常態分布，但需要校準與新資料可交換，常見的充分條件是資料獨立且同分布。它提供的是整體的邊際覆蓋，不能直接推成每個地區或每個分數範圍都有 95% 覆蓋；遇到時空相依或分布改變時，需要重新設計切分與校準方式。")
    small("完整個案的平均 CI、OLS PI 與 conformal PI 均存於 test_predictions.csv，可逐筆檢查。")

    page("10｜五項回歸假設與限制")
    story.append(image("07_diagnostics.png",72*mm))
    story.append(table(["檢查","證據（proper training）","解釋與處理"],[
        ["線性／規格","RESET F = 397.88；p = 2.08 × 10^-171","拒絕簡單線性規格，可能仍有非線性訊號。"],
        ["誤差獨立","沒有時間／空間群組；DW = 2.006","任意列序的 DW 無法證明獨立；保留為未驗證假設。"],
        ["等變異","Breusch-Pagan p = 3.13 × 10^-277","存在異質變異；係數用 HC3，個案區間另作校準。"],
        ["殘差常態","JB = 4,833.98；p < 10^-300","右偏 0.691、峰度 4.310；常態假設不成立。"],
        ["多重共線性",f"最大 VIF = {diag['max_vif']:.4f}","未見明顯共線性；Ridge 的改善有限。"],
    ],[30*mm,67*mm,WIDTH-97*mm]))
    body("RESET、Breusch-Pagan 與 JB 檢定的 p 值都很小，殘差圖及 Q-Q 圖也顯示模型仍有偏離線性、等變異與常態假設的情況。因此，我保留 OLS 作為容易解釋的基準，同時比較非線性模型，並另外校準預測區間。這次 OLS PI 的測試覆蓋率為 94.28%。")
    body("HC3 處理的是係數標準誤對異質變異的敏感性，conformal PI 處理的是新觀測的預測範圍，兩者用途不同。另外，大樣本下的假設檢定較敏感，需要搭配圖形及誤差大小一起判讀。JB 的 p 值因浮點數下溢顯示為 0，因此表中以 p < 10^-300 表示。")

    page("11｜網路解法比較與 Deployment")
    h("參考解法與比較結果")
    body("閱讀 Kaggle 的討論後，我注意到參賽者建議使用各欄總和、排序等對稱特徵，並討論原始資料中各特徵可能具有相近作用的假說。[3] 因此，我加入各列的特徵總和，觀察相同資料切分下的預測結果是否改善。")
    body(f"只使用原始特徵的 HistGB，其測試 RMSE 為 {scores.loc['HistGB_raw'].RMSE:.4f}，高於 OLS；加入總和特徵後，RMSE 降為 {hgb.RMSE:.4f}，R² 為 {hgb.R2:.4f}，相較主要線性模型的 RMSE 改善 {improvement:.2f}%。這次結果顯示，將合適的特徵加入模型，對預測有實際幫助。")
    body("Ridge 在平方誤差外加入 L2 係數懲罰，限制係數過大；HistGB 則以多棵決策樹逐步修正預測誤差，能表示非線性及交互作用。[7] 本次 HistGB 設定為 max_iter=180、max_leaf_nodes=15、learning_rate=0.08、l2_regularization=1，關閉 early stopping。由於沒有進一步搜尋參數，這裡比較的是上述設定下的結果。")
    h("Deployment：儲存模型與新資料預測")
    body("我將前處理流程、模型參數與校準分位數一起存成檔案。安裝 requirements.txt 後，執行 python 5113056021_hw2.py 可以重新產生分析結果；執行 python 5113056021_hw2.py --predict data/new_samples.csv，則可載入模型，對 5 筆範例資料進行預測。")
    body("新資料需要包含相同的 20 個特徵。程式會輸出點預測、平均反應信賴區間、OLS 預測區間、conformal 預測區間，以及是否超出訓練資料範圍的標記，結果存於 output/new_predictions.csv。")
    body("目前程式以本機 CSV 輸入及輸出為主。若未來應用到實際地區，需要加入真實洪災事件與時間、地點資料，並重新評估誤差及區間覆蓋率。重新訓練模型後，也需要重新計算校準分位數。")
    small("本次沒有提交 Kaggle 競賽，因此沒有競賽名次；結果以測試資料的評估指標與預測圖呈現。")

    page("12｜NotebookLM 摘要與 GPT 輔助內容")
    h("NotebookLM 摘要")
    if nb_complete:
        body(nb["summary"])
        small("研究筆記："+nb.get("notebook_url","未記錄網址"))
        small("研究日期："+nb.get("retrieved_date","2026-10-20")+f"；摘要共 {nb_chars} 個中文字。")
        small("我將六個來源匯入 NotebookLM，整理為上述摘要。完整提問與回覆另存於 notebooklm_raw.txt，來源資訊見 notebooklm_result.json。")
        small("引用對照：〔N1〕= [2]；〔N2〕= [3]；〔N3〕= [4]；〔N4〕= [5]；〔N5〕= [6]；〔N6〕= [8]。本文保留摘要內容，並統一引用格式。")
    else:
        body("尚未完成：NotebookLM / notebooklm.google.com 在本次操作中要求 Google 帳戶登入，尚未取得已登入狀態下的實際來源研究回覆。因此本報告不把 GPT 撰寫的內容冒標為 NotebookLM 摘要。這是目前唯一未完成的指定研究項目，尚未達成『NotebookLM 摘要至少 100 字』要求。")
        body("已準備 notebooklm_research.md，包含 6 個公開研究來源與可直接貼入的繁體中文提問。登入後應匯入可讀取的來源，產生至少 100 字摘要，保留實際回覆及筆記本網址，再更新本節與壓縮檔。若網址匯入失敗，應明確記錄，不可假裝已讀取。")
    h("GPT 輔助內容")
    body("本次作業使用 GPT 協助尋找資料與參考文件、撰寫及修改 Python 程式、整理圖表、解釋統計結果，以及修訂報告文字。分析流程包含特徵選擇、回歸建模、模型比較與預測區間；報告中的數值皆取自程式執行結果。")
    body("本次在 ChatGPT 網頁詢問資料選擇、特徵選擇、預測區間與作業結論，將實際網頁畫面截圖後收錄為 PDF 附錄。提問中的資料筆數與評估數值取自已完成的實驗；網頁回覆作為技術解釋的補充。")
    small("對話紀錄整理時間（台北）："+conversation["exported_at"]+"。")
    h("程式結果檢查")
    body("程式執行後，scikit-learn 與 statsmodels 的 OLS 預測值一致，儲存的模型也能重新載入並完成 5 筆範例預測。資料分組、模型係數及逐筆預測結果均另外存檔，方便之後重跑及比較。")

    page("13｜參考資料與執行環境")
    sources=[
        ("[1] Naiya Khalid. Flood Prediction Dataset, version 2. Kaggle.","https://www.kaggle.com/datasets/naiyakhalid/flood-prediction-dataset"),
        ("[2] Kaggle. Regression with a Flood Prediction Dataset (S4E5), Data.","https://www.kaggle.com/competitions/playground-series-s4e5/data"),
        ("[3] broccoli beef. Sorting along the feature axis as feature engineering. Kaggle.","https://www.kaggle.com/competitions/playground-series-s4e5/discussion/499579"),
        ("[4] scikit-learn. Feature selection.","https://scikit-learn.org/stable/modules/feature_selection.html"),
        ("[5] scikit-learn. Common pitfalls and recommended practices.","https://scikit-learn.org/stable/common_pitfalls.html"),
        ("[6] statsmodels. OLSResults.get_prediction.","https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLSResults.get_prediction.html"),
        ("[7] scikit-learn. Histogram-based Gradient Boosting.","https://scikit-learn.org/stable/modules/ensemble.html#histogram-based-gradient-boosting"),
        ("[8] Angelopoulos & Bates (2021/2022). A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification.","https://arxiv.org/abs/2107.07511"),
    ]
    for label,url in sources:
        small(label)
        story.append(p(f'<link href="{escape(url,quote=True)}" color="#2864A0">{escape(url)}</link>',"small",raw=True))
    small("查閱日期：2026-10-20。下載頁標示 CC0，原競賽資料頁標示 CC BY 4.0；本作業保留兩個來源連結。參考內容與用途整理於 sources.md。")
    h("執行環境")
    small("原始 train.csv SHA-256：\n"+meta["source_sha256"])
    small("環境："+"；".join(f"{k} {v}" for k,v in meta["versions"].items()))
    h("資料限制與待補資料")
    body("目前缺少真實洪災事件標記、觀測日期、地理位置，以及各評分欄位的實測單位與方向，因此無法評估不同時期或地區的預測能力。若要做實際洪災應用，需要先補上這些資料。不同分數範圍的覆蓋率、跨欄排序特徵與更完整的參數搜尋，也都列為後續可做的實驗，本次尚未執行。")

    page("14｜結論與作業內容整理")
    body(f"本次 OLS20 的測試 R² 為 {ols.R2:.4f}、RMSE 為 {ols.RMSE:.4f}。RFE14 的 RMSE 為 {scores.loc['RFE14_OLS'].RMSE:.4f}，刪欄後沒有改善；Ridge 也與 OLS 接近。相較之下，加入總和特徵的 HistGB 將 RMSE 降至 {hgb.RMSE:.4f}。根據這組實驗，後續會優先保留原始特徵，並繼續比較特徵表示與非線性模型。")
    body("區間評估方面，95% conformal PI 的測試覆蓋率為 94.86%，平均寬度約 0.080。結合殘差診斷來看，OLS 能提供有用的基準，但仍留下非線性及不等變異的問題。這些結果只對應本次合成資料與切分方式，實際洪災應用仍需要額外資料。以下整理分析內容與檔案位置。")
    rows=[
        ["資料與特徵","Kaggle train.csv；20 個輸入","第 1–3 節；data/"],
        ["資料整理","訓練、校準與測試資料切分","第 4 節"],
        ["特徵選擇","SelectKBest、RFE14","第 5 節"],
        ["模型與係數","多元線性回歸與 HC3 係數區間","第 6 節"],
        ["評估與預測圖","MAE、MSE、RMSE、R²、95% 預測區間","第 7–10 節；output/"],
        ["解法比較與新資料預測","Ridge、HistGB、總和特徵及模型存檔","第 11 節"],
        ["NotebookLM 摘要",f"研究摘要 {nb_chars} 個中文字","第 12 節；notebooklm_raw.txt"],
        ["GPT 輔助內容","使用方式說明與對話紀錄","第 12 節及附錄"],
        ["主程式","資料分析與預測功能","5113056021_hw2.py"],
        ["作業檔案","PDF、程式、資料與說明文件","5113056021_hw2.zip；README.md"],
    ]
    story.append(table(["項目","內容","章節或檔案"],rows,[36*mm,75*mm,WIDTH-111*mm]))
    story.append(Spacer(1,4*mm))
    small("本次沒有提交 Kaggle 競賽，也未建立 GitHub 或 Colab 連結；程式執行方式與結果整理於 README.md。")
    h("附錄：GPT 對話紀錄")
    small("以下依畫面順序附上 ChatGPT 網頁的技術問答截圖，包含提問、說明、修正與結論確認。附錄使用獨立頁碼。")

    tmp=ROOT/"tmp"/"pdfs";tmp.mkdir(parents=True,exist_ok=True)
    base=tmp/"report_body.pdf";doc(base,story)
    dest=ROOT/"5113056021_hw2_report.pdf"
    writer=PdfWriter();writer.append(str(base));writer.append(str(conversation_pdf))
    writer.add_metadata({"/Title":"5113056021 HW2 多元線性回歸與 CRISP-DM","/Author":"5113056021"})
    with dest.open("wb") as f:writer.write(f)
    (ROOT/"report_source.txt").write_text("\n\n".join(SOURCE_TEXT),encoding="utf-8")
    info={"report_pages":len(PdfReader(base).pages),"conversation_pages":len(PdfReader(conversation_pdf).pages),"combined_pages":len(PdfReader(dest).pages),
          "notebooklm_complete":nb_complete,"notebooklm_summary_chinese_characters":nb_chars,"conversation_screenshot_pages":len(conversation["screenshots"]),"conversation_scope":"supplementary ChatGPT web questions and answers",
          "report_file":dest.name,"conversation_file":conversation_pdf.name}
    (OUT/"report_manifest.json").write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(info,ensure_ascii=False,indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--session-log",type=Path)
    args=parser.parse_args()
    convo,data=export_conversation(args.session_log)
    SOURCE_TEXT.clear()
    report(convo,data)
