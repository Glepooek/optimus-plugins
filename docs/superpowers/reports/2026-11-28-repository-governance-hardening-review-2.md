# 第二轮审查报告：仓库治理加固 spec 与实现计划（修订版）

**日期：** 2026-11-28
**审查对象：**
- spec：`docs/superpowers/specs/2026-11-28-repository-governance-hardening-design.md`（状态：已按 review 修订，待实施）
- plan：`docs/superpowers/plans/2026-11-28-repository-governance-hardening.md`

**前一轮报告：** `docs/superpowers/reports/2026-11-28-repository-governance-hardening-review.md`

## 结论

**第一轮提出的 16 项意见全部被采纳，改法也都对。** 修订版收窄了范围（砍掉了能力矩阵和 marker），原先靠推测下结论的地方都改成了实验驱动，质量比第一版明显好。

但这一轮核对 eval case 时发现一个**新的阻断问题**：target 实验选用的 case 没有任何 grader，按现在的设计拿不到 spec 要求的证据。此外还有 2 个中等问题、3 个小问题。

## 一、第一轮意见的落实情况

| 第一轮意见 | 修订版落实位置 | 状态 |
|---|---|---|
| 删除「八项过期」这个错误前提 | spec §1 明确为「8 个逻辑检查 / 6 个脚本」 | ✅ |
| 「13 条目」改写为注明日期的历史测量 | spec §1；plan Task 6 Step 2 | ✅ |
| 引用 B2，并由用户显式裁决 | spec §7.3；plan Task 2 Step 6–7 | ✅ |
| 补上「10 个自建插件」和 jenkins 注释两处遗漏 | plan Task 6，扫描正则也已同步补上 | ✅ |
| 砍掉能力矩阵、marker、`precommit_checks` | spec §3 非目标 | ✅ |
| runner 通过 `__file__` 定位仓库根 | spec §5.2，并有单测覆盖 | ✅ |
| CI 继续执行 `sh .githooks/pre-commit` | spec §5.4 | ✅ |
| pre-commit 的说明注释迁到对应 Gate 旁 | plan Task 4 Step 3，逐项列出需保留的理由 | ✅ |
| 去掉 `.ps1` 包装 | spec §3 | ✅ |
| 「不少于一个」措辞、action 版本 | plan Task 6 Step 2；Task 7 Step 5 | ✅ |
| target A/B 实验 | spec §7.2；plan Task 1；付费审批按阶段分开 | ✅ |

## 二、新发现的问题

### 🔴 阻断：实验所选 case 没有 grader，无法证明 skill 被调用

逐个核对了 12 个 case 的 `graders/` 目录：

| case | grader |
|---|---|
| `optimus-devops/skills/commit-message-review/evals/01-invalid-message` | **0 个** |
| `optimus-frontend/skills/avalonia-wpf-migration/evals/01-basic` | **0 个** |
| 其余 10 个 | 各 1 个，均为 `type: llm` |

全仓**没有任何一个 `tool_used: Skill` 类型的 grader**。这会带来三个后果：

1. **spec §7.2 的 target 实验恰好选了一个没有 grader 的 case**，比较证据中的「grader 判定」「case 分数」都会是空的。至于「skill invocation / tool trace」，`claude plugin eval --help` 对 `--json` 的描述只有「prompts, graders, per-run scores」，并没有说包含工具调用轨迹。照现在的设计，A、B 两组跑完很可能都拿不到证据，直接触发决策规则第三条「两者都不能证明 → 停止」，这笔实验费用就白花了。
2. **plan Task 8 的正式 baseline 有 2 个 skill 做不了**：没有 grader 的 case，分数没有意义。要补 grader 就得改 `plugins/*`，这和 spec §3「不修改 `plugins/*`」冲突，属于范围升级，需要重新判断插件版本、skill 版本，以及是否触发 darwin-skill 门禁。
3. plan Task 7 Step 4 要求先登记「六个 baseline 条目」，其中 2 个从一开始就不可能晋级为 `enforced`。

**修订建议：**

- **实验用临时副本做，不动仓库**：把 `plugins/optimus-devops` 复制到仓库外的临时目录，在副本的 case 里加一个 `tool_used: Skill` grader（免费、结果确定），A、B 两组都对这个副本运行。这样「skill 有没有被调用」直接由 grader 判定，不依赖 JSON 里有没有轨迹。另外可以加上 `--verbose --debug-file <path>`，把轨迹留作辅助证据。
- spec §9.2、plan Task 7/8 需写明：这 2 个没有 grader 的 skill 暂不进 policy，或单列为后续工作——「需先补 grader，并走插件 Patch + skill 版本升级」——不在本次范围内。

### 🟡 中等问题

