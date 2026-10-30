# Git 提交信息审查规则

本参考随 `commit-message-review` 一起分发，供已安装插件在没有仓库根知识库时使用。内容是本仓 Git 提交信息规范中与该 skill 的审查职责直接相关的规则摘要。

> 摘要来源：optimus-plugins 仓库 knowledge-base 的 Git 规范领域中「提交信息」一篇（02-commit-messages），同步于 2026-10-30。该摘要是手工维护的副本，源规范变更后不会自动同步；两者不一致时以源规范为准，并回头更新本文件。

## 必须修复

- 标题必须符合 Conventional Commits：`<type>[(<scope>)][!]: <description>`。
- `type` 必须准确表达变更性质，可用值为：`feat`、`fix`、`docs`、`style`、`refactor`、`perf`、`test`、`build`、`ci`、`chore`、`revert`。
- 提交信息必须说明变更的 What 与 Why；禁止使用 `update`、单独的 `fix`、堆叠的 `wip` 等无意义描述。
- 发生不兼容变更时，标题的 `!` 与 footer 的 `BREAKING CHANGE: <说明>` 都可作为 breaking-change 信号。迁移说明必须让受影响方能采取行动。
- AI 实质生成或协助生成本次提交内容时，末尾必须用每位实际模型一行的 `Co-Authored-By: <模型名> <noreply@供应商域名>` footer 标注。不得以工具品牌替代实际模型名，也不得臆造模型名或邮箱。

## 建议改进

- scope 可选。需要表达影响范围时，使用简短、稳定的模块或功能名称。
- 英文 description 使用小写祈使语气且结尾不加句号；中文 description 保持简洁并说明结果。
- 多行 message 中，标题、body 与 footer 各区之间用空行分隔。body 说明动机和影响，不逐行复述 diff。
- 每个 trailer 独占一行。常见 trailer 包括 `BREAKING CHANGE:`、`Refs: #123` 与 `Reviewed-by:`。
- 一个提交应只覆盖一个逻辑变更。是否原子需结合暂存 diff 判断，不能只从 message 文本断言。

## 审查边界

提交信息合规不等于提交本身已安全或通过验证。hook 不得用 `--no-verify` 绕过；敏感信息、大文件和完整提交内容仍需由仓库 hook、CI 或专用扫描工具独立检查。