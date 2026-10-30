# 合并 optimus-avalonia 到 optimus-frontend 设计

> 日期：2026-10-30
> 状态：待审查
> 类型：插件结构调整（删除一个插件、扩充另一个）

## 1. 背景与意图

Avalonia 与 WPF 同属**桌面端前端 UI 开发**。现状是两者分属 `optimus-frontend`（WPF）与 `optimus-avalonia`（Avalonia）两个插件，用户需要分别安装。本次将 `optimus-avalonia` 整体并入 `optimus-frontend`，使"桌面前端"成为一个插件，并删除 `optimus-avalonia`。

## 2. 目标 / 非目标 / 反目标

**目标**
- `optimus-avalonia` 的 4 个 skill 与 `install.sh` 原样迁入 `optimus-frontend`
- 仓库内所有现行引用（清单、README、门禁配置、知识库、eval）同步到新位置
- 版本号按本仓触发矩阵升级，八项提交门禁通过

**非目标**
- 不修改 4 个 skill 的 SKILL.md 正文逻辑、触发词、`allowed-tools`
- 不回写历史记录（各 skill CHANGELOG、2026-09-15 spec、todo-list）
- 不调整 旧 MCP 插件（`avalonia-docs` MCP 与插件归属无关）

**反目标（即使技术上成功也算失败）**
- 迁移后 skill 的 `/optimus-frontend:<name>` 调用不可用或被重复发现
- 门禁或 CI 因路径残留而静默失效（本仓"不报错的失效形态"）
- 已有 WPF skill 的行为被意外改变；`.xaml` 门禁在改造后行为必须与改造前完全一致
- `.axaml` 与 `.xaml` 的门禁互相串味（审了一边就放行另一边）

## 3. 可行性结论

可行，技术风险低。依据：4 个 skill 均为扁平结构（符合 `skills/<name>/SKILL.md` 五段路径约定）；与 frontend 的 6 个 skill 无重名、触发词无重叠；`ci.yml` 的 9 个 unittest 目录不涉及 avalonia；唯一的 shell 脚本 `build-deb.sh` 不进 Python 测试。

## 4. 已定决策（用户确认）

| 决策点 | 结论 |
|---|---|
| 是否合并 | 是：删除 `optimus-avalonia`，内容并入 `optimus-frontend` |
| 钩子范围 | **扩展到 `.axaml`**：提交时 staged 含 `.axaml` 则必须先经 `avalonia-code-review` 审查，机制与 `.xaml`/`wpf-code-review` 对称 |
| `install.sh` 处理 | **方案 A**：随 skill 迁入 `plugins/optimus-frontend/install.sh`，只改头注释，接受它连同 WPF skill 一起安装（`${PLUGIN_ROOT}/skills` 整体复制） |

## 5. 我的默认决定（调用方未明确，标注为我的判断）

1. **钩子设计见 §6.4**。`avalonia-code-review` 与 `wpf-code-review` 的 SKILL.md 正文都不涉及 `mark`，放行流程完全由钩子拦截提示驱动，故**两个 review skill 的 SKILL.md 均不需要改**。
2. **展示文案同步**：`optimus-frontend` 的 `description`、`hooks/README.md` 标题与首段，由"WPF"改为"WPF + Avalonia 桌面前端"，并说明两类文件各走各的审查 skill。
3. **迁移用 `git mv`**：保留文件历史，不重新创建。
4. **`.gitattributes` 同步改路径**：`install.sh` 的 `eol=lf` 规则必须跟着新路径走，否则 Windows 检出会变 CRLF，shebang 失效。

## 6. 文件级改动清单

### 6.1 迁移（`git mv`）

| 源 | 目标 |
|---|---|
| `plugins/optimus-avalonia/skills/avalonia/` | `plugins/optimus-frontend/skills/avalonia/` |
| `plugins/optimus-avalonia/skills/avalonia-code-review/` | `plugins/optimus-frontend/skills/avalonia-code-review/` |
| `plugins/optimus-avalonia/skills/avalonia-deb-release/` | `plugins/optimus-frontend/skills/avalonia-deb-release/` |
| `plugins/optimus-avalonia/skills/avalonia-wpf-migration/` | `plugins/optimus-frontend/skills/avalonia-wpf-migration/` |
| `plugins/optimus-avalonia/install.sh` | `plugins/optimus-frontend/install.sh` |

### 6.2 删除

整个 `plugins/optimus-avalonia/` 目录（含其 `.claude-plugin/`、`.codex-plugin/`）。

### 6.3 修改

