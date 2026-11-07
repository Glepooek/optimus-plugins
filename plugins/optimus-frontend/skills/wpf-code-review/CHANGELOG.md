# Changelog

## [2.4.0] - 2026-11-07

### Added
- 第 11 章「单元层 · Converter」：纯函数测法（不建窗口、不依赖 `Application`）、`null` / 类型不符 / `parameter` / `culture` 四类输入、`ConvertBack` 往返与 `Binding.DoNothing`、`IMultiValueConverter` 的 `values` 长度校验、无状态验证、`Freezable` 跨线程陷阱
- 第 11 章「组件层 · 线程模型」：`[Fact]` / `[StaFact]` / `[WpfFact]` / `[UIFact]` 对照表，`[WpfFact]` 的语义（STA + `DispatcherSynchronizationContext`，**不创建 `Application`**、测试结束关闭该线程 `Dispatcher`）、`await` 场景为何不能用 `[StaFact]`、集合级 fixture 共享 UI 线程、xUnit v2/v3 与包版本匹配提示
- 第 11 章「组件层 · View 与控件」：绑定错误零容忍（`PresentationTraceSources` 监听 + `Measure`/`Arrange`/`UpdateLayout`）、`Border` 作根免 `Show()`、DP 与模板 `PART_*` 契约、视觉状态组位于模板根、截图回归的固定渲染参数
- 第 11 章「测试项目结构」补分层命名约定：同一被测单元同时有单元与集成测试时，项目名加层限定（`<被测>.Tests` / `<被测>.IntegrationTests` / `App.Component.Tests` / `App.E2E.Tests`）；同一类型两侧都测时集成侧加 `Integration` 后缀，避免 CI 报告与堆栈无法区分
- 第 11 章「反模式速查」表（7 条误测模式及替代做法）

### Changed
- 第 11 章由 10 节扁平列表重组为分层结构：**分层模型**（边界表 + 项目结构）→ **单元层**（ViewModel / Converter / 调度器替身）→ **组件层**（线程模型 / View / 控件 / XAML 资源 / 视觉回归）→ **集成层** → **UI 自动化层** → **跨层规范**（数据确定性 / 覆盖率 / 执行）→ **反模式**；每层补一句「不变量」
- 原「测试 UI 线程」并入 3.1，「测试结构」并入 1.2，「XAML / 资源验证」「集成测试」「覆盖率」「测试执行」分别归位到组件层、集成层、跨层规范；章节编号与正文交叉引用同步更新
- 覆盖率补「排除生成代码」；UI 自动化补交互式桌面会话、显式等待、失败截图三条；测试执行补单元测试秒级与 `[Trait]` 过滤

### Fixed
- 旧稿中的 `[StaThread]`（不存在的特性名）改为 `[WpfFact]` / `[StaFact]`

## [2.3.0] - 2026-11-05

### Added
- 新增「发现核验与复审收敛」章节（吸收 Claude Code 团队代码评审实践，claude.dev 博客 *How the Claude Code team does code review*）：出报告前逐条核验（位置真实、风险可由可见代码解释、非纯风格）；审 diff 时区分「既有」问题；同根因多处合并为一项；同一范围第 2 轮起只审新 diff、不重复已报发现，第 3 轮仍有新发现时提示作者重新考虑整体方案；轮次与上轮报告只认用户告知或对话内已有，缺失时按首轮审查并在摘要注明

## [2.2.2] - 2026-10-30

### Changed
- 插件目录重命名：`optimus-frontend-plugin` → `optimus-frontend`，本 skill 正文中的调用前缀与路径引用同步更新

## [2.0.5] - 2026-08-29

### Fixed
- 权威参考的两处 Markdown 链接目标随知识库领域元数据文件改名同步：`knowledge-base/wpf/00-README.md` → `README.md`。不改会成为坏链

## [2.0.4] - 2026-08-28

### Fixed
- 审查清单 12 个类别的 `§ 章节号` 引用全部补上标题文本（如 `§2、§3` → `§2. ViewModel 基类与可绑定属性、§3. 命令`）。裸章节号在规范文件重编号后会静默指向别的内容且无法被自动校验，补标题后可由 `knowledge-base-maintain` 的 `check_refs.py` 交叉校验
- 修正 #5「资源、样式与主题」的引用范围：`rules/07-resources-themes.md` §2-§5 少覆盖了一章——核对要点里的「资源可共享性」实为 §6，范围补齐为 §2-§6

## [2.0.3] - 2026-08-27

### Fixed
- 审查清单的 knowledge-base 引用路径同步知识库目录调整：`NN-*.md` → `rules/NN-*.md`（知识库 2.0.0 将各领域规范文件迁入 `<domain>/rules/`，旧路径已失效）

## [2.0.2] - 2026-08-22

### Changed
- 审查清单 #1「项目结构与 MVVM」核对要点补显「View 访问 ViewModel 的时机」：构造函数内 `DataContext` 未就绪时访问 VM 数据会空引用（补实测漏检的生命周期/时序 bug）
- 范围护栏"先定边界再扫描"升级为 🔴 CHECKPOINT：确需全仓扫描时须用户明确同意，默认不擅自扩大到全仓（检查点显性视觉标记）

## [2.0.1] - 2026-08-22

### Added
- 审查流程新增「确定审查范围」步骤与「范围护栏」章节：范围按优先级从窄到宽收敛（明确指定 → 模块定位 → git diff 改动 → 单点兜底），禁止无边界全仓 `Glob "**/*.xaml"`，报告需注明实际覆盖范围

## [2.0.0] - 2026-08-22

### Changed
- skill 从「WPF XAML 性能优化」重命名为「wpf 代码全量审查」`wpf-code-review`（原名 `wpf-xaml-performance`），目录同步重命名
- 内容从性能专项扩展为覆盖 `knowledge-base/wpf/` 全量规范：新增 12 类审查清单（逐类引用知识库锚点）、两档审查（完整/快速初审）、报告格式模板、反例黑名单，格式对齐 csharp-code-review
- 原 10 个性能检查点（grep 模式 + 修复代码 + 性能指标）保留为「性能专项诊断速查」内嵌章节，维持知识库 10 章"原则层 + skill 操作层"分层
- 审查模式：支持扫描本地代码库（Grep/Glob）与粘贴代码审查

### Removed
- 移除原描述前缀 `optimus-frontend-`（frontmatter name 与目录名统一为 `wpf-code-review`）

## [1.1.0] - 2026-07-09

### Added
- 新增「边界场景处理」章节：覆盖未发现问题、找不到目标文件、代码片段信息不全、反模式疑似业务权衡 4 类场景的显式处理分支
- 新增「应用修复前的确认」🔴 CHECKPOINT：区分局部修改（可直接应用）与架构级改动（需 🛑 STOP 用户确认）
- 新增「⛔ 不要做什么」反例黑名单：5 条反模式（滥用 OneTime、虚拟化误判、性能倍数过度承诺、误冻结动态 Freezable 对象、断言修复但未提示外部前提）

### Changed
- 步骤编号调整：原步骤 3「生成性能报告」顺延为步骤 4，为新增的「边界场景处理」腾出步骤 3

## [1.0.0] - 2026-05-08

### Added
- 初始版本：10 个检查点覆盖数据绑定、控件虚拟化、图形渲染、Freezable 冻结、启动时间、布局、资源、事件处理器内存泄漏、UI 线程阻塞等 WPF/XAML 性能问题
