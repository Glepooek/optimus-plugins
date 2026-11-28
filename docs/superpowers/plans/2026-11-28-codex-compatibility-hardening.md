# Codex 兼容性加固 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Codex 侧宣称的每个插件组件都有静态路径证据和使用侧可见性证据，并消除发布 skill 对 Claude 专属目录、字段与工具名的依赖。

**Architecture:** 分两个原子 PR。PR 1（Phase 1，能力真实性）：扩展 `check_plugin_versions.py` 增加 Codex manifest 契约检查 + 机器可读排除表，修 3 份 Codex manifest，autopilot 改能力判定，CI `plugin-validate` 追加零凭据 Codex 冒烟。PR 2（Phase 2，可移植性）：新增 `check_skill_portability.py`，用随包 helper 脚本解析配置/缓存目录，清理 11 个 skill 的非允许 frontmatter 字段。

**Tech Stack:** Python 3（仅标准库 + `unittest`，本机无 pytest）、bash、GitHub Actions、Codex CLI 0.172.0（npm 包 `@openai/codex`）。

**Spec:** `docs/superpowers/specs/2026-11-28-codex-compatibility-hardening-design.md`（另见两份审查报告 `docs/superpowers/reports/2026-11-28-codex-compatibility-hardening-review{,-2}.md`）

## Global Constraints

- Codex CLI 版本固定 `0.172.0`，禁止 `latest`。
- CI 不配置 OpenAI API key，不运行 `codex exec` 或任何模型请求，不启动 MCP server。
- 不新增、不改名 required job；六个 job 名（`gates-hooks`、`gates-tests`、`gates-data`、`plugin-validate`、`new-skill-eval-case`、`actionlint`）不变。
- `SKILL.md` 是唯一正文真源，不为 Codex 复制正文。
- 发布 skill 顶层 frontmatter 只允许：`name` / `description` / `license` / `compatibility` / `metadata` / `allowed-tools`。
- 署名统一 `metadata.author: desktop client team`。
- 配置/缓存目录优先级（spec §3.3，逐字）：① `OPTIMUS_CONFIG_DIR` / `OPTIMUS_CACHE_DIR`；② Windows 配置 `%APPDATA%\optimus`、缓存 `%LOCALAPPDATA%\optimus\cache`；POSIX 配置 `${XDG_CONFIG_HOME:-$HOME/.config}/optimus`、缓存 `${XDG_CACHE_HOME:-$HOME/.cache}/optimus`；③ 旧 `~/.claude/...` 只读回退。新写入只落 ① 或 ②，不得写入已安装插件目录。
- 例外标记固定文本：`codex-portability: allow-harness-path reason=<非空理由>`；一条标记豁免所在行或紧随其后一行的全部命中；YAML/bash/PowerShell 用 `#` 注释写在前一行，Markdown 正文/表格用同行 `<!-- ... -->`。
- 门禁口径：PR 1 后为「6 个脚本 / 9 个逻辑检查」；PR 2 后为「7 个脚本 / 10 个逻辑检查」。
- 版本：两份 `plugin.json` 同一提交内同值；Patch 不触发 darwin-skill 门禁；本计划所有 skill 改动均为 Patch（缺版本者建立 `1.0.0` 基线）。
- 每个被修改且缺 `CHANGELOG.md` 的 skill，新建 `CHANGELOG.md`，只写本次一条 `## [x.y.z] - <提交日>`，不伪造历史（doc-conventions：每个 skill 目录必须有 CHANGELOG）。
- 提交一律走 `commit-cc-plugin` skill（AGENTS.md 硬约定）；分支名 `<type>/<简短描述>`，`type` 与 commit type 一致。
- 编辑 Markdown 只改语义相关内容，不做空行/缩进/表格对齐等纯格式化改动。

## Review Focus

1. **路径含空格**：`OPTIMUS_CACHE_DIR="C:/Users/a b/cache"` 时，helper 输出的 JSON 路径完整保留空格，`run.sh` 的 venv 路径被正确引用 → 测试落在 Task 7、Task 8。
2. **环境变量给相对路径**：`OPTIMUS_CACHE_DIR=rel/cache` 时 helper 返回基于当前工作目录的**绝对**路径，而不是原样返回相对串 → 测试落在 Task 7。
3. **新旧配置并存**：`<optimus-config-dir>/jenkins-config.yaml` 与 `~/.claude/jenkins-config.yaml` 同时存在时取新路径；只有旧路径时仍能读到并提示迁移，且绝不向旧路径写入 → 测试落在 Task 8。
4. **`CODEX_HOME` 未设置**：冒烟脚本在 `CODEX_HOME` 缺失或指向 `~/.codex` 时拒绝运行，防止污染开发者本机 Codex 配置 → 测试落在 Task 4。
5. **CRLF 行尾的 SKILL.md**：Windows 检出的 `\r\n` frontmatter 仍能被 portability gate 正确解析键名与行号 → 测试落在 Task 6。

---

## File Structure

| 文件 | 职责 | 任务 |
|---|---|---|
| `.githooks/check_plugin_versions.py` | 既有第 1 项（版本同值）+ 新第 9 项（Codex manifest 契约），同一脚本、两段输出 | T1、T2 |
| `.githooks/codex_component_exclusions.json` | Claude-only 组件的唯一登记处 | T2 |
| `.githooks/test_check_plugin_versions.py` | 两项的单测 | T1、T2 |
| `plugins/optimus-frontend/.codex-mcp.json` | Codex 专用 MCP 配置（仅两个 HTTP server） | T2 |
| `plugins/{optimus-frontend,optimus-backend,optimus-devops}/.codex-plugin/plugin.json` | 组件声明与诚实描述 | T2 |
| `plugins/optimus-devops/skills/dotnet-diagnose-autopilot/SKILL.md` | 前置校验改能力判定 | T3 |
| `.githooks/codex_smoke.py` + `test_codex_smoke.py` | CI 专用 Codex 冒烟（**不是** catalog 门禁） | T4 |
| `.github/workflows/ci.yml` | `plugin-validate` 追加 Codex 步骤 | T4 |
| `knowledge-base/tools/reference/codex-cli.md` | Codex CLI 工具记录 | T5 |
| `.githooks/check_skill_portability.py` + test | 第 10 项 | T6、T11 |
| `plugins/optimus-backend/skills/optimus-backend-api-connect/scripts/optimus_dirs.py` + test | 目录解析 helper（backend 插件内副本） | T7 |
| `plugins/optimus-devops/skills/jenkins-build/scripts/optimus_dirs.py` + test | 同一 helper 的 devops 插件内副本 | T8 |

⚠️ 两份 `optimus_dirs.py` 是**刻意重复**：插件安装单元是 `plugins/<name>/`，跨插件共享会被第 8 项（自包含）拦下。两份内容必须逐字相同，T8 的测试断言这一点。

⚠️ 测试只能放在 `.githooks/`、`.claude/skills/*/scripts/`、`plugins/*/skills/*/scripts/` 三类位置，否则 `TestRealRepositoryCoverage` 变红。因此 helper 都放进 skill 的 `scripts/`。

---

# PR 1 — Phase 1：能力真实性

分支：`feat/codex-capability-truthfulness`（从最新 `master` 切出；工作区现有未跟踪的 spec 与两份审查报告随本 PR 一并提交）。

### Task 1: Codex manifest 契约检查（第 9 项）

**Files:**
- Modify: `.githooks/check_plugin_versions.py`（新增函数，`main()` 追加第二段）
- Test: `.githooks/test_check_plugin_versions.py`（新增 `TestCodexContract` 类）

**Interfaces:**
- Produces:
  - `EXCLUSIONS_REL = ".githooks/codex_component_exclusions.json"`
  - `load_exclusions(repo_root: Path) -> tuple[list[dict], list[str]]`：返回 (条目, 问题)；文件缺失视为空表；每条必须有非空 `plugin`/`kind`/`id`/`path`/`reason`，`kind ∈ {"agent","hook","mcp-server"}`。
  - `component_inventory(plugin_dir: Path) -> tuple[set[tuple[str, str, str]], list[str]]`：返回 ({(kind, id, path)}, 问题)。`mcp-server` 取 `.mcp.json` 顶层 `mcpServers` 的键，path=`.mcp.json`；`agent` 取 `agents/*.md` frontmatter 的 `name`，path=`agents/<file>.md`；`hook` 取 `hooks/hooks.json` 顶层 `hooks` 的键（事件名），path=`hooks/hooks.json`。`.mcp.json` 不可解析或缺 `mcpServers` 记为问题、不抛异常。
  - `codex_declared(plugin_dir: Path, manifest: dict) -> tuple[set[tuple[str, str, str]], list[str]]`：解析 Codex manifest 的 `skills`（目录）、`agents`（文件列表）、`mcpServers`（文件）；每个路径必须存在、类型正确、`resolve()` 后位于插件目录内。声明的 MCP 文件内的 server id 以 `("mcp-server", id, ".mcp.json")` 形式计入（按 Claude 侧 id 比对，path 统一记 `.mcp.json`）。出现 `hooks` 键即报问题：「Codex CLI 0.172.0 的 plugin_hooks 已 removed，Codex manifest 不得声明 hooks」。
  - `check_codex_contract(repo_root: Path) -> list[str]`：汇总下列规则的全部问题。
