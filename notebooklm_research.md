# NotebookLM 研究筆記

研究日期：2026-10-20。

我使用 NotebookLM 閱讀洪水資料的相關解法，將六個網路來源匯入 [HW2 洪水分數的多元線性回歸研究](https://notebook.google.com/notebook/11cff97a-cbaa-4e58-8eca-b6541d1b25e2)，摘要已存為「洪水預測研究」記事。

## 閱讀來源

- [Kaggle 官方資料說明](https://www.kaggle.com/competitions/playground-series-s4e5/data)
- [Kaggle 特徵工程討論](https://www.kaggle.com/competitions/playground-series-s4e5/discussion/499579)
- [scikit-learn 特徵選擇](https://scikit-learn.org/stable/modules/feature_selection.html)
- [scikit-learn 資料洩漏與常見問題](https://scikit-learn.org/stable/common_pitfalls.html)
- [statsmodels 信賴區間與預測區間](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLSResults.get_prediction.html)
- [Conformal Prediction 教學論文](https://arxiv.org/abs/2107.07511)

## 研究過程

第一輪提問著重在資料性質、列總和與跨欄排序、SelectKBest 與 RFE、Pipeline 的資料洩漏問題，以及信賴區間與預測區間的差別。

閱讀回覆後，我再請 NotebookLM 釐清三個地方：資料分布接近的是「原始資料」，不等於真實觀測；特徵等價性是參賽者提出的假說；conformal prediction 的覆蓋性質仍需要可交換性等條件。

校正後摘要共 276 個中文字，已放入報告「NotebookLM 摘要」。我只整理了引用編號及文字格式，保留原來的摘要內容。

## 相關檔案

- `notebooklm_raw.txt`：兩輪完整提問與原始回覆。
- `notebooklm_result.json`：採用摘要、筆記本網址與來源清單。
- `notebooklm_dom.txt`：原頁面的引用標記。
- `output/evidence/notebooklm_research.jpg`：保存摘要的頁面截圖。
