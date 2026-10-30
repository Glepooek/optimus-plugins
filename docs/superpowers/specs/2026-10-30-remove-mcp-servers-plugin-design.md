# 删除 旧 MCP 插件 并将 MCP 并入 optimus-frontend 设计

> 日期：2026-10-30
> 状态：待审查
> 类型：插件结构调整（删除一个插件、扩充另一个、收窄 harness 范围）

## 1. 背景与意图

旧 MCP 插件 是一个只有 `.mcp.json` 的"空壳"插件（0 个 skill），为全仓 skill 提供 3 个 MCP server。现状有三个问题：

1. 其中 `avalonia-docs` 与 `mastergo-magic-mcp` 的消费方几乎全是 `optimus-frontend`，却要用户另装一个插件；
2. 为同时服务 Claude/Codex 引入了一整套"单一真源 → 双份配置"的生成机制（`mcp.config.json` + `gen_mcp_config.py` + `config.toml.example` + 测试），维护成本高于收益；
3. 飞书项目 MCP 不再由本仓托管。

本次：删除该插件，把仍需要的两个 MCP 并入 `optimus-frontend`，MCP 不再考虑 Codex，飞书项目 MCP 移除。

## 2. 目标 / 非目标 / 反目标

**目标**
- `plugins/<旧 MCP 插件>/` 整个消失，`optimus-frontend` 获得 `.mcp.json`（仅 `avalonia-docs`、`mastergo-magic-mcp`）
- README 随迁，去掉飞书与 Codex 相关内容
- 仓库内所有现行引用（清单、README、CI、AGENTS.md、`.kiro/steering/`、skill 的 `compatibility`、知识库）同步
- MasterGo 令牌的用户侧环境变量统一为 `MASTERGO_TOKEN`（与三个 mastergo skill 的说明一致）
- 版本号按触发矩阵升级，八项提交门禁通过

**非目标**
- 不改任何 skill 的正文逻辑、触发词、`allowed-tools`
- 不回写历史记录（各 CHANGELOG、`docs/superpowers/` 旧 spec/plan、`docs/todo-list/`、`results.tsv`）
- `.kiro/steering/*.md` 只同步 MCP 相关条目，不顺手修其中其他早已脱节的内容（如不存在的 `optimus-feishu-plugin`）
- 不把飞书项目 MCP 改放到其他插件、不为 `optimus-qa` 的飞书 skill 改写成 CLI 流程

**反目标（即使技术上成功也算失败）**
- 迁移后 `mastergo-magic-mcp` / `avalonia-docs` 在 Claude Code 里加载不出来，或与旧插件同装时重复注册
- `optimus-frontend` 的 Codex 清单被误加 `mcpServers`，让 Codex 侧"悄悄"带上 MCP
- CI 因残留的 `plugins/<旧 MCP 插件>/scripts` 路径而红，或测试目录清单与 AGENTS.md 漂移（本仓"不报错的失效形态"）
- `optimus-qa` 两个飞书 skill 继续声称"本仓库内置 FeishuProjectMcp"（失实描述）

## 3. 可行性结论

可行，技术风险低。依据：

- 插件无 skill、无 hook，唯一的代码是将被删除的生成脚本，不被任何其他模块 import；
- `optimus-frontend` 当前没有 `.mcp.json`，不存在合并冲突；Claude Code 自动加载插件根的 `.mcp.json`，无需在 `plugin.json` 声明；
- `optimus-frontend` 的 Codex 清单（`.codex-plugin/plugin.json`）本就不声明 `mcpServers`，只要不加，Codex 侧自然不会加载 MCP——"不再考虑 Codex"零额外成本；
- CI 里仅两处引用该插件（unittest 目录清单、一条注释），pre-commit 门禁无 MCP 相关检查；
- 唯一的实质影响是**用户侧破坏性变更**（§8），以及 `optimus-qa` 的飞书依赖（§5 第 2 条）。

## 4. 已定决策（用户确认）

| 决策点 | 结论 |
|---|---|
| 删除 旧 MCP 插件 | 是 |
| `.mcp.json` 去向 | 移到 `optimus-frontend`，同时删除 `FeishuProjectMcp` |
| MCP 与 Codex | 不再考虑；README 中 Codex 相关内容全部删除 |
| README | 一并移到 `optimus-frontend` |
| `.kiro/steering/*` | 同步修改（仅 MCP 相关条目） |
| MasterGo 令牌变量名 | 统一使用 `MASTERGO_TOKEN` |
| `optimus-qa` 的飞书 skill | 只改 `compatibility` 说明，改为"需自行安装飞书项目 CLI，并完成授权"；不动 `allowed-tools` 与正文 |

