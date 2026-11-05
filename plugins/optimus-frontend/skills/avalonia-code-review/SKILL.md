---
name: avalonia-code-review
description: Use when reviewing Avalonia AXAML or C# UI code for framework correctness, binding and styling defects, cross-platform risks, accessibility, performance concerns, or before merging an Avalonia UI change. 触发词："审查 Avalonia 代码"、"Avalonia review"、"AXAML 检查"、"Avalonia PR 审查"。
license: MIT
compatibility: 需要 optimus-frontend 内置的无需认证的 Avalonia Docs MCP；支持审查用户粘贴的代码或本地 Avalonia 项目中的已限定文件范围。
metadata:
  version: "1.2.0"
  author: desktop client team
  category: quality
allowed-tools: Read Glob Grep avalonia-docs
---

# Avalonia 代码审查

以 Avalonia Docs MCP 的当前官方文档和 API 为唯一框架判据，审查用户指定范围内的 AXAML、C# UI 代码和项目配置。此 skill 不复制静态框架规则，也不把 WPF/UWP/WinUI 的习惯当作 Avalonia 结论。

## 需求预告

先对照用户已提供的信息，一次性列出缺失项：审查范围（文件、目录、代码片段或本次改动）、审查深度（快速或完整）、目标 Avalonia/.NET 版本、以及可用的构建或错误输出。用户只给出代码片段时，按可见代码审查并注明上下文限制；信息齐全时直接开始。

## Step 1：锁定范围与审查深度

按以下优先级收敛，除非用户明确要求，不得扩大范围：指定文件/片段 → 指定功能模块 → 本次 `git diff` 涉及的 Avalonia 文件 → 单一最相关文件。扫描前先确定目录边界；相关文件超过 20 个时请求用户缩小范围。

审查深度：用户说“完整”“全面”“逐项”时为完整审查；未指定时默认快速初审，并在报告摘要中写“快速初审（默认）”。

### 🔴 CHECKPOINT：全项目审查

只有用户明确同意后，才能扫描整个项目或执行无边界的 `**/*.axaml`、`**/*.cs` 搜索。默认不越过已确认范围。

- **快速初审**：AXAML 命名空间与资源、样式/主题、绑定与数据模板、UI 线程、明显跨平台或可访问性问题。
- **完整审查**：在快速初审基础上，逐项覆盖属性系统与自定义控件、MVVM、事件/输入、布局与性能、资源/资产、AOT/裁剪与部署风险。

## Step 2：用官方 MCP 核验判据

1. 对每次 Avalonia 审查会话调用 `get_avalonia_expert_rules`。
2. 读取范围内的 `.axaml`、相关 C#、`.csproj` 和用户提供的错误输出；不要检查范围外文件来补猜上下文。
3. 每个疑点至少调用一次官方资料。Avalonia 的确切类型/成员，第一次查询必须是 `lookup_avalonia_api`；该工具覆盖不全，对常见控件类型也可能返回无结果，无结果时改用 `search_avalonia_docs`（概念和示例）或 `lookup_wpf_to_avalonia_mapping`。WPF 独有的类型或成员（`System.Windows`、`DependencyProperty`、`Style.Triggers`、`Visibility`、`Dispatcher.Invoke` 等）不在 Avalonia API 中，直接调用 `lookup_wpf_to_avalonia_mapping`，每次只查一个主题。
4. 在完整审查中，按当前范围核对以下主题：

| 主题 | 核验重点 |
|---|---|
| AXAML、资源与资产 | `.axaml`、Avalonia 命名空间、`using:`、`avares://`、资源生成方式 |
| 样式、主题与模板 | selector、style class、pseudo-class、`ControlTheme`、模板绑定方向 |
| 绑定与模板 | `x:DataType`、编译绑定、DataTemplate、null/fallback、绑定模式 |
| 属性、控件与 MVVM | `StyledProperty`/`DirectProperty`、控件基类、命令、ViewModel 边界 |
| 线程、事件与输入 | `Dispatcher.UIThread`、指针/键盘路由事件、异步 UI 更新 |
| 布局、性能与跨平台 | 响应式布局、虚拟化、平台 API 隔离、AOT/裁剪风险 |
| 可访问性 | 键盘可达性、语义/自动化信息、缩放与主题可读性 |

## Step 3：判定、修复与严重度

每个问题必须同时包含：位置、可观察风险、已查询的官方依据、严重度、最小修正和验证状态。

- **🔴 严重**：已确认会导致构建失败、运行时异常、数据/交互故障、跨平台崩溃或阻断可访问性的缺陷。WPF 独有的类型、成员或命名空间在 Avalonia 中不存在（如 `System.Windows`、`DependencyProperty`、`Visibility`、`Style.Triggers`），一律按构建失败判 🔴，不得降级。
- **🟡 重要**：已确认违反 Avalonia 模型，或存在明确的性能、可维护性、跨平台或可访问性风险，但需要特定输入/配置才会失效。
- **🟢 建议**：不改变正确性、仅提升可读性、一致性或未来维护性的优化。
- 无法从可见代码和 MCP 资料确认的事项，列入“待确认项”，不得作为缺陷计数。
- **例外：XAML 语法层面的结构错误**可由语法直接判定，不依赖 Avalonia 版本或 API，不因 MCP 无结果而降入待确认项。仅限三类：属性元素（`<UserControl.Styles>` 这类 `<类型.属性>`）不是其所属类型元素的直接子级；同一元素的内容被重复赋值（如 `Border` 已有 `Child` 又出现第二个子元素）；标签未闭合或嵌套错位。判为 🔴 构建失败，“官方依据”栏写“XAML 语法”，验证写“未构建”。先调用一次 `search_avalonia_docs` 查该类型的属性元素写法，有结果则一并引用；无结果也照此判定。

