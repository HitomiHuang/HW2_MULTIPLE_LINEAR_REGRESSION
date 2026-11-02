# 5113056021 HW2：多元線性回歸實驗室

依 2026-11-02 修訂作業要求製作，完成加總分 2 分所需功能。實際評分依教師驗收。

- **網站**：[Regression Lab](https://hw2-regression-lab-5113056021.ivy819.chatgpt.site)
- **GitHub**：[HW2_MULTIPLE_LINEAR_REGRESSION](https://github.com/HitomiHuang/HW2_MULTIPLE_LINEAR_REGRESSION)

## 加分功能與驗收

1. **Problem 下拉選單**：切換洪水風險分數（20 個原始輸入特徵）與 King County 房價（18 個），各有資料、模型、特徵選擇及評估。
2. **任意 Dataset**：貼上公開 CSV 網址或上傳 UTF-8 CSV/TSV，選擇 Target 與排除欄位，按「執行回歸分析」實際重新訓練。
3. 教師範例可直接貼入：
   `https://raw.githubusercontent.com/Avik-Jain/100-Days-Of-ML-Code/master/datasets/50_Startups.csv`，Target 選 **Profit**。
4. 查看特徵選擇、MAE / MSE / RMSE / R² / 調整 R²，切換 **95% conformal 預測區間、OLS 平均反應信賴區間、OLS 單筆預測區間**；下載完整 JSON 或逐筆 CSV。

50 Startups 有 4 個原始特徵，僅用來驗證自訂 Dataset；主要兩題均符合 14–39 特徵要求。原始特徵數不包含 Target、CSV 索引、ID、日期；one-hot 後欄數另列。

## 操作與執行

網站第一次顯示的是預先計算示範。按「執行回歸分析」後，Pyodide Web Worker 在瀏覽器內真正執行 **scikit-learn LinearRegression**。首次需從 jsDelivr 下載 Python 與 numpy/pandas/scipy/scikit-learn，約 30–90 秒，依網路情況而異。自訂資料留在瀏覽器，不送至網站伺服器。

URL 必須直接回傳 CSV 並允許 CORS；受限時可下載後上傳。互動版上限 10 MB、100 個原始特徵、300 個編碼特徵；至少 30 筆有效目標。可選 1,000 / 4,000 / 10,000 筆分析上限。文字欄位超過 40 類或訓練集全空會明示排除；本工具不是所有格式與無限資料量的通用服務。

在專案根目錄啟動網站：

```bash
python -m http.server 8765 --directory web/dist
```

瀏覽器開啟 `http://localhost:8765`。請透過 HTTP 伺服器使用；直接雙擊 HTML 不支援 Worker 與資料載入。

不開網頁也可重現（建議 Python 3.12）：

```bash
python -m pip install -r requirements.txt
python analyze_dataset.py --problem flood --output output/flood_recomputed.json
python analyze_dataset.py --problem housing --output output/housing_recomputed.json
python analyze_dataset.py --input data/50_Startups.csv --target Profit --output output/startups_recomputed.json
python -m unittest discover -s tests -v
```

`analyze_dataset.py` 與網站使用同一個 `web/dist/analysis.py`。Python CLI 也支援 `--input https://...csv`、`--exclude ID date`、`--max-rows 4000`。

## 方法：CRISP-DM

1. **Business Understanding**：預測合成洪水分數與歷史房屋成交價；不將係數當作因果。
2. **Data Understanding**：確認來源、列數、特徵數與目標。洪水為合成資料，房價為 2014–2015 年 King County 交易。
3. **Data Preparation**：網站兩題各固定抽取 4,000 筆，seed 42；60% 訓練、20% 校準、20% 測試。數值中位數補值、標準化，類別眾數補值與 one-hot，皆只 fit 訓練折。
4. **Modeling**：訓練集五折 CV 比較保留 1 欄、50%、75%、100% 的 SelectKBest + LinearRegression；以平均 CV RMSE 選擇。全特徵模型與平均值基線一併比較。兩個內建題目都由 CV 選出保留全部特徵。
5. **Evaluation**：獨立測試集指標、預測圖、區間覆蓋率與寬度；殘差、Q-Q、Jarque–Bera、設計矩陣秩。未宣稱所有回歸假設通過。
6. **Deployment**：網頁與 CLI 可重跑、自訂 Dataset、下載結果；來源、分割列號、CV 及逐筆區間均保留。

95% conformal 半寬是校準絕對殘差第 `ceil((n_cal + 1) × 0.95)` 順位。新資料與校準資料可交換是其邊際覆蓋前提，不代表每個子群或每次預測都有 95% 覆蓋。小樣本至少保留 19 筆校準，因此 **50 Startups 為 21 訓練 / 19 校準 / 10 測試**。OLS 區間需額外假設，且未校正選模不確定性，僅作參考。

## 網站樣本的實際結果

| 題目 | 原始特徵 | 選入編碼特徵 | 測試 RMSE | 測試 R² | 95% PI 實測覆蓋 |
|---|---:|---:|---:|---:|---:|
| 洪水分數 | 20 | 20 / 20 | 0.020139 | 0.859509 | 94.625% |
| King County 房價 | 18 | 18 / 18 | 214,640.38 USD | 0.678480 | 96.375% |
| 50 Startups（自訂範例） | 4 | 1 / 5 | 7,702.21 | 0.926742 | 100%（測試僅 10 筆） |

房價存在 `sqft_living = sqft_above + sqft_basement` 的精確共線性，程式會警示矩陣秩不足，使用 SVD 最小範數解，個別共線係數不具唯一解。zipcode 在這個基線採數值表示，是模型限制。資料的地理依賴、重複房產及時間外泛化未由隨機測試保證；房價區間較寬且不裁切負下界。

舊洪水報告使用 **50,000 筆與 64/16/20 切分**，OLS RMSE 0.020046、R² 0.843466。舊版與網站的資料範圍不同，不能混用指標。

## GPT 輔助內容與 NotebookLM 摘要

GPT 協助資料研究、Python/網站程式、圖表、數值檢查、報告及部署。數值由程式實際產生。

沿用 **2026-10-20 已在 NotebookLM 實際完成**、超過 100 個中文字的洪水研究摘要；網站與補充報告明示原研究日期及六個來源。研究範圍為洪水與統計方法，未假稱本次重新使用 NotebookLM 研究房價。見 `notebooklm_research.md`、`notebooklm_result.json`、原始提問回覆與證據截圖。

## 繳交檔案

- `web/dist/`：可直接部署的完整網站，含兩題樣本、預先計算結果與共用 Python 引擎。
- `analyze_dataset.py`：新版主程式，支援兩題及本機/URL CSV。
- `5113056021_hw2_update.pdf`：新版補充報告，含方法、兩題結果、區間圖與 AI 研究標示。
- `5113056021_hw2_report.pdf`：舊版 50,000 筆洪水完整報告，作為原始研究附錄。
- `5113056021_gpt_conversation_updated.pdf`：可取得的舊保存文字與本次更新對話，範圍截至匯出；不包含工具紀錄、內部推理或未取得的其他聊天。
- `5113056021_gpt_conversation.pdf`：原始 ChatGPT 網頁技術問答截圖 PDF。
- `5113056021_hw2_updated.zip`：精簡原始碼提交包，不重複包含網站下載區。
- `tests/test_web_analysis.py`：誤差/覆蓋率獨立重算、分割不重疊、測試/校準標籤不影響選模、小樣本與缺失值測試。
- `VALIDATION_WEB.md`：新版驗證紀錄；`output/web_validation.json` 為可檢查數值。

舊主程式 `5113056021_hw2.py` 仍保留；它需要完整 1,117,957 筆 `data/train.csv`。此約 59 MB 原檔保留在本機與原始提交包，GitHub/新版精簡包不重複散布；可依 `DATA_LICENSE.md` 從 Kaggle 下載。**新版主程式及網站所需樣本已隨庫附上，不需要 Kaggle 登入。**

重新產生網站示範：`python tools/prepare_web.py`（需本機舊分析樣本與完整房價資料）。重建報告：`python tools/build_update_report.py`（字型/對話來源依本機環境調整）。

## 來源

- [Kaggle Playground Series S4E5](https://www.kaggle.com/competitions/playground-series-s4e5/data)
- [Kaggle House Sales in King County, USA](https://www.kaggle.com/datasets/harlfoxem/housesalesprediction)
- [King County 公開 CSV 鏡像](https://github.com/rheera/data-analysis-with-python/blob/main/kc_house_data.csv)
- [50 Startups 範例](https://github.com/Avik-Jain/100-Days-Of-ML-Code/blob/master/datasets/50_Startups.csv)
- [scikit-learn 資料洩漏與 Pipeline](https://scikit-learn.org/stable/common_pitfalls.html)
- [Split conformal prediction 教學](https://arxiv.org/abs/2107.07511)

更多來源與授權記錄見 `sources.md`、`DATA_LICENSE.md`。Plotly.js 與 Papa Parse 為 MIT 授權，原檔保留授權註記；Python/Pyodide 依各專案授權。

## GitHub Pages（選用部署）

本庫附 `.github/workflows/pages.yml`。在 GitHub Settings → Pages 選擇 **GitHub Actions**，再執行 Deploy homework website，即發布 `web/dist`。網站本身是靜態檔，Python 建模在瀏覽器執行，不需要伺服器、金鑰或付費 API。