- 问题消息格式：`[<plugin>] <描述>`，测试按关键子串断言。

规则（逐条对应测试）：
1. Codex manifest 的 `name` = 插件目录名；`.agents/plugins/marketplace.json` 中 `source.source == "local"` 的条目名集合 = `plugins/*/.codex-plugin/plugin.json` 所在插件名集合。
2. inventory 中每个 (kind, id) 必须被 Codex 声明覆盖或被排除表覆盖。
3. 排除表条目对应的组件必须真实存在于 inventory（否则「陈旧排除项」）；且不得同时被 Codex 声明（否则「排除项与 Codex 声明冲突」）。
4. 路径存在性、类型、越界（规则在 `codex_declared` 内）。

- [ ] **Step 1: 写失败测试**

在测试文件新增夹具 `make_codex_plugin(root, name, codex_extra=None, mcp=None, agents=None, hooks=None)`：建 `.claude-plugin/plugin.json` 与 `.codex-plugin/plugin.json`（同版本 `1.0.0`，Codex 带 `"skills": "./skills/"` 并建空 `skills/`），`mcp` 为 dict 时写 `.mcp.json`，`agents` 为名字列表时写 `agents/<n>.md`（frontmatter `name: <n>`），`hooks` 为事件名列表时写 `hooks/hooks.json`。另写 `write_marketplace(root, names)` 与 `write_exclusions(root, entries)`。测试：

```python
class TestCodexContract(unittest.TestCase):
    def test_minimal_plugin_passes(self): ...            # 无组件、marketplace 一致 → []
    def test_codex_name_mismatch(self): ...              # codex name="other" → 含 "name"
    def test_marketplace_missing_plugin(self): ...       # marketplace 少一个 → 含 "marketplace"
    def test_marketplace_extra_plugin(self): ...         # marketplace 多一个不存在的 → 含 "marketplace"
    def test_declared_mcp_file_missing(self): ...        # mcpServers="./nope.json" → 含 "nope.json"
    def test_declared_path_escapes_plugin(self): ...     # mcpServers="../x.json" → 含 "越界"
    def test_codex_hooks_key_rejected(self): ...         # codex_extra={"hooks":"./hooks/hooks.json"} → 含 "plugin_hooks"
    def test_mcp_server_uncovered(self): ...             # .mcp.json 有 a,b；codex 文件只含 a；无排除 → 含 "b"
    def test_mcp_server_excluded_passes(self): ...       # 同上 + 排除 b → []
    def test_agent_uncovered(self): ...                  # agents=["x"]，无声明无排除 → 含 "x"
    def test_hook_event_requires_exclusion(self): ...    # hooks=["PreToolUse"] 无排除 → 含 "PreToolUse"
    def test_stale_exclusion(self): ...                  # 排除 agent "ghost"，不存在 → 含 "陈旧"
    def test_exclusion_conflicts_with_declaration(self): ...  # agent 既声明又排除 → 含 "冲突"
    def test_exclusion_missing_reason(self): ...         # reason="" → 含 "reason"
    def test_malformed_mcp_json_reported_not_raised(self): ...  # .mcp.json 写 "{" → 含 ".mcp.json"，不抛异常
```

每个测试只断言 `check_codex_contract(self.root)` 的返回（空列表或某条包含给定子串）。

- [ ] **Step 2: 运行确认失败**

Run: `python -m unittest discover -s .githooks -p "test_check_plugin_versions.py" -v`
Expected: `ImportError`/`AttributeError`：`check_codex_contract` 未定义。

- [ ] **Step 3: 实现上述五个符号**

路径越界判定用 `(plugin_dir / rel).resolve().relative_to(plugin_dir.resolve())` 捕获 `ValueError`。agent frontmatter 只需取首个 `---` 块内 `name:` 行，不引入 YAML 依赖。`main()` 改为依次打印两段：既有「插件版本号校验」段不变；新增「Codex manifest 契约校验」段，通过时打印 `Codex manifest 契约校验通过`；任一段有问题则返回 1。模块 docstring 末尾补一段说明本文件承载第 1、9 两项及为何不拆脚本（复用 manifest 加载，避免牵动 catalog 引用）。

- [ ] **Step 4: 运行确认通过**

Run: `python -m unittest discover -s .githooks -p "test_check_plugin_versions.py" -v`
Expected: 既有 18 个 + 新 15 个全部 PASS。

此时**不要**跑真实仓库：真实仓库在 Task 2 之前必然不通过（frontend 的 `.mcp.json` 未声明、hooks 未排除），这是预期。

- [ ] **Step 5: 提交**

用 `commit-cc-plugin` 提交 `.githooks/check_plugin_versions.py`、`.githooks/test_check_plugin_versions.py`，message：`feat(repo): add Codex manifest contract check`。

### Task 2: Codex manifest 修正 + 排除表 + 登记第 9 项

**Files:**
- Create: `plugins/optimus-frontend/.codex-mcp.json`
- Create: `.githooks/codex_component_exclusions.json`
- Modify: `plugins/{optimus-frontend,optimus-backend,optimus-devops}/.codex-plugin/plugin.json`、对应 `.claude-plugin/plugin.json`（仅 `version`）
- Modify: `.githooks/repository_gates.py`（检查项 1 注释旁补第 9 项说明与计数口径）、`.githooks/README.md`（检查项表加第 9 行、计数改「9 个逻辑检查 / 6 个脚本」）、`AGENTS.md`（「八项提交门禁」等计数处）
- Test: `.githooks/test_check_plugin_versions.py`（新增 `TestRealRepository.test_real_repository_passes`）

**Interfaces:**
- Consumes: Task 1 的 `check_codex_contract`、`check_all`。
- Produces: 排除表文件，格式 `{"exclusions": [{"plugin", "kind", "id", "path", "reason"}, ...]}`；Task 4 从中读取 `kind == "mcp-server"` 的 id 作为「不得出现」名单。

- [ ] **Step 1: 写失败测试**

```python
class TestRealRepository(unittest.TestCase):
    def test_real_repository_passes(self):
        root = pathlib.Path(__file__).resolve().parent.parent
        self.assertEqual(check_all(root), [])
        self.assertEqual(check_codex_contract(root), [])
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m unittest discover -s .githooks -p "test_check_plugin_versions.py" -v`
Expected: FAIL，问题列表含 `mastergo-magic-mcp`、`PreToolUse`、`dotnet-diagnose`。

- [ ] **Step 3: 新建 `.codex-mcp.json`**

内容为 `plugins/optimus-frontend/.mcp.json` 去掉 `mastergo-magic-mcp` 后的结果：顶层 `mcpServers` 仅含 `avalonia-docs`（`type: http`，`url: https://docs-mcp.avaloniaui.net/mcp`）与 `microsoft-learn`（`type: http`，`url: https://learn.microsoft.com/api/mcp`），值逐字复制。`.mcp.json` 本身不动。

- [ ] **Step 4: 新建排除表，恰好 7 条**

| plugin | kind | id | path | reason |
|---|---|---|---|---|
| optimus-devops | agent | dotnet-diagnose | agents/dotnet-diagnose.md | Codex CLI 0.172.0 未注册插件 agent（含 multi_agent_v2），见 spec §4.2 |
| optimus-frontend | mcp-server | mastergo-magic-mcp | .mcp.json | Codex 不展开 ${MASTERGO_TOKEN}，token 无法传入，见 spec §4.1 |
| optimus-frontend | hook | PreToolUse | hooks/hooks.json | Codex CLI 0.172.0 的 plugin_hooks 已 removed，见 spec §4.3 |
| optimus-backend | hook | PreToolUse | hooks/hooks.json | 同上 |
| optimus-devops | hook | SessionStart | hooks/hooks.json | 同上 |
| optimus-devops | hook | PreToolUse | hooks/hooks.json | 同上 |
| optimus-devops | hook | Notification | hooks/hooks.json | 同上 |

（`reason` 字段写完整句子，不写「同上」。）

- [ ] **Step 5: 改三份 Codex manifest**

- frontend：加 `"mcpServers": "./.codex-mcp.json"`；`description` 与 `interface.longDescription` 改为：`桌面前端开发（WPF + Avalonia）：MasterGo 设计稿转页面与组件库、SVG 转 XAML、XAML/AXAML 代码审查、WPF 迁移 Avalonia 与 Linux deb 发布。Codex 侧内置 Avalonia Docs 与 Microsoft Learn MCP；MasterGo MCP 与 PreToolUse 提交门禁 Hook 仅 Claude Code 可用`；`interface.capabilities` 改为 `["Skills", "MCP"]`。
- backend：`description`/`longDescription` 改为 `后端开发：需求到实现全流程、公司服务 API 对接、C# 代码审查。PreToolUse 提交门禁 Hook 仅 Claude Code 可用`。
- devops：**不加** `agents`；`description`/`longDescription` 改为 `DevOps：Jenkins 构建、项目分析、周报转写、Git 提交信息审查、skill 链接同步、.NET 取证输出解读与根因定位。dotnet-diagnose agent 与 SessionStart/Notification Hook 仅 Claude Code 可用，Codex 侧直接使用 dotnet-diagnose-triage skill`。
- 版本：frontend `3.1.2 → 3.2.0`（Minor，新增 Codex MCP）；backend `2.0.3 → 2.0.4`；devops `2.0.11 → 2.0.12`（Task 3 的 skill 改动与本次同 PR，共用这一次 Patch）。两份 `plugin.json` 同值。若实施时 `master` 上的值已变化，按同样幅度从当时的值起算。
- Claude 侧 `plugin.json` 只改 `version`，描述不动。

