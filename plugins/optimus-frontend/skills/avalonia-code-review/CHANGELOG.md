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
