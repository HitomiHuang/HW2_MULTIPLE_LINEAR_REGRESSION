"""Build the analysis report with newly captured ChatGPT web question screenshots.

python tools/build_combined_report.py
Model outputs are read, not recomputed. Earlier dialogue appendices are excluded.
"""
from __future__ import annotations
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from io import BytesIO
from html import escape,unescape
import hashlib
import json
import math
import re
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image as PILImage
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate,Frame,PageTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image,Flowable,KeepTogether
from reportlab.platypus.tableofcontents import TableOfContents

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/pdf'
TMP=ROOT/'tmp/pdfs/combined'
OUT.mkdir(parents=True,exist_ok=True)
TMP.mkdir(parents=True,exist_ok=True)
LIVE='https://hitomihuang.github.io/HW2_MULTIPLE_LINEAR_REGRESSION/'
GITHUB='https://github.com/HitomiHuang/HW2_MULTIPLE_LINEAR_REGRESSION'
TZ=ZoneInfo('Asia/Taipei')
STAMP=datetime.now(TZ)
WIDTH=A4[0]-38*mm
GREEN=colors.HexColor('#1B5144')
INK=colors.HexColor('#24342F')
MUTED=colors.HexColor('#65776D')
PALE=colors.HexColor('#EEF4E8')
LINE=colors.HexColor('#D8E1D4')
GOLD=colors.HexColor('#B87837')

font_path=ROOT/'tmp/fonts/NotoSansTC-Regular.ttf'
if not font_path.exists():
 from fontTools.ttLib import TTFont as FontSource
 from fontTools.varLib.instancer import instantiateVariableFont
 source=FontSource('C:/Windows/Fonts/NotoSansTC-VF.ttf')
 font_path.parent.mkdir(parents=True,exist_ok=True)
 instantiateVariableFont(source,{'wght':400},inplace=False).save(str(font_path))
 source.close()
pdfmetrics.registerFont(TTFont('CJK',str(font_path)))
pdfmetrics.registerFontFamily('CJK',normal='CJK',bold='CJK',italic='CJK',boldItalic='CJK')
ST={
 'body':ParagraphStyle('body',fontName='CJK',fontSize=10,leading=16,textColor=INK,spaceAfter=8,wordWrap='CJK'),
 'small':ParagraphStyle('small',fontName='CJK',fontSize=8.2,leading=12.5,textColor=MUTED,spaceAfter=6,wordWrap='CJK'),
 'h1':ParagraphStyle('h1',fontName='CJK',fontSize=19,leading=27,textColor=GREEN,spaceAfter=12,wordWrap='CJK',keepWithNext=True),
 'h2':ParagraphStyle('h2',fontName='CJK',fontSize=12,leading=18,textColor=GREEN,spaceBefore=7,spaceAfter=7,keepWithNext=True,wordWrap='CJK'),
 'cover':ParagraphStyle('cover',fontName='CJK',fontSize=28,leading=39,textColor=GREEN,spaceAfter=15,wordWrap='CJK'),
 'eyebrow':ParagraphStyle('eyebrow',fontName='CJK',fontSize=9,leading=14,textColor=MUTED,spaceAfter=13),
 'cell':ParagraphStyle('cell',fontName='CJK',fontSize=8.3,leading=12.5,textColor=INK,wordWrap='CJK'),
 'chat':ParagraphStyle('chat',fontName='CJK',fontSize=8.5,leading=13,textColor=INK,spaceAfter=5,wordWrap='CJK'),
 'chat_head':ParagraphStyle('chat_head',fontName='CJK',fontSize=9.2,leading=14,textColor=GREEN,spaceBefore=10,spaceAfter=5,keepWithNext=True,wordWrap='CJK'),
}

def clean_glyphs(text):
 # Keep the source JSON unchanged. Rare unsupported PDF glyphs are explicit codes.
 cmap=pdfmetrics.getFont('CJK').face.charToGlyph
 return ''.join(c if c in '\n\t' or ord(c) in cmap else '[U+%04X]'%ord(c) for c in str(text))

def P(text,style='body',links=False):
 text=clean_glyphs(text)
 markup=escape(text).replace('\n','<br/>')
 if links:
  markup=re.sub(r'https?://[^\s<>]+',lambda m:'<link color="#1B5144" href="'+m.group(0)+'">'+m.group(0)+'</link>',markup)
 return Paragraph(markup,ST[style])