## 5. 我的默认决定（调用方未明确，标注为我的判断）

1. **整体删除生成机制**：`mcp.config.json`、`config.toml.example`、`scripts/gen_mcp_config.py`、`scripts/test_gen_mcp_config.py` 随插件删除，不迁移。理由：它唯一的价值是双 harness 同步；放弃 Codex 后，`.mcp.json` 只剩两个条目，直接手维护。`ci.yml` 的 unittest 目录清单与 `AGENTS.md` 的"9 个测试目录"同步改为 8 个。
2. **`optimus-qa` 的飞书 skill 只改说明**（`optimus-qa-feishu-project-sync`、`optimus-qa-test-report`）：`compatibility` 改为"需自行安装飞书项目 CLI 并完成授权"。⚠️ 已知缺口：两个 skill 的 `allowed-tools` 与正文仍按 `FeishuProjectMcp` 工具调用，并未改写为 CLI 流程——这是用户明确选择的"只改说明"范围，**本次不修，留作后续**，PR 描述需写明。
3. **`optimus-qa-test-design` 的 `compatibility` 微调**：现写"MasterGo 为本仓库内置 mastergo-magic-mcp"，MCP 搬走后该句仍成立但归属变了（用户需装 `optimus-frontend`），改为"由 `optimus-frontend` 插件提供"。
4. **AGENTS.md 加一条约束**：声明 MCP 配置只面向 Claude Code、不做 Codex 镜像，防止后人按"双 harness"惯性补 `config.toml`。写入「重要约束」，一句话。
5. **令牌变量名统一为 `MASTERGO_TOKEN`**：用户只需设置 `MASTERGO_TOKEN`。`@mastergo/magic-mcp` 读取的原生变量名是 `MG_MCP_TOKEN`，故 `.mcp.json` 的 `env` 写成 `"MG_MCP_TOKEN": "${MASTERGO_TOKEN}"`（键是 server 子进程看到的名字，值是用户设置的名字）；`args` 里的占位符 `--token=<MG_MCP_TOKEN>` 在合入后被改为 `--token=<MASTERGO_TOKEN>`（用户确认的有意改动），与用户设置的变量名一致。三个 mastergo skill 的 `compatibility` 已写 `MASTERGO_TOKEN`，无需改这一项。⚠️ 该映射是否让 MasterGo 真正鉴权成功，须在 §9 第 6 条实测。
6. **README 重写而非原样搬**：用 `git mv` 保留历史后再编辑；标题改为 MCP 说明，删「飞书项目 MCP」整节、「单一真源」引言、整个「Codex 使用方式」、飞书 Token 获取、`MCP_USER_TOKEN`；安装命令改为 `optimus-frontend@optimus-plugins`；`enabledMcpjsonServers` 示例去掉 `FeishuProjectMcp`。
7. **`optimus-frontend` 升 Minor**（`2.1.3 → 2.2.0`）：新增 MCP 配置，等同新增用户可见能力（触发矩阵 Minor 列虽未点名 MCP，按"新增 skill/agent/hook/command"同类处理）。

## 6. 文件级改动清单

### 6.1 迁移（`git mv`）

| 源 | 目标 |
|---|---|
| `plugins/<旧 MCP 插件>/.mcp.json` | `plugins/optimus-frontend/.mcp.json`（再删 `FeishuProjectMcp` 条目） |
| `plugins/<旧 MCP 插件>/README.md` | `plugins/optimus-frontend/README.md`（再按 §5 第 6 条重写） |

### 6.2 删除

整个 `plugins/<旧 MCP 插件>/` 目录（含两份 `plugin.json`、`mcp.config.json`、`config.toml.example`、`scripts/`）。

### 6.3 修改

