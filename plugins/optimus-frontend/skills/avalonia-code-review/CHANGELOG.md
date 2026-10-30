## [1.1.0] - 2026-10-30

### Added
- Step 1 增加审查深度默认值：用户未指定时按快速初审，并在报告摘要中写“快速初审（默认）”
- 严重度判据：WPF 独有的类型、成员或命名空间在 Avalonia 中不存在，一律判 🔴，不得降级
- 失败处理表新增“`lookup_avalonia_api` / `search_avalonia_docs` 返回无结果”分支：换工具或关键词重试一次，仍无则入待确认项，不计缺陷、不以记忆补依据
- “不要做什么”新增 6 条：不降级 WPF 独有 API 且按根因计数；不为显得完整添加无依据的 🟢；占位类型名须标注；不为片段编造行号；未经确认不改文件、不声称已构建；摘要计数须与正文条目数一致

### Changed
- Step 2 第 3 条由“按需调用”改为“至少调用一次”，列出触发 `lookup_wpf_to_avalonia_mapping` 的 WPF 痕迹，并写明 Avalonia 的确切类型/成员第一次查询必须是 `lookup_avalonia_api`（该工具覆盖不全，无结果时回退到 `search_avalonia_docs` / `lookup_wpf_to_avalonia_mapping`；WPF 独有类型不在其索引内，直接查映射表）
- 最小修正片段的提供条件由“信息足够时”改为两条可检验条件（已见完整定义；版本已知或写明版本假设）
- 缩小范围的触发阈值由“约 20 个”改为“超过 20 个”

## [1.0.4] - 2026-10-30

### Changed
- `compatibility` 与故障表中的 MCP 来源由 旧 MCP 插件 改为 `optimus-frontend` 内置（旧 MCP 插件 插件已删除，其 Avalonia Docs / MasterGo MCP 并入 `optimus-frontend`）；逻辑未改

## [1.0.3] - 2026-10-30

### Changed
- README 版本行与 SKILL.md 的 `metadata.version` 对齐（此前滞后于 SKILL.md）

## [1.0.2] - 2026-10-30

### Changed
- 本 skill 随 `optimus-avalonia` 并入 `optimus-frontend`，调用前缀改为 `/optimus-frontend:avalonia-code-review`；eval 的 `plugins` 字段同步为 `optimus-frontend`

## [1.0.1] - 2026-10-30

### Changed
- 插件目录重命名：`optimus-avalonia-plugin` → `optimus-avalonia`，本 skill 正文中的调用前缀与路径引用同步更新

## [1.0.0] - 2026-09-16

### Added
- 新增以 Avalonia Docs MCP 为唯一框架判据的 Avalonia 代码审查流程。
- 支持范围护栏、快速/完整审查、可追溯严重度报告、未验证项和最小修正建议。
- 新增 AXAML 命名空间、样式触发器与编译绑定场景的 eval case 及 LLM 判据。
