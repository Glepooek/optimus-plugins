# 仓库治理加固设计

**日期：** 2026-11-28

**状态：** 已按三轮 review 修订；按用户裁决（2026-11-28）删除全部付费 eval 内容，待实施

**评审依据：**

- `docs/superpowers/reports/2026-11-28-repository-governance-hardening-review.md`
- `docs/superpowers/reports/2026-11-28-repository-governance-hardening-review-2.md`
- `docs/superpowers/reports/2026-11-28-repository-governance-hardening-review-3.md`

## 1. 背景与问题定义

本次加固处理两类已经有证据的问题：

1. 单元测试目录在 CI 与维护文档中手工列举，注释中的目录数量与实际列表不符；
2. 本地 hook、CI 与维护文档分别描述同一组门禁，执行入口与说明容易分叉。

评审确认的当前口径是：仓库有 **8 个逻辑检查，由 6 个 Python 脚本实现**。两者不是同一个计数单位，因此不新增“门禁数量”自动校验，也不改写为“8 个脚本”。

同时清理以下已失真的状态性文本：

- CI/actionlint 注释中的“9 个测试目录”；
- CI 注释中的“10 个自建插件”；
- “48 个对外发布 skill”和“48 处存量越界”；
- `skill-eval.yml` 注释中已经不存在的 Jenkins 20-case 论证（只改注释，不改 workflow 行为）；
- marketplace “13 条目”不删除历史事实，但改写为带日期的历史测量，避免被理解成当前规模。

## 2. 目标

完成后应满足：

- 新增符合约定位置的 `test_*.py` 时，CI 无需手工补目录；
- 六个既有门禁脚本只有一个 catalog 与一个 Python runner；
- `.githooks/pre-commit` 成为薄入口，CI 仍执行 `sh .githooks/pre-commit`，从而同时验证 shell 包装和 Python runner；
- runner 从任意当前工作目录调用时，都以仓库根执行；
- 现有每项门禁的设计理由不因薄包装改造而丢失。

## 3. 非目标

本次不做：

- 不生成 Claude/Codex 能力与依赖矩阵；
- 不引入 repository-fact marker 或文档数字强制占位机制；
- 不新增 `precommit_checks` 计数；
- 不新增 PowerShell `.ps1` 包装；PowerShell 直接运行 Python runner；
- 不修改 `plugins/*`，因此不触发插件版本或 darwin-skill 门禁；
- 不修改六个 required status check 的 job 名；
- 不把收费的 `skill-eval` 加入 PR required checks；
- **不涉及任何付费内容**（用户裁决，2026-11-28）：不运行 `claude plugin eval`，不做 target / runs 实验，不建 eval policy 或 baseline，不改 `skill-eval.yml` 的执行逻辑（含凭据预检、参数、artifact 上传），不裁决 B2。B2 保持未决，`skill-eval.yml` 中 `--runs 1` 的注释须如实说明该冲突仍待裁决。

## 4. 单元测试自动发现

### 4.1 支持范围

测试发现只覆盖仓库已经采用的三类位置：

```text
.githooks/test_*.py
.claude/skills/*/scripts/test_*.py
plugins/*/skills/*/scripts/test_*.py
```

实现不得无边界递归扫描整个仓库，以免把文档样例、fixture 或第三方目录中的 `test_*.py` 当成测试套件。

### 4.2 执行语义

发现器返回去重、排序后的目录。执行器对每个目录分别运行：

```text
python -m unittest discover -s <directory> -p test_*.py
```

所有目录都必须执行；某一目录失败后仍继续执行其余目录，最后汇总失败并返回非零。发现结果为空时必须失败，避免错误工作目录产生假绿。

## 5. 统一门禁 runner

### 5.1 Catalog 口径

catalog 登记现有 **6 个脚本**，并保留它们覆盖 **8 个逻辑检查**的映射：

| 脚本 | 逻辑检查 |
|---|---|
| `check_plugin_versions.py` | 两份插件 manifest 版本一致 |
| `check_hook_configs.py` | hook 配置契约 |
| `check_external_entries.py` | 外部条目与登记一致性 |
| `check_skill_mirrors.py` | 维护型 skill 的两处镜像与符号链接模式，共 3 项 |
| `check_new_skill_eval_case.py --all` | eval case 目录完整性 |
| `check_plugin_self_contained.py` | 插件安装后引用仍可解析 |

不新增为了“凑数量”而存在的 gate。

### 5.2 仓库根与进程模型

runner 必须用下式定位仓库根：

```python
Path(__file__).resolve().parents[1]
```

不得使用调用者当前工作目录作为仓库根。子进程使用 `sys.executable`，`cwd` 固定为仓库根。

runner 逐项执行全部 gate；单项失败或进程启动异常都记为失败，但不阻止后续 gate 运行。结束时打印失败项汇总并以 1 退出。

### 5.3 说明文字的迁移

当前 `.githooks/pre-commit` 中每项检查旁的“为什么”属于治理知识，不得随着薄包装删除。实施时：

- 将每项专属说明移到 `repository_gates.py` 对应 `Gate` 定义旁；
- `.githooks/README.md` 继续承载跨 gate 的详细判据、历史事故与 CI 关系；
- 不把大段理由复制进 runner 执行代码。

### 5.4 三个执行入口

- 本地 hook：`.githooks/pre-commit` 只负责定位自身并执行 Python runner；
- PowerShell：直接运行 `python .githooks/run_repository_gates.py`；
- CI：`gates-hooks` 继续执行 `sh .githooks/pre-commit`。

CI 不直接绕过 shell wrapper 调 runner，因为 wrapper 本身也是需要验证的交付物。

## 6. 状态性文字清理原则

- 当前规模数字没有持续阅读价值时，改成语义描述，不新增另一个自动生成副本；
- 历史测量必须带日期或明确过去时，不能伪装成当前事实；
- “全部发布 skill”不得误写成“至少一个 skill”；
- 保留仍然成立的风险解释，只删除已失去前提的 Jenkins case 论证；
- `.githooks/README.md` 明确“8 个逻辑检查 / 6 个脚本 / 1 个 runner”的关系。

## 7. 验收标准

- 自动发现覆盖当前全部 8 个测试目录，并有允许/拒绝路径单测；
- `run_unit_tests.py` 从非仓库 cwd 调用仍定位正确；
- gate catalog 只有 6 个既有脚本，并能说明 8 个逻辑检查；
- gate runner 在中间失败或启动异常时仍执行其余项，最后正确返回非零；
- `sh .githooks/pre-commit`、直接 Python runner 与 CI 使用同一 catalog；
- `ci.yml` 的 `gates-hooks` 仍运行 shell wrapper；
- 过期数字与 Jenkins 注释扫描无残留；
- `skill-eval.yml` 只有注释行变化，执行步骤、参数与触发方式零改动；
- `plugins/*` 无 diff；
- 现有门禁、全部 unittest 与三项数据一致性检查通过。
