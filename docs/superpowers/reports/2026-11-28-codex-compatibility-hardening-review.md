# 审查报告：Codex 兼容性加固 spec

**日期：** 2026-11-28
**审查对象：** `docs/superpowers/specs/2026-11-28-codex-compatibility-hardening-design.md`
**审查重点：** 可行性——spec 提出的能力补齐、门禁与 CI 冒烟能否按所述方式落地。
**实测环境：** Codex CLI 0.172.0，Windows，隔离 `CODEX_HOME`（未登录、未配置任何 API key），仓库副本中临时修改 manifest，未改动工作区。

## 结论

**方向可行，但有 3 处必须修改后才能实施，另有 3 处判据需调整。**

- MCP 分发（§4.1）实测可行，但 MasterGo token 替换大概率在 Codex 下失效；
- agent 分发（§4.2）在 0.172.0 下未观察到生效，Phase 1「安装后缺组件问题必须消失」对 agent 无法保证；
- CI 冒烟（§7）的判据判不出组件是否生效——错误路径同样安装成功；
- 其余设计（`<skill-dir>`、版本幅度、分期回滚、不新增 required job）可行。

### 已核对的基线

| 项 | spec 声明 | 实测 |
|---|---|---|
| 自建插件 Codex manifest | 9 个 | 9 个 |
| 发布 skill | 54 个 | 54 个 `plugins/*/skills/*/SKILL.md` |
| 维护型 skill 镜像 | 7 个 | `.agents/skills/` 下 7 个 |
| 额外 frontmatter 字段的 skill | 11 个 | backend 1（`triggers`）+ office 3（`triggers`/`dependencies`）+ qa 7（`creator`）= 11 |
| `knowledge-base/tools/` 中 Codex CLI 记录 | 无 | 无（仅 `apifox-cli.md` 提及 codex） |
| CI runner | — | `plugin-validate` 为 `ubuntu-latest` |

### 实测记录

