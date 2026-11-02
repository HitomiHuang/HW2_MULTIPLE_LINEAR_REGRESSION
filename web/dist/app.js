'use strict';
const $ = id => document.getElementById(id);
const escapeHTML = value => String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = (x,d=4) => x===null||x===undefined?'—':(Number(x)!==0&&Math.abs(x)<.0001)?Number(x).toExponential(2):Math.abs(x)>=10000?Number(x).toLocaleString('en-US',{maximumFractionDigits:0}):Number(x).toLocaleString('en-US',{maximumFractionDigits:d});
const problems = {
  flood:{title:'洪水風險分數',target:'FloodProbability',excluded:['id'],copy:'以環境與管理分數，預測合成洪水風險。20 個數值輸入特徵。',source:'Kaggle · Playground Series S4E5',url:'https://www.kaggle.com/competitions/playground-series-s4e5/data',unit:'合成分數'},
  housing:{title:'King County 房價',target:'price',excluded:['id','date'],copy:'以房屋條件與區位，預測 2014–2015 年的成交價格。18 個輸入特徵。',source:'Kaggle · House Sales in King County',url:'https://www.kaggle.com/datasets/harlfoxem/housesalesprediction',unit:'美元 USD'},
  custom:{title:'自訂 Dataset',copy:'貼上公開 CSV 網址或上傳檔案，再選擇要預測的數值欄位。',source:'使用者提供',unit:'Target 原始單位'}
};
let state={csv:'',name:'',source:'',result:null,worker:null,busy:false,generation:0,problem:'flood'};
function status(message,error=false,loading=false){$('status').textContent=message;$('status').className='status'+(error?' error':'')+(loading?' loading':'');}
function busy(value){state.busy=value;['run','load-url','file','problem','target','sample','example'].forEach(id=>$(id).disabled=value);$('cancel').hidden=!value;document.querySelectorAll('#exclude-fields input').forEach(el=>el.disabled=value||el.value===$('target').value);}
function clearResult(){state.result=null;$('result-content').hidden=true;$('empty').hidden=false;$('result-mode').textContent='尚未分析';$('result-title').textContent='模型總覽 · 尚未分析';document.querySelectorAll('#features .chart-grid,#features > .card').forEach(el=>el.hidden=true);$('features-empty').hidden=false;$('crisp-cards').innerHTML='<p>執行分析後，這裡會顯示目前 Dataset 對應的六階段流程。</p>';['download-json','download-csv','print'].forEach(id=>$(id).disabled=true);}
function showTab(tab){document.querySelectorAll('.panel').forEach(el=>el.classList.toggle('active',el.id===tab));document.querySelectorAll('.nav').forEach(el=>el.classList.toggle('active',el.dataset.tab===tab));if(window.Plotly)requestAnimationFrame(()=>document.querySelectorAll('.panel.active .js-plotly-plot').forEach(el=>Plotly.Plots.resize(el)));}
function schema(csv,defaultTarget,excluded=[]){
  if(!window.Papa)throw new Error('CSV 解析元件尚未載入，請稍後重試。');
  const parsed=Papa.parse(csv,{header:true,transformHeader:(h,i)=>h.trim()||('Unnamed: '+i),preview:6,skipEmptyLines:'greedy',dynamicTyping:false});
  const columns=parsed.meta.fields||[];
  if(columns.length<2||!parsed.data.length)throw new Error('無法讀取 CSV，至少需要 2 欄及資料列。');
  if(parsed.meta.renamedHeaders&&Object.keys(parsed.meta.renamedHeaders).length)throw new Error('欄位名稱重複，請先修正 CSV。');
  $('target').replaceChildren(...columns.map(c=>{const o=document.createElement('option');o.value=o.textContent=c;return o;}));
  const known=columns.find(c=>['profit','price','saleprice','floodprobability','target','y'].includes(c.toLowerCase()));
  $('target').value=columns.includes(defaultTarget)?defaultTarget:(known||columns[columns.length-1]);
  $('exclude-fields').replaceChildren(...columns.map(c=>{const label=document.createElement('label');const input=document.createElement('input');input.type='checkbox';input.value=c;input.checked=excluded.includes(c)||c.startsWith('Unnamed:')||['id','index','date',''].includes(c.toLowerCase());label.append(input,document.createTextNode(' '+(c||'(未命名索引)')));return label;}));
  syncTarget();
}
function syncTarget(){document.querySelectorAll('#exclude-fields input').forEach(el=>{el.disabled=el.value===$('target').value;if(el.disabled)el.checked=false;});}
async function fetchText(url){
  const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),30000);
  try{
    const response=await fetch(url,{signal:controller.signal,credentials:'omit'});
    if(!response.ok)throw new Error('HTTP '+response.status+'，請確認網址能公開下載。');
    if(Number(response.headers.get('content-length'))>10*1024*1024)throw new Error('檔案超過 10 MB。');
    const reader=response.body.getReader();let total=0;const chunks=[];
    while(true){const {done,value}=await reader.read();if(done)break;total+=value.length;if(total>10*1024*1024){await reader.cancel();throw new Error('檔案超過 10 MB，請先縮小或抽樣。');}chunks.push(value);}
    return await new Blob(chunks).text();
  }finally{clearTimeout(timer);}
}
async function selectProblem(key){
  const generation=++state.generation;state.problem=key;
  const p=problems[key];$('problem-copy').textContent=p.copy;
  $('source-info').innerHTML=p.url?`<a href="${p.url}" target="_blank" rel="noopener">${escapeHTML(p.source)} ↗</a><span>網站樣本：固定 seed 42，4,000 筆</span>`:'自訂資料僅在瀏覽器中處理。';
  clearResult();state.csv='';state.name=p.title;state.source=p.url||'';
  $('target').replaceChildren();$('exclude-fields').replaceChildren();
  if(key==='custom'){$('custom-panel').open=true;status('請輸入 CSV 網址或上傳檔案。');return;}
  busy(true);status('正在載入 '+p.title+' 的資料與示範結果…',false,true);
  try{
    const [csv,result]=await Promise.all([fetchText('data/'+key+'_sample.csv'),fetch('data/'+key+'_result.json').then(r=>{if(!r.ok)throw new Error('無法載入示範結果。');return r.json();})]);
    if(generation!==state.generation)return;
    schema(csv,p.target,p.excluded);state.csv=csv;render(result,true);status('已載入示範結果。按「執行回歸分析」可在瀏覽器重新計算。');
  }catch(e){status(e.message,true);}finally{busy(false);}
}
function acceptCustom(csv,name,source){
  if(new TextEncoder().encode(csv).length>10*1024*1024)throw new Error('檔案超過 10 MB。');
  if(csv.trimStart().startsWith('<'))throw new Error('這個網址回傳 HTML 網頁，請改用 CSV 原始檔網址。');
  schema(csv,undefined);state.csv=csv;state.name=name;state.source=source;state.problem='custom';$('problem').value='custom';
  $('problem-copy').textContent=problems.custom.copy;
  $('source-info').textContent='目前資料：'+name+'；請確認 Target 與排除欄位。';clearResult();showTab('overview');
  status('資料已載入。請選擇 Target，然後執行回歸分析。');
}
function getWorker(){
  if(!state.worker){
    const worker=new Worker('worker.js');state.worker=worker;
    worker.onmessage=({data})=>{
      if(worker!==state.worker)return;
      if(data.type==='status')status(data.message,false,true);
      else if(data.type==='result'){busy(false);render(data.result,false);status('分析完成：已重新執行 Python LinearRegression、五折 CV 及區間校準。');}
      else if(data.type==='error'){busy(false);status('分析失敗：'+data.message,true);}
    };
    worker.onerror=e=>{busy(false);status('Python 載入失敗，請確認網路能存取 jsDelivr，再重試。'+(e.message||''),true);worker.terminate();state.worker=null;};
  }
  return state.worker;
}
function run(){
  if(state.busy)return;if(!state.csv){status('請先載入 Dataset。',true);return;}
  const excluded=[...document.querySelectorAll('#exclude-fields input:checked')].map(el=>el.value).filter(c=>c!==$('target').value);
  clearResult();busy(true);status('準備分析，首次使用需下載 Python 與套件…',false,true);
  getWorker().postMessage({type:'run',csv:state.csv,config:{target:$('target').value,excluded,max_rows:Number($('sample').value),alpha:.05}});
}
const layout={font:{family:'Segoe UI, Microsoft JhengHei, sans-serif',size:11,color:'#65756b'},paper_bgcolor:'transparent',plot_bgcolor:'transparent',margin:{l:58,r:22,t:18,b:45},colorway:['#28685b','#c98245','#93aa7e'],xaxis:{gridcolor:'#eff2eb',zeroline:false},yaxis:{gridcolor:'#e9eee5',zeroline:false},legend:{orientation:'h',y:-.22,font:{size:10}},hovermode:'closest'};
function plot(id,data,extra={}){
  if(!window.Plotly){$(id).textContent='圖表元件載入失敗，請重新整理；數值仍可從表格及下載檔查看。';return;}
  const active=$(id).closest('.panel').classList.contains('active');
  Plotly.react(id,data,structuredClone({...layout,...extra}),{responsive:true,displayModeBar:false}).then(()=>{if(active)Plotly.Plots.resize($(id));});
}
function table(id,headers,rows){$(id).innerHTML='<table><thead><tr>'+headers.map(h=>'<th>'+escapeHTML(h)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(row=>'<tr>'+row.map(v=>'<td>'+escapeHTML(v)+'</td>').join('')+'</tr>').join('')+'</tbody></table>';}
function intervalChart(){
  const r=state.result;if(!r)return;
  // Deterministic even-spaced sample from held-out row order, sorted for display.
  const points=r.predictions.filter((_,i)=>i%Math.max(1,Math.ceil(r.predictions.length/100))===0).slice(0,100).sort((a,b)=>a.prediction-b.prediction);
  const x=points.map((_,i)=>i+1),kind=$('interval-type').value;
  const lo=kind==='conformal'?'lower':kind+'_lower',hi=kind==='conformal'?'upper':kind+'_upper';
  const label=$('interval-type').selectedOptions[0].textContent;
  $('interval-description').textContent=label+(kind==='mean_ci'?' · 估計平均反應，不是單筆新觀測範圍':' · 在各自假設下描述新觀測的不確定性');
  plot('interval-chart',[
    {x,y:points.map(p=>p[lo]),type:'scatter',mode:'lines',line:{width:0},showlegend:false,hoverinfo:'skip'},
    {x,y:points.map(p=>p[hi]),type:'scatter',mode:'lines',line:{width:0},fill:'tonexty',fillcolor:'rgba(119,146,107,.19)',name:label,hoverinfo:'skip'},
    {x,y:points.map(p=>p.prediction),type:'scatter',mode:'lines',line:{color:'#28685b',width:2},name:'模型預測'},
    {x,y:points.map(p=>p.actual),type:'scatter',mode:'markers',marker:{color:'#c98245',size:5},name:'實際值',customdata:points.map(p=>p.row),hovertemplate:'原始 CSV 列 %{customdata}<br>實際值 %{y:.5g}<extra></extra>'}
  ],{xaxis:{...layout.xaxis,title:{text:'測試案例（依預測值排序）',font:{size:10}}},yaxis:{...layout.yaxis,title:{text:r.target,font:{size:10}}}});
}
function render(r,demo){
  state.result=r;document.querySelectorAll('#features .chart-grid,#features > .card').forEach(el=>el.hidden=false);$('features-empty').hidden=true;r.dataset_name=state.name;r.dataset_source=state.source;r.computation=demo?'precomputed':'browser-python';
  $('result-content').hidden=false;$('empty').hidden=true;['download-json','download-csv','print'].forEach(id=>$(id).disabled=false);
  const m=r.metrics[r.metrics.length-1];$('result-title').textContent=state.name+' · 模型總覽';
  $('result-mode').textContent=demo?'預先計算示範 · 4,000 筆':'本次瀏覽器實際分析 · '+r.sample_rows.toLocaleString()+' 筆';
  $('kpi-r2').textContent=fmt(m.r2);$('kpi-rmse').textContent=fmt(m.rmse);$('kpi-coverage').textContent=(r.interval.coverage*100).toFixed(2)+'%';
  $('kpi-features').innerHTML=r.selected_features.length+' <em>/ '+r.encoded_features+'</em>';
  $('feature-caption').textContent=r.original_features+' 個原始輸入特徵 · 編碼後選入';
  $('target-unit').textContent='越低越好 · '+(problems[state.problem]?.unit||'Target 原始單位');
  const notes=[...r.notices];if(!r.assignment_eligible)notes.unshift('這份資料有 '+r.original_features+' 個原始輸入特徵，未符合主要題目 14–39 個特徵限制；可用於自訂 Dataset 加分功能示範。');
  if(r.split.calibration/ r.sample_rows>.25)notes.push('小資料集調整：為建立有限的 95% conformal 區間，保留至少 19 筆校準資料；實際切分筆數如下。');
  $('notices').innerHTML=notes.map(t=>'<div class="notice">'+escapeHTML(t)+'</div>').join('');
  $('split-summary').textContent=`來源 ${r.source_rows.toLocaleString()} 筆，分析 ${r.sample_rows.toLocaleString()} 筆；訓練 ${r.split.train}、校準 ${r.split.calibration}、測試 ${r.split.test}。排除 Target 缺失或非數值 ${r.removed_target} 筆。95% 區間平均寬度 ${fmt(r.interval.width)}，校準殘差第 ${r.interval.rank} 順位；seed = ${r.seed}。`;
  intervalChart();
  const pred=r.predictions,range=[Math.min(...pred.map(p=>Math.min(p.actual,p.prediction))),Math.max(...pred.map(p=>Math.max(p.actual,p.prediction)))];
  plot('scatter-chart',[{x:pred.map(p=>p.actual),y:pred.map(p=>p.prediction),type:'scatter',mode:'markers',marker:{color:'#28685b',size:4,opacity:.38},name:'測試資料'},{x:range,y:range,type:'scatter',mode:'lines',line:{color:'#99a093',dash:'dash'},showlegend:false}],{showlegend:false,xaxis:{...layout.xaxis,title:'實際值'},yaxis:{...layout.yaxis,title:'預測值'}});
  table('metrics-table',['模型','特徵','MAE','MSE','RMSE','R²','調整 R²'],r.metrics.map(m=>[m.model,m.features,fmt(m.mae),fmt(m.mse),fmt(m.rmse),fmt(m.r2),fmt(m.adjusted_r2)]));
  table('selection-table',['保留比例','最終欄數','CV RMSE','折間 SD'],r.selection.map(s=>[(s.fraction*100).toFixed(1)+'%',s.k,fmt(s.rmse),fmt(s.sd)]));
  plot('selection-chart',[{x:r.selection.map(s=>(s.fraction*100).toFixed(1)+'%'),y:r.selection.map(s=>s.rmse),error_y:{type:'data',array:r.selection.map(s=>s.sd),visible:true,color:'#91a780'},type:'scatter',mode:'lines+markers',line:{color:'#28685b'},marker:{size:7},name:'五折 CV RMSE'}],{showlegend:false,xaxis:{...layout.xaxis,title:'保留編碼特徵比例'},yaxis:{...layout.yaxis,title:'CV RMSE（± 折間 SD）'}});
  const coef=r.coefficients.slice(0,15).reverse();
  plot('coefficient-chart',[{x:coef.map(c=>c.coefficient),y:coef.map(c=>c.feature),orientation:'h',type:'bar',marker:{color:coef.map(c=>c.coefficient>=0?'#28685b':'#c98245')}}],{margin:{l:155,r:15,t:10,b:40},showlegend:false,xaxis:{...layout.xaxis,title:'回歸係數'}});
  $('selected-names').innerHTML=r.selected_features.map(f=>'<span>'+escapeHTML(f)+'</span>').join('');
  plot('residual-chart',[{x:r.training_residuals.map(p=>p.fitted),y:r.training_residuals.map(p=>p.residual),type:'scatter',mode:'markers',marker:{color:'#28685b',size:4,opacity:.4}}],{showlegend:false,xaxis:{...layout.xaxis,title:'訓練擬合值'},yaxis:{...layout.yaxis,title:'殘差'}});
  plot('qq-chart',[{x:r.qq.map(p=>p.theoretical),y:r.qq.map(p=>p.observed),type:'scatter',mode:'markers',marker:{color:'#28685b',size:4,opacity:.6}}],{showlegend:false,xaxis:{...layout.xaxis,title:'常態理論分位數'},yaxis:{...layout.yaxis,title:'殘差分位數'}});
  const d=r.diagnostics;$('diagnostics').textContent=`Jarque–Bera p = ${Number(d.jarque_bera_p).toExponential(3)}；設計矩陣秩 ${d.design_rank} / ${d.design_columns}；殘差自由度 ${d.residual_df}。`;
  updateCrisp(r);showTab('overview');
}
function updateCrisp(r){
  const p=problems[state.problem];
  const cards=[['Business Understanding','定義可回答的問題',state.problem==='flood'?'以 20 項環境與管理分數預測合成 FloodProbability。這是風險分數建模練習，不能用作真實防災警報。':state.problem==='housing'?'利用房屋條件、鄰近房產與地理座標預測歷史成交價，觀察線性關係與模型誤差。':'以使用者選擇的 '+r.target+' 為數值預測目標，需自行確認欄位在實際預測時可取得，避免目標洩漏。'],
    ['Data Understanding','確認資料與限制',`${state.name}：來源 ${r.source_rows} 筆、分析 ${r.sample_rows} 筆、${r.original_features} 個原始特徵、${r.encoded_features} 個編碼特徵。排除欄位：${r.excluded.join(', ')||'無'}。`],
    ['Data Preparation','先切分，再處理',`seed 42；訓練 / 校準 / 測試為 ${r.split.train} / ${r.split.calibration} / ${r.split.test}。數值中位數補值與標準化、類別眾數補值及 one-hot，均只 fit 訓練折。`],
    ['Modeling','讓訓練集決定特徵','比較平均值基線、全特徵 LinearRegression 與訓練集五折 CV 選出的 SelectKBest + LinearRegression。CV 比較 1 欄、50%、75%、全部欄位。'],
    ['Evaluation','同時報告誤差與不確定性','在獨立測試集報告 MAE、MSE、RMSE、R²、調整 R²、區間覆蓋率與寬度，檢查殘差、Q-Q 與矩陣秩。特徵選擇與預處理不接觸測試標籤。'],
    ['Deployment','能操作，也能重現','透過網頁下拉切換題目、載入新 CSV 並實際重新建模；下載結果 JSON / CSV。Python 引擎與網站原始碼一併提供，資料留在瀏覽器，首次執行需網路下載套件。']];
  $('crisp-cards').innerHTML=cards.map((c,i)=>'<article class="crisp-card"><b>0'+(i+1)+' / '+c[0]+'</b><h3>'+c[1]+'</h3><p>'+escapeHTML(c[2])+'</p></article>').join('');
}
function download(filename,content,type){const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),10000);}
function csvExport(){if(!state.result)return;const rows=state.result.predictions;download('test_predictions.csv','\uFEFF'+Papa.unparse(rows),'text/csv;charset=utf-8');}
async function init(){
  document.querySelectorAll('.nav').forEach(el=>el.onclick=()=>showTab(el.dataset.tab));
  $('problem').onchange=()=>selectProblem($('problem').value);
  $('target').onchange=()=>{syncTarget();if(state.result){clearResult();status('Target 已變更，請重新執行分析。');}};
  $('sample').onchange=()=>{if(state.result){clearResult();status('分析筆數已變更，請重新執行分析。');}};
  $('exclude-fields').onchange=()=>{if(state.result){clearResult();status('排除欄位已變更，請重新執行分析。');}};
  $('interval-type').onchange=intervalChart;$('run').onclick=run;
  $('cancel').onclick=()=>{state.generation++;state.worker?.terminate();state.worker=null;busy(false);status('已取消。資料保留，可重新執行。');};
  $('example').onclick=()=>{$('dataset-url').value='https://raw.githubusercontent.com/Avik-Jain/100-Days-Of-ML-Code/master/datasets/50_Startups.csv';$('custom-panel').open=true;status('範例網址已填入，請按「載入網址」。');};
  $('load-url').onclick=async()=>{let url;try{url=new URL($('dataset-url').value);if(!['https:','http:'].includes(url.protocol))throw new Error();}catch{status('請輸入完整的 http 或 https CSV 網址。',true);return;}
    const generation=++state.generation;busy(true);status('正在下載自訂 CSV…',false,true);try{const csv=await fetchText(url.href);if(generation!==state.generation)return;acceptCustom(csv,url.pathname.split('/').pop()||'自訂 CSV',url.href);}catch(e){status('無法載入：'+e.message+' 若為 CORS 限制，請下載 CSV 後使用上傳功能。',true);}finally{busy(false);}};
  $('file').onchange=async()=>{const file=$('file').files[0];if(!file)return;try{if(file.size>10*1024*1024)throw new Error('檔案超過 10 MB。');acceptCustom(await file.text(),file.name,'本機上傳');}catch(e){status(e.message,true);}$('file').value='';};
  $('download-json').onclick=()=>{if(state.result)download('analysis_result.json',JSON.stringify(state.result,null,2),'application/json');};
  $('download-csv').onclick=csvExport;$('download-data').onclick=()=>{if(state.csv)download('dataset.csv','\uFEFF'+state.csv,'text/csv;charset=utf-8');else status('請先載入 Dataset。',true);};
  $('print').onclick=()=>window.print();window.addEventListener('beforeprint',()=>document.querySelectorAll('.js-plotly-plot').forEach(el=>Plotly.Plots.resize(el)));
  selectProblem('flood');
  try{const n=await fetch('data/notebooklm.json').then(r=>r.json());$('notebook-summary').innerHTML=n.summary.split('\n\n').map(p=>'<p>'+escapeHTML(p)+'</p>').join('');$('notebook-link').href=n.notebook_url;$('research-sources').innerHTML=n.sources.map(s=>'<a href="'+escapeHTML(s.url)+'" target="_blank" rel="noopener">['+s.id+'] '+escapeHTML(s.title)+' ↗</a>').join('');}catch{$('notebook-summary').textContent='研究摘要載入失敗，請從原始報告或作業檔案查看。';}
}
init();