- [ ] **Step 6: 登记第 9 项**

`.githooks/README.md` 检查项表追加：`| 9 | Codex manifest 组件声明与真实组件一致（含 Claude-only 排除表） | Codex 安装成功但组件缺失、越界或被误报为可用——codex plugin add 对此不报错 |`；标题与正文计数改为「9 个逻辑检查 / 6 个脚本」，说明 `check_plugin_versions.py` 覆盖第 1、9 项。`repository_gates.py` 的 docstring 计数与检查项 1 的注释同步。`AGENTS.md` 中「八项提交门禁（8 个逻辑检查，由 6 个脚本实现）」「覆盖全部八项」「八项提交门禁与全仓单测入口」三处改成九项。用 `grep -rn "八项\|8 个逻辑" AGENTS.md .githooks` 确认无遗漏（`docs/` 与 `.claude/skills/sync-cc-tips` 下的命中是历史记录，不改）。

- [ ] **Step 7: 运行确认通过**

Run: `python -m unittest discover -s .githooks -p "test_check_plugin_versions.py" -v` → 全部 PASS
Run: `python .githooks/run_repository_gates.py` → 退出码 0，输出含 `Codex manifest 契约校验通过`
Run: `python .githooks/run_unit_tests.py` → 全部 PASS（`test_run_repository_gates` 仍断言 `len(GATES) == 6`，本任务不改它）

- [ ] **Step 8: 提交**

用 `commit-cc-plugin` 提交上述文件，message：`feat(repo): ship verified Codex MCP servers and register Claude-only components`。

### Task 3: autopilot 前置校验改为能力判定

**Files:**
- Modify: `plugins/optimus-devops/skills/dotnet-diagnose-autopilot/SKILL.md`（frontmatter 第 3、5、8 行；「执行前置校验」表第 1 行，约第 37 行）
- Modify: `plugins/optimus-devops/skills/dotnet-diagnose-autopilot/CHANGELOG.md`
- Modify: `plugins/optimus-devops/skills/dotnet-diagnose-autopilot/README.md`（仅当其中描述了依赖或适用 harness 时，同步一句「agent 仅 Claude Code 可用」）

**Interfaces:**
- Consumes / Produces：无代码接口。该任务是文档行为契约，验证靠人工验收（spec §13.3），不在 CI。

- [ ] **Step 1: 改 frontmatter**

- `metadata.version`：`1.0.4 → 1.0.5`。
- `compatibility` 改为：`需要 Claude Code 且已安装 optimus-devops 的 dotnet-diagnose agent 与 dotnet-diagnose-triage skill（本 skill 经 Task 工具调度前者，不直接读取判据）。dotnet-diagnose agent 当前仅 Claude Code 可用；Codex 中请直接使用 optimus-devops:dotnet-diagnose-triage。`
- `description`：在「调度 dotnet-diagnose agent 完成分析」之后插入「（该 agent 仅 Claude Code 可用；Codex 下请直接用 dotnet-diagnose-triage）」，其余不动。

- [ ] **Step 2: 改前置校验表第 1 行**

「检查内容」列改为：`optimus-devops:dotnet-diagnose` 是否作为**具名 agent** 出现在当前可调用 agent 列表中；通用子 agent、`spawn_agent` 默认角色、或任何「转发给 @optimus-devops:dotnet-diagnose」但该 agent 未注册的调用，均**不满足**本项。

「不满足时」列改为：硬约束，在派发任何子任务之前终止，原样保留用户素材，并回复：「未检测到具名 agent optimus-devops:dotnet-diagnose（当前仅 Claude Code 提供）。本 skill 的双次盲态复核无法执行；请直接使用 optimus-devops:dotnet-diagnose-triage 对同一份素材做单次分析。」

表格之后紧接一行：「⚠️ 禁止用通用子 agent 冒充 dotnet-diagnose：它拿不到 agent 定义，返回的是自行分析却会被当作 agent 原文解析，单次分析因此被包装成两次独立交叉验证。」

- [ ] **Step 3: 写 CHANGELOG**

```markdown
## [1.0.5] - <提交日>

### Fixed
- 前置校验第 1 项改为「具名 agent 是否可用」的能力判定，明确通用子 agent / spawn_agent 不满足依赖，避免在 Codex 下以单次分析冒充双次盲态复核
- compatibility 与 description 注明 dotnet-diagnose agent 仅 Claude Code 可用，并给出 dotnet-diagnose-triage 回退入口
```

- [ ] **Step 4: 验证**

Run: `python .githooks/run_repository_gates.py` → 退出码 0。
Run: `grep -n "具名 agent" plugins/optimus-devops/skills/dotnet-diagnose-autopilot/SKILL.md` → 至少 2 处命中。

- [ ] **Step 5: 提交**

用 `commit-cc-plugin` 提交，message：`fix(optimus-devops): gate autopilot on a named dotnet-diagnose agent`。

### Task 4: CI Codex 冒烟

**Files:**
- Create: `.githooks/codex_smoke.py`
- Create: `.githooks/test_codex_smoke.py`
- Modify: `.github/workflows/ci.yml`（`plugin-validate` job 末尾追加 3 个 step）
- Modify: `.githooks/README.md`（新增一小节：该脚本是 **CI 专用冒烟，不在 catalog 内，不计入门禁项数**）

**Interfaces:**
- Consumes: `.agents/plugins/marketplace.json`、`plugins/*/skills/*/SKILL.md`、`plugins/optimus-frontend/.codex-mcp.json`、Task 2 的排除表。
- Produces（全部在 `codex_smoke.py`）：
  - `local_plugin_names(repo_root: Path) -> list[str]`：marketplace 中 `source.source == "local"` 的条目名，保持文件顺序。
  - `expected_skill_ids(repo_root: Path) -> set[str]`：`"<plugin>:<frontmatter name>"`。
  - `rendered_text(prompt_input_stdout: str) -> str`：`json.loads` 后递归收集所有字符串值，以 `"\n"` 连接。原始输出里的换行是 JSON 转义的 `\n`，必须先解码再匹配。
  - `missing_skill_ids(rendered: str, expected: set[str]) -> list[str]`：某 id 当且仅当 `"\n- " + id + ": "` 出现在 `rendered` 中才算可见；返回排序后的缺失列表。
  - `mcp_problems(mcp_list_stdout: str, expected: set[str], forbidden: set[str]) -> list[str]`：解析 `codex mcp list --json`（顶层数组，元素取 `name`）；缺 expected 或出现 forbidden 各报一条。
  - `require_isolated_codex_home(env: Mapping[str, str]) -> str | None`：`CODEX_HOME` 未设置、为空、或 `resolve()` 后等于 `Path.home() / ".codex"` 时返回错误消息，否则 `None`。
  - `main(argv: list[str]) -> int`：`argv[1]` 为仓库根。顺序：隔离检查 → `codex plugin marketplace add <root> --json` → 逐插件 `codex plugin add <p>@optimus-plugins --json`（单个失败继续）→ `codex plugin list --json` 断言全部已安装且 `enabled` → `codex mcp list --json` → `codex debug prompt-input x`。期望 MCP = `.codex-mcp.json` 的 server id；禁止 MCP = 排除表中 `kind == "mcp-server"` 的 id。全部跑完后按 `[plugin-install]`、`[skill-visibility]`、`[mcp-enumeration]` 分类打印失败名单，有任一失败返回 1；否则打印 `Codex 冒烟通过：<n> 插件 / <m> skill / <k> MCP` 并返回 0。子进程用 `subprocess.run(..., capture_output=True, text=True, encoding="utf-8")`；Windows 下 `codex` 是 `.cmd` 包装，用 `shutil.which("codex")` 取可执行路径。

- [ ] **Step 1: 写失败测试**

