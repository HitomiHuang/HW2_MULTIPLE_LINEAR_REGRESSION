# 資料來源與授權記錄

下載時間：2026-10-20（台北時間）。

本作業使用 Naiya Khalid 上傳之 **Flood Prediction Dataset**, Kaggle version 2：
https://www.kaggle.com/datasets/naiyakhalid/flood-prediction-dataset

資料卡標示 CC0，並註明來源、蒐集方法與地理涵蓋範圍無法獨立驗證。下載包包含四個 CSV；作業僅附使用的 train.csv，以及用於資料品質說明的 flood.csv。

train.csv 的研究脈絡為 Kaggle **Regression with a Flood Prediction Dataset**, Playground Series Season 4 Episode 5：
https://www.kaggle.com/competitions/playground-series-s4e5/data

原競賽資料頁標示 **Creative Commons Attribution 4.0 International (CC BY 4.0)**：
https://creativecommons.org/licenses/by/4.0/

原競賽說明資料由深度學習模型生成，分布與原始 Flood Prediction Factors 資料接近但不完全相同。本作業保留 Kaggle 與 Naiya Khalid 的來源資訊及連結。

本作業由 train.csv 固定抽取 50,000 筆並建立訓練／校準／測試分割；未修改隨附的完整 train.csv。抽樣檔、預測與圖表為本作業衍生產出。完整檔案雜湊及抽樣方式見 output/run_metadata.json。

## 修訂版新增資料（2026-11-02）

- House Sales in King County, USA：https://www.kaggle.com/datasets/harlfoxem/housesalesprediction 。來源卡標示 CC0；取得鏡像為 https://raw.githubusercontent.com/rheera/data-analysis-with-python/main/kc_house_data.csv 。鏡像含額外 CSV 索引，網站抽樣前已移除，原始檔保留在 data/kc_house_data.csv。來源有 21,613 筆、21 欄，排除 id/date/price 後 18 個預測特徵；網站固定 seed 42 抽取 4,000 筆。
- 教師範例 50 Startups：https://raw.githubusercontent.com/Avik-Jain/100-Days-Of-ML-Code/master/datasets/50_Startups.csv 。依作業指定用作 CSV 功能驗證；保留來源，未額外宣稱未驗證的資料授權或蒐集過程。只有 4 個原始特徵，不充當合規主要題目。
- 網站洪水樣本由既有 output/tables/analysis_sample.csv 以 seed 42 再抽 4,000 筆；維持原始來源標示與 CC BY 4.0 脈絡。各網站樣本 SHA-256 存在對應 data/*_result.json。
- 固定版本前端套件：Papa Parse 5.5.3、Plotly.js 2.35.2（MIT）；原始檔保留授權註記。Pyodide 0.27.7 由官方 jsDelivr 發行路徑載入。