| 验证项 | 操作 | 结果 |
|---|---|---|
| marketplace 添加 | `codex plugin marketplace add ./ --json` | ✅ 成功，无需登录 |
| MCP 声明 | frontend Codex manifest 加 `"mcpServers": "./.mcp.json"` 后安装 | ✅ `codex mcp list --json` 列出 `avalonia-docs`、`microsoft-learn`、`mastergo-magic-mcp` |
| agent 声明 | devops Codex manifest 加 `"agents": ["./agents/dotnet-diagnose.md"]` 后安装 | ⚠️ 安装成功，`agents/` 已复制进缓存；`codex debug prompt-input` 渲染结果中 `dotnet-diagnose.md` 正文命中 0 次，未见该 agent 被注册 |
| 错误路径 | prd manifest 写 `mcpServers: "./nope.json"`、`agents: ["./agents/ghost.md"]`、`hooks: "../../escape.json"` | ❌ **仍然安装成功，无报错** |
| token 替换 | 查看 `codex mcp list --json` 中 mastergo 条目 | ⚠️ `"MG_MCP_TOKEN": "${MASTERGO_TOKEN}"` 原样保留，`env_vars: []` |
| 零凭据 skill 枚举 | `codex debug prompt-input "x"` | ✅ 未登录可运行，输出含全部已装插件的 `plugin:skill` 名与 SKILL.md 绝对路径 |
| 特性开关 | `codex features list` | `hooks` stable/true；`plugin_hooks` **removed**；`multi_agent_v2` stable/**false** |

## 必须修改

### M1. §7 CI 冒烟的判据无法判定组件是否生效

**问题。** 实测中错误路径（含越界路径 `../../escape.json`）同样安装成功，说明 `codex plugin add` 不校验 manifest 组件。因此：

- §7.1 第 3、4 步「逐个 `plugin add` 成功 + `plugin list` 显示已启用」通过，不代表 MCP/skill/agent 被加载；
- §7.1 第 5 步「检查安装缓存中的文件存在」是同义反复——缓存就是插件目录的整体拷贝。

**建议。** 改用两条实测可用、零凭据、零模型调用的使用方断言：

1. `codex mcp list --json`：断言 frontend 三个 server 名全部出现；
2. `codex debug prompt-input "x"`：断言 54 个 `plugin:skill` 名全部出现在渲染结果中。

CI 中以 `CODEX_HOME=$RUNNER_TEMP/codex-home` 实现「全新环境」，不依赖 runner 用户目录状态。

**连带结论。** Codex 不校验越界路径，§6.1 的静态路径校验是这一类错误的**唯一**防线，应保留且优先实施。

### M2. §4.2 agent 分发在 0.172.0 下未观察到生效

**问题。** agent 文件被复制进缓存，但没有出现在模型可见的提示中；`multi_agent_v2` 默认关闭，CLI 也无列出自定义 agent 的命令。spec 的人工验收「Codex 可发现 `dotnet-diagnose`」目前没有可执行的验证手段，Phase 1 的完成标准对 agent 一项无法保证。

**被忽略的事实。** 本仓已有 `dotnet-diagnose-triage` skill，其 description 明确「判据全部内置于本 skill 的 references/，安装后即可完整运行」——它就是 Codex 侧的等价物。真正在 Codex 下断裂的是 `dotnet-diagnose-autopilot`：它调度 `dotnet-diagnose` agent。

**建议。**

1. 先做最小 pilot：单一变量为 `--enable multi_agent_v2`，成功信号是 `codex debug prompt-input` 中出现该 agent 或 spawn 工具可选到它；
2. pilot 失败则把 agent 登记为 Claude-only，在 autopilot 正文中写明 Codex 下回退为直接加载 `dotnet-diagnose-triage`；
3. 同步放宽 §6.1「插件有 `agents/*.md` 时 Codex manifest 必须显式列全」为「列全或显式登记为 Claude-only」，否则门禁会强迫写入一个不生效的声明——正是 §2.3 反目标描述的形态。

### M3. MasterGo token 替换大概率失效，缺少预案

**问题。** Codex 解析后 `env` 中保留字面量 `${MASTERGO_TOKEN}`，`env_vars` 为空。Codex 原生的转发机制是 `env_vars`，若不做 `${}` 展开，MasterGo server 启动后拿到的是字面字符串，认证失败且不一定有明显报错。spec §2.3 已把它列为反目标，§12 也列了风险，但缓解只有「单列人工验收」，没有失败后的落点。

**建议。** 在 Phase 1 前置决定退路，三选一：

| 方案 | 代价 |
|---|---|
| Codex manifest 指向单独的 MCP 文件，只含两个 HTTP server | 多一份配置；MasterGo 在 Codex 下暂不可用，需在描述中如实说明 |
| 共用文件中追加 `env_vars: ["MG_MCP_TOKEN"]` | 需先确认 Claude 对未知字段静默忽略；用户须设置 `MG_MCP_TOKEN` 而非 `MASTERGO_TOKEN` |
| 文档要求 Codex 用户直接设置 `MG_MCP_TOKEN` | 依赖 Codex 默认是否继承该变量，需同样实测 |

无论选哪个，§4.1 与 §8.2「三个 MCP 会随 Codex 插件声明分发」的表述都要以 pilot 结果为准。

## 判据需调整

### A1. §6.1 以描述文案关键词判定组件，过于脆弱

「Codex description 含『内置 MCP』时必须声明 `mcpServers`」「含 `PreToolUse` 等时必须标注 Claude-only」依赖中文措辞，换一种写法即可绕过或误报。

**建议。** 从组件实际存在反推：插件目录存在 `.mcp.json` / `agents/*.md` / `hooks/hooks.json` 时，Codex manifest 必须声明对应字段，**或**在一处显式登记为 Claude-only（如 manifest 旁的登记表或门禁脚本内常量）。描述文案只作人工审查项。

### A2. §6.2 portability gate 的规则不可直接实现，且覆盖面不足

1. 「`AskUserQuestion` 等单 harness 工具名」中的「等」必须替换为显式清单。`Bash`、`Task`、`Read` 在正文中大量作为普通词或合法示例出现，不限定会大面积误报；并应限定只扫正文，`allowed-tools` 字段按 §5.3 只校验形态。
2. 门禁只扫 `SKILL.md`，但 `plugins/optimus-devops/skills/jenkins-build/scripts/run.sh:14` 同样硬编码 `VENV_DIR="$HOME/.claude/cache/jenkins-build/.venv"`。本次整改会修掉它，门禁却拦不住回退。扫描范围至少应包含 skill 包内的 `scripts/` 与随包脚本。
3. 「`~/.claude` 只在明确标注『迁移兼容/同步目标』时允许」需定义机器可识别的标注形式（如固定注释标记），否则无法判定。

### A3. §3.3「按操作系统解析」对 LLM 执行步骤不确定

`optimus-backend-api-connect` 的缓存路径由 agent 拼接后交给 `curl -o` 与脚本 `--output`，不是脚本内部计算。让模型「按操作系统解析配置目录」会在不同会话产生不同路径，读写不一致。

**建议。** SKILL.md 中只给一条确定规则，例如 `${OPTIMUS_CACHE_DIR:-$HOME/.cache/optimus}/<skill-name>/`；多平台分支只放在 `run.sh` 这类脚本里实现。旧路径 `~/.claude/...` 的只读回退同样写成固定顺序，而不是「如存在则」的开放描述。

## 可行、无需修改

- **`<skill-dir>` 定位**：`codex debug prompt-input` 输出中每个 skill 都带 SKILL.md 绝对路径，Claude 侧亦提供 skill base directory，agent 可据此解析。`optimus-backend-api-connect` 的三个脚本位于 skill 根目录（无 `scripts/` 子目录），解析目标真实存在。
- **不新增 required job**：步骤挂在 `plugin-validate` 内可避免 ruleset 同步问题。代价是 Codex CLI 安装偶发失败会让 Claude 侧检查一起变红——§12「区分安装失败与插件校验失败」需落实为独立 step 与独立日志前缀。
- **版本幅度与分期回滚**：§10 与 AGENTS.md 触发矩阵一致；两阶段分别升版、不预升的约束正确。
- **`optimus-qa-ui-scripts` 去工具名绑定**：仅该 skill 正文与 `allowed-tools` 出现 `AskUserQuestion`，范围与 spec 一致。

## 补充提示

- **Phase 3 hook pilot 的前提可能已变**：`codex features list` 显示 `plugin_hooks` 为 `removed`，开展 Codex 原生 hook 评估前应先确认插件级 hook 是否仍存在、还是只剩用户级 `hooks` 配置。
- **`optimus-backend-dev` 的安装提示**：第 51 行「将 superpowers 技能复制到项目的 `.claude/skills/`」说的是第三方 superpowers 的安装，不是本插件自身。改为「Claude/Codex 插件安装入口」时需先确认 superpowers 在 Codex 侧的安装方式，否则只是把一个 Claude 绑定换成另一个未验证的说明。
- **工具调研登记**：`codex debug prompt-input` 可零凭据渲染模型可见 skill 清单、`codex plugin add` 不校验组件路径，这两条结论建议随 §7.2 一起登记到 `knowledge-base/tools/`。

## 建议的处理顺序

1. 执行 M2、M3 的两个最小 pilot（agent 发现、MasterGo token），按结果修订 §4.1、§4.2、§8.2、§13.3；
2. 按 M1 重写 §7.1 第 3–5 步的断言；
3. 按 A1–A3 修订 §3.3、§6.1、§6.2；
4. 再进入 writing-plans。
