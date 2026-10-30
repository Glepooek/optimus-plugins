# 合并 optimus-avalonia 到 optimus-frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `optimus-avalonia` 的 4 个 skill 与 `install.sh` 并入 `optimus-frontend` 并删除前者，同时让提交门禁钩子同时覆盖 `.xaml` 与 `.axaml`。

**Architecture:** 用 `git mv` 平移目录保留历史；钩子脚本改为同一文件内两个互相独立的门禁（各自「文件模式 / 审查 skill / 标记文件」三元组）；其余为引用与版本号的机械同步。整个改动落在一个特性分支、一个 PR。

**Tech Stack:** Bash（钩子与验证脚本）、JSON 清单、Markdown、Python（仓库既有一致性门禁脚本，仅运行不修改）。

**Spec:** `docs/superpowers/specs/2026-10-30-merge-avalonia-into-frontend-design.md`

## Global Constraints

- 4 个迁入 skill 的 SKILL.md **正文、触发词、`allowed-tools` 一字不改**；仅 `avalonia-code-review` 的 frontmatter `metadata.version` 由 `"1.0.1"` 升 `"1.0.2"`
- `.xaml` 门禁改造后行为必须与改造前完全一致（含 `wpf.hash` 标记文件名、`exit 2` 拦截、非 git 仓库干净 `exit 0`）
- `review-gate.sh` 保持：纯 bash 正则匹配 `git commit`、不起解释器、拦截用 `exit 2`
- `mark` 必须带类别参数 `wpf` 或 `avalonia`；无参数/非法参数 `exit 1` 并打印用法
- `hooks.json` 不改
- 版本号：`optimus-frontend` 两份 `plugin.json` 同升 `2.0.0 → 2.1.0`；marketplace 顶层 `14.4.0 → 15.0.0`；`knowledge-base/tools` `1.0.0 → 1.0.1`（README 版本行与 CHANGELOG 最新条目须一致）
- 统一的 frontend 描述文案（三处清单必须逐字相同）：
  `桌面前端开发（WPF + Avalonia）：MasterGo 设计稿转页面与组件库、SVG 转 XAML、XAML/AXAML 代码审查、Avalonia 文档 MCP 路由开发、WPF 迁移 Avalonia 与 Linux deb 发布。内置 PreToolUse Hook：git commit 前门禁校验 .xaml / .axaml 改动是否已审查`
- 不回写历史记录：各 skill 的既有 CHANGELOG 条目、`docs/superpowers/specs/2026-09-15-*`、`docs/todo-list/*`
- 禁止 `--no-verify`；提交必须走 `commit-cc-plugin` skill，主干 `master` 受保护，只能 特性分支 → PR
- 长文件分段写入（用户全局规则）

## Review Focus

- 同一次提交同时 staged `foo.xaml` 与 `bar.axaml`：只审查/标记其中一类，另一类必须仍被拦截（防串味）→ Task 2 矩阵「两类都 staged，只标记 wpf」
- `*.xaml` pathspec 误匹配 `*.axaml`（或反之）：两个模式必须互不相交，需实测 → Task 2 回归 2
- 已存在的旧 `wpf.hash` 标记：改造后对未变动的 `.xaml` 内容仍然有效，不得因改造而失效 → Task 2 回归 1
- 标记后再改动 staged 内容（哈希失效）：两类都必须重新被拦截 → Task 2 矩阵「标记后再改动 `.axaml`」，`.xaml` 同理由实现者补一条
- `install.sh` 迁移后若丢失 LF 行尾规则：Windows 检出变 CRLF，shebang 静默失效 → Task 1 Step 6

---

### Task 1: 建分支并平移文件

**Files:**
- Move: `plugins/optimus-avalonia/skills/{avalonia,avalonia-code-review,avalonia-deb-release,avalonia-wpf-migration}` → `plugins/optimus-frontend/skills/`
- Move: `plugins/optimus-avalonia/install.sh` → `plugins/optimus-frontend/install.sh`
- Delete: `plugins/optimus-avalonia/`（余下的 `.claude-plugin/`、`.codex-plugin/`）
- Modify: `.gitattributes:22`、`plugins/optimus-frontend/install.sh:2`

**Interfaces:**
- Produces: 后续任务依赖的新路径 `plugins/optimus-frontend/skills/avalonia-code-review/`（Task 5 用）与 `plugins/optimus-frontend/install.sh`

