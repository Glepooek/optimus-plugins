# Changelog

## [1.0.0] - 2026-11-28

### Changed
- 移除非规范字段 creator（作者信息已在 metadata.author）
- 首次建立 metadata.version 基线 1.0.0

### Fixed
- 移除 allowed-tools 中仅 Claude Code 可用的 AskUserQuestion，信息收集步骤改为不绑定具体工具的通用表述
