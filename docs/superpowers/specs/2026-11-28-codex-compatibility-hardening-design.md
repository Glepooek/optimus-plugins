# Codex 兼容性加固设计

> 日期：2026-11-28
> 状态：待用户复审（已按两轮可行性审查修订）
> 类型：双 harness 分发与运行时能力加固
> 审查基线：Codex CLI 0.172.0

## 1. 背景与问题定义

本仓已经完成 Codex marketplace、每插件 Codex manifest、维护型 skill 镜像和双 harness 版本同步。当前机械基线是：

- 9 个自建插件均有 `.codex-plugin/plugin.json`；
- 54 个发布 skill 共用 `plugins/*/skills/*/SKILL.md` 单一真源；
- 7 个仓库维护型 skill 以 `120000` 符号链接镜像到 `.agents/skills/`；
- 两侧插件版本全部同值；
- 仓库门禁、全部单元测试与三项数据一致性检查通过。

因此当前问题不是“Codex 能否安装”，而是“安装后是否获得与 manifest 描述一致、足以执行 skill 的能力”。可行性审查与复核实测确认六类缺口：

1. Codex manifest 宣称内置 MCP 或 Hook，但没有相应 Codex 组件声明；
2. Codex CLI 0.172.0 安装时会复制 agent 文件，但未观察到 agent 注册或进入模型可见提示；
3. 多个发布 skill 硬编码 `.claude/skills/`、`~/.claude/` 或 Claude 专属工具名；
4. 11 个发布 skill 使用六字段允许清单之外的 frontmatter 键，Codex 虽可加载文件，但忽略这些字段的语义；
5. CI 只做 Claude 插件校验，Codex 侧只有“文件存在、JSON 可解析、版本同值”检查，没有真实 marketplace 安装冒烟；
6. `codex plugin add` 对缺失路径和越界路径仍可成功，安装成功与缓存文件存在都不能证明组件已加载。

历史决策也已经出现漂移：

- `2026-08-23-codex-agent-compat-design.md` 原本规划通过 `mcpServers` 向 Codex 分发 MCP；
- `2026-10-30-remove-mcp-servers-plugin-design.md` 后来决定 MCP 不再考虑 Codex；
- 当前 Codex 插件 manifest 能声明 skills、agents 与 MCP servers，但“字段存在”不等于运行时已经支持：0.172.0 可验证 skills 与 MCP，未验证 agent；`plugin_hooks` 特性已标记 `removed`。仓库内的绝对表述应改成按当前 CLI surface 与实测证据逐项判定。

本次修订采用以下已验证事实作为基线：

- `codex mcp list --json` 可在零 API 凭据下列出安装后的 MCP server；
- `codex debug prompt-input "x"` 可在零 API 凭据下枚举模型可见的 `plugin:skill`；条目格式为 `\n- <plugin>:<skill>: <description>`，路径以别名根表（如 `` `r4` = `<cache>/optimus-devops/<version>/skills` ``）加相对路径 `(file: r4/<skill>/SKILL.md)` 给出，可还原为绝对路径；以上均为 Windows 实测，Linux 待首个 PR 的 CI 证明；
- 打开或关闭 `multi_agent_v2` 都未使插件 agent 正文进入渲染提示；
- `.mcp.json` 中的 `${MASTERGO_TOKEN}` 在 Codex 解析结果中保持字面量，且 `env_vars` 为空；
- `codex features list` 显示 `hooks` 为 stable，而 `plugin_hooks` 为 removed。

本设计以“能力声明必须真实”为核心，不追求两个 harness 的文件逐字相同。

## 2. 目标、非目标与反目标

### 2.1 目标

- Codex 安装 `optimus-frontend` 后能够发现并列出 `avalonia-docs`、`microsoft-learn` 两个无需认证的 HTTP MCP；
- 在 Codex CLI 0.172.0 下不再宣称插件 agent 可用；Codex 的 .NET 诊断入口明确回退为直接使用自包含的 `dotnet-diagnose-triage` skill；
- Codex manifest 不再宣称未向 Codex 分发的 Claude Hook；
- 发布 skill 不依赖 Claude 专属安装目录、缓存目录或交互工具名；
- 六字段 frontmatter 允许清单成为机械门禁，而不只是一条文字约定；
- CI 在零 API 凭据、零模型调用条件下完成 Codex marketplace 添加、逐插件安装、54 个 skill 可见性断言与预期 MCP 枚举；
- 保留 `SKILL.md` 单一真源，不生成 Codex 专属正文副本；
- 不改变现有六个 required status check 的 job 名。

### 2.2 非目标