```python
class TestCodexSmoke(unittest.TestCase):
    def test_rendered_text_decodes_escaped_newlines(self):
        out = json.dumps([{"content": [{"text": "x\n- p:a: desc"}]}])
        self.assertIn("\n- p:a: desc", rendered_text(out))

    def test_missing_skill_detected(self):
        self.assertEqual(missing_skill_ids("\n- p:a: d", {"p:a", "p:b"}), ["p:b"])

    def test_mention_in_other_description_does_not_count(self):
        self.assertEqual(missing_skill_ids("\n- p:a: 先调用 p:b 再继续", {"p:a", "p:b"}), ["p:b"])

    def test_mcp_expected_and_forbidden(self):
        out = json.dumps([{"name": "avalonia-docs"}, {"name": "mastergo-magic-mcp"}])
        problems = mcp_problems(out, {"avalonia-docs", "microsoft-learn"}, {"mastergo-magic-mcp"})
        self.assertTrue(any("microsoft-learn" in p for p in problems))
        self.assertTrue(any("mastergo-magic-mcp" in p for p in problems))

    def test_codex_home_unset_refused(self):          # Review Focus 4
        self.assertIsNotNone(require_isolated_codex_home({}))

    def test_codex_home_user_default_refused(self):   # Review Focus 4
        self.assertIsNotNone(require_isolated_codex_home({"CODEX_HOME": str(pathlib.Path.home() / ".codex")}))

    def test_codex_home_temp_accepted(self):
        self.assertIsNone(require_isolated_codex_home({"CODEX_HOME": tempfile.mkdtemp()}))

    def test_expected_skill_ids_real_repo(self):
        root = pathlib.Path(__file__).resolve().parent.parent
        ids = expected_skill_ids(root)
        self.assertEqual(len(ids), len(list(root.glob("plugins/*/skills/*/SKILL.md"))))
        self.assertIn("optimus-devops:dotnet-diagnose-triage", ids)

    def test_local_plugin_names_real_repo(self):
        root = pathlib.Path(__file__).resolve().parent.parent
        self.assertEqual(len(local_plugin_names(root)), 9)
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m unittest discover -s .githooks -p "test_codex_smoke.py" -v`
Expected: `ModuleNotFoundError: No module named 'codex_smoke'`。

- [ ] **Step 3: 实现 `codex_smoke.py`**

签名见 Interfaces。模块 docstring 写明三点：CI 专用；不进 `repository_gates.py`（要联网装 CLI，违反「门禁只读工作树」约定）；`debug prompt-input` 是调试面，CLI 升级时先复核 `rendered_text` 与列表项前缀。

- [ ] **Step 4: 运行确认通过**

Run: `python -m unittest discover -s .githooks -p "test_codex_smoke.py" -v` → 9 个 PASS
Run: `python .githooks/run_unit_tests.py` → 全部 PASS

- [ ] **Step 5: 本机端到端（Windows，已装 0.172.0）**

Run（Git Bash）：`CODEX_HOME="$(mktemp -d)/codex-home" python .githooks/codex_smoke.py .`
Expected: 退出码 0，输出 `Codex 冒烟通过：9 插件 / 54 skill / 2 MCP`。

反向验证：临时从 `.codex-mcp.json` 删掉 `microsoft-learn`，用新的临时 `CODEX_HOME` 重跑 → 退出码 1，`[mcp-enumeration]` 名单含 `microsoft-learn`。用 `git checkout -- plugins/optimus-frontend/.codex-mcp.json` 还原（文件此时已在 Task 2 提交）。

- [ ] **Step 6: 改 `ci.yml`**

在 `plugin-validate` 的「各插件 skills 目录的严格校验」step 之后追加：

```yaml
      - uses: actions/setup-python@v7
        with:
          python-version: '3.x'
      - name: Codex CLI 安装（固定 0.172.0）
        run: |
          for i in 1 2 3; do
            npm install -g @openai/codex@0.172.0 && codex --version && exit 0
            echo "[cli-install] 第 $i 次失败，10 秒后重试"; sleep 10
          done
          echo "[cli-install] 三次均失败"; exit 1
      - name: Codex 安装冒烟（零凭据，不调用模型）
        env:
          CODEX_HOME: ${{ runner.temp }}/codex-home
        run: python .githooks/codex_smoke.py .
```

上方加注释块，写清三件事：为什么挂在 `plugin-validate` 而不新开 job（ruleset 的六个 job 名不变）；为什么固定版本（`prompt-input` 格式不属公开契约）；`prompt-input` 只在 Windows 实测过，若首个 PR 在 ubuntu 上于 `[skill-visibility]` 失败，按 spec §7.2 把该断言移到非 required 的 Windows job，不得删除。

- [ ] **Step 7: 验证 workflow 语法**

本机无 actionlint。Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml', encoding='utf-8'))"`；无 PyYAML 时跳过，并在 PR 描述中注明依赖 PR 上的 `actionlint` job。

- [ ] **Step 8: 提交**

用 `commit-cc-plugin` 提交，message：`ci(repo): add zero-credential Codex install smoke to plugin-validate`。

### Task 5: 双 harness 判据文档、Codex CLI 工具记录、开 PR 1

**Files:**
- Modify: `AGENTS.md`（「必要差异」表的 Hooks 行；「重要约束」中「MCP 配置只面向 Claude Code」一条）
- Modify: `README.md`（仓库根）
- Create: `knowledge-base/tools/reference/codex-cli.md`，并更新 `knowledge-base/tools/index.jsonl`、`knowledge-base/tools/CHANGELOG.md`（经 `record-tools` skill）

**Interfaces:**
- Consumes: Task 2 的排除表（文档引用它作为 Claude-only 唯一登记处）、Task 4 的 `codex_smoke.py`（文档引用为 CI 冒烟入口）。
- Produces: 无代码接口。

- [ ] **Step 1: 改 `AGENTS.md`**

- 「必要差异」表 Hooks 行的 Codex 列改为：`Claude Hook 不随 Codex 插件生效；Codex CLI 0.172.0 的 plugin_hooks 已 removed，用户级 hooks 特性不等于插件级分发面`。
- 表中新增一行「插件组件」：Claude 列 `.claude-plugin/plugin.json` 声明 `agents`，`.mcp.json` 自动加载；Codex 列 `.codex-plugin/plugin.json` 显式声明 `mcpServers`（frontend 用 `.codex-mcp.json`）；Claude-only 组件登记在 `.githooks/codex_component_exclusions.json`。
- 「重要约束」中「MCP 配置只面向 Claude Code……Codex 清单不声明 `mcpServers`」整条替换为：`MCP/agent 按 harness 实际能力分别声明：只有路径校验（第 9 项）与使用侧冒烟（CI 的 codex_smoke.py）都通过的组件才可写进 Codex manifest；其余登记进排除表并写明理由。展示文案必须与该 harness 实际分发的组件一致。`
- 「本地测试」节在三项本地检查之后补一句：Codex 冒烟本地可跑 `CODEX_HOME=<临时目录> python .githooks/codex_smoke.py .`（需已装 Codex CLI 0.172.0），它不属于门禁。

- [ ] **Step 2: 改仓库根 `README.md`**

插件列表或能力矩阵增加 Claude / Codex 两列（若现有结构是列表，则在 frontend、backend、devops 三项下各加一行「Codex 差异：」）。必须出现的事实，各一句：
- frontend 的 `avalonia-docs`、`microsoft-learn` 随 Codex 插件分发；`mastergo-magic-mcp` 在经验证的 token 转发方案出现前仅 Claude Code 可用；
- `dotnet-diagnose` agent 在 Codex CLI 0.172.0 下未注册，Codex 用户直接使用 `dotnet-diagnose-triage`；
- Claude Hook 不随 Codex 插件生效；
- Claude marketplace 另有 3 个外部引用条目，Codex marketplace 只含 9 个本仓自建插件。

- [ ] **Step 3: 登记 Codex CLI 工具记录**

调用 `record-tools` skill，记录对象「Codex CLI」，要求记录内容至少包括：
- 安装方式：`npm install -g @openai/codex@0.172.0`，CI 固定版本，禁止 `latest`；
- 已验证行为（0.172.0，Windows）：`codex debug prompt-input "x"` 在未登录、无 API key 时可渲染模型可见 skill 清单，条目格式 `\n- <plugin>:<skill>: <description>`，路径以别名根表加相对路径给出；`codex mcp list --json` 可零凭据列出插件 MCP；`codex plugin add` **不校验** manifest 组件路径（缺失与越界路径均安装成功），不能作为加载成功判据；
- 已验证限制：插件 `agents` 声明在 `multi_agent_v2` 开关下均未进入渲染提示；`.mcp.json` 的 `${VAR}` 不展开；`plugin_hooks` 为 removed；
- 本仓使用位置：`.githooks/codex_smoke.py`、`ci.yml` 的 `plugin-validate`。

Run（record-tools 完成后）：
`python .claude/skills/knowledge-base-maintain/scripts/check_index.py` → 通过
`python .claude/skills/knowledge-base-maintain/scripts/check_refs.py` → 通过

- [ ] **Step 4: PR 1 全量本地验证**

Run: `python .githooks/run_repository_gates.py` → 退出码 0
Run: `python .githooks/run_unit_tests.py` → 全部 PASS
Run: 上一步两条 + `python .claude/skills/sync-cc-tips/scripts/validate_tips.py` → 全部通过
Run: `git diff master --stat` → 只包含本 PR 的 File Structure 中 T1–T5 的文件与 spec/两份报告

- [ ] **Step 5: 提交并推送开 PR**

用 `commit-cc-plugin` 提交本任务文件（message：`docs(repo): document per-harness component rules and record Codex CLI`），并按其第五步推送分支、开 PR 1。PR 描述写明：spec 路径；`prompt-input` 在 ubuntu 上是首次运行；本机未跑 actionlint。

- [ ] **Step 6: 观察 CI，处理 Linux 分支**