仅当同时满足以下两条时才提供最小修正片段：已看到问题元素或成员的完整定义；已知 Avalonia 主版本，或在片段旁明确写出版本假设。缺哪一条就在“修正后代码”中写明缺哪一条。任何情况下都不生成声称可直接替换整个文件的代码。审查默认只读；用户明确要求修复时，先确认拟修改的文件和范围，并在修改后重新审查该范围。

## 发现核验与复审收敛

报告里的每一条都要经得起追问，同一范围反复审查时要能收敛：

1. **出报告前逐条核验**：每个候选问题回到源码确认——位置真实存在；风险能由可见代码和已查询的官方依据解释；不是纯风格或顺手清理。任一不满足 → 丢弃，或降入“待确认项”，不计入缺陷数。
2. **审 diff 时标注归属**：问题所在行不是本次改动引入的，标“既有”并单列，不算作者本次必须修复。
3. **同根因合并**：同一根因在多处出现，只列一项并写全所有位置，让作者一次修完。
4. **复审收敛**：同一范围的第 2 轮起，只审上轮修改涉及的 diff，不重复已报告的发现。第 3 轮仍有新的 🔴/🟡 时，不再逐条追加，改为提示作者退一步重新考虑整体方案，并指出反复出现的问题类别。
   - **轮次与上轮报告的来源**：只认用户明确告知的轮次，或当前对话里已有的上轮报告。两者都没有时，按首轮审查，并在“审查摘要”的“未验证项”注明“未获上轮报告，按首轮审查，可能与此前发现重复”；不得凭猜测假定已是第 2 轮而缩小审查范围。

## 报告格式

```markdown
# Avalonia 代码审查报告

## 审查摘要
- 审查范围：[文件 / 代码片段 / diff]
- 审查深度：[快速初审 / 完整审查]
- 已核验的官方依据：[MCP 查询主题或 API]
- 未验证项：[构建、平台、配置或缺失上下文]
- 发现问题：[总数] 个；🔴 [X] / 🟡 [Y] / 🟢 [Z]

## 问题清单
### 🔴 严重问题
- `[文件:行]` [风险]；官方依据：[资料]；修正：[最小改动]；验证：[已验证/未验证]

### 🟡 重要问题
...

### 🟢 建议
...

## 待确认项
- [依赖的项目配置、运行平台或不可见代码]

## 修正后代码
[仅提供有充分上下文的最小片段；否则说明为什么不能安全生成]
```

## 失败处理

| 触发条件 | 一线处理 | 仍失败兜底 |
|---|---|---|
| Avalonia Docs MCP 不可用 | 报告 MCP 不可用并检查 `optimus-frontend` 内置的 MCP 是否已启用 | 停止框架合规判定，不以记忆替代官方依据 |
| `lookup_avalonia_api` 或 `search_avalonia_docs` 对某疑点返回无结果 | 换另一个工具或关键词重试一次（如 API 名查不到就改用概念搜索） | 该疑点写入“待确认项”并注明“MCP 无结果”，不计入缺陷数，不以记忆补写官方依据 |
| 代码不属于 Avalonia 或缺少必要上下文 | 明确说明可见范围和不适用部分 | 只给通用说明或请求最小可复现代码，不编造问题 |
| 官方资料与目标包版本不匹配 | 从 `.csproj` 确认版本并重新查询 | 标为待确认项，不给确定性修复指令 |
| 构建/多平台行为无法运行 | 审查静态代码并列出未验证项 | 不将静态审查描述为已通过构建或平台验收 |

## 不要做什么

- 不扫描范围外文件、编造问题，或为了让报告“有产出”而把正确实现标为缺陷。
- 不把 WPF `Style.Triggers`、`DependencyProperty`、`pack://`、`Visibility` 或 `Dispatcher` 语义直接套到 Avalonia。
- 不在没有 MCP 官方依据时给出确定性的 Avalonia API、版本或兼容性结论；Step 3 列出的三类 XAML 语法错误除外，其余一律不得借“语法”之名绕过此条。
- 不把配置依赖的推断、未运行的构建或未测试的平台行为标记为已验证。
- 不把 WPF 独有 API 降级为 🟡/🟢。按根因计数：同一语法块只列一项（如 `Style.Triggers` 与其内的 `Trigger`/`IsMouseOver`，或 `DependencyProperty` 声明与其 `Register`/`PropertyMetadata`）；根因不同的 WPF API（如 `Visibility` 与 `DependencyProperty`）分别列项。
- 不为让报告“显得完整”而添加 🟢 建议；没有可查证的依据就不列。
- 不把为修正示例假设的类型名、命名空间（如 `SearchViewModel`）当作项目事实；必须在示例旁标注“占位，需替换”。
- 不为代码片段编造文件行号；只引用片段自身的行序，或写“片段第 N 行”。
- 不在用户未确认拟修改的文件和范围前改动任何文件，也不声称已运行构建。
- 不让摘要中的问题总数和 🔴/🟡/🟢 计数与正文条目数不一致；写完报告后逐级数一遍，以正文实际条目为准更正摘要。
