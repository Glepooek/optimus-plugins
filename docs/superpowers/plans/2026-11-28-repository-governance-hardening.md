# Repository Governance Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 统一仓库门禁与测试执行入口，清除失真的维护文字。按用户裁决（2026-11-28），本计划不含任何付费 eval 内容。

**Architecture:** Python 标准库提供测试目录发现器、六脚本 gate catalog、门禁 runner 与 unittest runner；shell hook 保持为薄入口且继续由 CI 执行。`skill-eval.yml` 只清理失效注释，不改执行逻辑。

**Tech Stack:** Python 3 标准库、POSIX sh、PowerShell、GitHub Actions YAML、JSON、Markdown、`unittest`

**Spec:** `docs/superpowers/specs/2026-11-28-repository-governance-hardening-design.md`

**Review:** `docs/superpowers/reports/2026-11-28-repository-governance-hardening-review.md`

**Second Review:** `docs/superpowers/reports/2026-11-28-repository-governance-hardening-review-2.md`

**Third Review:** `docs/superpowers/reports/2026-11-28-repository-governance-hardening-review-3.md`

## Global Constraints

- 不修改 `plugins/*`；若实现确实需要修改，停止并重新评估插件版本、skill 版本与 darwin-skill 门禁。
- 不修改 required status check job 名：`gates-hooks`、`gates-tests`、`gates-data`、`plugin-validate`、`new-skill-eval-case`、`actionlint`。
- `skill-eval` 保持 `workflow_dispatch`，不得加入 required checks。
- 新增 Python 代码只使用标准库。
- 新增测试放 `.githooks/`，不制造新的测试目录。
- 编辑仓库文件时使用当前 harness 提供的文件编辑工具；不得要求另一 harness 必须具备某个专有工具。
- 不手动提交；完成后使用仓库规定的 `commit-cc-plugin` 流程，禁止 `--no-verify`。
- **不运行任何会产生费用的命令**（含 `claude plugin eval`），不建 eval policy / baseline，不改 `skill-eval.yml` 的执行步骤、参数与触发方式，不裁决 B2。

---

### Task 0: 建立分支与免费基线

**Files:**
- Read: `docs/superpowers/specs/2026-11-28-repository-governance-hardening-design.md`
- Read: `.githooks/pre-commit`
- Read: `.githooks/README.md`
- Read: `.github/workflows/ci.yml`
- Read: `.github/workflows/skill-eval.yml`

- [ ] **Step 1: 检查工作树并保护既有改动**

Run:

```powershell
git status --short
git diff --name-only
```

Expected: 记录已有用户改动；后续不覆盖与本计划无关的文件内容。

- [ ] **Step 2: 创建实施分支**

Run:

```powershell
git switch -c feat/repository-governance-hardening
```

Expected: 当前分支为 `feat/repository-governance-hardening`。若分支已存在，先检查归属，不重建或覆盖。

- [ ] **Step 3: 运行现有门禁基线**

Run:

```powershell
python .githooks/check_plugin_versions.py .
python .githooks/check_hook_configs.py .
python .githooks/check_external_entries.py .
python .githooks/check_skill_mirrors.py .
python .githooks/check_new_skill_eval_case.py --all .
python .githooks/check_plugin_self_contained.py
```

Expected: 六个脚本均退出 0；不要把“六个脚本”误写成“六个逻辑检查”。

- [ ] **Step 4: 运行现有测试与数据基线**

按当前 `AGENTS.md` 的 8 个目录逐项运行 `unittest discover`，再运行：

```powershell
python .claude/skills/knowledge-base-maintain/scripts/check_index.py
python .claude/skills/knowledge-base-maintain/scripts/check_refs.py
python .claude/skills/sync-cc-tips/scripts/validate_tips.py
```

Expected: 既有测试与三项数据检查全绿。记录实际用例数，不把历史数字写成新的长期断言。

---

### Task 1: 自动发现 unittest 目录

**Files:**
- Create: `.githooks/repository_inventory.py`
- Create: `.githooks/test_repository_inventory.py`

**Interface:** `discover_unit_test_directories(root: Path) -> tuple[str, ...]`

- [ ] **Step 1: 写失败测试**

覆盖三类允许路径、`docs/**/test_*.py` 拒绝、同目录去重与稳定排序。

- [ ] **Step 2: 确认测试先红**

```powershell
python -m unittest discover -s .githooks -p 'test_repository_inventory.py' -v
```

- [ ] **Step 3: 实现固定 glob 发现器**

```python
TEST_PATTERNS = (
    '.githooks/test_*.py',
    '.claude/skills/*/scripts/test_*.py',
    'plugins/*/skills/*/scripts/test_*.py',
)
```

不要递归扫描整个仓库。