- 本次不把 Claude `PreToolUse`、`SessionStart`、`Notification` 脚本直接复制为 Codex hooks；两侧事件结构与运行环境须单独验证；
- 本次不把 `dotnet-diagnose` agent 作为 Codex 可用能力发布；只有未来 pilot 给出可执行的发现与调用证据后才重新评估；
- 本次不向 Codex 分发 `mastergo-magic-mcp`；先保持 Claude-only，等待经验证的 Codex token 转发方案；
- 本次不迁移到插件根目录 portable `plugin.json`；当前 `.codex-plugin/plugin.json` 仍是 Codex CLI 0.172.0 可用的兼容格式；
- 本次不把 Claude marketplace 的 3 个外部引用条目自动复制进 Codex marketplace；先明确它们为 Claude-only，再单独验证 Codex 对外部 source 模式的支持；
- 不新增 MCP server，不改变 Claude 侧现有三个 server 的业务配置；Codex 使用单独的最小 MCP 配置，只包含两个已验证的 HTTP server；
- 不新增付费 eval，不在 CI 发起模型请求；
- 不修改 skill 的业务算法、产物格式或用户可见功能边界，除非是消除 harness 绑定所必需。

### 2.3 反目标

- manifest 写了 `mcpServers`，但安装后路径不存在、格式不被 Codex 接受或把无法认证的 MasterGo 误报为可用；
- manifest 写了 `agents`，但仅因文件被复制进缓存就宣称 agent 可发现、可调用；
- Codex description 继续声称具备未加载的 Hook；
- 为了 Codex 复制一份 `SKILL.md`，形成第二真源；
- CI 只校验 JSON schema、安装成功或缓存文件存在，却没有从使用侧断言 skill/MCP 已加载；
- Codex 冒烟依赖账号、API key 或付费模型，导致 fork PR 永久失败；
- 把历史 `.claude` 路径简单替换成 `.codex`，继续制造 harness 专属路径；
- 新增 required job 名但未同步 GitHub ruleset，形成静默失效。

## 3. 已定设计原则

### 3.1 单一内容真源，分 harness 能力视图

`plugins/*/skills/*/SKILL.md` 继续是唯一正文真源。Claude 与 Codex manifest 是同一插件的两个能力视图，可以因 harness 实际能力不同而在以下字段产生必要差异：

- `agents`
- `mcpServers`
- `hooks`
- `description` / `interface.longDescription`

版本号仍必须同值，因为两份 manifest 描述的是同一次插件发布；但展示文案不得为了“看起来同步”而声称不存在的能力。Codex manifest 对真实存在的组件必须“显式声明或在统一排除登记中说明 Claude-only”，不能用描述文案关键词替代组件清单。

### 3.2 资源定位不依赖安装目录

发布 skill 引用随包脚本时，统一使用逻辑占位符 `<skill-dir>`：它表示当前 `SKILL.md` 所在目录，执行前由 agent 解析为绝对路径。禁止依赖：

- 当前项目 cwd；
- `.claude/skills/<name>`；
- `.codex/skills/<name>`；
- `CLAUDE_PLUGIN_ROOT`；
- 某个 harness 才会注入的未验证环境变量。

命令示例必须引用解析后的绝对路径并正确处理空格。

### 3.3 用户配置与缓存使用产品无关目录

需要持久化配置或缓存的 skill 使用以下逻辑目录：

- `<optimus-config-dir>`：用户级配置；
- `<optimus-cache-dir>`：可删除、可重新生成的缓存。

目录解析只能由随 skill 分发的脚本完成，`SKILL.md` 只调用脚本并消费其输出，不让 LLM 自行拼接操作系统路径。固定优先级为：

1. 显式环境变量 `OPTIMUS_CONFIG_DIR` / `OPTIMUS_CACHE_DIR`；
2. helper script 定义的平台默认目录：Windows 配置为 `%APPDATA%\optimus`、缓存为 `%LOCALAPPDATA%\optimus\cache`；POSIX 配置为 `${XDG_CONFIG_HOME:-$HOME/.config}/optimus`、缓存为 `${XDG_CACHE_HOME:-$HOME/.cache}/optimus`；
3. 既有 `~/.claude/...` 只读兼容回退。

所有新写入都落到第 1 或第 2 项；不得写回旧路径，也不得把可变缓存写进已安装插件目录。`optimus-backend-api-connect` 必须新增或扩展 helper script，统一返回脚本路径和缓存路径，避免 `curl -o`、`--output` 由模型各自拼接。

### 3.4 静态门禁与真实安装冒烟分层

- 本地 gate 负责快速、确定、无网络的结构校验；Codex 当前不校验组件路径，因此这是缺失路径与越界路径的唯一自动防线；
- CI 的现有 `plugin-validate` job 追加 Codex CLI 安装冒烟；
- CI 从使用侧验证 skill 与 MCP 已加载，不把“安装成功”或“缓存存在”当作加载证据；
- 需要模型推理的自然语言触发与 MCP 实调放入人工 `test-locally`，不进入 required CI；agent 发现 pilot 在当前基线失败，登记为已知限制。

## 4. Codex 能力补齐

### 4.1 `optimus-frontend` MCP

新增 Codex 专用的最小 MCP 配置 `plugins/optimus-frontend/.codex-mcp.json`，只包含：

- `avalonia-docs`
- `microsoft-learn`

