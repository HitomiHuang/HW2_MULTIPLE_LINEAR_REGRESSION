# 修訂版驗證紀錄

範圍：新版網頁、共用 Python 引擎、兩個內建樣本、教師 50 Startups 範例，以及新版補充報告。

## 已完成

- 兩個內建題目分別有 20 / 18 個原始輸入特徵；皆在 14–39 範圍。
- CPython 實際執行兩題，產生示範結果與 output/web_validation.json。
- unittest 四個案例通過：獨立重算 RMSE / R² / 覆蓋率、分割不重疊；區分 OLS CI / PI 寬度；測試/校準標籤不影響訓練選模；50 筆含類別小樣本；缺失欄位與無效 Target。
- 瀏覽器實測：Problem 切換至 King County；Pyodide 實際重新訓練後 R² = 0.6785，與 CPython 四位小數一致。
- 瀏覽器實測：教師 CSV URL 直接載入，Target = Profit；實際重新訓練後 R² = 0.9267、RMSE = 7702.2053，切分 21 / 19 / 10。
- 瀏覽器實測：本機 50_Startups.csv 透過檔案選擇器上傳成功；Target 正確辨識為 Profit。
- 瀏覽器實測：95% OLS 平均反應 CI 可切換，標題顯示為平均反應，未誤稱為單筆 PI。
- CLI 50 Startups 重跑通過；含來源、設定與逐筆結果。
- JavaScript app.js / worker.js 語法檢查通過。
- 新版 7 頁報告已全部轉成 PNG 檢視，表格、圖表、字型與頁碼完整；對話文字 PDF 首頁檢視通過。
- 已驗證的 NotebookLM 原始摘要沿用於本版，明示研究日期與範圍。

## 重要解讀限制

- 小樣本校準至少 19 筆；50 Startups 測試僅 10 筆，100% 實測覆蓋不代表穩定表現。
- 房價有精確共線性，程式以 SVD 解並警示；zipcode 的數值表示屬基線簡化。
- Conformal 需要可交換性；房價可能有重複房產、空間與時間依賴，網站不宣稱跨區域或跨時期有效。
- 網址下載須允許 CORS；套件首次載入需網路。未測試所有任意資料格式。
- 原始洪水報告為 50,000 筆，網站為 4,000 筆，不混用兩者指標。

部署與公開網址的狀態另見 output/deployment.json；本檔不以預期 URL 代替實際部署成功。

## 發布與最後視覺確認

- Sites 公開版本 2 發布成功；實際 URL 與來源 commit 記錄於 output/deployment.json。
- 正式網站可直接開啟，洪水示範 R² = 0.8595、95% PI 圖與模型比較正常顯示；完成畫面存於 output/evidence/website_live.jpg。
- 修正 Plotly 共用 layout 物件造成的座標軸型態互相影響：各圖使用獨立深拷貝。房價殘差 / Q-Q 圖重新檢視，數值刻度恢復正確。
- 新版 ZIP 通過 CRC、全部 manifest SHA-256、主要必備檔案及最終圖表程式檢查。
