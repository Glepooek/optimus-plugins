## [2.1.2] - 2026-10-30

### Changed
- README 版本行与 SKILL.md 的 `metadata.version` 对齐（此前滞后于 SKILL.md）

## [2.1.1] - 2026-10-30

### Changed
- 插件目录重命名：`optimus-avalonia-plugin` → `optimus-avalonia`，本 skill 正文中的调用前缀与路径引用同步更新

## [2.1.0] - 2026-09-16

### Added
- 新增 `avalonia-code-review` 路由：以 Avalonia Docs MCP 作为代码审查的官方判据，输出范围受限、可追溯的严重度报告。


## [2.0.0] - 2026-09-16

### Changed
- 从上游通用参考路由收敛为由 Avalonia Docs MCP 提供官方事实的企业开发入口。
- 将 WPF 迁移任务转交给 `avalonia-wpf-migration`，并加入范围、验证和 MCP 不可用时的护栏。

### Removed
- 移除对 31 个静态通用 Avalonia 参考 skill 的路由与社区包清单，避免与官方 MCP 和全局技能重复。


## [1.0.0] - 2026-09-15

### Added
- 从上游 linuxdevel/Avalonia-skills 原样引入（自建插件 optimus-avalonia-plugin，MIT License）
