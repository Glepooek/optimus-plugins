# 审查报告（复审）：Codex 兼容性加固 spec

**日期：** 2026-11-28
**审查对象：** `docs/superpowers/specs/2026-11-28-codex-compatibility-hardening-design.md`（按首轮报告修订后的版本）
**首轮报告：** `docs/superpowers/reports/2026-11-28-codex-compatibility-hardening-review.md`
**审查重点：** 可行性——修订后的方案能否按所述方式落地；首轮 6 条意见是否落实。
**实测环境：** Codex CLI 0.172.0，Windows，隔离 `CODEX_HOME`（未登录、未配置 API key），在 `git ls-files` 导出的仓库副本上临时修改 manifest，未改动工作区。

## 结论

**可以进入 writing-plans。** 首轮的 3 条必改项和 3 条判据项均已落实，修订后新增的关键前提全部实测成立。剩下的问题都在实现细节层，没有一处会推翻方案：

- 2 处需在 plan 中写成确定规则（M1 autopilot 终止条件、M2 例外标记的计量单位）；
- 3 处小的事实或口径偏差，可顺手修正。

### 首轮意见落实情况

| 首轮编号 | 意见 | 修订后 | 状态 |
|---|---|---|---|
| M1 | CI 判据判不出组件是否生效 | §7.1 第 5–7 步改为 `mcp list` + `prompt-input` 使用侧断言，明确缓存不作证据 | ✅ |
| M2 | agent 未生效 | §4.2 降级为 Claude-only，autopilot 在 Codex 下终止并指向 triage | ✅ |
| M3 | MasterGo token 无预案 | 选了「独立 Codex MCP 文件、只含两个 HTTP server」 | ✅ |
| A1 | 描述关键词判定脆弱 | §6.1 改为从组件反推 + 机器可读排除表，含陈旧项检测 | ✅ |
| A2 | portability gate 规则不可实现、覆盖面不足 | 阻断清单只含 `AskUserQuestion`；扫描范围扩到 `scripts/**` 与根目录脚本；定义了固定标记 | ✅（细节见 M2） |
| A3 | 按 OS 解析交给 LLM 不确定 | §3.3 改为只由 helper script 解析，SKILL.md 消费输出 | ✅ |

### 新前提的实测记录

| 验证项 | 操作 | 结果 |
|---|---|---|
| 独立 MCP 文件 | frontend Codex manifest 指向 `./.codex-mcp.json`（去掉 mastergo 的 `.mcp.json` 副本） | ✅ `codex mcp list --json` 恰好列出 `avalonia-docs`、`microsoft-learn` |
| 9 插件全量安装 | 按 `.agents/plugins/marketplace.json` 逐个 `codex plugin add` | ✅ 9/9 成功 |
| 54 skill 可见性 | 从 `plugins/*/skills/*/SKILL.md` 的 `name` 生成 `plugin:skill` 期望清单，与 `codex debug prompt-input "x"` 输出比对 | ✅ 54/54，缺失 0；含仍带 `creator`/`triggers` 等额外键的 11 个 skill |
| `multi_agent_v2` 下的 agent | `codex debug prompt-input "x" --enable multi_agent_v2` | ✅ 与 spec 一致：agent 正文命中 0 次 |
| 渲染体量 | 9 插件全装后 prompt-input 输出 | 约 108K 字符，skill 列表未被截断 |

## 需在 plan 中写成确定规则

### M1. autopilot「在 Codex 下终止」缺少可执行的判定条件

**问题。** SKILL.md 是两侧共用的单一真源，正文无法写「如果当前是 Codex」——模型没有可靠的 harness 自识别手段。§4.2 与 §13.3 要求 autopilot「在 Codex 下于前置校验阶段明确终止」，但没有说明终止条件是什么。

更具体的风险：Codex 有自己的 `spawn_agent` 工具（实测渲染提示中可见）。模型若把 `Task` 理解成 `spawn_agent` 的同义词，会派发一个**通用**子 agent 去「转发给 @optimus-devops:dotnet-diagnose」。这个通用 agent 拿不到 agent 定义，结果可能是它自己做一份分析并以「agent 原文」名义返回——正是 §4.2 禁止的「把单次 triage 包装成两次独立交叉验证」，而且没有任何报错。

**建议。** 终止条件写成**能力判定**而非 harness 判定，直接复用 autopilot 现有的前置校验第 1 项（`SKILL.md:37`「`dotnet-diagnose` agent 是否可用」）：

- 判定依据：`optimus-devops:dotnet-diagnose` 是否作为**具名 agent** 出现在当前可调用 agent 列表中；
- 明确写出「通用子 agent / `spawn_agent` 默认角色不满足本依赖」；
- 不满足时终止，并给出直接调用 `dotnet-diagnose-triage` 的入口（§4.2 已写）。

同时 `compatibility` 字段（`SKILL.md:8`）与 description 中「调度 dotnet-diagnose agent」的表述需同步注明 Claude-only，否则 Codex 侧仍会按 description 触发进来。

**验证。** 这一条只能人工验收（需要模型推理），§13.3 已覆盖，但验收用例要包含「Codex 下模型不得调用 `spawn_agent` 冒充」这一反例，而不只是「看到终止提示」。

### M2. 例外标记的计量单位不明确，部分命中位置放不下标记

**问题。** §6.2 要求合法命中「在命中行或紧邻前一行写固定标记」，且「一条标记覆盖多处命中均失败」。对照 `sync-skill-symlinks/SKILL.md` 的实际命中（7 行）：