| 文件 | 改动 |
|---|---|
| `.claude-plugin/marketplace.json` | 删 旧 MCP 插件 条目；顶层 `version` `15.0.0 → 16.0.0`；`optimus-frontend` 条目 `description` 若需体现 MCP 则一并补（保持展示文案与 `plugin.json` 一致） |
| `.agents/plugins/marketplace.json` | 删 旧 MCP 插件 条目（无顶层 version） |
| `plugins/optimus-frontend/.claude-plugin/plugin.json`、`.codex-plugin/plugin.json` | 两份 `version` 同升 `2.2.0`；`description` 补"内置 Avalonia Docs 与 MasterGo MCP"。**`.codex-plugin` 不加 `mcpServers`** |
| `plugins/optimus-qa/.claude-plugin/plugin.json`、`.codex-plugin/plugin.json` | 两份同升 `2.0.2`（Patch：改已有 skill 的说明） |
| `plugins/optimus-qa/skills/optimus-qa-feishu-project-sync/SKILL.md` | `compatibility` 换飞书项目 CLI 表述（保留"模式C依赖 Playwright/Midscene"等其余句子）。该 skill 无 `metadata.version`，无需升 |
| `plugins/optimus-qa/skills/optimus-qa-test-report/SKILL.md` | 同上 |
| `plugins/optimus-qa/skills/optimus-qa-test-design/SKILL.md` | `compatibility` 按 §5 第 3 条 |
| `plugins/optimus-frontend/skills/{avalonia,avalonia-code-review,avalonia-wpf-migration}/SKILL.md` | `compatibility` 与故障表中的"旧 MCP 插件"改为"`optimus-frontend` 内置的 Avalonia Docs MCP"；`metadata.version` 各升 Patch：`2.1.2→2.1.3`、`1.0.3→1.0.4`、`1.2.3→1.2.4` |
| `plugins/optimus-frontend/skills/{mastergo-icon-expoter,mastergo-to-wpf-components,mastergo-to-wpf-page}/SKILL.md` | `compatibility` 中"本仓库 plugins/<旧 MCP 插件>/.mcp.json 内置"改为"`optimus-frontend` 插件内置"；`metadata.version` 各升 Patch：`1.1.2→1.1.3`、`1.0.2→1.0.3`、`2.0.3→2.0.4` |
| 上述 6 个 frontend skill 的 `CHANGELOG.md`（若有） | 各补一条 Patch 记录；有无以执行时 `ls` 为准，格式遵 `.claude/rules/doc-conventions.md` |
| `.kiro/steering/plugins.md` | 删 旧 MCP 插件 整节（L89–98）；`optimus-frontend` 节补一行"内置 MCP：Avalonia Docs、MasterGo Magic（`MASTERGO_TOKEN`）" |
| `.kiro/steering/structure.md` | 删插件表 L56 行；L60 命名约定去掉"（MCP 例外：…）"；L74 的 `.mcp.json` 路径改为 `plugins/optimus-frontend/.mcp.json` |
| `.kiro/steering/tech.md` | MCP 服务器表（L23–29）删 `Feishu Project` 行；其余行不动 |
| `README.md`（仓库根） | 删插件列表行（L19）与外部依赖行（L36）；frontend 依赖行改为"自带 Avalonia Docs MCP 与 MasterGo MCP（`MASTERGO_TOKEN`）"；qa 依赖行（L32）的"飞书项目 MCP"改为"飞书项目 CLI（需自行安装并授权）" |
| `.github/workflows/ci.yml` | 删 unittest 清单中 `plugins/<旧 MCP 插件>/scripts`；修正 L225 注释（不再有"无 skills/ 的插件"例外，计数同步核对） |
| `AGENTS.md` | "共 **9 个**测试目录"→8 并删对应命令行；加 §5 第 4 条约束 |
| `.claude/rules/skill-conventions.md` L61 | 示例中的 旧 MCP 插件 改为 `optimus-frontend`（先读上下文，确认只是举例） |
| `knowledge-base/mcp/README.md` L7、L69 | 改指 `optimus-frontend`，去掉"飞书项目"；版本 `1.0.0 → 1.0.1`，`CHANGELOG.md` 补条（走 `knowledge-base-maintain`） |
| `knowledge-base/tools/reference/github-cli.md` L14 | 先读该行：若只是引用已被替换的历史 GitHub MCP 则不动；若断言现状则修正（并按其所属领域规则升版） |

### 6.4 不改（有意）

`docs/superpowers/` 旧文件、`docs/todo-list/*`、`.claude/skills/commit-cc-plugin/CHANGELOG.md`、`.claude/skills/darwin-skill/results.tsv`。

## 7. 版本号依据（按 AGENTS.md 触发矩阵）