在 `plugins/optimus-frontend/.codex-plugin/plugin.json` 声明：

```json
"mcpServers": "./.codex-mcp.json"
```

现有 `plugins/optimus-frontend/.mcp.json` 继续作为 Claude 侧配置并保留三个 server；不生成 `config.toml` 镜像。Codex 配置不包含 `mastergo-magic-mcp`，因为 0.172.0 解析后仍保留字面量 `${MASTERGO_TOKEN}`，没有证据证明认证 token 能可靠传入。只有未来 pilot 验证明确定义的 Codex token 转发机制后，MasterGo 才能加入 Codex 配置。

安装与使用侧冒烟至少校验：

- 引用路径存在且不能逃出插件目录；
- 顶层含 `mcpServers`；
- Codex 配置恰好包含 `avalonia-docs`、`microsoft-learn` 两个条目；
- `codex mcp list --json` 中两个 server 均出现；
- Codex README 与 manifest 描述明确 MasterGo 为 Claude-only，不能以“安装成功”替代认证可用性证明。

受益 skill 至少包括：

- `avalonia-code-review`
- `avalonia-wpf-migration`

三个 MasterGo skill 仍可作为发布 skill 被 Codex 发现，但其依赖的 MCP 在当前基线下明确标注 Claude-only；Codex 用户不得被引导为“安装插件即可使用 MasterGo MCP”。

### 4.2 `optimus-devops` 诊断能力降级

Codex CLI 0.172.0 下，插件 agent 文件即使被复制到缓存，且显式打开 `multi_agent_v2`，仍未观察到正文进入 `codex debug prompt-input` 或出现可执行的发现入口。因此 Phase 1 不在 Codex manifest 中声明 `dotnet-diagnose` agent，也不宣称 agent parity；该 agent 登记为 Claude-only。

Codex 的可执行回退路径为：

- 用户直接触发自包含的 `optimus-devops:dotnet-diagnose-triage`；
- `dotnet-diagnose-autopilot` 不按 harness 判定，而按**能力**判定：SKILL.md 两侧共用，模型无可靠的 harness 自识别手段。复用其执行前置校验第 1 项（“`dotnet-diagnose` agent 是否可用”），把判据写死为：
  - 只有 `optimus-devops:dotnet-diagnose` 作为**具名 agent** 出现在当前可调用 agent 列表中才视为满足；
  - 通用子 agent、`spawn_agent` 默认角色或任何“转发给 @optimus-devops:dotnet-diagnose”的未注册调用均**不满足**，不得用来替代；
  - 不满足时在派发任何子任务之前终止，保留用户原始素材，并给出直接调用 `dotnet-diagnose-triage` 的确定入口；
- `dotnet-diagnose-autopilot` 的 `compatibility` 与 description 同步注明“依赖的 `dotnet-diagnose` agent 当前仅 Claude Code 可用”，避免 Codex 按 description 触发后才发现缺依赖；
- 不得把 Codex 下的单次 triage 包装成“两次独立 agent 交叉验证”。

Claude 侧继续由 `.claude-plugin/plugin.json` 声明 `dotnet-diagnose` agent，保持原样转发契约。未来只有在最小 pilot 能从使用侧证明 agent 可发现且可调用时，才另开变更加入 Codex manifest。

### 4.3 Hook 描述诚实化

以下 Codex manifest 不得再把 Claude Hook 描述成 Codex 已安装能力：

- `optimus-frontend`
- `optimus-backend`
- `optimus-devops`

处理规则：

- Claude marketplace 与 Claude manifest 可以保留 Hook 描述；
- Codex manifest 删除 `PreToolUse`、`SessionStart`、`Notification` 的“内置”表述；
- README 的能力表增加 harness 列，明确“Claude Hook 不自动随 Codex 插件生效”；
- `AGENTS.md` 将“Codex 无对应机制”改成“Claude Hook 不可直接复用；Codex hook 能力须按当前 surface 和事件契约单独实现与验证”。当前 `plugin_hooks` 已移除，因此不得从用户级 `hooks` 特性存在推导出插件级 hook 可分发。

本次不声明非空 Codex `hooks`，避免把 Claude 事件 JSON 和退出码语义未经验证地带入 Codex。

## 5. Skill 可移植性整改

### 5.1 目录与配置路径

| Skill | 当前问题 | 目标状态 |
|---|---|---|
| `optimus-backend-api-connect` | 脚本与缓存硬编码到 `.claude/skills/...`，输出路径由 LLM 拼接 | 脚本从 `<skill-dir>` 读取；新增或扩展 helper script 解析 `<optimus-cache-dir>/optimus-backend-api-connect/`，所有 `curl -o` 与 `--output` 都消费脚本返回路径 |
| `optimus-backend-dev` | 对第三方 superpowers 的安装提示只说明复制到项目 `.claude/skills/` 并重启 Claude Code | 先核实 superpowers 在 Claude/Codex 两侧的实际安装方式，再分别写可验证的安装说明；不得把它误写成本插件自身的 marketplace 安装入口 |
| `jenkins-build` | 用户配置、脚本与 venv 使用 `.claude` 路径，`scripts/run.sh` 也硬编码 `$HOME/.claude/cache/...` | 脚本统一解析配置/缓存目录；配置写入 `<optimus-config-dir>`，venv 写入 `<optimus-cache-dir>`；保留旧路径只读回退 |
| `optimus-qa-ui-scripts` | 正文强制使用 `AskUserQuestion` | 改为“集中询问缺失信息”，不绑定工具名；frontmatter 只列可移植或确有映射的能力 |