| 文件 | 改动 |
|---|---|
| `.claude-plugin/marketplace.json` | 删除 `optimus-avalonia` 条目；`optimus-frontend` 条目 `description` 加入 Avalonia；顶层 `version` `14.4.0 → 15.0.0` |
| `.agents/plugins/marketplace.json` | 删除 `optimus-avalonia` 条目（该文件无顶层 version） |
| `plugins/optimus-frontend/.claude-plugin/plugin.json` | `version 2.0.0 → 2.1.0`；`description` 加入 Avalonia |
| `plugins/optimus-frontend/.codex-plugin/plugin.json` | 同上，两份 `version` 必须同值；另有 `interface.shortDescription`、`longDescription`、`defaultPrompt` 三个仅含 WPF 的展示字段，**一并**改为覆盖 Avalonia（我的判断，审查中发现） |
| `README.md` | 删插件列表行（L14）与外部依赖行（L32）；frontend 的职责与依赖行并入 Avalonia 内容；L69、L123 示例前缀 `optimus-avalonia` → `optimus-frontend`。frontend 的依赖行须保留"Avalonia Docs MCP 由 旧 MCP 插件 提供"这一说明（frontend 自身没有 `.mcp.json`，我的判断） |
| `.gitattributes` | L22 路径改为 `plugins/optimus-frontend/install.sh` |
| `plugins/optimus-frontend/install.sh` | 头注释"optimus-avalonia 版"→"optimus-frontend 版"，并注明会安装插件内全部 skill |
| `plugins/optimus-frontend/hooks/pretooluse/review-gate.sh` | 见 §6.4 |
| `plugins/optimus-frontend/hooks/README.md` | 标题、功能说明、工作原理、使用方式改为双门禁；标记文件说明加 `avalonia.hash` |
| `.claude/rules/hook-conventions.md` | 已登记配置表中 frontend 一行的用途改为"staged `.xaml`/`.axaml` 未经对应 review skill 时拦 `git commit`"（该文件属规范依据，改动需与脚本实际行为一致） |
| `plugins/optimus-frontend/skills/avalonia-code-review/evals/01-*/prompt.md` | frontmatter `plugins:` 由 `optimus-avalonia` 改 `optimus-frontend` |
| `knowledge-base/tools/reference/build-mcp.md` | 备注中的 `optimus-avalonia` 改 `optimus-frontend` |
| `knowledge-base/tools/index.jsonl` | 同上，对应条目内的提及 |
| `knowledge-base/tools/README.md` + `CHANGELOG.md` | 版本 `1.0.0 → 1.0.1`（修订已有条目），两处须一致 |

### 6.4 钩子改造设计（`review-gate.sh`）

**结构**：同一脚本内两个独立门禁，各自拥有「文件模式 / 审查 skill / 标记文件」三元组，互不影响。

| 类别 | 文件模式 | 审查 skill | 标记文件 |
|---|---|---|---|
| `wpf` | `*.xaml` | `wpf-code-review` | `.git/optimus-review-marks/wpf.hash`（沿用现有，保证旧标记不失效） |
| `avalonia` | `*.axaml` | `avalonia-code-review` | `.git/optimus-review-marks/avalonia.hash`（新增） |

**行为要点**
1. 两个模式互不相交：`*.xaml` 不会匹配 `foo.axaml`（后者后缀是 `.axaml`），实现时须实测而不是假设。
2. 检测模式：先看两类 staged 文件是否都为空，都空则 `exit 0`（保持"无 staged 目标文件时零感知"）；再判断命令是否含 `git commit`；然后**逐类**比对哈希，任一类未通过就拦截。
3. 一次提交同时含两类且都未审查时，拦截提示**同时列出两类**，各附对应 skill 与对应的 `mark` 命令，避免来回两轮。
4. `mark` 改为**必须带类别参数**：`review-gate.sh mark wpf` / `mark avalonia`；无参数或参数非法时打印用法并 `exit 1`。理由：无参数标记"全部"会让审查一边就放行另一边，违背"诚实门禁"；该脚本与拦截提示同包分发，不存在旧提示指向新脚本的兼容问题。
5. 保持现有约束不变：纯 bash 正则匹配 `git commit`、不起解释器、拦截用 `exit 2`、非 git 仓库干净 `exit 0`。
6. `hooks.json` **不改**（matcher、命令、timeout 均不变）。

**范围外**：沿用现有"诚实门禁"局限性（不能防刻意跳过审查直接 `mark`；仅 Claude Code 会话内生效）。

## 7. 版本号依据（按 AGENTS.md 触发矩阵）

