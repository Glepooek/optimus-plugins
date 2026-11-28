## [1.0.0] - 2026-11-28

### Fixed
- 脚本与缓存路径不再硬编码 `.claude/skills/`：脚本经 `<skill-dir>` 定位，缓存由 `scripts/optimus_dirs.py` 解析到用户缓存目录
- 飞书 token 缓存与默认输出不再写入已安装插件目录
- 首次建立 `metadata.version` 基线