`sync-skill-symlinks` 把 `~/.claude/skills/`、`~/.codex/skills/` 作为默认同步目标（`.agents` 是 source，`.kiro` 不在阻断清单内），这属于其业务职责，但必须逐处使用 §6.2 的固定例外标记说明理由，不能靠文件名获得隐式豁免。

### 5.2 Frontmatter 允许清单

发布 skill 的顶层 frontmatter 继续只允许：

```text
name / description / license / compatibility / metadata / allowed-tools
```

现有非可移植字段按下表归并：

| 字段 | 当前范围 | 迁移位置 |
|---|---|---|
| `triggers` | backend 1 个、office 3 个 | 合并进 `description` 的触发与不适用说明 |
| `dependencies` | office 2 个 | 合并进 `compatibility`；复杂安装步骤移入正文或 references |
| `creator` | qa 7 个 | 删除；署名统一使用 `metadata.author: desktop client team` |

受影响 skill 修改时必须按现行规则更新 `metadata.version`。原本缺失版本的存量 skill 在本轮建立 `1.0.0` 基线；已有版本者按修改性质升 Patch。不得伪造过去版本历史。

### 5.3 工具名处理

正文描述行为，不强制不存在于另一 harness 的工具名。frontmatter 的 `allowed-tools` 保持当前 Agent Skills 字段，但新增门禁只校验字段形态，不假设两侧会执行相同的预授权语义。

确有跨 harness 别名需求时：

- agent 的 `tools` 可列公共别名集合；
- skill 正文使用“读取文件”“执行命令”“询问用户”等能力描述；
- 不在正文写“必须调用 AskUserQuestion/Task/Bash 工具”，除非该 skill 明确只支持某一 harness。

## 6. 机械门禁设计

### 6.1 扩展 `check_plugin_versions.py`：新增独立逻辑检查「Codex manifest 契约」

Codex manifest 契约与现有第 1 项“两份 `plugin.json` 版本同值”判据不同、失效后果不同，因此登记为**独立的新逻辑检查**，而不是第 1 项的扩展；实现仍放在 `check_plugin_versions.py` 内（复用其 manifest 加载逻辑），本次不改脚本名，避免牵动 `repository_gates.py` 与 README 的既有引用。`.githooks/README.md` 为其新增一行“这个错误不拦会怎样”：Codex 安装成功但组件缺失或越界，且 `codex plugin add` 不报错。

在现有“文件存在、JSON 可解析、版本同值”基础上增加 Codex manifest 契约：

- `name` 必须与插件目录名、Codex marketplace 条目名一致；
- `skills`、`agents`、`mcpServers` 的路径必须存在、位于插件目录内且类型正确；
- 从实际组件反推 Codex 声明：插件存在 `.mcp.json`、`agents/*.md`、`hooks/hooks.json` 时，相应能力必须在 Codex manifest 声明，或登记到统一的机器可读排除表 `.githooks/codex_component_exclusions.json`；
- Codex 使用独立 MCP 配置时，Claude `.mcp.json` 中每个 server id 必须出现在 Codex 配置或排除表中，不能只检查“某个 `mcpServers` 字段存在”；
- 排除表每项至少包含 `plugin`、`kind`（`agent` / `hook` / `mcp-server`）、`id`、`path`、`reason`；路径与 id 必须能解析到真实组件。`id` 取值固定为：`agent` 取 agent 文件 frontmatter 的 `name`，`hook` 取 `hooks.json` 中的事件名（如 `PreToolUse`、`SessionStart`、`Notification`，同一插件每个事件一项），`mcp-server` 取 `.mcp.json` 中的 server id。当前至少登记 `optimus-devops` agent 为 Claude-only、三个插件的 Claude hooks 为 Claude-only、frontend 的 MasterGo server 为 Claude-only；
- 组件从仓库删除、进入 Codex manifest 或路径变化后，陈旧排除项必须使 gate 失败；
- `.agents/plugins/marketplace.json` 的本地插件集合必须与 `plugins/*/.codex-plugin/plugin.json` 集合一致；
- `interface.capabilities` 不作为运行能力真源，不能替代上述组件字段。

description 与 `interface.longDescription` 只作为人工审查项，不参与组件存在性判定，避免中文关键词变化导致漏报或误报。由于 `codex plugin add` 不校验缺失/越界组件路径，以上静态路径校验是该类错误的唯一自动防线。

