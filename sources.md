# 參考資料與閱讀筆記

查閱日期：2026-10-20。

## 資料集

1. Naiya Khalid，**Flood Prediction Dataset**，Kaggle，version 2。
   https://www.kaggle.com/datasets/naiyakhalid/flood-prediction-dataset

   下載檔案包含 flood.csv、train.csv、test.csv 及 sample_submission.csv。本作業使用 train.csv 進行分析，flood.csv 則用來比較資料特性。資料頁註明原始蒐集方式與地理範圍不明。讀檔後也發現 FloodProbability 是浮點數，與介紹中「全部欄位皆為整數」的描述不同。

2. Kaggle，**Regression with a Flood Prediction Dataset**，Playground Series S4E5。
   https://www.kaggle.com/competitions/playground-series-s4e5/data

   官方說明 train/test 是用深度學習模型從原始 Flood Prediction Factors 資料生成，分布與原始資料接近。本作業因此將它視為合成資料，主要比較模型的預測表現。

## 特徵工程與模型

3. broccoli beef，**Sorting along the feature axis as "feature engineering"**，Kaggle 討論。
   https://www.kaggle.com/competitions/playground-series-s4e5/discussion/499579

   討論提到列總和、跨欄排序等對稱特徵工程，並提出原始資料中的特徵可能有相近作用的假說。我參考列總和的想法，分別放入 OLS 及 HistGB 比較，結果列在報告第 11 節。

4. scikit-learn，**Feature selection**。
   https://scikit-learn.org/stable/modules/feature_selection.html

   我參考此文件了解 SelectKBest 的單變量分數與 RFE 的遞迴刪除方式，並以交叉驗證比較不同特徵數。

5. scikit-learn，**Common pitfalls and recommended practices**。
   https://scikit-learn.org/stable/common_pitfalls.html

   這份文件說明前處理及特徵選擇造成資料洩漏的情況。本作業先切分資料，再用 Pipeline 讓每一折只從訓練資料估計轉換規則。

6. statsmodels，**OLSResults.get_prediction**。
   https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLSResults.get_prediction.html

   此方法可以計算平均反應的信賴區間與單一觀測的預測區間。我將兩種區間存入逐筆預測結果，並比較它們的寬度與用途。

7. scikit-learn，**Histogram-based Gradient Boosting**。
   https://scikit-learn.org/stable/modules/ensemble.html#histogram-based-gradient-boosting

   我使用 HistGradientBoostingRegressor 作為非線性模型，觀察原始 20 欄及加入列總和後的結果差異。

8. Angelopoulos, A. N. and Bates, S.，**A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification**，arXiv:2107.07511，2021／2022。
   https://arxiv.org/abs/2107.07511

   本作業使用獨立校準資料的絕對殘差，計算 split-conformal 預測區間。解釋結果時，我保留校準與新資料需可交換的前提；整體覆蓋率也不等於各個子群都有相同覆蓋率。

## 圖表整理

我使用 matplotlib 繪製目標分布、相關矩陣、特徵選擇、模型誤差、實際與預測值、預測區間、殘差及係數圖。除最後評估外，資料探索及模型診斷都使用訓練資料。

散布圖固定抽取 2,500 筆測試資料，區間圖固定抽取 120 筆，再依預測值排序；評估指標仍以全部 10,000 筆測試資料計算。圖中的排序不代表時間變化。

資料來源與授權另整理於 DATA_LICENSE.md。

## 修訂版新增參考資料（2026-11-02）

- House Sales in King County, USA：https://www.kaggle.com/datasets/harlfoxem/housesalesprediction
- CSV 取得鏡像：https://github.com/rheera/data-analysis-with-python/blob/main/kc_house_data.csv
- 教師指定 50 Startups：https://raw.githubusercontent.com/Avik-Jain/100-Days-Of-ML-Code/master/datasets/50_Startups.csv
- Pyodide 官方套件載入：https://pyodide.org/en/stable/usage/loading-packages.html
- 網站採用 scikit-learn LinearRegression + Pipeline + SelectKBest；conformal 方法與既有研究沿用上述 primary sources。