- [ ] **Step 1: 从最新 master 建特性分支**

Run: `git switch -c refactor/merge-avalonia-into-frontend`（当前在 master 且工作区除两份未跟踪的 docs 文件外干净）
Expected: `Switched to a new branch`；分支名 type 前缀 `refactor` 须与最终 commit 的 Conventional Commits type 一致（`knowledge-base/git/rules/01-branching.md`）

- [ ] **Step 2: `git mv` 四个 skill 目录与 `install.sh`**

Run: 对每个 skill 执行 `git mv plugins/optimus-avalonia/skills/<name> plugins/optimus-frontend/skills/<name>`，再 `git mv plugins/optimus-avalonia/install.sh plugins/optimus-frontend/install.sh`
Expected: 无输出；`git status --short` 全部显示为 `R`（重命名）

- [ ] **Step 3: 删除旧插件残留并确认目录消失**

Run: `git rm -r plugins/optimus-avalonia` 后 `test ! -e plugins/optimus-avalonia && echo gone`
Expected: 输出 `gone`（若 `git rm` 后磁盘上仍留有空目录，手工删除空目录再复测）

- [ ] **Step 4: 修 `.gitattributes` 第 22 行为新路径**

将 `plugins/optimus-avalonia/install.sh text eol=lf` 改为 `plugins/optimus-frontend/install.sh text eol=lf`，其上方注释保持不动。

- [ ] **Step 5: 改 `install.sh` 头注释**

第 2 行 `# Avalonia Skills Installer — optimus-avalonia 版` 改为 `— optimus-frontend 版`；在头部说明块（第 3–8 行"两级分发"段）内补一句：本插件整体分发，`${PLUGIN_ROOT}/skills` 下**全部** skill（WPF 与 Avalonia）都会被复制并链接。其余逻辑一字不动。

- [ ] **Step 6: 验证**

Run: `ls plugins/optimus-frontend/skills | wc -l`，`git check-attr eol -- plugins/optimus-frontend/install.sh`，`head -c 40 plugins/optimus-frontend/install.sh | od -c | head -3`
Expected: 目录数 `10`；`eol: lf`；shebang 行尾为 `\n` 而非 `\r\n`

- [ ] **Step 7: 暂不提交**（单 PR；提交统一在 Task 8 经 `commit-cc-plugin` 完成）

### Task 2: 钩子改为 `.xaml` / `.axaml` 双门禁

**Files:**
- Modify: `plugins/optimus-frontend/hooks/pretooluse/review-gate.sh`
- Create（**不入库**）: 验证脚本，放系统临时目录，如 `$TMPDIR/gate-matrix.sh`

**Interfaces:**
- Consumes: Task 1 无依赖，可独立执行
- Produces: 命令行契约，Task 3 的 README 与拦截提示须与之一致：
  - 检测模式：`review-gate.sh`（stdin 为 hook JSON）
  - 标记模式：`review-gate.sh mark <wpf|avalonia>`
  - 标记文件：`<git-dir>/optimus-review-marks/wpf.hash`、`avalonia.hash`

- [ ] **Step 1: 先写验证脚本（失败测试）**

脚本接口：`check <用例名> <期望退出码> <命令...>`，打印 `PASS/FAIL <用例名>`，任一 FAIL 则脚本最终 `exit 1`。在 `mktemp -d` 出的临时 git 仓库内运行，`GATE` 变量指向待测脚本绝对路径；触发钩子用 `printf '{"tool_input":{"command":"git commit -m x"}}' | bash "$GATE"`。覆盖 spec §8 第 8 条矩阵的全部 10 行，另加两条回归：
  1. 旧式 `wpf.hash` 兼容：在仓库里用旧脚本语义手工写入 `sha256(git diff --cached -- '*.xaml')` 到 `wpf.hash`，仅 staged `.xaml` 时期望 `exit 0`
  2. 模式不相交：仅 staged `x.axaml` 且仅标记 `wpf` 后，期望仍 `exit 2`

- [ ] **Step 2: 对旧脚本跑验证，确认失败**

Run: `GATE=$PWD/plugins/optimus-frontend/hooks/pretooluse/review-gate.sh bash "$TMPDIR/gate-matrix.sh"`
Expected: `.xaml` 相关用例 PASS；所有 `.axaml` 用例与 `mark` 参数校验用例 FAIL（旧脚本对 `.axaml` 返回 0）