外部引用插件不属于 `plugins/`，继续不要求本仓生成 Codex manifest。

### 6.2 新增 `check_skill_portability.py`

扫描以下范围：

- `plugins/*/skills/*/SKILL.md`：frontmatter 与正文分开处理；
- skill 包内 `scripts/**`；
- skill 根目录随包分发的 `*.sh`、`*.ps1`、`*.py`。

规则如下：

- frontmatter 顶层键只能来自六字段允许清单；
- 拒绝新增 `.claude/skills/`、`.codex/skills/` 形式的 bundled resource 路径；
- 拒绝新增 `~/.claude/`、`$HOME/.claude/`、`%USERPROFILE%\.claude\`、`$env:USERPROFILE\.claude\` 及对应 `.codex` 的配置/缓存写入路径；
- 单 harness 工具名阻断清单首版只包含正文中的完整 token `AskUserQuestion`；`Bash`、`Task`、`Read` 等兼具普通语义或跨 harness 映射的词不做全局字符串阻断；
- `allowed-tools` 只校验字段形态，不参与正文工具 token 扫描；
- 合法迁移兼容、同步目标或 harness 专属产物必须带固定标记 `codex-portability: allow-harness-path reason=<非空理由>`，规则如下：
  - **计量单位是行**：一条标记豁免其所在行（或紧随其后一行）的全部命中，同一行命中 `.claude` 与 `.codex` 只需一条标记；“一条标记覆盖多处”只指跨行，跨行即失败；
  - **载体按上下文固定**：YAML frontmatter、bash、PowerShell 用 `#` 注释写在命中行的前一行；Markdown 正文与表格行用同行 `<!-- codex-portability: ... -->`，不得在表格行之间插入独立注释行（会断开表格）；
  - 缺理由、孤立标记（其后一行与本行均无命中）均失败；
- `<skill-dir>` 引用必须能在 skill 包内解析到实际文件；
- 输出包含文件和行号，支持 `--list` 审计模式与默认阻断模式。

已知需标记的存量命中：`sync-skill-symlinks/SKILL.md` 共 7 行（frontmatter `description` 1 行、PowerShell 代码块 2 行、bash 代码块 2 行、正文 1 行、表格 1 行），以及 `jenkins-build` 保留的旧路径只读回退。

该脚本及单测加入 `repository_gates.py` 与自动发现测试目录。连同 §6.1 的新逻辑检查，仓库口径从“6 个脚本 / 8 个逻辑检查”更新为“7 个脚本 / 10 个逻辑检查”；所有计数声明同步修改，不新增第二份 catalog。

## 7. Codex CI 冒烟

不新增 required job；在现有 `plugin-validate` job 的 Claude 校验之后追加 Codex 步骤，因此 GitHub ruleset 的六个 job 名保持不变。

### 7.1 执行流程

1. 安装并固定 Codex CLI 版本；首版以本 spec 实测的 `0.172.0` 为基线；
2. 将 `CODEX_HOME` 显式设为 `${RUNNER_TEMP}/codex-home`，在与 runner 用户目录隔离的全新环境中执行：

```bash
codex plugin marketplace add ./ --json
codex plugin list --available --json
```

3. 从 `.agents/plugins/marketplace.json` 读取 9 个本地插件名，逐个执行：

```bash
codex plugin add <plugin>@optimus-plugins --json
```

4. 再执行 `codex plugin list --json`，断言 9 个插件均已安装且启用；
5. 执行 `codex mcp list --json`，断言 `avalonia-docs`、`microsoft-learn` 均出现，且当前 Claude-only 的 `mastergo-magic-mcp` 不被误报为 Codex 已分发；
6. 执行 `codex debug prompt-input "x"`，以仓库内 54 个 `plugins/*/skills/*/SKILL.md` 的 `name` 与所属插件生成期望清单，断言每个 `plugin:skill` 都以列表项前缀 `\n- <plugin>:<skill>: ` 出现在渲染结果中；**不得用裸子串匹配**——skill 之间常在 description 中互相引用 `plugin:skill`，裸子串会让缺失的 skill 因被他人提及而误判通过；
7. 不把安装缓存中的文件存在当作组件加载证据；缓存只可用于失败诊断，路径安全由 §6.1 的仓库静态 gate 保证；
8. 每个安装与断言 step 使用独立日志前缀；任一插件失败时继续收集其余结果，最后统一返回非零并打印“CLI 安装失败 / 插件安装失败 / skill 可见性失败 / MCP 枚举失败”分类名单。

### 7.2 CI 约束

