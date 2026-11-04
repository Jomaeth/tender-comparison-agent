# AGENTS.md

Entry point for Codex and other coding agents. 供 Codex 及其他編程代理使用的入口。

This repository is one agent skill: supplier tenders (PDF) → like-for-like comparison → recommendation draft → PDF report.
本 repo 為單一代理技能：供應商標書（PDF）→ 同一基準比較 → 建議初稿 → PDF 報告。

Read these three files in order, then follow `SKILL.md` exactly. 請依次閱讀下列三個檔案，並嚴格遵循 `SKILL.md`。

1. `AGENT.md` — role, permissions, how the model is constrained / 角色、權限、模型約束方式
2. `PROJECT.md` — context, inputs, outputs, configuration, how to open in Codex / 背景、輸入、輸出、設定、於 Codex 開啟的方法
3. `SKILL.md` — ordered procedure; each step tagged `[DET]` `[LLM]` `[HUM]` `[CFG]` / 有序程序，每步標示控制類型

Short form of the hard limits / 硬性限制摘要:

- `input/` is read-only; write only under `outputs/`. / `input/` 唯讀；僅可於 `outputs/` 寫入。
- Every number comes from the tools or is cited to a tender and an item or note number. Estimates are labelled. / 每個數字均來自工具或引用標書及項目或附註編號；估算須註明。
- The award decision belongs to a person. Draft only; do not decide; do not contact bidders. / 授標決定屬人員；僅擬稿，不作決定，不聯絡投標者。
- Do not install packages or download anything. / 不得安裝套件或下載任何內容。
- Reply in the user's language (English / 繁體中文 / 廣東話). / 以使用者的語言回覆。