- [ ] **Step 3: 重写 `review-gate.sh`**

保持文件头注释风格，更新用法说明为双类别。结构要求（签名即契约）：
  - `CATEGORIES=(wpf avalonia)`；不用关联数组（兼容 bash 3.2），用 `case` 函数：`gate_pattern <cat>` → `'*.xaml'` / `'*.axaml'`；`gate_skill <cat>` → `wpf-code-review` / `avalonia-code-review`
  - `current_hash <cat>`：`git diff --cached -- "$(gate_pattern <cat>)" | sha256sum | cut -d' ' -f1`
  - 非 git 仓库分支、`GIT_DIR`、`MARK_DIR` 逻辑沿用现有，`mark` 模式在非 git 仓库仍 `exit 1`
  - `mark` 模式：`$2` 必须属于 `CATEGORIES`，否则向 stderr 打印 `用法: review-gate.sh mark <wpf|avalonia>` 并 `exit 1`；合法则把 `current_hash` 写入 `$MARK_DIR/<cat>.hash` 并提示已标记
  - 检测模式顺序不变：先对每类取 `git diff --cached --name-only -- <pattern>`，**全部为空则在读 stdin 之前 `exit 0`**；再读 stdin 并用现有 `GIT_COMMIT_RE` 判断是否 `git commit`，否则 `exit 0`；再**逐类**比对哈希，把未通过的类别收集起来
  - 有未通过类别时向 stderr 输出一条提示：逐类列出「文件清单、应调用的 skill、对应的 `bash "<脚本路径>" mark <cat>` 命令」，随后 `exit 2`；全部通过 `exit 0`

- [ ] **Step 4: 重跑验证，确认全绿**

Run: 同 Step 2 命令
Expected: 全部用例 `PASS`，脚本退出码 0

- [ ] **Step 5: 跑仓库钩子配置门禁**

Run: `python .githooks/check_hook_configs.py .`
Expected: 退出码 0（`hooks.json` 未改，该检查应保持通过）

### Task 3: 钩子文档与规则登记

**Files:**
- Modify: `plugins/optimus-frontend/hooks/README.md`
- Modify: `.claude/rules/hook-conventions.md:45`

**Interfaces:**
- Consumes: Task 2 的命令行契约（`mark <wpf|avalonia>`、两个 `.hash` 标记文件）

- [ ] **Step 1: 改 hooks README**

保留「规范依据」整节不动。改动点：
  - 一级标题 `# WPF 代码审查门禁 Hook` → `# WPF / Avalonia 代码审查门禁 Hook`
  - 「功能说明」：改为拦截 `git commit`（含 `--amend`），staged 含 `.xaml` 须先经 `wpf-code-review`，staged 含 `.axaml` 须先经 `avalonia-code-review`；两类各自独立判定
  - 「工作原理」：哈希按类别分别计算；标记文件为 `.git/optimus-review-marks/wpf.hash` 与 `avalonia.hash`；某类无 staged 改动则该类不拦
  - 「使用方式」第 3 步命令改为两条：`... review-gate.sh mark wpf` 与 `... review-gate.sh mark avalonia`，注明只标记已审查的那一类；同一次提交含两类时拦截提示会一并列出
  - 「局限性」「依赖」两节不动

- [ ] **Step 2: 改规则登记表**

`.claude/rules/hook-conventions.md` 第 45 行用途列改为：`staged `.xaml` 未经 `wpf-code-review`、或 staged `.axaml` 未经 `avalonia-code-review` 时拦 `git commit``。其余行不动。

- [ ] **Step 3: 验证文档与脚本一致**

Run: `grep -n "mark " plugins/optimus-frontend/hooks/README.md` 与 `grep -n "mark" plugins/optimus-frontend/hooks/pretooluse/review-gate.sh`
Expected: README 中出现的每条 `mark` 命令形式都能在脚本的用法/提示中找到同形；README 不再出现无参数的 `mark` 命令

### Task 4: 清单与版本号