- 不配置 OpenAI API key；
- 不运行 `codex exec` 或任何模型请求；
- 不访问企业内网服务，不启动 MCP server；
- 不依赖用户全局 marketplace；hosted runner 必须保持全新环境；
- Codex CLI 安装方式属于新 CI 依赖，实施前按 `AGENTS.md` 先登记或确认 `knowledge-base/tools/` 调研结论；当前审查未找到既有记录；
- 同一工具记录中补充两条已验证行为：`codex debug prompt-input` 可零凭据枚举模型可见 skill；`codex plugin add` 不校验 manifest 组件路径，不能作为加载成功判据；
- CLI 升级须单独 PR，重新执行 marketplace 与 manifest pilot，不能使用 `latest` 静默漂移；`debug prompt-input` 是调试面、输出格式不属公开契约，升级时**首先**复核 §7.1 第 5、6 步的解析逻辑；
- `prompt-input` 零凭据渲染只在 Windows 实测过，CI 运行于 `ubuntu-latest`。首个 PR 必须以 CI 日志证明其在 Linux 可用；若不可用，第 6 步退回到独立的非 required Windows job（`workflow_dispatch` + PR 触发），第 1–5 步仍留在 `plugin-validate` 内，不得为此静默删除第 6 步。

## 8. 文档与历史决策修订

### 8.1 `AGENTS.md`

修改双 harness 差异表与重要约束：

- 删除“Codex 无 Hook 机制”的绝对结论；
- 删除“Codex manifest 不声明 `mcpServers`”的绝对禁令；
- 改为“现有 Claude Hook 不自动适用于 Codex；MCP 仅在路径与使用侧都验证后按 Codex manifest 分发；agent 在 0.172.0 下暂列 Claude-only”；
- 记录 `plugin_hooks` 已移除，未来 hook pilot 必须先确认是否仍存在插件级分发面，而不是把用户级 `hooks` 特性当作插件级能力；
- 增加“展示文案必须与该 harness 实际分发组件一致”；
- 增加 Codex 静态门禁与 CI 冒烟入口。

### 8.2 `README.md`

- 保留现有 Codex CLI 安装命令；
- 插件列表或能力矩阵增加 Claude/Codex 差异列；
- 说明 `optimus-frontend` 的 `avalonia-docs`、`microsoft-learn` 两个 MCP 会随 Codex 插件声明分发；
- 说明 `mastergo-magic-mcp` 在 verified token forwarding 出现前为 Claude-only；
- 说明 `dotnet-diagnose` agent 在 Codex CLI 0.172.0 下未观察到注册，Codex 用户应直接使用 `dotnet-diagnose-triage`；
- 说明 Claude Hook 不随 Codex 自动生效；
- 说明 Claude marketplace 另有 3 个外部引用条目，Codex marketplace 当前只包含 9 个本仓自建插件。

### 8.3 历史 spec 的关系

历史 spec 不回写，但本文件作为当前决策覆盖以下旧结论：

| 历史文件 | 被覆盖的结论 | 当前结论 |
|---|---|---|
| `2026-08-23-codex-agent-compat-design.md` | Codex 无 Hook 对应机制；可按 manifest 规划 agent parity | Claude Hook 不可直接复用；`plugin_hooks` 已移除；agent 在 0.172.0 下未观察到注册，暂列 Claude-only |
| `2026-10-30-remove-mcp-servers-plugin-design.md` | MCP 不再考虑 Codex、Codex manifest 不得写 `mcpServers` | `optimus-frontend` 使用独立 Codex MCP 配置分发两个已验证 HTTP server，MasterGo 暂不分发 |

`docs/superpowers/plans/` 与旧 review 报告保持历史原貌；后续实施计划以本 spec 为准。

## 9. 文件级改动范围

| 范围 | 预期改动 |
|---|---|
| `plugins/optimus-frontend/.codex-plugin/plugin.json`、`.codex-mcp.json` | 增加 Codex 专用的两个 HTTP MCP 声明，修正 Codex 描述 |
| `plugins/optimus-devops/.codex-plugin/plugin.json` | 修正 Codex 描述，不声明当前不可验证的 agent |
| `plugins/optimus-backend/.codex-plugin/plugin.json` | 删除 Codex 未具备的 PreToolUse 宣称 |
| 三插件对应 `.claude-plugin/plugin.json` | 只同步版本；Claude 能力描述可保留 |
| `plugins/optimus-backend/skills/{optimus-backend-api-connect,optimus-backend-dev}/` | helper 驱动的路径解析；核实并修订 superpowers 双 harness 安装提示 |
| `plugins/optimus-devops/skills/{jenkins-build,dotnet-diagnose-autopilot}/` | 配置/缓存路径可移植化；autopilot 前置校验改为“具名 agent 可用”能力判定，不满足即终止并给出 triage 入口，`compatibility`/description 注明 agent 仅 Claude 可用 |
| `plugins/optimus-qa/skills/optimus-qa-ui-scripts/` | 去除 AskUserQuestion 绑定 |
| backend/office/qa 共 11 个含额外 frontmatter 字段的 skill | 归并到六字段集合并升 skill 版本 |
| `.githooks/check_plugin_versions.py`、`.githooks/codex_component_exclusions.json` + tests | Codex manifest、真实组件 inventory、Claude-only 排除与 marketplace 契约 |
| `.githooks/check_skill_portability.py` + tests | 新增发布 skill 可移植性 gate |
| `.githooks/repository_gates.py`、`.githooks/README.md`、相关计数声明 | 登记第 7 个脚本；新增第 9（Codex manifest 契约）、第 10（skill 可移植性）两个逻辑检查 |
| `.github/workflows/ci.yml` | 在 `plugin-validate` 内追加零凭据 Codex 安装冒烟 |
| `knowledge-base/tools/` 的 Codex CLI 工具记录 | 登记固定安装方式、零凭据 skill 枚举与“plugin add 不校验组件路径”结论 |
| `AGENTS.md`、`README.md`、相关规则文件 | 更新当前双 harness 判据与验证入口 |

