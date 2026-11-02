let runtime;
async function initialize() {
  if (!runtime) runtime = (async () => {
    postMessage({type:'status',message:'正在載入 Python 與分析套件，首次約需 30–90 秒…'});
    importScripts('https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.js');
    const py = await loadPyodide({indexURL:'https://cdn.jsdelivr.net/pyodide/v0.27.7/full/'});
    await py.loadPackage(['numpy','pandas','scipy','scikit-learn']);
    const response = await fetch('analysis.py');
    if (!response.ok) throw new Error('無法載入分析程式。');
    await py.runPythonAsync(await response.text());
    return py;
  })().catch(e => {runtime=null; throw e;});
  return runtime;
}
self.onmessage = async ({data}) => {
  try {
    const py = await initialize();
    py.globals.set('csv_input',data.csv);
    if (data.type === 'inspect') {
      postMessage({type:'inspected',result:JSON.parse(await py.runPythonAsync('inspect_csv(csv_input)'))});
    } else {
      postMessage({type:'status',message:'正在進行五折交叉驗證、特徵選擇與區間校準…'});
      py.globals.set('config_json',JSON.stringify(data.config));
      postMessage({type:'result',result:JSON.parse(await py.runPythonAsync('run_analysis(csv_input, **json.loads(config_json))'))});
    }
    py.globals.delete('csv_input');
  } catch (e) {postMessage({type:'error',message:String(e.message||e)});}
};