**Files:**
- Modify: `plugins/optimus-frontend/.claude-plugin/plugin.json`
- Modify: `plugins/optimus-frontend/.codex-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `.agents/plugins/marketplace.json`

**Interfaces:**
- Consumes: Global Constraints 中的统一 frontend 描述文案（下称「统一文案」）

- [ ] **Step 1: 两份 `plugin.json`**

两份都：`version` → `2.1.0`；`description` → 统一文案。仅 Codex 一份另改 `interface`：`shortDescription` → `桌面前端开发工具集（WPF + Avalonia）`；`longDescription` → 统一文案；`defaultPrompt` 数组唯一元素 → `开始一段 WPF 或 Avalonia 桌面前端开发任务`。其余字段（含 `skills`、`displayName`、`capabilities`）不动。

- [ ] **Step 2: `.claude-plugin/marketplace.json`**

整体删除 `optimus-avalonia` 条目（含前后逗号处理，保证 JSON 合法）；`optimus-frontend` 条目 `description` → 统一文案；顶层 `version` `14.4.0` → `15.0.0`；条目内**不写** `version`。

- [ ] **Step 3: `.agents/plugins/marketplace.json`**

整体删除 `optimus-avalonia` 条目；该文件无顶层 `version`，不新增。

- [ ] **Step 4: 验证**

Run: `python -c "import json;[json.load(open(f,encoding='utf-8')) for f in ['.claude-plugin/marketplace.json','.agents/plugins/marketplace.json','plugins/optimus-frontend/.claude-plugin/plugin.json','plugins/optimus-frontend/.codex-plugin/plugin.json']];print('json ok')"`，再 `grep -c "optimus-avalonia" .claude-plugin/marketplace.json .agents/plugins/marketplace.json`
Expected: 输出 `json ok`；两个 marketplace 的计数均为 `0`；两份 `plugin.json` 的 `version` 同为 `2.1.0`

### Task 5: 根 README 与 eval、CHANGELOG

**Files:**
- Modify: `README.md`（插件表第 14 行附近、依赖表第 32 行附近、示例第 69/123 行附近）
- Modify: `plugins/optimus-frontend/skills/avalonia-code-review/evals/01-compiled-binding-and-styles/prompt.md:5`
- Modify: `plugins/optimus-frontend/skills/avalonia-code-review/SKILL.md`（仅 frontmatter `metadata.version`）
- Modify: `plugins/optimus-frontend/skills/avalonia-code-review/CHANGELOG.md`（顶部新增条目）

- [ ] **Step 1: 根 README 插件表**

删除 `optimus-avalonia` 一行；`optimus-frontend` 一行职责改为：`桌面前端开发（WPF + Avalonia）：MasterGo 设计稿转页面与组件库、SVG 转 XAML、XAML/AXAML 代码审查、Avalonia 文档 MCP 路由开发与 WPF 迁移 Avalonia、Linux deb 发布`。

- [ ] **Step 2: 根 README 依赖表**

删除 `optimus-avalonia` 一行；`optimus-frontend` 一行依赖改为：`MasterGo MCP（设计稿读取）、Python 3；Avalonia 相关 skill 另需 Avalonia Docs MCP（由 旧 MCP 插件 提供，无需认证），实际迁移/构建依赖目标项目的 .NET SDK`。

- [ ] **Step 3: 根 README 示例前缀**

两处 `optimus-avalonia:avalonia-wpf-migration`（`/` 与 `@` 两种写法）前缀改为 `optimus-frontend:`。

- [ ] **Step 4: 改 eval 与版本**

eval `prompt.md` frontmatter 的 `plugins:` 列表项 `optimus-avalonia` → `optimus-frontend`。`SKILL.md` frontmatter `metadata.version: "1.0.1"` → `"1.0.2"`，正文不动。`CHANGELOG.md` 顶部按既有格式新增 `## [1.0.2] - 2026-10-30` / `### Changed`：一条，说明 skill 随 `optimus-avalonia` 并入 `optimus-frontend`，调用前缀改为 `/optimus-frontend:avalonia-code-review`，eval 的 `plugins` 字段同步。

- [ ] **Step 5: 验证**

Run: `grep -n "optimus-avalonia" README.md plugins/optimus-frontend/skills/avalonia-code-review/evals -r`
Expected: 无输出

### Task 6: 知识库引用同步

**Files:**
- Modify: `knowledge-base/tools/reference/build-mcp.md`（第 21 行"备注"）
- Modify: `knowledge-base/tools/index.jsonl`（第 3 行 `tools.ref.build-mcp` 条目内的同一提及）
- Modify: `knowledge-base/tools/README.md`（第 3 行版本行）
- Modify: `knowledge-base/tools/CHANGELOG.md`（顶部新增条目）

