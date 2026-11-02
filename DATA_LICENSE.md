# 資料來源與授權記錄

本儲存庫保留網站使用的固定樣本與 CSV 範例。完整原始下載檔及舊版分析輸出不隨專案附送。

## 洪水合成資料

- 原競賽：[Regression with a Flood Prediction Dataset，Kaggle S4E5](https://www.kaggle.com/competitions/playground-series-s4e5/data)。
- 取得來源：[Naiya Khalid，Flood Prediction Dataset，version 2](https://www.kaggle.com/datasets/naiyakhalid/flood-prediction-dataset)。原下載記錄日期為 2026-10-20，包含競賽 train.csv。
- 原競賽記錄之授權為 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)，下載資料卡另標示 CC0；本專案保留兩個來源及原競賽歸屬資訊。
- 隨附檔案：`web/dist/data/flood_sample.csv`。此檔從先前固定 50,000 筆抽樣資料，再以 seed 42 抽取 4,000 筆，保留原欄位與目標。
- 資料為模型生成的合成分數，未驗證為真實洪災機率。

## King County 房價

- 資料集：[House Sales in King County, USA](https://www.kaggle.com/datasets/harlfoxem/housesalesprediction)。原取得記錄之資料卡標示 CC0。
- [CSV 鏡像](https://raw.githubusercontent.com/rheera/data-analysis-with-python/main/kc_house_data.csv)。抽樣時移除額外 CSV 索引，再以 seed 42 抽取 4,000 筆。
- 隨附檔案：`web/dist/data/housing_sample.csv`。來源為 21,613 筆歷史交易；排除 id、date 與 price 後有 18 個預測特徵。
- 價格為 2014–2015 年交易金額，單位 USD。

## 50 Startups

- [來源 CSV](https://raw.githubusercontent.com/Avik-Jain/100-Days-Of-ML-Code/master/datasets/50_Startups.csv)。
- `data/50_Startups.csv` 供 CLI 與測試使用，網站目錄內另附一份供下載和上傳測試。
- 保留來源連結；不額外宣稱未驗證的資料授權或蒐集方式。

## 網站套件與衍生檔案

- Papa Parse 5.5.3 與 Plotly.js 2.35.2 採 MIT 授權，`web/dist/vendor/` 原始檔保留授權註記。
- Pyodide 0.27.7 從官方 jsDelivr 發行路徑載入。
- 對應 `*_result.json` 保留樣本 SHA-256、切分列號、設定與逐筆結果；圖表及 PDF 為本專案分析與整理的衍生產出。
