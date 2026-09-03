# Workflow — Tender Comparison 標書比較（白話 SOP）

> 呢份係「一個識睇標書嘅人」平時點做嘅步驟，寫俾 AI agent 跟。唔係 code。
> The practitioner writes this. The agent follows it. The tools do the arithmetic.

## 觸發 Trigger
收到同一份工程 / 同一項採購的兩份或以上報價 / 標書，需要決定邊份先傾落去。

## 輸入 Inputs
- 每份標書 PDF（放喺一個 folder）
- 一份範圍基準表 `config/scope_benchmarks.json`：呢單嘢一定要包嘅項目，同每項嘅參考價（通常用最完整嗰份標書）

## 步驟 Steps

1. **逐份讀，包括附註細字。** 唔好只睇總價頁。每份抽：公司、總價、分項、工期、付款條款、訂金、保修、有效期、所有「不包括 / 另行報價 / 實報實銷 / 暫定數」。
   → 工具：`extract_tenders.py`

2. **砌返同一比較基準。** 某份標書冇包某個必要項目，就用基準價補返落去，並且寫明「估算 · 基準來自邊度」。
   → 工具：`compare_tenders.py`

3. **標出風險條款。** 高訂金、短保修、短有效期、物價調整條款、暫定數、有條件工期 —— 逐項列，唔好只寫「有風險」。
   → 工具：`compare_tenders.py`

4. **寫一段唔多於 150 字嘅建議。** 邊份性價比最高、邊份風險最大（引返標書同附註號碼）、決定前要向投標者澄清嘅兩三點。
   → Agent 寫（人審）

5. **停。** 交俾決定人。唔會自動聯絡任何投標者。

## 人手把關 Human gate
- 決定人確認補回估算合唔合理
- 有需要就向投標者發澄清（人發，唔係 agent 發）
- 中標決定同簽名：人

## 輸出 Outputs
`outputs/tenders_extracted.json` · `outputs/tender_comparison.md` · `outputs/tender_recommendation.md`（全部 DRAFT）

## 常見錯誤 Common mistakes this SOP prevents
- 見到「最平」就簽 —— 補返唔包嘅嘢之後可能一樣價，仲多咗風險
- 冇睇附註第 8 條嘅物價調整條款
- 用 AI「估」市價 —— 本 SOP 只准用列明來源嘅基準價