- [ ] **Step 1: 替换两处提及**

两个文件里的 `optimus-avalonia` 一律替换为 `optimus-frontend`，句子其余部分不动。`index.jsonl` 是 JSON Lines，替换后该行仍须是合法 JSON。

- [ ] **Step 2: 升版本**

`README.md` 版本行 `1.0.0` → `1.0.1`；`CHANGELOG.md` 顶部新增 `## [1.0.1] - 2026-10-30` / `### Changed`：一条，说明 Build MCP 条目备注中的插件名随 `optimus-avalonia` 并入 `optimus-frontend` 同步。两处版本须一致。

- [ ] **Step 3: 跑知识库一致性校验**

Run: `python .claude/skills/knowledge-base-maintain/scripts/check_index.py` 与 `python .claude/skills/knowledge-base-maintain/scripts/check_refs.py`
Expected: 两个均退出码 0

### Task 7: 全量验证

**Files:** 无改动（只读验证；发现问题回到对应任务修）

- [ ] **Step 1: 全仓残留扫描**

Run: `grep -rIn "optimus-avalonia" . --exclude-dir=.git --exclude-dir=node_modules`
Expected: 命中仅限允许清单——各 skill 的 `CHANGELOG.md`、`docs/superpowers/specs/2026-09-15-*`、`docs/todo-list/*`、本 spec 与本 plan；出现其他任何文件则回去修

- [ ] **Step 2: 目录与镜像核对**

Run: `ls plugins/optimus-frontend/skills | wc -l` 与 `test ! -e plugins/optimus-avalonia && echo gone`
Expected: `10` 与 `gone`

- [ ] **Step 3: 八项提交门禁**

Run: `git add -A` 后 `sh .githooks/pre-commit`（暂存只为让门禁看到全部改动，不提交）
Expected: 退出码 0；若报"版本不同值"或"悬空引用"，回到 Task 4 / 对应任务修

- [ ] **Step 4: 回归钩子矩阵**

Run: 同 Task 2 Step 4 的命令
Expected: 全部 `PASS`

- [ ] **Step 5: Python 单元测试（9 个目录）**

Run: 按 `AGENTS.md`「本地测试」节列出的 9 条 `python -m unittest discover` 命令逐个执行
Expected: 全部通过（本改动不触及这些目录，仅防路径连带影响）

- [ ] **Step 6: 本地加载验证**

按 `test-locally` skill，用 `--plugin-dir` 加载本仓，确认 `optimus-frontend` 下可发现 `avalonia`、`avalonia-code-review`、`avalonia-deb-release`、`avalonia-wpf-migration` 四个命令，且不再出现 `optimus-avalonia:*`。若本机无法交互式验证，如实记为"未覆盖"，不得声称已验证。

### Task 8: 提交、PR 与收尾

**Files:** 无新增改动

- [ ] **Step 1: 经 `commit-cc-plugin` skill 提交**

调用该 skill，不手写 git 流程。提交范围：Task 1–6 全部改动，加上 `docs/superpowers/specs/2026-10-30-merge-avalonia-into-frontend-design.md` 与本 plan。type 用 `refactor`（须与分支名前缀一致），scope 可用 `plugins`；message 须点明破坏性变更：已安装 `optimus-avalonia` 的用户需改装 `optimus-frontend`，调用前缀由 `/optimus-avalonia:` 变为 `/optimus-frontend:`。末尾带系统指定的 Co-Authored-By 行。

- [ ] **Step 2: 推送并开 PR**

走「特性分支 → PR」，PR 描述末尾带指定的 `Generated with Claude Code` 行。PR 描述须包含：破坏性变更说明、版本号变化（frontend `2.1.0`、marketplace `15.0.0`）、钩子新增 `.axaml` 门禁及 `mark <类别>` 新用法。

- [ ] **Step 3: 等待 6 个必需检查全绿**

必需检查：`gates-hooks`、`gates-tests`、`gates-data`、`plugin-validate`、`new-skill-eval-case`、`actionlint`。其中 `plugin-validate`、`new-skill-eval-case`、`actionlint` 无本地等价命令，只能在 PR 上确认。任一红灯先读日志定位，不得 `--no-verify` 或绕过。

- [ ] **Step 4: 合并后**

PR 由用户决定是否 squash merge；不要自行合并。
