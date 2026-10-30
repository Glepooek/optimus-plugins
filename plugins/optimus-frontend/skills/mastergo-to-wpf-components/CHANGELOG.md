## [1.0.3] - 2026-10-30

### Changed
- `compatibility` 中 mastergo-magic-mcp 的来源由 旧 MCP 插件 改为 `optimus-frontend` 插件内置（旧 MCP 插件 插件已删除，MCP 并入 `optimus-frontend`）；令牌环境变量仍为 `MASTERGO_TOKEN`；逻辑未改

# Changelog

## [1.0.2] - 2026-10-30

### Changed
- 插件目录重命名：`optimus-frontend-plugin` → `optimus-frontend`，本 skill 正文中的调用前缀与路径引用同步更新

## [1.0.1] - 2026-08-20

### Added
- 补充中英文触发词示例到 frontmatter description："抽组件"、"生成组件库"、"抽取可复用组件"、"设计稿转组件"、"WPF 组件库"、"沉淀样式"。

### Changed
- 修正 Step 5 CHECKPOINT 格式为独立段落，与 Step 2 保持一致。

## [1.0.0] - 2026-08-19

### Added
- 新增 MasterGo 设计稿组件抽取 Skill：组件索引、颜色资源、DataTemplate 资源与严格映射控件登记。
- 配套 README、references/component-extraction-rules.md、test-prompts.json 与离线契约测试。
