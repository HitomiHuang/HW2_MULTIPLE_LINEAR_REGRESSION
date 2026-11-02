# 程式執行與結果檢查

程式、報告與研究摘要已完成檢查。

我使用檢查程式確認資料分組、預測數值及儲存模型的結果，以下列出執行紀錄。

## 資料與計算結果
- 20 original predictors, excluding id and target
- Both assignment feature-count requirements satisfied
- Current main program passes Python syntax compilation
- 50,000 sampled rows recorded
- Every sampled row has exactly one split
- 32,000 / 8,000 / 10,000 disjoint split sizes
- Predictions contain exactly the held-out test ids
- Reported test targets match source sample
- OLS RMSE independently recomputed from saved predictions
- OLS R2 independently recomputed from saved predictions
- Prediction intervals contain each point prediction
- Conformal test coverage independently recomputed
- Finite-sample corrected 7,601st calibration residual verified
- Serialized model reload reproduces five deployment examples
- Source train.csv SHA-256 matches metadata
- Eight expected analytical figures present
- Combined report page count matches manifest
- Six CRISP-DM stages and separately marked AI sections present
- PDF text extraction has no Unicode replacement characters
- Both fixed 14-feature selection methods actually retain exactly 14 predictors
- Final feature count agrees with the lowest training CV RMSE
- Actual NotebookLM summary contains at least 100 Chinese characters
- NotebookLM result records verified output and successfully imported sources
- NotebookLM original prompts and responses preserved
- Complete NotebookLM summary appears in the report body
- Current report and README have no obsolete NotebookLM pending status
- Screenshot appendix records a real ChatGPT web conversation
- All captured ChatGPT browser images are present
- Screenshot PDF contains one image page per captured browser image
- All screenshot pixels are preserved unchanged in the PDF appendix

## 分析時需要留意的地方
- 資料為合成資料，本次主要比較相似分布下的預測結果。
- 交叉驗證用來選擇模型設定，最後再以保留測試資料計算誤差。
- Conformal 預測區間需要校準與新資料可交換的前提。
- 係數表示條件關聯，不能直接當成因果效果。

## 報告排版
- PDF 已轉成圖片檢查文字、表格及圖表的位置。