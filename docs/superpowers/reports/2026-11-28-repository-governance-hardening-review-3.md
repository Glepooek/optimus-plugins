# 第三轮审查报告：仓库治理加固 spec 与实现计划（二次修订版）

**日期：** 2026-11-28
**审查对象：**
- spec：`docs/superpowers/specs/2026-11-28-repository-governance-hardening-design.md`（状态：已按两轮 review 修订，待实施）
- plan：`docs/superpowers/plans/2026-11-28-repository-governance-hardening.md`

**前序报告：**
- `docs/superpowers/reports/2026-11-28-repository-governance-hardening-review.md`
- `docs/superpowers/reports/2026-11-28-repository-governance-hardening-review-2.md`

## 结论

**第二轮的 1 个阻断、2 个中等、3 个小问题和 1 项用户裁决全部落实。** 免费部分（Tasks 0、3–6、9）已经可以开始实施，不用等下面这些问题解决。

付费 eval 部分还有 **1 个新的阻断问题**，加上 2 个中等问题、1 个小问题。三者都出在同一个地方：**spec 自己给出的「这个 case 能不能证明 skill 被调用」的判断标准，没有用到其他地方。**

> **✅ 用户裁决（2026-11-28）：所有涉及付费的内容一律删除，不再考虑。** spec §7–§8 和 plan 的原 Task 1、2、7、8 已整段删除。因此本报告第二节的 🔴 阻断问题与两个 🟡 中等问题、第三节的 A′ 裁决、第四节对 spec §7.2/§8.1 和 plan Task 1/2/7 的修订建议**全部不再适用**，仅作为当时审查结论保留。`skill-eval.yml` 只清理失效注释，B2 保持未决。

## 一、第二轮意见的落实情况

| 第二轮意见 | 修订版落实位置 | 状态 |
|---|---|---|
| 🔴 实验 case 没有 grader | spec §7.2、plan Task 1 Step 2–3：复制到仓库外临时副本，副本中加 `tool_used: Skill` grader | ✅ grader 写法与 git 历史中 jenkins-build 的 `triggered.md` 一致 |
| 🔴 2 个没有 grader 的 skill | spec §3、§8.1；plan Task 7 Step 4：不纳入 policy，写进「暂不纳入」节 | ✅ |
| 🟡 `apply_patch` 只有 Codex 有 | plan Global Constraints 改为「当前 harness 的文件编辑工具」 | ✅ |
| 🟡 任务依赖矛盾 | plan Task 9 Dependencies 与 Task Dependencies 末条 | ✅ |
| 🟢 实验 C 冗余 | spec §7.3 删掉 C；D 的预算按 3 次运行设为 5 美元；注明样本量有限 | ✅ |
| 🟢 spec §1 措辞 | 已改为「注释中的目录数量与实际列表不符」 | ✅ |
| 用户裁决：不保存实验报告 | target 结论写进 `docs/skill-eval-baselines.md`，runs 结论写进 B2；全文已无 experiment report 引用 | ✅ |

另外，policy 解析器新增了「任一 case 缺少 `graders/*.md` 就拒绝」的规则（spec §8.1，plan Task 7 Step 3）。这样「没有 grader 的 skill 不进 policy」从人工约定变成了代码强制，比第二轮建议的做法更好。

## 二、新发现的问题

### 🔴 阻断：policy 里 4 个 skill 有 2 个的 `allowed_tools` 不含 `Skill`

spec §7.2 判定 `commit-message-review` 不能直接拿来做实验，理由之一是它的 `allowed_tools` 不含 `Skill`；plan Task 1 Step 3 也为此在临时副本里补上了 `Skill`。也就是说，spec 默认了一个前提：**`allowed_tools` 是白名单，不在名单里的 `Skill` 工具不能调用。**

拿同一个标准去查 policy 要登记的 4 个 skill：

| skill | case 的 `allowed_tools` | 含 `Skill` |
|---|---|---|
| `dotnet-diagnose-autopilot` | `[Task, Write, Read]` | ❌ |
| `avalonia-code-review` | `[Read, Glob, Grep, avalonia-docs]` | ❌ |
| `avalonia-deb-release`（2 个 case） | `[Read, Glob, Grep, Skill]` | ✅ |
| `wpf-code-review`（6 个 case） | `[Read, Glob, Grep, Skill]` | ✅ |

如果这个前提成立，那么前 2 个 skill 的 baseline 测出来的是**模型在没有 skill 时的表现**，分数可能看起来正常，实际上并没有在评测这个 skill。结果要么是「行为闸」形同虚设，要么阈值被定在一个和 skill 无关的水平上。

如果这个前提不成立（`allowed_tools` 管不到 `Skill`），那临时副本里补 `Skill` 这一步就是多余的，但这一点也同样没有验证过。

**这是一个「共同未知」，可以用最小实验解决**：在 Task 1 增加第三组 A′，**只改一个变量**：

