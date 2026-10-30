# Changelog

## [1.0.4] - 2026-10-30

### Changed
- 插件目录重命名：`optimus-devops-plugin` → `optimus-devops`，本 skill 正文中的调用前缀与路径引用同步更新

## [1.0.3] - 2026-10-30

### Changed
- 边界说明补充插件 `PreToolUse` 提交门禁：`git commit` 前强制先审查，标记与重新提交由调用方完成，skill 仍只读。

## [1.0.2] - 2026-10-30

### Changed
- `description` 增加「准备 git commit / 提交代码、提交前把关 message」触发场景，使提交流程中拟好 message 时能按描述匹配到本 skill；仍为只读审查，不执行提交。

## [1.0.1] - 2026-10-30

### Changed
- 输出模板与结论定义中的"知识库"措辞改为指向随 skill 分发的 `references/commit-message-rules.md`，避免安装后模型去寻找不存在的 `knowledge-base/`；README 同步。
- `references/commit-message-rules.md` 标注摘要来源与同步日期。
- `known-issues.md` 注明所引流程文档不随插件分发。

## [1.0.0] - 2026-10-29

### Added
- 新增 `commit-message-review`：按 Git 知识库审查 Conventional Commits 格式、变更意图、破坏性变更信号和 AI 协作者 footer。
- 支持审查用户粘贴的 message 或明确指定的 Git commit，并可按请求与暂存改动核对。
- 随 skill 分发提交信息规则参考，安装后无需依赖仓库根目录的知识库文件。