- [ ] **Step 4: 跑绿并核对真实仓库**

```powershell
python -m unittest discover -s .githooks -p 'test_repository_inventory.py' -v
python -c "import sys; from pathlib import Path; sys.path.insert(0, '.githooks'); from repository_inventory import discover_unit_test_directories; print(*discover_unit_test_directories(Path('.').resolve()), sep='\n')"
```

Expected: 发现当前全部测试目录，不把数量写死进实现。

---

### Task 2: 建立六脚本 gate catalog 与 runner

**Files:**
- Create: `.githooks/repository_gates.py`
- Create: `.githooks/run_repository_gates.py`
- Create: `.githooks/test_run_repository_gates.py`

**Interfaces:**

```python
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
GATES: tuple[Gate, ...]
run_gates(root: Path, gates: tuple[Gate, ...], runner=subprocess.run) -> int
```

- [ ] **Step 1: 写 runner 失败测试**

覆盖全通过、中间失败仍继续、启动异常仍继续、`sys.executable`、固定 `cwd`，以及从仓库外 cwd 调 CLI 仍使用 `Path(__file__).resolve().parents[1]`。

- [ ] **Step 2: 确认测试先红**

```powershell
python -m unittest discover -s .githooks -p 'test_run_repository_gates.py' -v
```

- [ ] **Step 3: 定义六项 catalog**

登记：

```text
check_plugin_versions.py .
check_hook_configs.py .
check_external_entries.py .
check_skill_mirrors.py .
check_new_skill_eval_case.py --all .
check_plugin_self_contained.py
```

在每个 `Gate` 定义旁迁入原 `.githooks/pre-commit` 的专属说明，尤其保留 manifest 不互相覆盖、hook 静默失效、外部条目锁 SHA、mirror 两条正交排除理由与 `--no-index`、eval 双模式边界、self-contained 安装边界。注明 `check_skill_mirrors.py` 覆盖 3 个逻辑检查，因此是 6 个脚本、8 个逻辑检查。

- [ ] **Step 4: 实现 runner**

逐项打印稳定名称；所有 gate 都运行；末尾汇总失败名称。CLI `main()` 固定使用 `REPOSITORY_ROOT`，不接受调用者仓库根。

- [ ] **Step 5: 跑绿并真实执行**

```powershell
python -m unittest discover -s .githooks -p 'test_run_repository_gates.py' -v
python .githooks/run_repository_gates.py
```

---

### Task 3: 建立 unittest runner 并改造 hook/CI

**Files:**
- Create: `.githooks/run_unit_tests.py`
- Create: `.githooks/test_run_unit_tests.py`
- Modify: `.githooks/pre-commit`
- Modify: `.githooks/README.md`
- Modify: `.github/workflows/ci.yml`
- Modify: `AGENTS.md`

- [ ] **Step 1: 写 unittest runner 失败测试**

覆盖每个发现目录都执行、中间失败仍继续、空发现失败、使用 `sys.executable`，以及从仓库外 cwd 调用仍定位仓库根。

- [ ] **Step 2: 确认测试先红**

```powershell
python -m unittest discover -s .githooks -p 'test_run_unit_tests.py' -v
```

- [ ] **Step 3: 实现 unittest runner**

每个目录执行：

```python
[
    sys.executable,
    '-m',
    'unittest',
    'discover',
    '-s',
    directory,
    '-p',
    'test_*.py',
]
```

工作目录固定仓库根，打印发现目录与失败汇总。

- [ ] **Step 4: 把 pre-commit 收窄为薄入口**

```sh
#!/bin/sh
set -u
HOOK_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python "$HOOK_DIR/run_repository_gates.py"
```

Task 2 已迁移逐项理由后才删除旧注释。

- [ ] **Step 5: 修改 CI，但继续测试 shell wrapper**

`gates-hooks` 保持：

```yaml
- run: sh .githooks/pre-commit
```

`gates-tests` 替换为：

```yaml
- name: 运行自动发现的单元测试目录
  run: python .githooks/run_unit_tests.py
```

- [ ] **Step 6: 更新维护文档**

`AGENTS.md` 将门禁与 8 条 unittest 命令分别改为两个 Python runner，并说明自动发现，不保留需人工同步的目录数量断言。

`.githooks/README.md` 明确：8 个逻辑检查由 6 个脚本实现；`repository_gates.py` 是 catalog 真源；pre-commit 与 CI 调同一 runner；CI 仍逐字执行 shell wrapper；暂存区无关和 eval 双模式说明完整保留。

- [ ] **Step 7: 验证三个入口**

```powershell
python -m unittest discover -s .githooks -p 'test_run_*.py' -v
python .githooks/run_repository_gates.py
python .githooks/run_unit_tests.py
sh .githooks/pre-commit
```