| 层级 | 变化 | 依据 |
|---|---|---|
| `optimus-frontend` 两份 `plugin.json` | `2.1.3 → 2.2.0` 同值 | 新增 MCP → Minor |
| `optimus-qa` 两份 `plugin.json` | `2.0.1 → 2.0.2` 同值 | 修改已有 skill 说明 → Patch |
| marketplace 顶层 | `15.0.0 → 16.0.0` | 删除插件 → Major，MINOR/PATCH 归零 |
| 6 个 frontend skill 的 `metadata.version` | 各升 Patch | 改动落在 `skills/<name>/` 内 |
| 3 个 qa skill | 无 `metadata.version`，不升 | 该字段不存在，不凭空新增 |
| `knowledge-base/mcp` | `1.0.0 → 1.0.1` | 修订已有条目文字 |

⚠️ darwin 评分门禁只在 skill 升 Minor/Major 时触发；本次 skill 全是 Patch 且只改 frontmatter 的 `compatibility`，不触发。

## 8. 用户侧影响与风险

| 风险 | 缓解 |
|---|---|
| 已装 旧 MCP 插件 的用户升级后该插件消失；若新旧同装则 `avalonia-docs` 等重复注册 | 破坏性变更，故 marketplace 升 Major。新 README 加"从旧插件迁移"小节：先卸载旧插件，再装 `optimus-frontend` |
| MCP 工具名带插件命名空间，从 旧 MCP 插件 换成 `optimus-frontend` 后，用户手写的 `permissions.allow` / `enabledMcpjsonServers` 失效 | 迁移小节提醒更新；**命名空间的确切形态待 `--plugin-dir` 实测确认**，不凭记忆写进 README |
| 不装 `optimus-frontend` 的人（如只用 `optimus-qa` 的设计稿一致性）拿不到 MasterGo MCP | §5 第 3 条在 qa skill 说明里点明依赖 |
| 旧用户已设置的 `MG_MCP_TOKEN` 不再被读取 | 迁移小节明确：改设 `MASTERGO_TOKEN` |
| 飞书项目 MCP 用户失去托管配置 | 非目标；`optimus-qa` skill 说明已指向自行安装 CLI |
| `optimus-qa` 飞书 skill 说明与实际调用不一致 | §5 第 2 条已声明为已知缺口，PR 描述写明 |

回滚：单 PR，`git revert` 合并提交即可完整恢复。

## 9. 验证标准

1. `sh .githooks/pre-commit` 退出码 0
2. 8 个 unittest 目录逐个通过（见 AGENTS.md 清单，已删 mcp-servers 一项）；`check_index.py`、`check_refs.py` 通过
3. `plugins/<旧 MCP 插件>/` 不存在；`plugins/optimus-frontend/.mcp.json` 含且仅含 `avalonia-docs`、`mastergo-magic-mcp`；`.codex-plugin/plugin.json` 无 `mcpServers`
4. `grep -rIn "旧 MCP 插件"` 在现行文件无残留；允许残留仅限 §6.4 所列与本 spec/plan
5. `grep -rIn "MG_MCP_TOKEN"` 现行文件中仅剩 `plugins/optimus-frontend/.mcp.json` 的 `env` 键一处（`args` 已改为 `<MASTERGO_TOKEN>`）及 README 迁移小节的说明；`.kiro/steering/` 无 旧 MCP 插件 与 `Feishu Project` 残留
5b. `grep -rIn "FeishuProjectMcp\|MCP_USER_TOKEN"`：`allowed-tools` 中的 `FeishuProjectMcp` 按 §5 第 2 条保留，其余现行文件无残留
6. `test-locally`：`--plugin-dir` 加载本仓，`/mcp` 能看到 frontend 提供的两个 server，且不再出现 `FeishuProjectMcp`；记录实测的命名空间并回填 README 迁移小节。另在仅设置 `MASTERGO_TOKEN`（不设 `MG_MCP_TOKEN`）的环境下确认 MasterGo server 状态为已连接——需有效令牌，由用户协助验证
7. PR 上六个必需检查全绿（`plugin-validate`、`new-skill-eval-case`、`actionlint` 无本地等价，只能在 PR 验证）

## 10. 留给实现者决定

- README 具体措辞与"迁移"小节排版
- 各 `compatibility` 的具体措辞（须保持 §5 第 2、3 条的语义）
- PR 描述与提交信息（走 `commit-cc-plugin` 与特性分支 → PR 流程）
