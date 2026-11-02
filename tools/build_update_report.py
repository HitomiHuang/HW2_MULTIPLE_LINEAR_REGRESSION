"""Build the revised report and export available user-visible collaboration text."""
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from html import escape
import importlib.util
import json
import re
import shutil
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from reportlab.platypus import PageBreak,Spacer,Image
from reportlab.lib.units import mm
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import build_report as pdf
WEB=ROOT/'web/dist'
OUT=ROOT/'output'
FIG=OUT/'web_figures'
FIG.mkdir(exist_ok=True)
LIVE='https://hw2-regression-lab-5113056021.ivy819.chatgpt.site'
GITHUB='https://github.com/HitomiHuang/HW2_MULTIPLE_LINEAR_REGRESSION'

def figure(name,title,r):
    rows=r['predictions'][::max(1,len(r['predictions'])//100)][:100]
    rows=sorted(rows,key=lambda p:p['prediction'])
    x=np.arange(1,len(rows)+1)
    fig,ax=plt.subplots(figsize=(8.5,3.6),layout='constrained')
    ax.fill_between(x,[p['lower'] for p in rows],[p['upper'] for p in rows],color='#91AA7C',alpha=.25,label='95% split-conformal prediction interval')
    ax.plot(x,[p['prediction'] for p in rows],color='#28685b',label='Prediction',lw=1.5)
    ax.scatter(x,[p['actual'] for p in rows],s=12,color='#c98245',label='Observed',zorder=3)
    ax.set(title=title,xlabel='Held-out cases sorted by prediction (not time)',ylabel=r['target'])
    ax.grid(alpha=.15);ax.spines[['top','right']].set_visible(False)
    ax.legend(fontsize=8,frameon=False,loc='upper left')
    fig.savefig(FIG/name,dpi=180);plt.close(fig)

def img(name,height=85*mm):
    from PIL import Image as PI
    path=FIG/name
    with PI.open(path) as im:w,h=im.size
    scale=min(pdf.WIDTH/w,height/h)
    return Image(str(path),width=w*scale,height=h*scale)

def export_conversation():
    prior=json.loads((ROOT/'gpt_conversation.json').read_text(encoding='utf-8'))['messages']
    session=Path('C:/Users/black/.codex/sessions/2026/11/02/rollout-2026-11-02T23-34-06-01a19ce5-77aa-7940-bd31-75c52930e315.jsonl')
    current=[]
    for line in session.read_text(encoding='utf-8').splitlines():
        entry=json.loads(line)
        payload=entry.get('payload',{})
        if entry.get('type')!='response_item' or payload.get('type')!='message' or payload.get('role') not in ['user','assistant']:
            continue
        if payload.get('channel') not in [None,'commentary','final']:
            continue
        content='\n'.join(c.get('text','') for c in payload.get('content',[]) if c.get('type') in ['input_text','output_text','text'])
        if not content.strip() or content.startswith(('<environment_context>','<external_codex_apps_open_page>')):
            continue
        current.append({'role':payload['role'],'timestamp':entry.get('timestamp',''),'text':content})
    record={'method':'ReportLab typesetting of locally available user-visible message text; excludes system/developer instructions, reasoning and tool logs.',
      'scope':'Previous saved assignment conversation snapshot plus current revision chat through export time. Other chats or missing historical messages are not claimed complete.',
      'exported_at':datetime.now(ZoneInfo('Asia/Taipei')).isoformat(),'messages':prior+current}
    (ROOT/'gpt_conversation_updated.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    story=[pdf.p('GPT 協作對話紀錄','h1'),pdf.p('學號 5113056021；作業修訂版','body'),
      pdf.p('收錄範圍：先前已保存的作業對話文字，以及本次修訂聊天中可取得的使用者與助理可見訊息，內容截至本 PDF 匯出時間。系統指令、內部推理與工具執行紀錄未列入；未宣稱包含其他聊天或尚未取得的歷史對話。','small')]
    for i,msg in enumerate(record['messages'],1):
        story.append(pdf.p(str(i)+' / '+('使用者' if msg['role']=='user' else 'GPT 助理')+' / '+msg.get('timestamp',''),'h2'))
        # Bound paragraphs prevents oversized unbreakable flowables, preserves all text.
        for para in msg['text'].splitlines():
            if para.strip():
                for start in range(0,len(para),1400):
                    story.append(pdf.p(para[start:start+1400]))
    path=ROOT/'5113056021_gpt_conversation_updated.pdf'
    pdf.doc(path,story)
    return path,record

def main():
    results={key:json.loads((WEB/f'data/{key}_result.json').read_text(encoding='utf-8')) for key in ['flood','housing']}
    for key,r in results.items():figure(key+'_interval.png',key.title()+' | held-out predictions and 95% intervals',r)
    notebook=json.loads((ROOT/'notebooklm_result.json').read_text(encoding='utf-8'))
    story=[]
    def p(t,style='body'):story.append(pdf.p(t,style))
    def h(t):p(t,'h1')
    def page():story.append(PageBreak())
    h('HW2 多元線性回歸')
    p('修訂版：雙題目與自訂 Dataset','cover')
    p('學號：5113056021')
    p('本版依 2026-11-02 提供的新作業說明製作，以加總分 2 分的兩項功能為目標。主要交付為 GitHub 原始碼與可操作網站；本 PDF 補充網站方法與結果，原始洪水完整報告另附。')
    story.append(pdf.table(['加分要求','本版實作'],[
      ['加總分 1 分：下拉呈現兩種 problem','洪水分數（20 特徵）與 King County 房價（18 特徵）'],
      ['加總分 2 分：任意輸入 Dataset','公開 CSV URL / 檔案上傳；自選 Target 與排除欄位；實際重新訓練'],
      ['主要分析要求','LinearRegression、訓練集特徵選擇、獨立測試評估與 95% 區間圖'],
      ['AI 研究標示','GPT 輔助內容與既有 NotebookLM 摘要分別標示']],[65*mm,pdf.WIDTH-65*mm]))
    story.append(Spacer(1,8*mm))
    p('GitHub：'+GITHUB,'small');p('網站：'+LIVE,'small')
    p('操作方式：切換 Problem；或展開自訂 Dataset、載入 CSV、選 Target，再按「執行回歸分析」。首次 Python 套件載入需網路；網站示範結果可立即查看。')
    p('本版不保證評分結果；實際加分依教師驗收認定。','small')
    page();h('01 / Business Understanding')
    p('洪水題目：使用 20 個環境與管理分數預測 FloodProbability，評估線性模型能否擷取合成分數規律。資料為合成資料，不推論為真實洪災機率，不能作為防災警報。')
    p('房價題目：使用房屋條件、區位與周邊房產資訊預測 King County 2014–2015 年成交價 price，單位美元。這是歷史資料練習，不是目前市場估價。')
    h('02 / Data Understanding')
    story.append(pdf.table(['資料集','來源筆數','原始輸入特徵','Target'],[
      ['Kaggle S4E5 洪水','1,117,957','20','FloodProbability'],['King County 房價','21,613','18','price'],['50 Startups（自訂範例）','50','4','Profit']],[64*mm,28*mm,38*mm,pdf.WIDTH-130*mm]))
    p('特徵數不包含目標、索引、ID、日期；兩個主要題目都落在 14–39 範圍。50 Startups 只有 4 個原始特徵，僅作為老師指定 URL 的加分功能驗收，不充當主要題目。房價的原始檔含額外 CSV 索引，已移除。')
    p('洪水來源：https://www.kaggle.com/competitions/playground-series-s4e5/data','small')
    p('房價來源：https://www.kaggle.com/datasets/harlfoxem/housesalesprediction','small')
    p('房價取得鏡像：https://raw.githubusercontent.com/rheera/data-analysis-with-python/main/kc_house_data.csv','small')
    h('03 / Data Preparation')
    p('網站固定 seed = 42，兩題各抽取 4,000 筆；分為訓練 2,400、校準 800、測試 800 筆。數值補值採訓練折中位數並標準化；類別採眾數補值與 one-hot，未知類別忽略。所有 fit 與特徵選擇均在交叉驗證的訓練折內。')
    p('自訂 CSV 以使用者選定 Target 建模，移除無效或缺失目標；原始特徵上限 100、編碼後上限 300、文字類別上限 40，較高基數或全空欄位會明示排除。互動版檔案最多 10 MB，可選分析 1,000 / 4,000 / 10,000 筆上限。')
    page();h('04 / Modeling 與 Feature Selection')
    p('比較平均值基線、全特徵 sklearn.linear_model.LinearRegression 與 SelectKBest + LinearRegression。以訓練集五折 KFold CV 比較保留 1 欄、50%、75%、100% 編碼特徵，依平均 CV RMSE 選擇設定。若類別數隨折改變，保留欄數依該訓練折維度向上取整。')
    p('特徵選擇不必然刪欄。兩題在本次抽樣與候選設定中，都以保留全部特徵的 CV RMSE 最小；這是實際選模結果，並未為了呈現刪欄而使用測試集挑選設定。')
    for key,title in [('flood','洪水題目'),('housing','房價題目')]:
        p(title+'：訓練集五折 CV','h2')
        r=results[key]
        story.append(pdf.table(['比例','完整訓練集保留欄數','平均 RMSE','折間 SD'],[
          [f"{v['fraction']*100:.1f}%",v['k'],f"{v['rmse']:.6g}",f"{v['sd']:.6g}"] for v in r['selection']]))
    p('係數以標準化數值特徵與類別虛擬變數為基礎，代表條件關聯，不能解讀成因果效果。房價 zipcode 在此基線採數值表示，不能視為郵遞區號有真實距離順序；可在後續模型改為適當的區域編碼。')
    page();h('05 / Evaluation：洪水題目')
    r=results['flood'];m=r['metrics'][-1]
    story.append(pdf.table(['模型','RMSE','MAE','R²'],[[v['model'],f"{v['rmse']:.6f}",f"{v['mae']:.6f}",f"{v['r2']:.6f}"] for v in r['metrics']],[70*mm,30*mm,30*mm,pdf.WIDTH-130*mm]))
    story.append(img('flood_interval.png'))
    p(f"選入 {len(r['selected_features'])} / {r['encoded_features']} 個編碼特徵。測試 MSE = {m['mse']:.8f}；調整 R² = {m['adjusted_r2']:.6f}。95% conformal 區間實測覆蓋率 {r['interval']['coverage']*100:.3f}%，平均寬度 {r['interval']['width']:.6f}。")
    p('區間以獨立校準集 800 筆絕對殘差排序，取 ceil((800+1) × 0.95) = 761 順位；覆蓋率使用全部 800 筆測試資料計算。圖僅呈現最多 100 筆固定抽樣案例，依預測值排序，並非時間序列。')
    p('原始洪水完整報告另以 50,000 筆樣本及 64/16/20 分割，RMSE 0.020046、R² 0.843466；網站的 4,000 筆與 60/20/20 分割因此呈現不同數值，兩者不混用。')
    page();h('05 / Evaluation：King County 房價')
    r=results['housing'];m=r['metrics'][-1]
    story.append(pdf.table(['模型','RMSE（USD）','MAE（USD）','R²'],[[v['model'],f"{v['rmse']:,.2f}",f"{v['mae']:,.2f}",f"{v['r2']:.6f}"] for v in r['metrics']],[66*mm,34*mm,34*mm,pdf.WIDTH-134*mm]))
    story.append(img('housing_interval.png'))
    p(f"選入 {len(r['selected_features'])} / {r['encoded_features']} 個編碼特徵。測試 MSE = {m['mse']:,.2f} USD²；調整 R² = {m['adjusted_r2']:.6f}。95% conformal 區間實測覆蓋率 {r['interval']['coverage']*100:.3f}%，平均寬度 {r['interval']['width']:,.2f} USD。")
    p('房價有偏態與高價離群值，線性模型的誤差及區間較大。sqft_living = sqft_above + sqft_basement 造成精確共線性；程式辨識矩陣秩不足並明示，採 SVD 最小範數解。個別共線係數無唯一解，不強行詮釋其效果。')
    p('主要採 conformal 區間，不裁切負下界。其邊際覆蓋保證需要校準與新資料可交換，不保證每個價位子群都有 95% 覆蓋。隨機切分可能包含同一房產或鄰近房產，跨年份、跨地區評估需另做時間或群組切分。')
    page();h('區間、假設與自訂資料驗證')
    p('網頁可切換三種 95% 區間：split-conformal 單筆預測區間、OLS 平均反應信賴區間、OLS 單筆預測區間。OLS 區間以設計矩陣 SVD 偽逆計算 leverage，t 分布自由度為訓練筆數減矩陣秩；選模後未另校正選擇不確定性，故列為參考。')
    p('五項假設：線性與等變異透過殘差圖檢視；常態透過 Q-Q 圖及 Jarque–Bera；共線性透過矩陣秩；獨立性依資料蒐集過程判斷，隨機列序不適合用 Durbin–Watson 當作時間獨立性的證據。此版沒有宣稱所有假設都通過。')
    validation=json.loads((OUT/'web_validation.json').read_text(encoding='utf-8'))
    s=validation['startups'];sm=s['metrics'][-1]
    p('50 Startups 實測結果','h2')
    p(f"老師指定的公開 CSV 網址可直接載入，Target = Profit。4 個原始特徵含 State 類別，編碼後 5 欄。五折 CV 選出 {len(s['selected_features'])} 欄；測試 RMSE {sm['rmse']:.4f}、R² {sm['r2']:.6f}。")
    p('小樣本修正：若僅留 10 筆校準，ceil((10+1) × 0.95)=11 超過可用殘差，無法給有限區間。因此至少保留 19 筆校準，本例訓練 21 / 校準 19 / 測試 10，取最大校準殘差為半寬。10 筆測試的覆蓋率變動很大，不宣稱穩定泛化。')
    h('06 / Deployment')
    p('以 buildless HTML/CSS/JS 發布，Python/scikit-learn 經 Pyodide 在 Web Worker 內執行。內建題目先顯示與同一程式產生的示範結果；按下執行後會真的重新訓練。自訂資料不送至網站伺服器；URL 下載須允許 CORS，限制時改用上傳。結果 JSON 含設定、分割列號、CV、係數、逐筆區間與來源。')
    p('程式驗證涵蓋：獨立重算 RMSE、R²、覆蓋率；三份資料分割不重疊；修改測試標籤不影響選模、係數與區間半寬；修改校準標籤只影響區間；缺失值處理與不合法目標；兩題及 50 Startups 實例。')
    page();h('GPT 輔助內容')
    p('GPT 協助查找公開資料、撰寫與調整 Python、網站互動、特徵選擇流程、區間公式、圖表、測試、報告及 GitHub/網站部署。分析數值由實際程式執行，不是由語言模型臆測。原有報告保留較完整的洪水模型比較，本補充報告交代新增功能與第二題。')
    h('NotebookLM 摘要')
    p('以下沿用 2026-10-20 已實際完成並保存的 NotebookLM 洪水研究；不是本次新產生的 NotebookLM 回覆，也未用它宣稱房價結果。原始兩輪問答、摘要、來源與截圖均保留。摘要超過 100 個中文字。','small')
    for para in notebook['summary'].split('\n\n'):p(para)
    p('研究筆記本：'+notebook['notebook_url'],'small')
    for source in notebook['sources']:p('['+source['id']+'] '+source['title']+'：'+source['url'],'small')
    p('GPT 對話 PDF 收錄既有 ChatGPT 網頁問答；另輸出目前可取得的歷次保存文字與本次更新對話，範圍截至匯出時點。未取得的其他聊天不宣稱完整。','small')
    dest=ROOT/'5113056021_hw2_update.pdf'
    pdf.doc(dest,story)
    convo,record=export_conversation()
    for path in [dest,convo,ROOT/'5113056021_hw2_report.pdf',ROOT/'5113056021_gpt_conversation.pdf']:
        shutil.copy2(path,WEB/'downloads'/path.name)
    from pypdf import PdfReader
    print(json.dumps({'report_pages':len(PdfReader(dest).pages),'conversation_pages':len(PdfReader(convo).pages),'conversation_messages':len(record['messages'])},ensure_ascii=False))
if __name__=='__main__':main()