## 10. 版本号设计

最终版本以实施分支起点为准，升级幅度按以下性质确定：

| 产物 | 幅度 | 理由 |
|---|---|---|
| `optimus-frontend` 插件 | Minor | Codex 侧新增两个可用 HTTP MCP 能力 |
| `optimus-devops` 插件 | Patch | 修正文案并修复 `jenkins-build` / `dotnet-diagnose-autopilot` 的现有可移植性问题，不新增 Codex agent |
| `optimus-backend` 插件 | Patch | 修正文案并修复已有 skill 的可移植路径 |
| `optimus-office` 插件 | Patch | 清理已有 skill 的非可移植 frontmatter |
| `optimus-qa` 插件 | Patch | 清理已有 skill frontmatter 与交互工具绑定 |
| 受影响 skill | Patch；缺版本者建立 `1.0.0` 基线 | 行为修复与文档可移植化，不新增业务功能 |
| marketplace 顶层 | 不变 | 没有新增或删除插件 |

两份插件 manifest 仍在同一提交中升到同一个新值。Skill 若只改 frontmatter/路径说明按 Patch，不触发 darwin-skill Minor/Major 评分门禁。

## 11. 实施分期

### Phase 1：能力真实性

- frontend 两个 HTTP MCP；
- MasterGo 与 devops agent 的 Claude-only 登记；
- devops autopilot 按“具名 agent 是否可用”判定，不满足时在派发前终止并把用户引导到 `dotnet-diagnose-triage`，不冒充 agent 双活；
- 三个 Codex manifest 描述修正；
- manifest/component inventory 静态校验；
- Codex marketplace CI 冒烟与 54 个 skill、两个 MCP 的使用侧断言。

Phase 1 完成后，所有 Codex 宣称的组件都有静态路径证据和使用侧可见性证据；未生效的 agent 与 MasterGo 不再被宣称为 Codex 可用。

### Phase 2：Skill 可移植性

- 四个明确路径/工具问题整改；
- 11 个额外 frontmatter 字段清理；
- 新增 portability gate；
- 文档与版本更新。

Phase 2 完成后，新发布 skill 不得再引入 harness 专属目录与未知顶层字段。

### Phase 3：后续 pilot，不阻塞本次完成

1. **Portable 根 manifest**：官方当前推荐插件根 `plugin.json`，`.codex-plugin/plugin.json` 是兼容回退。另开 pilot 验证 Claude 共存、Codex marketplace 解析、版本门禁与缓存升级后再迁移。
2. **Codex 插件级 hooks**：先确认当前 CLI 是否仍存在插件级 hook 分发面；`plugin_hooks` 已移除，只有用户级 `hooks` 存在不能视为前提成立。确认 surface 后，再围绕 commit review gate、权限通知和启动提示分别评估事件契约。
3. **Codex agent 发现**：以单一最小插件重跑 agent pilot；成功信号必须是从使用侧可发现且可调用，不能是缓存中出现 agent 文件。
4. **MasterGo token 转发**：验证 Codex 支持的 `env_vars` 或其他明确机制，并完成一次只读查询后再考虑纳入 Codex MCP 配置。
5. **外部插件 parity**：分别验证 `cangjie-skill`、`archify`、`ppt-master` 的 Codex 安装方式；无法直接引用时，选择独立 marketplace 或明确 Claude-only，不复制第三方正文。

## 12. 风险与回滚

| 风险 | 缓解 |
|---|---|
| Claude 与 Codex 的 MCP 解析细节不同 | 使用独立 Codex 最小配置；CI 以 `codex mcp list --json` 断言两个 server；失败时回滚 Codex `mcpServers` 字段，不改现有 Claude 配置 |
| MasterGo token 替换在 Codex 不生效 | 当前明确不向 Codex 分发并登记 Claude-only；只有 token forwarding pilot + 只读查询通过后再启用 |
| agent 文件被缓存但未注册 | 当前不在 Codex manifest 声明 agent；README 引导直接使用 triage；未来 pilot 必须从使用侧证明可发现与可调用 |
| `codex plugin add` 对错误组件路径仍成功 | §6.1 静态路径 gate 作为唯一自动防线；CI 不以安装成功或缓存存在证明组件加载 |
| 新 portability gate 一次暴露大量存量问题 | 本 spec 已列出已知 11 个 frontmatter 与 4 个行为问题；同一 PR 清零后再设硬失败，不长期豁免 |
| Codex CLI 升级造成 CI 漂移 | 固定版本；升级单独 PR；禁止 `latest` |
| hosted runner 安装 CLI 偶发失败 | 使用官方安装源、固定版本与有限重试；失败必须可区分“安装失败”和“插件校验失败” |
| `prompt-input` 在 Linux runner 上不可零凭据运行 | 首个 PR 以 CI 日志验证；不可用时按 §7.2 把第 6 步移到非 required Windows job，不静默删除 |
| autopilot 在 Codex 下被通用子 agent 冒充执行 | §4.2 按能力判定：只认具名 agent；人工验收含反例用例 |
| 两个阶段造成版本号重复升级 | 可以拆成两个 PR，各自按实际改动升版；不得预升下一阶段版本 |

