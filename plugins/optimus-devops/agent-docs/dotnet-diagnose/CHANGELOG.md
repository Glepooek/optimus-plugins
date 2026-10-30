## [1.1.1] - 2026-10-30

### Changed
- 插件目录重命名：`optimus-devops-plugin` → `optimus-devops`，本 skill 正文中的调用前缀与路径引用同步更新（agent 正文中的插件名引用同步更新）

## [1.1.0] - 2026-10-27

### Changed

- 判据出处从知识库改为同插件 `dotnet-diagnose-triage` skill 的 `references/`：`.NET 高级调试` 领域 15 篇判据文件随插件分发，安装后 agent 仍能读到完整判据
- `agents/dotnet-diagnose.md` 第 35 行的「判据的唯一出处」与 `agent-docs/dotnet-diagnose/README.md` 的依赖图同步更新

### 迁移理由

插件 marketplace 安装只复制 `plugins/<name>/` 整目录，知识库不在包内。判据留在 `knowledge-base/dotnet-debugging/` 会让安装后的 agent 读不到判据，退化为泛型经验推断——报告看起来正常，但判据一条没用上。

---

## [1.0.0] - 2026-09-06

### Added
- 新建 agent：本仓首个 agent 形态产物，编排 .NET 取证输出的根因定位流程
- 三步主干：证据清点 → 定征象与初始化台账 → 裁剪台账与自检出结论
- 承载层加载时机：Step 1 之后加载 `optimus-devops-plugin:dotnet-diagnose-triage`，判据不写在 agent 内
- 输出格式固定四段：结论与出处、修复方向 anchor、台账交接块、免责声明
- 边界四条：无证据不入循环、不执行取证、不硬套征象、知识库无判据时标「超出覆盖」
