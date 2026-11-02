# NotebookLM 研究筆記

研究日期：2026-11-03。

本次在 NotebookLM 使用 Fast Research 搜尋多元線性回歸、特徵選擇、Pipeline、交叉驗證與預測區間解法。檢視搜尋結果後，選入 UBC、BYU 與 South Carolina 三份大學教材，另加入 Kaggle King County 房價資料背景，與原有六份網路來源合併研究。舊的洪水摘要記事未勾選為本次研究來源。

## NotebookLM 摘要

在 Kaggle 洪水預測競賽中，參賽者假說 20 個特徵為等價偽隨機數，並提出「列總和」與跨欄排序等對稱特徵工程作為候選解法，惟其效果仍須經訓練集交叉驗證，不可斷言已優於原始線性回歸。在資料特性與外推限制上，洪水資料集係由深度學習模型生成的合成資料，分佈僅接近原始資料而非真實觀測；King County 房價則為 2014 至 2015 年的真實歷史房屋交易記錄。若將模型外推至資料範圍之外，預測力將受限。 〔N1、N2、N7、N9〕

依據 UBC 與 scikit-learn 指南，標準流程應先切分訓練與測試集，再執行補值、縮放與單熱編碼；需注意 OLS 估計並非必須標準化。為防止資料洩漏，應將 SelectKBest 特徵選擇與模型封裝至 Pipeline 中，使 fit 僅作用於每個 CV 的訓練折，測試集則嚴格保留至最終評估。 〔N3、N4、N8、N10〕

在相同 OLS 模型、信賴水準與特徵條件下，平均反應信賴區間僅估計總體均值不確定性，而單一新觀測預測區間因包含個體隨機誤差，範圍必定較寬。若採用 Split-Conformal 預測，雖可提供無分佈假設的保證，但需滿足可交換性且僅限邊際覆蓋。尚待驗證的改進建議，是將對稱特徵工程建構為自訂轉換器併入 Pipeline，透過 CV 嚴格驗證其效益。 〔N2、N6、N9〕

摘要原文字數：370 個中文字（不含引用編號）。正文未改寫，只移除 Markdown 標題並整理引用編號。

## 研究與採用方式

先請 NotebookLM 根據十份已勾選的網路來源產生摘要，再追問釐清特徵工程尚未在本作業驗證，以及平均 CI／單筆 PI 須在相同模型與條件下比較。最終回覆已存為「NotebookLM 摘要｜洪水與房價多元線性回歸」記事。

報告在資料背景、Pipeline 防洩漏、特徵選擇與預測區間的採用段落，標示「NotebookLM 摘要」及 N 編號。列總和與跨欄排序保留為待驗證改進，不作為已完成實驗。

報告另以「GPT 輔助內容」及 G1–G6 編號標示此次 ChatGPT 問答的採用位置，與 NotebookLM 研究來源分別對照。

## 閱讀來源

- [N1] [Kaggle S4E5：官方資料說明](https://www.kaggle.com/competitions/playground-series-s4e5/data)
- [N2] [Kaggle：Sorting along the feature axis as feature engineering](https://www.kaggle.com/competitions/playground-series-s4e5/discussion/499579)
- [N3] [scikit-learn：Feature selection](https://scikit-learn.org/stable/modules/feature_selection.html)
- [N4] [scikit-learn：Common pitfalls and recommended practices](https://scikit-learn.org/stable/common_pitfalls.html)
- [N5] [statsmodels：OLSResults.get_prediction](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLSResults.get_prediction.html)
- [N6] [Angelopoulos and Bates：A Gentle Introduction to Conformal Prediction](https://arxiv.org/abs/2107.07511)
- [N7] [Kaggle：House Sales in King County, USA](https://www.kaggle.com/datasets/harlfoxem/housesalesprediction)
- [N8] [UBC CPSC 330：Preprocessing and sklearn pipelines](https://ubc-cs.github.io/cpsc330-2024W2/lectures/notes/05_preprocessing-pipelines.html)
- [N9] [BYU Stat 121：Multiple Linear Regression - Prediction](https://stat121.byu.edu/Content_in_Quarto/Unit_7_MLR/3_Prediction/LectureNotes/MLR_Prediction.pdf)
- [N10] [University of South Carolina：Multiple Linear Regression](https://people.stat.sc.edu/sshen/courses/17smstat509/notes/Chapter%209%20Multiple%20Linear%20Regression.pdf)

## 研究記錄

- [研究摘要與來源記錄](output/evidence/notebooklm_revision/research_result.json)
- [兩輪提問](output/evidence/notebooklm_revision/research_prompts.json)
- [NotebookLM 最終原文](output/evidence/notebooklm_revision/final_response.txt)

公開研究記錄保留提問、回覆與網路來源，原始瀏覽器畫面及私人筆記本資訊保存在本機。