| 层级 | 变化 | 依据 |
|---|---|---|
| `optimus-frontend` 两份 `plugin.json` | `2.0.0 → 2.1.0`，同值 | 插件内新增 4 个 skill → Minor |
| marketplace 顶层 | `14.4.0 → 15.0.0` | 删除插件 → Major；MINOR/PATCH 归零 |
| 4 个迁入 skill 的 `metadata.version` | **不变** | 仅物理位置改变，SKILL.md 正文未动；矩阵口径是"改动落在该产物内部才升" |
| `avalonia-code-review` 的 eval | 其 `metadata.version` **升 Patch**（`1.0.1 → 1.0.2`） | `evals/` 内文件被改，矩阵明确"含 evals/ 也要升"；同步补该 skill 的 CHANGELOG 一条 |
| `knowledge-base/tools` | `1.0.0 → 1.0.1` | 修订已有条目的文字引用 |
| `optimus-avalonia` 的 `plugin.json` | 随目录删除，无需升 | — |
| 钩子脚本与 hooks README | 无独立版本号 | 落在 `plugins/optimus-frontend/` 默认行，已被 frontend Minor 覆盖 |

⚠️ darwin 评分门禁仅在 Minor/Major 升级且改动 SKILL.md 时触发。本次 `avalonia-code-review` 只升 Patch 且 SKILL.md 正文未改，不触发。

## 8. 验证标准

执行完成后必须全部满足：

1. `sh .githooks/pre-commit` 退出码 0（含两份 `plugin.json` 同值、`.kiro`/`.agents` 镜像、marketplace 一致性、`check_hook_configs.py`）
2. `python .claude/skills/knowledge-base-maintain/scripts/check_index.py` 与 `check_refs.py` 通过
3. `grep -rIn "optimus-avalonia"` 在**现行文件**中无残留；允许残留仅限：各 skill `CHANGELOG.md`、`docs/superpowers/specs/2026-09-15-*`、`docs/todo-list/*`、本 spec
4. `plugins/optimus-avalonia/` 不存在；`plugins/optimus-frontend/skills/` 下共 10 个 skill 目录（原 6 个含 `wpf-project-conventions` 加 4 个）
5. `plugins/optimus-frontend/install.sh` 在 `.gitattributes` 中有 `eol=lf` 规则，且文件本身为 LF
6. 用 `--plugin-dir` 加载本仓（`test-locally`），确认 `/optimus-frontend:avalonia` 等 4 个命令可被发现，旧 `optimus-avalonia:*` 不再出现
7. `ci.yml` 无需改动（已确认不含 avalonia 路径）；PR 上 6 个必需检查全绿
8. **钩子行为矩阵**（在临时 git 仓库中手工实测，输入伪造的 hook JSON）：

| 场景 | 期望 |
|---|---|
| 仅 staged `.xaml`，未标记 | `exit 2`，提示 `wpf-code-review` |
| 仅 staged `.axaml`，未标记 | `exit 2`，提示 `avalonia-code-review` |
| 两类都 staged，都未标记 | `exit 2`，提示同时列出两类 |
| 两类都 staged，只标记 `wpf` | `exit 2`，仍只提示 avalonia |
| 两类都 staged，分别标记后 | `exit 0` |
| 标记后再改动 `.axaml` 内容 | `exit 2`（哈希失效） |
| 无 staged 目标文件 | `exit 0` |
| staged 有目标文件但命令不是 `git commit` | `exit 0` |
| `mark` 无参数 / 参数非法 | `exit 1` 并打印用法 |
| 非 git 仓库 | 检测模式 `exit 0` |


## 9. 风险与回滚

| 风险 | 缓解 |
|---|---|
| 已安装 `optimus-avalonia` 的用户升级后丢失该插件，调用名变化 | 属预期的破坏性变更，故 marketplace 升 Major；PR 描述与提交信息明确写出新调用前缀 |
| `.gitattributes` 漏改导致 `install.sh` 变 CRLF | 验证标准第 5 条 |
| 迁移后 skill 间相对引用失效 | 4 个 skill 互相只用同级相对路径（`../xxx`），整体同层迁移不会变；执行时以 grep 实证 |
| `install.sh` 变宽，连带安装 WPF skill | 已在 §4 接受（方案 A），并在头注释注明 |

回滚：整个改动是单个 PR，`git revert` 该合并提交即可完整恢复。

## 10. 留给实现者决定

- 钩子脚本内部实现（函数拆分、提示文案），须满足 §6.4 行为要点
- 各处 `description` / README 的具体措辞（须保持"WPF + Avalonia"语义一致）
- `install.sh` 头注释的改写文字
- PR 描述与提交信息文案（须走 `commit-cc-plugin` skill 与特性分支 → PR 流程）