- A′：用同一个临时副本，加 `tool_used: Skill` grader，但 `allowed_tools` **保持** `[Read, Bash]` 不变，target 形态与 A 相同。
- **判据**：A′ 的 grader 通过 → `allowed_tools` 管不到 `Skill`，4 个目标都可以登记；A′ 不通过、A 通过 → 白名单前提成立，`dotnet-diagnose-autopilot` 和 `avalonia-code-review` 也要归入「暂不纳入」（补 `Skill` 需要改 `plugins/*`，按第二轮的同一规则另行处理）。
- **成本**：多一次 commit-message-review 运行，`--max-cost-usd 1`，Task 1 的合计 ceiling 从 2 美元变成 3 美元。
- **配套的代码规则**：policy 解析器在「每个 case 都有 grader」之外，可以按 A′ 的结论再加一条机械检查——「每个 case 的 `allowed_tools` 必须含 `Skill`（或未声明）」，让这个判断标准也由代码强制，而不是靠人记住。

### 🟡 中等问题

1. **`--verbose` 放错了层级，辅助证据可能根本采不到**（spec §7.2，plan Task 1 Step 5–6）。命令写的是 `claude --verbose --debug-file <log> plugin eval …`。核对 CLI 2.1.332 的帮助：
   - 顶层 `claude --verbose` 的说明是「Override the verbose setting」；
   - `claude plugin eval --verbose` 的说明才是「Log per-message trace events to the debug log (use --debug-file to read them)」；
   - `--debug-file` 是顶层选项。

   所以正确写法应是 `claude --debug-file <log> plugin eval … --verbose`。这个问题比看上去严重：plan Task 1 Step 7 规定「grader 未通过**或 debug 无法识别目标 skill** 时，不算有效装载证据」，debug log 已经是**必要证据**。如果 trace 没写进日志，A、B 两组都会被判为「不能证明」，落入「停止」这条规则，实验费用白花。顺带一提：plan Task 1 Step 1 的 Expected 写的是「支持全局 `--verbose`/`--debug-file`」，按这个检查会误判为通过，应改成核对 `plugin eval --verbose` 的说明。

2. **`avalonia-code-review` 依赖一个 eval 里不会启动的 MCP server**。它的 case 在 `allowed_tools` 里写了 `avalonia-docs`（`plugins/optimus-frontend/.mcp.json` 里的 server），但 `optimus-frontend` 下没有任何 `mocks/` 目录。`claude plugin eval` 默认 `--mocks record`，帮助原文是「a plugin server with no mock is NOT started」，policy workflow 也没有传 `--mocks` 或 `--allow-real-servers`。因此这个 case 的 baseline 是在**拿不到文档工具**的条件下测出来的，和真实使用场景不一样。另外 `avalonia-docs` 是不是一个能匹配上的工具名（MCP 工具一般是 `mcp__<server>__<tool>` 的形式）也没有核实过。建议：不论 A′ 结论如何，这个 skill 都在 `docs/skill-eval-baselines.md` 里注明「MCP 无 mock，baseline 为降级条件下的分数」，或者干脆归入暂不纳入；补 mock 属于 `plugins/*` 改动，另行处理。

### 🟢 小问题

1. **临时副本写文件时的编码**（plan Task 1 Step 3）。`Set-Content` 在 pwsh 7 下默认写无 BOM 的 UTF-8，没有问题；但 plan 的 Tech Stack 只写了「PowerShell」，如果有人在 Windows PowerShell 5.1 下执行，默认编码不是 UTF-8，grader 里的中文会变成乱码，frontmatter 也可能被 CLI 读错。建议显式指定 `-Encoding utf8`，或者在 Global Constraints 里写明「PowerShell 命令按 pwsh 7 编写」。

另有一处不算问题、但值得写明的前提：Task 2 的 D 实验把 Task 1 在 **optimus-devops** 上得出的 target 结论直接用到 **optimus-frontend** 上。frontend 带有 3 个 MCP server，两者的加载条件不完全相同。D 的结果如果出现装载异常，应先怀疑这个推广是否成立，不要直接读成 runs 的问题。

## 三、需要用户裁决

**是否批准在 Task 1 增加 A′ 组？** 合计 ceiling 从 2 美元升到 3 美元，换来的是「policy 里另外 2 个 skill 的 baseline 到底有没有在测 skill」的答案。不加 A′ 的话，稳妥做法是把 `dotnet-diagnose-autopilot` 和 `avalonia-code-review` 也先排除，policy 只剩 2 个目标。

## 四、修订建议汇总

| 改哪份 | 修订项 |
|---|---|
| spec §7.2 | 增加 A′ 组与判据；命令改为 `claude --debug-file <log> plugin eval … --verbose` |
| spec §8.1 | 按 A′ 结论增加「`allowed_tools` 必须含 `Skill` 或未声明」的解析规则；`avalonia-code-review` 注明 MCP 无 mock 的降级条件，或归入暂不纳入 |
| plan Task 1 | Step 1 的 Expected 改为核对 `plugin eval --verbose`；新增 A′ 步骤；Hard stop 合计 ceiling 改为 3 美元；Step 5–6 修正 `--verbose` 位置；Step 3 的 `Set-Content` 显式指定编码 |
| plan Task 2 | 注明 target 结论是从 devops 推广到 frontend 的，装载异常时先排查这一点 |
| plan Task 7 | Step 1/3 按 A′ 结论增加 `allowed_tools` 检查的测试与实现；Step 4 的登记清单按 A′ 结论确定 |