回滚按阶段进行：Phase 1 与 Phase 2 各自保持原子 PR，可分别 `git revert`，不要求同时回滚。

## 13. 验收标准

### 13.1 静态验收

- 9 个 Codex marketplace 本地插件与 9 个 Codex manifest 一一对应；
- 所有 manifest 路径均存在且未逃出插件目录；
- frontend Codex manifest 声明 `.codex-mcp.json`，其中恰好包含 `avalonia-docs` 与 `microsoft-learn`；
- devops Codex manifest 不宣称当前不可验证的 `dotnet-diagnose` agent，统一排除表将其登记为 Claude-only；
- Claude 侧存在但 Codex 不分发的 hook、agent、MCP server 均有有效的机器可读排除项，且不存在陈旧项；
- backend/frontend/devops 的 Codex 描述不再误报 Claude Hook；
- 所有发布 skill 的顶层 frontmatter 只含六字段允许清单；
- 发布 skill 正文及随包脚本无未标记的 harness 专属 bundled-resource、配置或缓存路径；`sync-skill-symlinks` 的每个合法命中均带固定理由标记；
- 正文无被禁工具 token `AskUserQuestion`；frontmatter `allowed-tools` 不参与该字符串扫描；
- `sync-skill-symlinks` 的 7 行存量命中均带符合 §6.2 载体规则的标记，Markdown 表格渲染未被破坏；
- `repository_gates.py` 登记 7 个脚本，`.githooks/README.md` 说明 10 个逻辑检查，且新增两项各有“这个错误不拦会怎样”说明。

### 13.2 自动验证

- `python .githooks/run_repository_gates.py` 退出码 0；
- `python .githooks/run_unit_tests.py` 全部通过；
- 三项数据一致性检查通过；
- CI `plugin-validate` 同时完成 Claude 严格校验、Codex 9 插件安装、54 个 `plugin:skill` 可见性断言与两个 MCP 枚举；
- Codex CI 日志能区分 CLI 安装、插件安装、skill 可见性与 MCP 枚举失败；
- PR 上既有六个 required status checks 全绿，job 名无变化。

### 13.3 人工 Codex 验收

- 使用本地 marketplace 安装 `optimus-frontend`，能看到 `avalonia-docs` 与 `microsoft-learn` 两个 MCP 配置，且不把 MasterGo 显示为 Codex 已分发能力；
- `avalonia-docs` 与 `microsoft-learn` 可连接；
- README 与 manifest 将 MasterGo 明确标为 Claude-only，不要求 Codex 的 `MASTERGO_TOKEN` 验收；
- 安装 `optimus-devops` 后可直接触发 `dotnet-diagnose-triage`；
- 在 Codex 中触发 `dotnet-diagnose-autopilot`：在派发任何子任务前即因“具名 agent `optimus-devops:dotnet-diagnose` 不可用”终止，并给出 triage 入口；
- **反例用例**：同一会话中模型不得调用 `spawn_agent` 或通用子 agent 冒充 `dotnet-diagnose`，最终输出不得出现“首次分析 / 复核分析”双段结构；任一出现即验收失败；
- `optimus-backend-api-connect` 与 `jenkins-build` 在插件缓存不位于 `.claude/skills` 时仍能定位脚本、配置与缓存；
- `optimus-qa-ui-scripts` 在没有 `AskUserQuestion` 工具名的环境中仍能正常收集信息。

## 14. 参考依据

- OpenAI Plugin architecture：<https://developers.openai.com/plugins/build/plugins>
- OpenAI Plugin hooks：<https://developers.openai.com/plugins/build/hooks>
- 可行性审查报告：`docs/superpowers/reports/2026-11-28-codex-compatibility-hardening-review.md`
- 可行性复审报告：`docs/superpowers/reports/2026-11-28-codex-compatibility-hardening-review-2.md`
- 历史 Codex 适配设计：`docs/superpowers/specs/2026-08-23-codex-agent-compat-design.md`
- 历史 MCP 收窄设计：`docs/superpowers/specs/2026-10-30-remove-mcp-servers-plugin-design.md`
- 当前仓库规则：`AGENTS.md`