Run: `gh pr checks <PR号> --watch`
- 六项全绿 → 等待用户 squash merge，PR 1 完成。
- `plugin-validate` 失败且日志为 `[cli-install]` → 重跑一次 job；仍失败则停下报告用户，不改设计。
- `plugin-validate` 失败于 `[skill-visibility]` 而 `[plugin-install]`、`[mcp-enumeration]` 都通过 → 这是 spec §7.2 的 Linux 分支：给 `codex_smoke.py` 加参数 `--skip-skill-visibility`（跳过 prompt-input 断言并打印 `[skill-visibility] skipped on <platform>`），`plugin-validate` 改为带该参数运行；新增独立 workflow 文件 `.github/workflows/codex-smoke-windows.yml`（触发 `pull_request` 与 `workflow_dispatch`，单 job `codex-smoke-windows`，`runs-on: windows-latest`，执行完整冒烟；单独成文件是因为 workflow 触发器是文件级的，不能在 `ci.yml` 内给单个 job 配触发器）。在 `test_codex_smoke.py` 为该参数补一个测试：用 `unittest.mock.patch("codex_smoke.subprocess.run")` 断言带参数时不出现含 `prompt-input` 的调用。新 job **不加入** ruleset。完成后重新推送。

---

# PR 2 — Phase 2：Skill 可移植性

分支：`fix/skill-portability`，**从 PR 1 合并后的 `master` 切出**。PR 1 未合并前不开始本阶段（版本号要从 PR 1 之后的值起算）。

### Task 6: portability gate 脚本（第 10 项，先不登记）

**Files:**
- Create: `.githooks/check_skill_portability.py`
- Create: `.githooks/test_check_skill_portability.py`

**Interfaces:**
- Produces:
  - `ALLOWED_FRONTMATTER_KEYS = frozenset({"name", "description", "license", "compatibility", "metadata", "allowed-tools"})`
  - `MARKER = "codex-portability: allow-harness-path reason="`
  - `HARNESS_PATH_PATTERNS: tuple[re.Pattern, ...]`，对 `claude` 与 `codex` 各匹配：`\.<h>/skills/`、`~/\.<h>/`、`\$HOME/\.<h>/`、`%USERPROFILE%\\\.<h>\\`、`\$env:USERPROFILE\\\.<h>\\`。
  - `BLOCKED_TOOL_TOKENS = ("AskUserQuestion",)`，按 `\b` 词边界匹配，**只扫正文**（frontmatter 之后），`allowed-tools` 行不参与。
  - `@dataclass(frozen=True) class Finding: path: str; line: int; rule: str; text: str`，`rule ∈ {"frontmatter-key", "harness-path", "tool-token", "marker-no-reason", "marker-orphan", "skill-dir-missing"}`。
  - `scan_skill(skill_dir: Path, repo_root: Path) -> list[Finding]`
  - `scan_repo(repo_root: Path) -> list[Finding]`：遍历 `plugins/*/skills/*/`。
  - `main(argv: list[str]) -> int`：`check_skill_portability.py [--list] <repo_root>`；默认模式有 Finding 则逐条打印 `<path>:<line>: [<rule>] <text>` 并返回 1；`--list` 同样打印但返回 0。
- 扫描文件：`SKILL.md`；skill 目录下递归的 `*.sh`、`*.ps1`、`*.py`（覆盖 spec 的 `scripts/**` 与根目录脚本，且不漏 `jenkins_build/` 这类子目录）；**排除 `test_*.py`**（测试夹具必须字面写出旧路径来断言回退行为）。
- 标记规则：含 `MARKER` 的第 N 行豁免第 N 行与第 N+1 行的 `harness-path` 命中；`reason=` 后为空 → `marker-no-reason`；第 N、N+1 行都没有 `harness-path` 命中 → `marker-orphan`。
- `<skill-dir>` 规则：正文中 `<skill-dir>/<相对路径>`（路径到空白、反引号、引号或右括号为止）必须在 skill 目录内存在，否则 `skill-dir-missing`。
- frontmatter：首个 `---` 块内，行首无缩进、非 `#` 开头的 `key:` 视为顶层键。文件用 `read_text(encoding="utf-8")` 读（通用换行，CRLF 自动归一）。

- [ ] **Step 1: 写失败测试**

夹具 `make_skill(root, plugin, name, skill_md: str, files: dict[str, str] | None = None) -> Path`，在临时仓库 `plugins/<plugin>/skills/<name>/` 下写文件。测试（每个断言 `scan_repo` 的 `rule` 与 `line`）：

```python
def test_clean_skill_passes(self): ...                    # 六字段 + 普通正文 → []
def test_unknown_frontmatter_key(self): ...               # triggers: → rule "frontmatter-key", line 指向该键
def test_crlf_frontmatter_parsed(self): ...               # Review Focus 5：同上内容用 "\r\n" 写入（write_bytes），键与行号一致
def test_claude_skills_path_in_body(self): ...            # ".claude/skills/x/a.py" → "harness-path"
def test_powershell_userprofile_path(self): ...           # "$env:USERPROFILE\\.codex\\skills" → "harness-path"
def test_home_path_in_script(self): ...                   # scripts/run.sh 含 "$HOME/.claude/cache" → "harness-path"，path 指向 run.sh
def test_nested_script_scanned(self): ...                 # jenkins_build/main.py 含 "~/.claude/" → "harness-path"
def test_test_files_excluded(self): ...                   # scripts/test_x.py 含 "~/.claude/" → []
def test_marker_same_line_html_comment(self): ...         # 表格行末尾 "<!-- codex-portability: allow-harness-path reason=同步目标 -->" → []
def test_marker_previous_line_comment(self): ...          # "# codex-portability: ... reason=x" 下一行命中 → []
def test_one_marker_covers_both_hits_on_a_line(self): ... # 同一行 .claude 与 .codex → []
def test_marker_does_not_reach_two_lines(self): ...       # 标记在 N，命中在 N+2 → "harness-path" + "marker-orphan"
def test_marker_without_reason(self): ...                 # "reason=" 后为空 → "marker-no-reason"
def test_ask_user_question_in_body(self): ...             # 正文 "用 AskUserQuestion 收集" → "tool-token"
def test_ask_user_question_in_allowed_tools_ignored(self): ...  # 仅 allowed-tools 含 → []
def test_skill_dir_reference_missing(self): ...           # "<skill-dir>/scripts/nope.py" → "skill-dir-missing"
def test_skill_dir_reference_present(self): ...           # 文件存在 → []
def test_list_mode_returns_zero(self): ...                # main(["--list", root]) == 0 且有输出
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m unittest discover -s .githooks -p "test_check_skill_portability.py" -v`
Expected: `ModuleNotFoundError: No module named 'check_skill_portability'`。

- [ ] **Step 3: 实现**

签名与规则见 Interfaces。模块 docstring 引用 spec §6.2，并说明三处取舍：为什么排除 `test_*.py`；为什么阻断清单只有 `AskUserQuestion`；标记以行为单位。

- [ ] **Step 4: 运行确认通过**

Run: `python -m unittest discover -s .githooks -p "test_check_skill_portability.py" -v` → 18 个 PASS

- [ ] **Step 5: 审计真实仓库存量（不阻断）**

Run: `python .githooks/check_skill_portability.py --list .`
Expected: 命中只落在以下文件（数量对不上就先停下核对，不要扩大豁免）：`optimus-backend-api-connect/SKILL.md`、`optimus-backend-dev/SKILL.md`、`jenkins-build/{SKILL.md,scripts/run.sh}`、`sync-skill-symlinks/SKILL.md`（7 行）、`optimus-qa-ui-scripts/SKILL.md`（正文 `AskUserQuestion`），以及 11 个 skill 的 `frontmatter-key`。这份清单就是 Task 7–10 的工作量。注意 `jenkins_build/main.py` 用 `os.path.join(expanduser("~"), ".claude", ...)` 拼路径，正则**扫不到**——这是本门禁的已知盲区（只认字面路径），Task 8 会直接改掉这处，不必为它扩充正则。

- [ ] **Step 6: 提交**

用 `commit-cc-plugin` 提交，message：`feat(repo): add skill portability scanner`。

### Task 7: `optimus-backend-api-connect` 目录解析可移植化

**Files:**
- Create: `plugins/optimus-backend/skills/optimus-backend-api-connect/scripts/optimus_dirs.py`
- Create: `plugins/optimus-backend/skills/optimus-backend-api-connect/scripts/test_optimus_dirs.py`
- Modify: `plugins/optimus-backend/skills/optimus-backend-api-connect/fetch_feishu_doc.py`（第 53–55 行的 token 缓存、第 245/256 行的默认输出）
- Modify: `plugins/optimus-backend/skills/optimus-backend-api-connect/SKILL.md`（第 20–131 行所有 `.claude/skills/optimus-backend-api-connect/...`；frontmatter 加 `metadata.version: "1.0.0"`）
- Create: `plugins/optimus-backend/skills/optimus-backend-api-connect/CHANGELOG.md`

