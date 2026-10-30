# Changelog

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