1. **`apply_patch` 是 Codex 专有的工具**（plan Global Constraints、Task 1 Step 7、Task 2 Step 7）。Claude Code 里没有这个工具。本仓同时支持两个 harness，写死它会让 Claude 侧无法照 plan 执行。建议改成「使用当前 harness 的文件编辑工具」。
2. **任务依赖和「免费部分可单独交付」互相矛盾**。spec §9 末尾允许在付费实验未获批准时只交付免费部分，但 plan 写的是「Task 9 依赖 Tasks 3–7」，而 Task 7 又依赖付费的 Task 1–2。结果是 Task 9 会被卡住。应改为「Task 9 依赖 3–6；Task 7 仅在实验完成后执行」，并在 Task 9 Step 6 的 PR 描述里分开写明各部分的完成情况。

### 🟢 小问题

1. **实验 C 基本可以省掉**。D 会跑 3 次，已经能得出实际 run 数、单 run 成本和分数分布；C 只是再确认一次 `--runs 1` 会覆盖 case 自己的配置，而 `--help` 已经写明「Override per-case runs」。另外，如果 C、D 共用一个预算上限，这个上限要按 D 跑 3 次来定，否则 D 会被截断成部分结果。报告里还应注明：1 个 case 跑 3 次只能看出大致的波动，不足以下统计结论。
2. **实验报告的存放位置不符合 AGENTS 的定义**。AGENTS.md 第 78 行规定 `superpowers/reports/` 只放 `*-review.md` 审查报告，而 plan 要在这里写 `-experiment.md`。
   **✅ 用户已裁决（2026-11-28）：不保存实验报告。** 因此 AGENTS 的定义不改。但实验结论仍需要一个能追溯的落点，否则 policy 里 `evalDir`、`runs` 的取值就说不清依据。建议把实验结论写进以下已有的两个地方：
   - **target 结论**（选了 A 还是 B，证据是什么）：写进 Task 7 新建的 `docs/skill-eval-baselines.md`，专设一节「target 形态依据」；
   - **runs 结论**（实际 run 数、成本、分数分布）：在关闭 B2 时直接写进 `docs/todo-list/2026-09-12-todo.md` 的 B2 条目。按 AGENTS 的约定，「裁决的完整经过只记在那里」，本来就该写在这里。

   需要同步修改的位置：spec §7.1（删掉 `…-experiment.md` 这一落点）、spec §9.2 和 plan Task 2 Step 7（关闭 B2 时不再引用实验报告路径）、plan Task 1 Step 7 和 Task 2 Step 5（改为把结论记在临时目录，最终写进上述两处）、plan Task 9 Step 5（不再检查实验报告）。
3. spec §1 第 1 点「目录数量和实际列表已经发生漂移」不准确：目录列表本身是对的（8 个），漂移的只是注释里写的数字。

## 三、需要用户裁决

**2 个没有 grader 的 skill（`commit-message-review`、`avalonia-wpf-migration`）怎么处理？**

- **(a) 推荐**：本次 policy 不纳入这 2 个 skill，另开一项任务给它们补 grader。补 grader 要改 `plugins/*`，会触发插件 Patch、skill `metadata.version` 升级和 darwin-skill 门禁。
- **(b)** 扩大本次范围，把补 grader 一起做掉，并相应修改 spec §3、§9 中的版本影响声明。

target 实验改用「临时副本 + 免费 grader」这一条不涉及取舍，建议直接写进 plan。

## 四、修订建议汇总

| 改哪份 | 修订项 |
|---|---|
| spec §1 | 第 1 点改为「注释中的目录数量与实际列表不符」 |
| spec §7.2 | 实验对象改为仓库外临时副本，副本中加一个 `tool_used: Skill` grader；比较证据以该 grader 的判定为主，`--debug-file` 轨迹为辅 |
| spec §7.3 | 考虑删掉 C，或说明保留它的理由；预算上限按 D 的 3 次运行来定；注明样本量有限 |
| spec §9.2 | 写明 2 个没有 grader 的 skill 如何处理（按第三节的裁决） |
| plan Global Constraints | 去掉对 `apply_patch` 的硬性要求，改为「当前 harness 的文件编辑工具」 |
| plan Task 1 | 新增「复制插件到临时目录并添加 `tool_used: Skill` grader」步骤；A/B 命令的 target 指向副本 |
| plan Task 7 Step 4 / Task 8 | 按第三节的裁决调整 baseline 条目范围 |
| plan Task Dependencies | 改为「Task 9 依赖 3–6；Task 7 视实验情况执行」 |
| spec §7.1 / §9.2，plan Task 1–2、9 | 按用户裁决不保存实验报告：target 结论写进 `docs/skill-eval-baselines.md`，runs 结论写进 B2 条目；删掉所有对 `…-experiment.md` 的引用 |