**Interfaces:**
- Produces（`optimus_dirs.py`，仅标准库）：
  - `config_root(env: Mapping[str, str] | None = None, os_name: str | None = None, home: Path | None = None) -> Path`
  - `cache_root(env=None, os_name=None, home=None) -> Path`
  - `skill_dirs(skill: str, env=None, os_name=None, home=None) -> dict[str, str]`：返回 `{"config_dir": str(config_root()/skill), "cache_dir": str(cache_root()/skill)}`
  - CLI：`python optimus_dirs.py <skill-name> [--create]`，向 stdout 打印 `json.dumps(skill_dirs(...), ensure_ascii=False)`；`--create` 时 `mkdir(parents=True, exist_ok=True)` 两个目录。
  - 参数默认值：`env=os.environ`、`os_name=os.name`、`home=Path.home()`。
- 解析规则（Global Constraints 的优先级①②）：环境变量非空 → `Path(value).expanduser().resolve()`（相对路径按当前工作目录转绝对）；否则 `os_name == "nt"`：配置 `Path(env.get("APPDATA") or home/"AppData"/"Roaming")/"optimus"`，缓存 `Path(env.get("LOCALAPPDATA") or home/"AppData"/"Local")/"optimus"/"cache"`；否则配置 `Path(env.get("XDG_CONFIG_HOME") or home/".config")/"optimus"`，缓存 `Path(env.get("XDG_CACHE_HOME") or home/".cache")/"optimus"`。
- Produces（`fetch_feishu_doc.py`）：`token_cache_file(env: Mapping[str, str] | None = None) -> Path`，返回 `Path(skill_dirs("optimus-backend-api-connect", env)["cache_dir"]) / ".feishu_token_cache.json"`；模块常量 `_TOKEN_CACHE_FILE` 删除，调用处改为调用该函数。脚本通过 `sys.path.insert(0, str(_SCRIPT_DIR / "scripts"))` 导入 `optimus_dirs`。

- [ ] **Step 1: 写失败测试**

```python
class TestOptimusDirs(unittest.TestCase):
    def test_env_override_wins(self):
        d = skill_dirs("s", env={"OPTIMUS_CACHE_DIR": "/x/cache"}, os_name="posix", home=Path("/h"))
        self.assertEqual(Path(d["cache_dir"]), Path("/x/cache").resolve() / "s")

    def test_relative_env_becomes_absolute(self):          # Review Focus 2
        d = skill_dirs("s", env={"OPTIMUS_CACHE_DIR": "rel/cache"}, os_name="posix", home=Path("/h"))
        self.assertTrue(Path(d["cache_dir"]).is_absolute())
        self.assertEqual(Path(d["cache_dir"]), (Path.cwd() / "rel" / "cache" / "s").resolve())

    def test_path_with_spaces_preserved(self):             # Review Focus 1
        d = skill_dirs("s", env={"OPTIMUS_CACHE_DIR": str(Path(tempfile.mkdtemp()) / "a b")}, os_name="posix", home=Path("/h"))
        self.assertIn("a b", d["cache_dir"])

    def test_windows_defaults(self):
        env = {"APPDATA": r"C:\U\R", "LOCALAPPDATA": r"C:\U\L"}
        d = skill_dirs("s", env=env, os_name="nt", home=Path(r"C:\U"))
        self.assertEqual(Path(d["config_dir"]), Path(r"C:\U\R") / "optimus" / "s")
        self.assertEqual(Path(d["cache_dir"]), Path(r"C:\U\L") / "optimus" / "cache" / "s")

    def test_posix_xdg_defaults(self):
        d = skill_dirs("s", env={}, os_name="posix", home=Path("/h"))
        self.assertEqual(Path(d["config_dir"]), Path("/h/.config/optimus/s"))
        self.assertEqual(Path(d["cache_dir"]), Path("/h/.cache/optimus/s"))

    def test_cli_prints_json_and_creates(self):
        tmp = Path(tempfile.mkdtemp()) / "a b"
        out = subprocess.run([sys.executable, str(HERE / "optimus_dirs.py"), "s", "--create"],
                             env={**os.environ, "OPTIMUS_CACHE_DIR": str(tmp), "OPTIMUS_CONFIG_DIR": str(tmp / "cfg")},
                             capture_output=True, text=True, encoding="utf-8", check=True).stdout
        self.assertTrue(Path(json.loads(out)["cache_dir"]).is_dir())

    def test_feishu_token_cache_outside_skill_dir(self):
        sys.modules.setdefault("requests", types.ModuleType("requests"))   # 该脚本在导入期要求 requests
        sys.path.insert(0, str(HERE.parent))
        import fetch_feishu_doc
        tmp = tempfile.mkdtemp()
        p = fetch_feishu_doc.token_cache_file({"OPTIMUS_CACHE_DIR": tmp})
        self.assertEqual(p, Path(tmp).resolve() / "optimus-backend-api-connect" / ".feishu_token_cache.json")
        self.assertNotIn(str(HERE.parent.resolve()), str(p.resolve()))
```

（`HERE = Path(__file__).resolve().parent`；`posix` 用例在 Windows 上同样成立，因为只比较 `Path` 对象。）

- [ ] **Step 2: 运行确认失败**

Run: `python -m unittest discover -s plugins/optimus-backend/skills/optimus-backend-api-connect/scripts -v`
Expected: `ModuleNotFoundError: No module named 'optimus_dirs'`。

- [ ] **Step 3: 实现 `optimus_dirs.py`，并改 `fetch_feishu_doc.py`**

`optimus_dirs.py` 顶部 docstring 写明：本文件在 `optimus-devops/skills/jenkins-build/scripts/` 有一份逐字相同的副本（插件自包含要求），改一处必须同步另一处。`fetch_feishu_doc.py` 的 `--output` 默认值改为 `Path(skill_dirs(...)["cache_dir"]) / f"feishu-{doc_token[:8]}.md"`，写入前 `mkdir(parents=True, exist_ok=True)`；docstring 中 `cache/my-doc.md` 示例保持不变（那是用户显式传参的示例）。

- [ ] **Step 4: 运行确认通过**

Run: `python -m unittest discover -s plugins/optimus-backend/skills/optimus-backend-api-connect/scripts -v` → 7 个 PASS
Run: `python .githooks/run_unit_tests.py` → 新目录被自动发现且全部 PASS

- [ ] **Step 5: 改 SKILL.md**

- 「阶段一：读取配置」之前插入「阶段零：解析目录」：执行 `python "<skill-dir>/scripts/optimus_dirs.py" optimus-backend-api-connect --create`，取输出 JSON 的 `cache_dir` 记为 `<cache>`；`<skill-dir>` 为本 SKILL.md 所在目录的绝对路径。后续所有命令里的路径都用双引号包裹。
- 全文 `.claude/skills/optimus-backend-api-connect/cache/` → `<cache>/`；`.claude/skills/optimus-backend-api-connect/fetch_` → `<skill-dir>/fetch_`。
- 情况 A（远程拉取失败）的缓存检查改为依次：`<cache>/api-services.yml` → 旧路径 `.claude/skills/optimus-backend-api-connect/cache/api-services.yml`（**只读**，命中时提示「已读取旧缓存位置，新缓存将写入 `<cache>`」）。旧路径那一行行尾加 `<!-- codex-portability: allow-harness-path reason=旧缓存位置只读回退 -->`。
- 第 108 行飞书 token 缓存位置改为 `<cache>/.feishu_token_cache.json`。
- frontmatter `metadata` 下新增 `version: "1.0.0"`（建立基线，置于 `author` 之前）。

- [ ] **Step 6: 验证与 CHANGELOG**

Run: `python .githooks/check_skill_portability.py --list .` → 输出中不再有 `optimus-backend-api-connect` 的任何行。
新建 `CHANGELOG.md`：

```markdown
## [1.0.0] - <提交日>

### Fixed
- 脚本与缓存路径不再硬编码 `.claude/skills/`：脚本经 `<skill-dir>` 定位，缓存由 `scripts/optimus_dirs.py` 解析到用户缓存目录
- 飞书 token 缓存与默认输出不再写入已安装插件目录
- 首次建立 `metadata.version` 基线
```

- [ ] **Step 7: 提交**

用 `commit-cc-plugin` 提交，message：`fix(optimus-backend): resolve api-connect paths via bundled helper`。

### Task 8: `jenkins-build` 配置/缓存可移植化 + 修复项目级配置查找

**已有 bug（本任务一并修复）：** `scripts/run.sh` 末尾先 `cd "$SKILL_DIR/jenkins_build"` 再运行 `main.py`，而 `main.py` 用 `os.getcwd()` 找项目级 `jenkins-config.yaml`——此时 cwd 已是 skill 目录，**项目级配置永远找不到**，SKILL.md 宣称的优先级 1 从未生效。

**Files:**
- Create: `plugins/optimus-devops/skills/jenkins-build/scripts/optimus_dirs.py`（与 Task 7 的文件**逐字相同**）
- Create: `plugins/optimus-devops/skills/jenkins-build/scripts/jenkins_config_paths.py`
- Create: `plugins/optimus-devops/skills/jenkins-build/scripts/test_jenkins_config_paths.py`
- Create: `.githooks/test_bundled_helper_copies.py`
- Modify: `plugins/optimus-devops/skills/jenkins-build/jenkins_build/main.py`（第 14–31 行）
- Modify: `plugins/optimus-devops/skills/jenkins-build/scripts/run.sh`（第 13–14 行、末尾 `cd` 前）
- Modify: `plugins/optimus-devops/skills/jenkins-build/SKILL.md`（第 42、66–72、77、98、133 行；`metadata.version` `1.3.2 → 1.3.3`）
- Modify: `plugins/optimus-devops/skills/jenkins-build/CHANGELOG.md`

