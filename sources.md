# 參考資料

本專案以網站附帶的固定樣本進行分析：洪水及房價各 4,000 筆，使用 seed 42 切分訓練、校準與測試資料。來源與授權記錄見 [DATA_LICENSE.md](DATA_LICENSE.md)。

## 資料集

- [Kaggle：Regression with a Flood Prediction Dataset](https://www.kaggle.com/competitions/playground-series-s4e5/data)：20 個數值特徵與 FloodProbability。資料由模型生成，分析結果用於理解合成分數。
- [Kaggle：House Sales in King County, USA](https://www.kaggle.com/datasets/harlfoxem/housesalesprediction)：2014–2015 年房屋交易，以 18 個原始輸入特徵預測 price。[CSV 鏡像](https://github.com/rheera/data-analysis-with-python/blob/main/kc_house_data.csv)。
- [50 Startups CSV](https://raw.githubusercontent.com/Avik-Jain/100-Days-Of-ML-Code/master/datasets/50_Startups.csv)：自訂資料輸入範例，含 4 個原始特徵與 Profit。

## 模型與區間

- [scikit-learn：Feature selection](https://scikit-learn.org/stable/modules/feature_selection.html)：SelectKBest 與其他特徵選擇方法。
- [scikit-learn：Common pitfalls](https://scikit-learn.org/stable/common_pitfalls.html)：Pipeline、訓練折內前處理與資料洩漏。
- [statsmodels：get_prediction](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLSResults.get_prediction.html)：平均反應 CI 與單筆 PI 的方法參考；本專案引擎使用 NumPy／SciPy 計算。
- [Angelopoulos 與 Bates：Conformal Prediction](https://arxiv.org/abs/2107.07511)：獨立校準、可交換性與邊際覆蓋。
- [Kaggle：Sorting along the feature axis](https://www.kaggle.com/competitions/playground-series-s4e5/discussion/499579)：列總和與跨欄排序的候選解法，保留為後續驗證方向。

## 網站與研究

- [Pyodide：套件載入](https://pyodide.org/en/stable/usage/loading-packages.html)：瀏覽器 Python 執行環境。
- [NotebookLM 研究筆記](notebooklm_research.md)：本次研究摘要、十份來源及提問記錄。

測試指標依網站全部 800 筆測試資料計算。報告區間圖展示固定抽取的 100 筆案例，按預測值排序，橫軸不表示時間。診斷使用訓練資料；模型係數不作因果解釋。
