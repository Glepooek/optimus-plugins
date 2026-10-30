## [1.1.2] - 2026-10-30

### Changed
- 插件目录重命名：`optimus-decision-plugin` → `optimus-decision`，本 skill 正文中的调用前缀与路径引用同步更新

## [1.1.1] - 2026-08-30

### Added
- 新增 `known-issues.md` 使用期反馈记录机制（空模板），配套仓库新增的 skill 持续优化硬性约定，见 `knowledge-base/skill-authoring/rules/06-continuous-improvement.md`

## [1.1.0] - 2026-08-30

### Added
- 补充 `metadata.category: decision`，标注该 skill 属于"决策支持类"（仅给出选型结论/依据，不产出代码或文件），新增 `decision` 枚举值见 `.claude/rules/skill-conventions.md`

## [1.0.0] - 2026-08-29

### Added
- 初版发布：基于《Hello 算法》第 4-9 章蒸馏的数据结构选型决策 skill，覆盖数组/链表/栈队列/哈希表/树/堆/图的工程取舍框架