**Interfaces:**
- Consumes: Task 7 的 `optimus_dirs.skill_dirs`（本插件内副本）。
- Produces（`jenkins_config_paths.py`）：
  - `PROJECT_DIR_ENV = "JENKINS_BUILD_PROJECT_DIR"`
  - `config_search_paths(env: Mapping[str, str] | None = None, os_name: str | None = None, home: Path | None = None, cwd: Path | None = None) -> list[tuple[Path, bool]]`：返回 `[(路径, 是否旧路径)]`，顺序固定为：`Path(env.get(PROJECT_DIR_ENV) or cwd)/"jenkins-config.yaml"` → `Path(skill_dirs("jenkins-build", env, os_name, home)["config_dir"])/"jenkins-config.yaml"` → `home/".claude"/"jenkins-config.yaml"`（`True`）。
  - `find_config(env=None, os_name=None, home=None, cwd=None) -> tuple[Path, bool] | None`：返回第一个存在的条目。

- [ ] **Step 1: 写失败测试**

```python
class TestJenkinsConfigPaths(unittest.TestCase):
    # 每个测试在 tempfile.mkdtemp() 下造 home/、proj/、cfg/，env 只含 OPTIMUS_CONFIG_DIR=cfg

    def test_project_dir_env_beats_cwd(self): ...          # 配置只放在 proj/；cwd=skill 目录；env 含 JENKINS_BUILD_PROJECT_DIR=proj → 命中 proj/jenkins-config.yaml
    def test_new_config_beats_legacy(self): ...            # Review Focus 3：cfg/jenkins-build/ 与 home/.claude/ 都有 → 命中 cfg，is_legacy False
    def test_legacy_only_is_flagged(self): ...             # Review Focus 3：只有 home/.claude/ → 命中且 is_legacy True
    def test_none_found(self): ...                         # 都没有 → find_config 返回 None
    def test_order_is_fixed(self): ...                     # config_search_paths 三项顺序与 is_legacy 标志 == [False, False, True]
```

`.githooks/test_bundled_helper_copies.py`：

```python
def test_optimus_dirs_copies_identical(self):
    root = pathlib.Path(__file__).resolve().parent.parent
    a = root / "plugins/optimus-backend/skills/optimus-backend-api-connect/scripts/optimus_dirs.py"
    b = root / "plugins/optimus-devops/skills/jenkins-build/scripts/optimus_dirs.py"
    self.assertEqual(a.read_bytes(), b.read_bytes())
```

（该测试放 `.githooks/` 而非 skill 内：skill 内写跨插件路径会被第 8 项「插件自包含」拦下。）

- [ ] **Step 2: 运行确认失败**

Run: `python -m unittest discover -s plugins/optimus-devops/skills/jenkins-build/scripts -v` → `ModuleNotFoundError: jenkins_config_paths`
Run: `python -m unittest discover -s .githooks -p "test_bundled_helper_copies.py" -v` → FAIL（文件不存在）

- [ ] **Step 3: 实现**

- 复制 Task 7 的 `optimus_dirs.py` 到本插件 `scripts/`（字节级一致）。
- 实现 `jenkins_config_paths.py`。
- `main.py`：删除 `CONFIG_SEARCH_PATHS` 常量；`sys.path.insert(0, <skill 根>/"scripts")` 后导入 `find_config`、`config_search_paths`；`load_config()` 命中旧路径时额外打印 `[!] 正在读取旧配置位置 <path>；请迁移到 <新路径>，旧位置今后只读不写`；未找到时逐行打印 `config_search_paths()` 的三个路径。
- `run.sh`：在 `cd` 之前加 `export JENKINS_BUILD_PROJECT_DIR="$PWD"`；`VENV_DIR` 改为由 helper 解析：`CACHE_DIR="$(python3 "$SCRIPT_DIR/optimus_dirs.py" jenkins-build --create | python3 -c 'import json,sys; print(json.load(sys.stdin)["cache_dir"])')"`，`VENV_DIR="$CACHE_DIR/.venv"`；所有 `$VENV_DIR`、`$CACHE_DIR` 引用保持双引号（Review Focus 1）。旧 venv `~/.claude/cache/jenkins-build/.venv` 不迁移也不删除（缓存可重建，首次运行会在新位置重建）。

- [ ] **Step 4: 运行确认通过**

Run: `python -m unittest discover -s plugins/optimus-devops/skills/jenkins-build/scripts -v` → 5 个 PASS
Run: `python -m unittest discover -s .githooks -p "test_bundled_helper_copies.py" -v` → PASS
Run（Git Bash，Review Focus 1 的端到端）：`OPTIMUS_CACHE_DIR="$(mktemp -d)/a b" bash plugins/optimus-devops/skills/jenkins-build/scripts/run.sh` 在无配置的临时目录中执行 → venv 建在含空格的路径下，最终输出「未找到配置文件」并列出三个路径，第一个是**执行时的当前目录**而不是 skill 目录。

- [ ] **Step 5: 改 SKILL.md 与 CHANGELOG**

- 查找优先级表改为三行：`1（最高）| <当前工作目录>/jenkins-config.yaml | 项目级`；`2 | <optimus-config-dir>/jenkins-build/jenkins-config.yaml（Windows 为 %APPDATA%\optimus\jenkins-build\，其他平台为 ~/.config/optimus/jenkins-build/，可用 OPTIMUS_CONFIG_DIR 覆盖） | 用户级全局默认`；`3 | ~/.claude/jenkins-config.yaml | 旧位置，只读兼容，命中时提示迁移` 行尾加 `<!-- codex-portability: allow-harness-path reason=旧配置位置只读回退 -->`。
- 三条 `.claude/skills/jenkins-build/scripts/run.sh` 命令改为 `"<skill-dir>/scripts/run.sh"`，并在代码块前说明 `<skill-dir>` 是本 SKILL.md 所在目录的绝对路径；`python3 jenkins_build/main.py` 改为 `python3 "<skill-dir>/jenkins_build/main.py"`。
- 「venv 位置」改为 `<optimus-cache-dir>/jenkins-build/.venv`（由 `scripts/optimus_dirs.py` 解析）。
- 错误处理表中「在 `~/.claude/jenkins-config.yaml` 创建配置」改为「在优先级 1 或 2 的位置创建配置」。
- CHANGELOG 新增 `## [1.3.3] - <提交日>`，`### Fixed` 下三条：项目级配置因 run.sh 切换 cwd 从未生效；配置/venv 不再使用 `.claude` 目录；命令改用 `<skill-dir>` 定位。

Run: `python .githooks/check_skill_portability.py --list .` → 不再有 `jenkins-build` 的行。

- [ ] **Step 6: 提交**

用 `commit-cc-plugin` 提交，message：`fix(optimus-devops): make jenkins-build config and venv paths harness-neutral`。

### Task 9: 去除交互工具名绑定与 Claude 专属安装说明

**Files:**
- Modify: `plugins/optimus-qa/skills/optimus-qa-ui-scripts/SKILL.md`（frontmatter `allowed-tools`；正文第 26 行）
- Modify: `plugins/optimus-backend/skills/optimus-backend-dev/SKILL.md`（第 44–58 行的「未安装」提示块）

**Interfaces:** 无代码接口。两个 skill 的 `metadata.version` 与 CHANGELOG 统一在 Task 10 处理，本任务**不升版本**（同一 PR 内只升一次）。

- [ ] **Step 1: `optimus-qa-ui-scripts`**

- `allowed-tools: Bash Read Write AskUserQuestion` → `allowed-tools: Bash Read Write`。
- 第 26 行「询问用户以下信息（用 AskUserQuestion 逐步收集）：」→「询问用户以下信息（一次集中列出缺失项，用户未提供的必填项逐项追问）：」。
- Run: `grep -rn "AskUserQuestion" plugins/*/skills/*/SKILL.md` → 无输出。

- [ ] **Step 2: `optimus-backend-dev` 的 superpowers 安装提示**

代码块内第 1–3 步替换为两个 harness 的安装入口（依据 superpowers 7.0.2 README「Claude Code / Codex CLI」两节，已核实）：

```
请先安装 superpowers：
- Claude Code：/plugin install superpowers@claude-plugins-official，然后重启会话
- Codex CLI：在会话中输入 /plugins，搜索 superpowers，选择 Install Plugin
```

其余行（⚠ 提示首行、「安装完成后重新触发本技能」「不继续任何后续步骤」）不动。

- [ ] **Step 3: 验证**

Run: `python .githooks/check_skill_portability.py --list .` → 不再有这两个 skill 的 `harness-path` / `tool-token` 行（`frontmatter-key` 行留给 Task 10）。

- [ ] **Step 4: 提交**

用 `commit-cc-plugin` 提交，message：`fix(repo): describe user prompts and superpowers install without Claude-only bindings`。