| 行 | 位置 | 问题 |
|---|---|---|
| 3 | YAML frontmatter 的 `description` | 同一行同时命中 `~/.claude/skills/` 与 `~/.codex/skills/`——按「一条标记覆盖多处命中即失败」需要两条标记，但单行 YAML 值只能放一条前置 `#` 注释 |
| 29、215 | PowerShell 代码块 | 形式是 `$env:USERPROFILE\.claude\skills`，**不在** §6.2 列出的模式（`~/.claude/`、`$HOME/.claude/`、`%USERPROFILE%\.claude\`）内，会被漏判 |
| 61、261 | bash 代码块 | 同一行同时命中 `.claude` 与 `.codex` |
| 370 | Markdown 表格行 | 「紧邻前一行」放注释会把表格断开；只能同行放 `<!-- -->` |

**建议。**

1. 计量单位定为**行**：一条标记豁免本行全部命中，「覆盖多处」只指跨行。这样 7 行对应 7 条标记，可实现、可审查；
2. 标记的载体按上下文固定三种写法：YAML/bash/PowerShell 用 `#` 注释，Markdown 正文与表格用同行 `<!-- codex-portability: ... -->`；
3. 路径模式补齐 PowerShell 形式 `$env:USERPROFILE\.claude\`、`$env:USERPROFILE\.codex\`；
4. `.kiro` 不在阻断清单中，无需标记——§5.1 第 197 行写成「对 `.claude`、`.kiro`、`.agents` 的显式处理」，实际命中的是 `.claude`、`.codex`（`.agents` 是 source 而非被阻断路径），该句需更正。

## 小的事实或口径偏差

### N1. `prompt-input` 的 skill 路径不是直接的绝对路径

§1 第 36 行称 `codex debug prompt-input` 可枚举「`plugin:skill` 与绝对路径」。实测渲染结果是**别名根 + 相对路径**：先给出 `` `r4` = `C:/.../optimus-devops/2.0.11/skills` `` 这样的根表，条目写成 `(file: r4/dotnet-diagnose-triage/SKILL.md)`。对 `<skill-dir>` 可行性无影响（模型可由根表还原），但措辞应改为「可解析到绝对路径」。

### N2. CI 第 6 步的匹配应锚定列表项格式

§7.1 第 6 步「断言所有 `plugin:skill` 均出现在渲染结果中」若用子串匹配，某个 skill 缺失时可能因为**另一个 skill 的 description 提到它**而误判通过（本仓 skill 之间互相引用 `plugin:skill` 很常见）。实测条目格式为 `\n- <plugin>:<skill>: <description>`，断言应锚定这个前缀。

同时注意：`debug prompt-input` 是调试面，输出格式不在公开契约内。§7.2 的「固定版本、升级单独 PR」已经覆盖这一风险，plan 中应写明升级 CLI 时**首先**复核这两条断言的解析逻辑。

### N3. 门禁计数口径

§6.1 把 Codex manifest 契约、组件 inventory、排除表、marketplace 集合一致性全部塞进 `check_plugin_versions.py`。`.githooks/README.md` 当前把该脚本登记为第 1 项「版本同值」。两种处理都可以，但 plan 里要二选一并写明：

- 视为第 1 项的扩展 → 总数保持「9 个逻辑检查」，但 README 第 1 项的名称与「这个错误不拦会怎样」一栏必须重写；
- 视为新的逻辑检查 → 总数应为「10 个逻辑检查 / 7 个脚本」，§6.2 末段与 §13.1 最后一条要跟着改。

脚本名 `check_plugin_versions.py` 届时已名不副实，是否改名可以留给 plan，但改名会牵动 `repository_gates.py` 与 README 的引用。

## 可行、无需修改

- **独立 `.codex-mcp.json`**：实测可行，且不碰 Claude 侧 `.mcp.json`，回滚面最小。
- **排除表 + 陈旧项检测**：把「Claude-only」从散落的文案变成一处可机械核对的清单，与 §3.1 的原则一致。plan 中需补一条：`kind: hook` 的 `id` 取什么（建议取 `hooks.json` 中的事件名），否则「id 必须能解析到真实组件」无从判定。
- **§3.3 helper script 解析目录**：确定性问题已解决；Windows 下 `run.sh` 经 Git Bash 执行时 `$APPDATA`、`$LOCALAPPDATA` 可用。
- **版本幅度**：devops 由 Minor 改为 Patch 正确——不再新增 Codex agent，只修已有 skill。

## 尚未验证、需由首个 PR 证明

- **Linux runner 上的 `prompt-input`**：本轮只在 Windows 实测。CI 跑在 `ubuntu-latest`，零凭据渲染在 Linux 上是否同样可用，只能由首个 PR 的 CI 日志证明。若不可用，§7.1 第 6 步需要退路（例如改为只在 `workflow_dispatch` 的 Windows job 上跑），plan 中应预留这一分支。

## 建议的处理顺序

1. 按 M1 把 autopilot 的终止条件写成能力判定，并补 §13.3 的反例用例；
2. 按 M2 定下标记的计量单位、载体与 PowerShell 模式；
3. 顺手修正 N1、N3 与 §5.1 第 197 行；
4. 进入 writing-plans，把 N2 的锚定匹配与 Linux 退路写进 CI 任务。

---

> 实测临时目录 `/tmp/tmp.7Jtfags4kC`（以及首轮遗留的 `/tmp/tmp.yuU63OO8hY`）未自动清理，可手动删除。