Expected: 全部通过；本机没有 `sh` 时，直接 Python 入口必须可运行，shell wrapper 由 Git Bash/CI 验证，不新增 `.ps1`。

---

### Task 4: 清理失真的计数与 eval 注释

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/actionlint.yml`
- Modify: `.github/workflows/skill-eval.yml`
- Modify: `.githooks/README.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: 修正测试目录文字**

- `9 个目录的单元测试` 改为自动发现语义；
- `actionlint.yml` 的“gates-tests 的 9 目录遍历”改为“gates-tests 的自动发现执行器”。

- [ ] **Step 2: 修正 plugin/marketplace/skill 文字**

- 两处“10 个自建插件在前”改为“自建插件在前、外部引用条目集中在末尾”；
- “CLI 2.1.270 / marketplace 13 条目”改为带日期的历史测量，例如“2026-09-13 当时的 marketplace 13 条目”；
- “48 个对外发布 skill”改为“全部对外发布 skill”；
- 删除“48 处存量越界”，改写为当前检查目的，不写失效规模。

- [ ] **Step 3: 删除 Jenkins 20-case 的过期依据**

从 `skill-eval.yml` 删除 Jenkins case 仍存在、其 `tool_used: Skill` 决定 ablation、其 `runs: 1` 无冲突等论证。保留非交互信任、不发布、避免默认双臂成本、预算上限不是首 run 硬阻断等仍成立的理由。`--runs 1` 一段改写为：该参数会覆盖 wpf-code-review 6 个 case 的 `runs: 3`，冲突已登记为 B2，**仍未裁决**。

只改注释行：完成后用 `git diff -- .github/workflows/skill-eval.yml` 确认所有 `+`/`-` 变更行去掉前导空白后都以 `#` 开头（或为空行）。

- [ ] **Step 4: 扫描残留**

```powershell
Select-String -Path '.github\workflows\ci.yml','.github\workflows\actionlint.yml','.github\workflows\skill-eval.yml','.githooks\pre-commit','.githooks\README.md','AGENTS.md' `
  -Pattern '9 个目录','10 个自建插件','48 个对外发布','48 处存量越界','jenkins-build 那 20','20 个 case'
```

Expected: 无失效断言；历史上下文确需保留时必须明确过去时和日期。

---

### Task 5: 全量验证与交付

**Files:**
- Verify: 本计划涉及的全部文件
- Verify: `plugins/` 无 diff

**Dependencies:** Tasks 1–4。

- [ ] **Step 1: 运行统一门禁与全部单测**

```powershell
python .githooks/run_repository_gates.py
python .githooks/run_unit_tests.py
```

- [ ] **Step 2: 运行 CI 同款 shell wrapper**

```bash
sh .githooks/pre-commit
```

- [ ] **Step 3: 运行数据一致性检查**

```powershell
python .claude/skills/knowledge-base-maintain/scripts/check_index.py
python .claude/skills/knowledge-base-maintain/scripts/check_refs.py
python .claude/skills/sync-cc-tips/scripts/validate_tips.py
```

- [ ] **Step 4: 检查范围、空白与残留**

```powershell
git diff --name-only -- plugins
git diff --check
Select-String -Path '.github\workflows\ci.yml','.github\workflows\actionlint.yml','.github\workflows\skill-eval.yml','.githooks\pre-commit','.githooks\README.md','AGENTS.md' `
  -Pattern '9 个目录','10 个自建插件','48 个对外发布','48 处存量越界','jenkins-build 那 20','20 个 case'
```

Expected: `plugins` 无 diff；无空白错误；无失效状态断言。

- [ ] **Step 5: 使用仓库规定流程提交与 PR**

触发 `commit-cc-plugin`，建议提交：

```text
feat(repo): unify governance runners and clean stale claims
```

PR 描述说明：统一 runner 与测试自动发现、过期文字清理、`skill-eval.yml` 仅改注释；required job 名未变化；付费 eval 相关工作（target / runs 实验、policy、baseline、B2 裁决）按用户裁决不在本次范围。

- [ ] **Step 6: 等待六个 required checks**

必须通过：`gates-hooks`、`gates-tests`、`gates-data`、`plugin-validate`、`new-skill-eval-case`、`actionlint`。若服务端 ruleset 与文档不一致，以 ruleset API 实时结果为准并修正文档，不改 job 名。

## Task Dependencies

- Task 0 是全部任务的基线。
- Task 1 和 Task 2 是 Task 3 的前置。
- Task 3 完成后才能安全删除旧 pre-commit 注释。
- Task 4 可与 Tasks 1–3 独立编辑，最终扫描在入口改造后执行。
- Task 5 依赖 Tasks 1–4。