def link(label,url,style='small'):
 return Paragraph('<link color="#1B5144" href="'+escape(url,quote=True)+'">'+escape(label)+'</link>',ST[style])

def table(headers,rows,widths=None):
 data=[[P(x,'cell') for x in headers]]+[[P(str(x),'cell') for x in row] for row in rows]
 t=Table(data,colWidths=widths or [WIDTH/len(headers)]*len(headers),repeatRows=1,hAlign='LEFT')
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PALE),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('LINEBELOW',(0,0),(-1,0),.7,GREEN),('LINEBELOW',(0,-1),(-1,-1),.4,LINE),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F8FAF6')])]))
 return t

def image(path,height=90*mm):
 path=Path(path)
 with PILImage.open(path) as im:w,h=im.size
 ratio=min(WIDTH/w,height/h)
 return Image(str(path),width=w*ratio,height=h*ratio,hAlign='CENTER')

class ReportDoc(BaseDocTemplate):
 def __init__(self,path):
  super().__init__(str(path),pagesize=A4,leftMargin=19*mm,rightMargin=19*mm,topMargin=18*mm,bottomMargin=20*mm,title='AIoT-DA｜多元線性回歸整合分析報告',author='Regression Lab')
  self.sections={}
  frame=Frame(self.leftMargin,self.bottomMargin,self.width,self.height,id='normal',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
  self.addPageTemplates(PageTemplate(id='all',frames=frame,onPage=self.page_footer))
 def page_footer(self,c,doc):
  c.saveState();c.setStrokeColor(LINE);c.line(19*mm,15*mm,A4[0]-19*mm,15*mm)
  c.setFont('CJK',8);c.setFillColor(MUTED);c.drawString(19*mm,10*mm,'Regression Lab | Multiple Linear Regression')
  c.drawRightString(A4[0]-19*mm,10*mm,'第 '+str(doc.page)+' 頁');c.restoreState()
 def afterFlowable(self,f):
  if hasattr(f,'section_key'):
   key=f.section_key;self.canv.bookmarkPage(key);self.canv.addOutlineEntry(f.section_title,key,level=0,closed=False)
   self.notify('TOCEntry',(0,f.section_title,self.page,key));self.sections[key]=self.page

def heading(title,key):
 p=P(title,'h1');p.section_key=key;p.section_title=title
 return p

class Infographic(Flowable):
 def __init__(self,results):super().__init__();self.width=WIDTH;self.height=590;self.r=results
 def draw(self):
  c=self.canv;w=self.width
  def box(x,y,bw,bh,title,text,fill=PALE):
   c.setFillColor(fill);c.setStrokeColor(LINE);c.roundRect(x,y,bw,bh,8,stroke=1,fill=1)
   pp=P(title,'h2');_,ph=pp.wrap(bw-22,bh);pp.drawOn(c,x+11,y+bh-12-ph)
   pp=P(text,'small');_,ph2=pp.wrap(bw-22,bh);pp.drawOn(c,x+11,y+bh-18-ph-ph2)
  box(0,478,(w-14)/2,100,'洪水風險分數','20 個輸入特徵\nTarget：FloodProbability\n合成分數；非真實災害警報')
  box((w+14)/2,478,(w-14)/2,100,'King County 房價','18 個輸入特徵\nTarget：price（美元）\n2014–2015 年歷史交易')
  c.setFont('CJK',11);c.setFillColor(GREEN);c.drawString(0,455,'每個題目 4,000 筆 | seed = 42')
  widths=[w*.6,w*.2,w*.2];xs=[0,widths[0],widths[0]+widths[1]]
  for x,bw,color,label in zip(xs,widths,[GREEN,colors.HexColor('#DCEBB9'),colors.HexColor('#E7CFA9')],['訓練 2,400（60%）','校準 800（20%）','測試 800（20%）']):
   c.setFillColor(color);c.rect(x,417,bw,25,fill=1,stroke=0);c.setFillColor(colors.white if color==GREEN else INK);c.setFont('CJK',8.5);c.drawCentredString(x+bw/2,425,label)
  steps=[('01 問題定義','定義數值預測目標與使用限制'),('02 資料理解','確認來源、輸入特徵與缺失情形'),('03 資料準備','先切分；補值與編碼只 fit 訓練折'),('04 建模選擇','五折 CV + SelectKBest + 線性回歸'),('05 模型評估','獨立測試誤差與 95% 預測區間'),('06 網站部署','GitHub Pages；自訂 CSV 與結果匯出')]
  for i,(title,text) in enumerate(steps):
   col=i%2;row=i//2;box(col*(w+14)/2,326-row*78,(w-14)/2,65,title,text,colors.white)
  for i,key in enumerate(['flood','housing']):
   r=self.r[key];m=r['metrics'][-1];unit='（合成分數）' if i==0 else 'USD'
   text='測試 R² = '+f"{m['r2']:.4f}"+'\nRMSE = '+(f"{m['rmse']:.6f}" if i==0 else f"{m['rmse']:,.2f}")+' '+unit+'\n95% PI 實測覆蓋率 '+f"{r['interval']['coverage']*100:.3f}%"
   box(i*(w+14)/2,53,(w-14)/2,105,'洪水模型結果' if i==0 else '房價模型結果',text)
  note=P('每題測試 800 筆。RMSE 的單位不同，兩題不直接比較。95% conformal 區間需要校準與新資料可交換的前提；實測覆蓋不是每個子群的保證。','small')
  _,ph=note.wrap(w,50);note.drawOn(c,0,43-ph)


def plot_diagnostics(results):
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
 fig,axes=plt.subplots(2,2,figsize=(9,5.3),layout='constrained')
 for row,key in enumerate(['flood','housing']):
  r=results[key];a=axes[row,0];points=r['training_residuals']
  a.scatter([p['fitted'] for p in points],[p['residual'] for p in points],s=6,color='#28685B',alpha=.4)
  a.axhline(0,color='#B87837',ls='--',lw=1);a.set(title=key.title()+' | training residuals',xlabel='Fitted value',ylabel='Residual');a.grid(alpha=.15)
  a=axes[row,1];points=r['qq']
  a.scatter([p['theoretical'] for p in points],[p['observed'] for p in points],s=6,color='#28685B',alpha=.6)
  a.set(title=key.title()+' | normal Q-Q',xlabel='Theoretical normal quantile',ylabel='Residual quantile');a.grid(alpha=.15)
 path=TMP/'diagnostics.png';fig.savefig(path,dpi=180);plt.close(fig)
 return path


def main():
 results={k:json.loads((ROOT/f'web/dist/data/{k}_result.json').read_text(encoding='utf-8')) for k in ['flood','housing']}
 nb=json.loads((ROOT/'notebooklm_result.json').read_text(encoding='utf-8'))
 validation=json.loads((ROOT/'output/web_validation.json').read_text(encoding='utf-8'))
 webqa=json.loads((ROOT/'output/evidence/chatgpt_revision/qa_index.json').read_text(encoding='utf-8'))
 assert webqa['verified_in_browser'] and len(webqa['questions'])==6
 assert len(re.findall(r'[\u4e00-\u9fff]',nb['summary']))>=100
 checks=[]
 for key,r in results.items():
  rows=r['predictions'];actual=np.array([p['actual'] for p in rows]);pred=np.array([p['prediction'] for p in rows])
  rmse=float(np.sqrt(np.mean((actual-pred)**2)));r2=float(1-np.sum((actual-pred)**2)/np.sum((actual-actual.mean())**2))
  coverage=float(np.mean([(p['lower']<=p['actual']<=p['upper']) for p in rows]))
  assert np.isclose(rmse,r['metrics'][-1]['rmse']) and np.isclose(r2,r['metrics'][-1]['r2']) and np.isclose(coverage,r['interval']['coverage'])
  splits=[set(r['split_rows'][s]) for s in ['train','calibration','test']]
  assert len(set.union(*splits))==4000 and not (splits[0]&splits[1] or splits[0]&splits[2] or splits[1]&splits[2])
  checks.append(key+': independently verified RMSE, R2, coverage and disjoint splits')
 diag=plot_diagnostics(results)
 story=[]
 def add(text,style='body'):story.append(P(text,style))
 def section(title,key):story.append(PageBreak());story.append(heading(title,key))
 add('AIoT-DA 課程作業 | AI Vibe Coding HW2','eyebrow')
 add('多元線性回歸\n整合分析報告','cover')
 add('Regression Lab','h2')
 add('以洪水合成分數與 King County 房價為例，整合資料理解、特徵選擇、線性回歸、獨立測試評估與預測區間，並提供可操作的 GitHub Pages 網站。')
 story.append(Spacer(1,7*mm))
 story.append(table(['分析主題','原始特徵','測試 R²','95% PI 實測覆蓋'],[[label,r['original_features'],f"{r['metrics'][-1]['r2']:.6f}",f"{r['interval']['coverage']*100:.3f}%"] for label,r in [('洪水風險分數',results['flood']),('King County 房價',results['housing'])]],[57*mm,25*mm,38*mm,WIDTH-120*mm]))
 story.append(Spacer(1,6*mm))
 story.append(link('網站：'+LIVE,LIVE));story.append(link('GitHub：'+GITHUB,GITHUB))
 add('文件整理時間：'+STAMP.strftime('%Y-%m-%d %H:%M')+'（Asia/Taipei）','small')
 add('內容包含：資訊圖表、CRISP-DM 分析、模型評估與區間圖、GPT 輔助內容、NotebookLM 摘要，以及本次實際在 ChatGPT 網頁取得的六組技術問答截圖。','small')
 add('本報告以網站使用的每題 4,000 筆樣本為主要結果。既有 50,000 筆洪水實驗屬不同資料範圍，其指標不與本報告混用。','small')
 section('內容索引','contents')
 toc=TableOfContents();toc.levelStyles=[ParagraphStyle('toc',fontName='CJK',fontSize=10.2,leading=19,textColor=INK,leftIndent=0,rightIndent=15,spaceAfter=5)]
 story.append(toc);story.append(Spacer(1,8*mm))
 add('閱讀方式：先看資訊圖表與兩個題目的評估結果，再查看分析方法與 AI 研究；本次 ChatGPT 技術問答截圖集中於文末。','small')
 section('資訊圖表｜從資料到預測','infographic');story.append(Infographic(results))
 section('01 / 問題定義與資料理解','understanding')
 add('Business Understanding','h2')
 add('洪水題目：以 20 個環境與管理分數預測 FloodProbability，研究線性模型是否能擷取合成資料中的規律。此分數未經驗證為真實洪災發生機率，不能作為防災警報。 [D1]')
 add('房價題目：以房屋條件、區位與鄰近房產資訊預測 King County 2014–2015 年歷史成交價 price，單位美元；這是歷史交易建模，不代表目前市場估價。 [D2]')
 add('Data Understanding','h2')
 story.append(table(['資料集','來源筆數','原始輸入特徵','Target'],[['Kaggle S4E5 洪水','1,117,957','20','FloodProbability'],['King County 房價','21,613','18','price'],['50 Startups 範例','50','4','Profit']],[60*mm,30*mm,38*mm,WIDTH-128*mm]))
 add('輸入特徵數不包含 Target、索引、ID 與日期。房價鏡像含額外 CSV 索引，抽樣前移除；兩個內建題目各固定抽取 4,000 筆。50 Startups 僅作自訂 CSV 範例，含 State 類別欄位。 [D3]')
 for key,label in [('flood','洪水'),('housing','房價')]:
  r=results[key];add(label+'樣本 SHA-256：'+r['dataset_sha256'],'small')
 add('資料限制：洪水為合成分數；房價可能有同一房產重複交易、空間依賴與時間差異。來源的資料生成或蒐集背景，會限制可作出的推論。')
 section('02 / 資料準備與建模','modeling')
 add('Data Preparation','h2')
 add('固定 seed = 42，每題切為訓練 2,400、校準 800、測試 800。先分割再處理：數值欄以訓練折中位數補值、標準化；類別欄以訓練折眾數補值與 one-hot 編碼。未知類別採忽略處理，預處理與特徵選擇放在 Pipeline 內，測試標籤不參與選模。 [M1]')
 add('Modeling 與 Feature Selection','h2')
 add('比較平均值基線、全特徵 LinearRegression，以及 SelectKBest + LinearRegression。訓練集五折 CV 比較保留 1 欄、50%、75% 與全部編碼特徵，依平均 CV RMSE 選擇。類別數可能隨折改變，因此保留欄數按各訓練折維度計算。 [M2]')
 for key,label in [('flood','洪水：CV RMSE，單位合成分數'),('housing','房價：CV RMSE，單位美元')]:
  add(label,'h2');r=results[key]
  story.append(table(['保留比例','最終欄數','平均 CV RMSE','折間 SD'],[[f"{v['fraction']*100:.1f}%",v['k'],f"{v['rmse']:.6g}",f"{v['sd']:.6g}"] for v in r['selection']]))
 add('本次候選設定中，兩題都由 CV 選出保留全部特徵。特徵選擇不必然刪欄；本報告如實保留此結果，未依測試集挑選設定。','small')
 for key,label in [('flood','洪水'),('housing','房價')]:
  section('03 / Evaluation：'+label,'evaluation_'+key)
  r=results[key];m=r['metrics'][-1]
  unit='合成分數' if key=='flood' else 'USD'
  story.append(table(['模型','MAE','RMSE','R²'],[[v['model'],f"{v['mae']:.6f}" if key=='flood' else f"{v['mae']:,.2f}",f"{v['rmse']:.6f}" if key=='flood' else f"{v['rmse']:,.2f}",f"{v['r2']:.6f}"] for v in r['metrics']],[66*mm,34*mm,34*mm,WIDTH-134*mm]))
  add('MAE 與 RMSE 單位：'+unit+'；測試 800 筆。','small')
  story.append(image(ROOT/f'output/web_figures/{key}_interval.png',height=91*mm))
  add('圖：100 筆固定抽樣測試案例，按預測值排序，橫軸不是時間。綠線為預測，橘點為實際值，陰影為 95% split-conformal 預測區間。完整覆蓋率使用全部 800 筆測試資料計算。','small')
  add(f"選入 {len(r['selected_features'])} / {r['encoded_features']} 欄。測試 MSE = {m['mse']:.8f}"+('。' if key=='flood' else ' USD²。')+f"調整 R² = {m['adjusted_r2']:.6f}；95% 區間實測覆蓋率 {r['interval']['coverage']*100:.3f}%，平均寬度 {r['interval']['width']:.6f} {unit}。")
  if key=='flood':add('相較平均值基線，線性回歸降低測試誤差；仍有未被線性模型解釋的雜訊與偏差。這些結果描述本次相似分布樣本，不應直接推廣至真實洪災決策。')
  else:add('房價偏態與高價離群值使誤差及區間較大。sqft_living = sqft_above + sqft_basement 造成精確共線性，模型採 SVD 最小範數解，個別共線係數不具唯一解。zipcode 的數值表示也是此基線的簡化。跨年份或地區部署需重新評估。')
 section('04 / 預測區間與模型診斷','uncertainty')
 add('主要區間：95% split-conformal','h2')
 add('用獨立校準集的絕對殘差取第 ceil((n_cal + 1) × 0.95) 順位為半寬。800 筆校準取第 761 順位；測試集只評估覆蓋率與誤差，不決定半寬。其邊際覆蓋需要校準與新資料可交換，並不保證每個價位或地區子群都達 95%。區間未裁切上下界。 [M4]')
 add('OLS 平均反應信賴區間與單筆預測區間','h2')
 add('網站另提供 95% OLS mean CI 與 observation PI，以設計矩陣 SVD 偽逆求 leverage，自由度為訓練筆數減矩陣秩。單筆 PI 多含新觀測的隨機誤差，通常較寬。OLS 區間需額外假設，且未校正選模不確定性，作為參考。 [M3]')
 story.append(image(diag,height=92*mm))
 add('上排洪水、下排房價；左圖為訓練殘差，右圖為常態 Q-Q。圖使用固定間隔取出的訓練點。','small')
 story.append(table(['診斷','洪水','房價'],[['Jarque–Bera p',f"{results['flood']['diagnostics']['jarque_bera_p']:.3g}",'小於浮點數顯示範圍'],['設計矩陣秩 / 欄數','21 / 21','18 / 19'],['殘差自由度','2,379','2,382']],[70*mm,(WIDTH-70*mm)/2,(WIDTH-70*mm)/2]))
 add('線性與等變異以殘差圖檢視；常態以 Q-Q 與 Jarque–Bera 檢視；共線性以矩陣秩辨識；獨立性需依採樣流程判斷。隨機表格列序不適合當作時間獨立性的證據，本報告未宣稱五項假設全部通過。','small')
 section('05 / Deployment 與自訂資料','deployment')
 add('GitHub Pages 與瀏覽器分析','h2')
 add('網站已發布至 GitHub Pages，透過 GitHub Actions 將 web/dist 靜態檔部署。推送網站檔案或部署設定到 main 會自動更新；Python/scikit-learn 透過 Pyodide 在 Web Worker 內執行，不需要後端推論服務。')
 story.append(link(LIVE,LIVE));story.append(image(ROOT/'docs/images/site-overview.jpg',height=85*mm))
 add('圖：資料集切換、自訂 CSV 與分析設定畫面。首次先顯示預先計算示範，點選執行後才實際重新訓練。','small')
 add('操作條件與結果匯出','h2')
 add('可輸入公開 CSV URL 或上傳 UTF-8 CSV/TSV，選 Target、排除欄位與分析筆數。互動版上限 10 MB、100 個原始欄位、300 個編碼欄位；有效目標至少 30 筆，分析上限可選 1,000 / 4,000 / 10,000 筆。文字欄超過 40 類或訓練集全空會明示排除。首次需網路載入套件；URL 須允許 CORS，受限時可改用上傳。')
 add('可下載 JSON、逐筆預測 CSV 與目前資料集，也能列印結果為 PDF。自訂資料留在瀏覽器；來源、設定、CV、分割列號與逐筆區間均可檢查。')
 s=validation['startups'];m=s['metrics'][-1]
 add('50 Startups：實際執行範例','h2')
 add(f"以 Profit 為目標，4 個原始特徵（含 State）編碼為 5 欄，CV 選入 {len(s['selected_features'])} 欄；測試 RMSE {m['rmse']:.4f}、R² {m['r2']:.6f}。為給有限的 95% conformal 區間，至少保留 19 筆校準，本例分為訓練 21 / 校準 19 / 測試 10。測試僅 10 筆，100% 實測覆蓋不可解讀為穩定表現。")
 section('06 / GPT 輔助內容與 NotebookLM 摘要','ai_research')
 add('GPT 輔助內容','h2')
 add('GPT 協助公開資料研究、Python 與網站程式、特徵選擇與資料洩漏檢查、區間計算、圖表、測試、文件整理，以及 GitHub Pages 部署。模型指標來自實際程式，不由語言模型臆測；係數不作因果詮釋。')
 add('NotebookLM 摘要','h2')
 add('採用既有於 2026-10-20 實際完成並保存的洪水研究。摘要共 276 個中文字，保留原意與 N1–N6 引用；這不是本次重新生成的 NotebookLM 回覆，也不代表房價結果的研究結論。','small')
 for para in nb['summary'].split('\n\n'):add(para)
 story.append(link('研究筆記本：'+nb['notebook_url'],nb['notebook_url']))
 add('原始證據：notebooklm_raw.txt 保存兩輪提問與回覆，notebooklm_result.json 保存摘要與來源，原 NotebookLM 頁面截圖保存於 output/evidence/notebooklm_research.jpg。','small')
 section('參考來源與重現資料','references')
 refs=[('D1','Kaggle：Regression with a Flood Prediction Dataset','https://www.kaggle.com/competitions/playground-series-s4e5/data'),('D2','Kaggle：House Sales in King County, USA','https://www.kaggle.com/datasets/harlfoxem/housesalesprediction'),('D3','50 Startups CSV 範例','https://raw.githubusercontent.com/Avik-Jain/100-Days-Of-ML-Code/master/datasets/50_Startups.csv'),('M1','scikit-learn：Common pitfalls and recommended practices','https://scikit-learn.org/stable/common_pitfalls.html'),('M2','scikit-learn：Feature selection','https://scikit-learn.org/stable/modules/feature_selection.html'),('M3','statsmodels：OLSResults.get_prediction','https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLSResults.get_prediction.html'),('M4','Angelopoulos and Bates：A Gentle Introduction to Conformal Prediction','https://arxiv.org/abs/2107.07511')]
 for ident,title,url in refs:story.append(link('['+ident+'] '+title+'\n'+url,url))
 add('NotebookLM 引用對照','h2')
 for source in nb['sources']:story.append(link('['+source['id']+'] '+source['title']+'\n'+source['url'],source['url']))
 add('本機重現','h2')
 for text in ['python -m pip install -r requirements.txt','python analyze_dataset.py --problem flood','python analyze_dataset.py --problem housing','python analyze_dataset.py --input data/50_Startups.csv --target Profit','python -m unittest discover -s tests -v']:add(text,'small')
 add('主分析引擎：web/dist/analysis.py；網站樣本與示範結果：web/dist/data/；既有數值檢查與部署結果：output/web_validation.json、output/deployment.json。')
 section('ChatGPT 技術問答｜實際網頁截圖','chatgpt_web_qa')
 add('本章收錄本次在 ChatGPT 網頁實際送出問題、取得完整回答後擷取的畫面。問題根據本專案已完成的資料、流程、實測指標與部署方式提出，包含方法確認與適用範圍的追問。')
 add('提問時提供了本專案的實驗設定與數值，ChatGPT 據此解釋方法及結果；這些回覆不是 ChatGPT 另行執行本機程式或 NotebookLM 的驗證紀錄。','small')
 story.append(link('實際對話：'+webqa['conversation_url'],webqa['conversation_url']))
 add('網頁顯示模型：'+webqa['model_label']+'。以下保留原始截圖，不重製或改寫畫面中的回答。','small')
 story.append(table(['問答','主題'],[[str(i),q['topic']] for i,q in enumerate(webqa['questions'],1)],[20*mm,WIDTH-20*mm]))
 add('問答 4 的一般獨立性檢查建議，於問答 5 進一步釐清為隨機表格資料、時間及群組切分的適用範圍。閱讀時請一併參照。','small')
 for i,q in enumerate(webqa['questions'],1):
  section('問答 '+str(i)+'｜'+q['topic'],'qa_'+str(i))
  if q.get('editor_note'):add(q['editor_note'],'small')
  for j,rel in enumerate(q['screenshots']):
   if j:story.append(PageBreak());add('問答 '+str(i)+'｜續圖','h2')
   story.append(image(ROOT/rel,height=226*mm))
   captured=datetime.fromisoformat(q['captured_at'].replace('Z','+00:00')).astimezone(TZ)
   add('ChatGPT 實際網頁畫面 | 擷取時間：'+captured.strftime('%Y-%m-%d %H:%M:%S')+'（Asia/Taipei）','small')
 destination=OUT/'regression_lab_complete_report.pdf'
 doc=ReportDoc(destination);doc.multiBuild(story,maxPasses=5)
 reader=PdfReader(destination)
 all_text='\n'.join(p.extract_text() or '' for p in reader.pages)
 for term in ['Business Understanding','Data Preparation','Modeling','Evaluation','Deployment','GPT 輔助內容','NotebookLM 摘要','資訊圖表','ChatGPT 技術問答']:
  assert term in all_text,term
 assert 'https://hitomihuang.github.io/HW2_MULTIPLE_LINEAR_REGRESSION/' in all_text
 assert nb['summary'].split('\n\n')[0][:24] in all_text.replace('\n','')
 for removed in ['先前保存的 ChatGPT 協作文字','本次修訂、網站部署與文件整理對話','ChatGPT 網頁問答原始截圖','請幫我組成文件PDF']:
  assert removed not in all_text,removed
 screenshot_checks=[]
 for i,q in enumerate(webqa['questions'],1):
  page=reader.pages[doc.sections['qa_'+str(i)]-1]
  assert len(page.images)==1
  original=PILImage.open(ROOT/q['screenshots'][0]).convert('RGB')
  embedded_bytes=page.images[0].indirect_reference.get_object().get_data()
  assert embedded_bytes==(ROOT/q['screenshots'][0]).read_bytes(),q['topic']
  embedded=PILImage.open(BytesIO(embedded_bytes)).convert('RGB')
  assert np.array_equal(np.asarray(original),np.asarray(embedded)),q['topic']
  screenshot_checks.append({'topic':q['topic'],'path':q['screenshots'][0],'sha256':hashlib.sha256((ROOT/q['screenshots'][0]).read_bytes()).hexdigest(),'original_pixels_preserved':True,'original_jpeg_bytes_preserved':True})
 manifest={'file':destination.name,'pages':len(reader.pages),'sections':doc.sections,'exported_at':STAMP.isoformat(),'chatgpt_web_qa_count':len(webqa['questions']),'chatgpt_conversation_url':webqa['conversation_url'],'screenshot_checks':screenshot_checks,'notebooklm_chinese_characters':len(re.findall(r'[\u4e00-\u9fff]',nb['summary'])),'numerical_checks':checks,'prior_dialogue_appendices_removed':True,'sha256':hashlib.sha256(destination.read_bytes()).hexdigest()}
 (OUT/'report_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(manifest,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