### Task 10: 11 个 skill 的 frontmatter 归并

**Files（每个 skill 改 `SKILL.md`；缺 `CHANGELOG.md` 的新建）：**

| skill | 移除字段 | 归并到 | `metadata.version` |
|---|---|---|---|
| `optimus-backend/skills/optimus-backend-dev` | `triggers` | `description` | `1.0.1 → 1.0.2` |
| `optimus-office/skills/docx-writer` | `triggers` | `description` | `1.0.1 → 1.0.2` |
| `optimus-office/skills/file-to-markdown` | `triggers`、`dependencies` | `description`、`compatibility` + 正文 | `1.1.1 → 1.1.2` |
| `optimus-office/skills/web-to-markdown` | `triggers`、`dependencies` | `description`、`compatibility` + 正文 | `1.9.2 → 1.9.3` |
| `optimus-qa/skills/optimus-qa-*`（7 个） | `creator` | 删除（`metadata.author` 已是 `desktop client team`） | 新增 `version: "1.0.0"` |

**Interfaces:** 无代码接口。

- [ ] **Step 1: 归并 `triggers`**

规则：只把**尚未出现在 description 中**的触发词，以「触发词：a、b、c。」一句追加到 description 末尾；已出现的不重复。多行折叠的 `description: >` 保持折叠写法，在最后一行之后追加一行。然后删除整个 `triggers:` 块。

- [ ] **Step 2: 归并 `dependencies`**

- `compatibility` 已经概括了依赖，只补缺失的硬依赖信息：file-to-markdown 补「markitdown 缺失时立即中断」；web-to-markdown 不用补（已写明可选）。
- 各依赖的 `check_command` / `install_command` 移入正文：若正文已有「依赖检查」「环境准备」类章节，追加到该章节；没有则在第一个 `##` 章节之前新增 `## 依赖检查` 小节，用表格列出 `依赖 | 必需 | 检查命令 | 安装命令`，逐字搬运原值（含 `install_url`）。
- 删除整个 `dependencies:` 块。

- [ ] **Step 3: 删除 `creator` 并建立版本基线**

7 个 qa skill：删除 `creator:` 行；在 `metadata:` 下第一行加 `version: "1.0.0"`。

- [ ] **Step 4: CHANGELOG**

已有 CHANGELOG 的 skill 追加新版本条目；没有的新建，只写本次一条。条目统一为 `### Changed`，内容按实际情况写其中适用的几条：「顶层 triggers 归并入 description」「顶层 dependencies 归并入 compatibility 与正文依赖检查表」「移除非规范字段 creator」「首次建立 metadata.version 基线」。`optimus-backend-dev` 与 `optimus-qa-ui-scripts` 的条目同时写上 Task 9 的改动（`### Fixed`）。

- [ ] **Step 5: 验证**

Run: `python .githooks/check_skill_portability.py --list .` → 不再有任何 `frontmatter-key` 行。
Run: `python -c "import pathlib,re;[print(p, len(re.search(r'(?ms)^description:(.*?)^\S', p.read_text(encoding='utf-8').split('---')[1] + '\nX').group(1))) for p in pathlib.Path('plugins').glob('*/skills/*/SKILL.md')]"` → 4 个改了 description 的 skill 都 ≤ 1024。
Run: `claude plugin validate plugins/optimus-office/skills --strict`、`claude plugin validate plugins/optimus-qa/skills --strict`、`claude plugin validate plugins/optimus-backend/skills --strict` → 全部通过（与 CI 的 `plugin-validate` 同一检查）。

- [ ] **Step 6: 提交**

用 `commit-cc-plugin` 提交，message：`fix(repo): fold non-standard skill frontmatter into the six allowed fields`。

### Task 11: 存量标记、登记第 10 项、版本与开 PR 2

**Files:**
- Modify: `plugins/optimus-devops/skills/sync-skill-symlinks/SKILL.md`（第 3、29、61、208、215、261、370 行加标记；`metadata.version` `2.0.1 → 2.0.2`）、其 `CHANGELOG.md`
- Modify: `.githooks/repository_gates.py`（登记 `Gate("skill-portability", ".githooks/check_skill_portability.py", (".",))`）
- Modify: `.githooks/test_run_repository_gates.py`（`len(GATES) == 6` → `7`）
- Modify: `.githooks/README.md`、`AGENTS.md`（计数改为「10 个逻辑检查 / 7 个脚本」，第 10 行检查项）
- Modify: `plugins/{optimus-backend,optimus-devops,optimus-office,optimus-qa}/.claude-plugin/plugin.json` 与 `.codex-plugin/plugin.json`（`version`）

**Interfaces:**
- Consumes: Task 6 的 `check_skill_portability.py` CLI。

- [ ] **Step 1: 改登记测试使其失败**

`test_run_repository_gates.py` 中 `self.assertEqual(len(GATES), 6)` 改为 `7`。
Run: `python -m unittest discover -s .githooks -p "test_run_repository_gates.py" -v` → FAIL（`6 != 7`）。

- [ ] **Step 2: 给 `sync-skill-symlinks` 加 7 处标记**

按 Global Constraints 的载体规则，`reason=` 统一写 `本 skill 的职责就是向各 harness 的 skills 目录同步链接`：
- 第 3 行（frontmatter `description`）：在其前一行插入 `# codex-portability: allow-harness-path reason=...`；
- 第 29、215 行（PowerShell 代码块）与第 61、261 行（bash 代码块）：各在前一行插入同样的 `#` 注释；
- 第 208 行（正文）与第 370 行（表格行）：行尾追加 `<!-- codex-portability: allow-harness-path reason=... -->`，不插入独立行。

插入注释后行号会后移，按内容定位，不按行号定位。CHANGELOG 新增 `## [2.0.2]`，`### Changed`：为默认同步目标路径加 portability 豁免标记，行为不变。

- [ ] **Step 3: 登记第 10 项**

`repository_gates.py` 末尾追加 Gate，注释写明：本项拦的是「发布 skill 写死 harness 专属目录或工具名」，不拦会导致 Codex 侧脚本或缓存路径解析失败；判据见 spec §6.2 与脚本 docstring。docstring 计数改为 **7 个脚本 / 10 个逻辑检查**。`.githooks/README.md` 检查项表追加 `| 10 | 发布 skill 不写死 harness 专属路径、不用非允许 frontmatter 键、正文不绑定 AskUserQuestion | Codex 侧 skill 找不到脚本、把缓存写进插件目录，或依赖被忽略的字段——都不报错 |`，标题与正文计数同步。`AGENTS.md` 中九项相关的三处改为十项。

- [ ] **Step 4: 升插件版本**

以 PR 1 合并后的值为起点，四个插件各升 Patch（预期：backend `2.0.4 → 2.0.5`、devops `2.0.12 → 2.0.13`、office `2.0.1 → 2.0.2`、qa `2.0.2 → 2.0.3`）；每个插件两份 `plugin.json` 同值。frontend 本阶段无改动，不升。

- [ ] **Step 5: 全量验证**

Run: `python .githooks/check_skill_portability.py .` → 退出码 0（默认阻断模式）
Run: `python .githooks/run_repository_gates.py` → 退出码 0，共 7 段输出
Run: `python .githooks/run_unit_tests.py` → 全部 PASS
Run: `python .claude/skills/knowledge-base-maintain/scripts/check_index.py`、`python .claude/skills/knowledge-base-maintain/scripts/check_refs.py`、`python .claude/skills/sync-cc-tips/scripts/validate_tips.py` → 全部通过
Run: `grep -rn "九项\|9 个逻辑" AGENTS.md .githooks` → 无输出
Run（反向验证）：在任一 skill 的 SKILL.md 正文临时写入 `.claude/skills/x/a.py`，`python .githooks/run_repository_gates.py` → 退出码 1 且输出含 `[pre-commit] 未通过`；用 `git checkout -- <文件>` 还原。

- [ ] **Step 6: 人工验收（spec §13.3，需要模型推理，不进 CI）**

用 `test-locally` skill 在 Claude 侧加载本仓；Codex 侧用 Task 4 的隔离 `CODEX_HOME` 安装本地 marketplace。逐条记录结果：
1. Codex 中 frontend 的 `avalonia-docs`、`microsoft-learn` 可连接，MasterGo 不出现；
2. Codex 中触发 `dotnet-diagnose-triage` 正常；触发 `dotnet-diagnose-autopilot` 时在派发前终止并给出 triage 入口；**反例**：会话中不出现 `spawn_agent` 调用，输出没有「首次分析 / 复核分析」双段结构；
3. `optimus-backend-api-connect`、`jenkins-build` 在插件缓存不位于 `.claude/skills` 时能定位脚本、配置与缓存；
4. `optimus-qa-ui-scripts` 在没有 `AskUserQuestion` 的环境中能正常收集信息。

任一条失败：停下报告用户，不在本 PR 内扩大范围修补。

- [ ] **Step 7: 提交并开 PR 2**

用 `commit-cc-plugin` 提交本任务文件（message：`feat(repo): enforce skill portability gate`），推送并开 PR。PR 描述附 Step 6 的人工验收记录。等待六项 required check 全绿后由用户 squash merge。


