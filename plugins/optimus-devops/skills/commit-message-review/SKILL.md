---
name: commit-message-review
description: 审查拟提交或已有 Git commit message 是否符合随插件分发的 Git 提交信息规则，包括 Conventional Commits、变更意图、破坏性变更和 AI 协作者 footer。用户要求审查、review、检查、改写或生成 Git 提交信息，或在准备 git commit / 提交代码、已拟好 commit message 需要提交前把关时使用；不执行 git commit、amend、push 或绕过 hook。
metadata:
  version: "1.0.6"
  author: desktop client team
  category: quality
compatibility: 审查粘贴的提交信息不需要本地依赖；读取指定 commit 或将信息与暂存改动比对时，需要在 Git 仓库中运行 Git。
allowed-tools: Read Bash Grep
---

# Git 提交信息审查

审查提交信息的合规性与表达质量，给出可执行的修正建议。此 skill 是只读传感器：它不暂存文件、不修改历史、不创建提交，也不替代 hook 或敏感信息扫描。本 skill 含 0 个阻塞式人工确认点，因为它不执行写入或其他不可逆操作。

规范依据以 `references/commit-message-rules.md` 为准。该文件随本 skill 一起分发，覆盖 Conventional Commits、变更意图、破坏性变更与 AI footer 的审查判据。

## Step 1：确认审查对象与范围

先从用户的请求中收集以下信息；已经提供的内容不得重复询问。

| 信息 | 必需性 | 说明 |
|---|---|---|
| 完整提交信息 | 必需 | 优先审查用户粘贴的原文，保留 subject、body 和 footer 的真实换行。 |
| Git commit 引用 | 与完整信息二选一 | 如用户明确说审查 `HEAD` 或某个 hash，读取该提交的 message。 |
| 是否按 AI 协作完成本次改动或采用本 skill 的改写 | 必需 | AI 实质生成或改写此次提交内容时必须有 AI footer；无法确认时按“是”处理并标为待用户确认。 |
| 是否与暂存改动核对 | 可选 | 只有用户要求核对意图、范围或原子性时才读取暂存 diff。 |

缺少“完整提交信息”且未给 commit 引用时，一次性请求其中一项。不得把摘要、文件名或分支名臆造成提交信息。

读取已有提交时，先解析为 commit 对象，再读取 message，避免把未验证的参数作为 Git 选项：

```bash
git rev-parse --verify "<用户提供的引用>^{commit}"
git show -s --format=%B <上一步解析出的对象ID>
```

只有审查已有提交、读取暂存改动或执行仓库特定检查时，才运行以下前置校验；失败时停止对应的 Git 读取，仍可审查用户直接粘贴的 message：

```bash
git rev-parse --is-inside-work-tree
git --version
```

用户要求与暂存改动核对时，仅读取：

```bash
git diff --cached --stat
git diff --cached
```

### 输入与读取失败处理

| 触发条件 | 处置 |
|---|---|
| 未提供完整 message，也没有明确 commit 引用 | 停止审查，一次性请求粘贴完整 message 或提供一个 commit 引用。 |
| `git rev-parse --verify` 失败 | 不把引用猜成 `HEAD` 或其他提交。报告引用不可解析，并请求有效引用或 message 原文。 |
| Git 仓库校验失败 | 不执行 Git 读取；请求直接粘贴 message，或让用户在正确的仓库目录重新调用。 |
| 用户要求核对暂存改动但暂存区为空 | 报告无法验证 message 与提交内容的一致性；仍完成对 message 文本的规则审查。 |
| message 中只有字面 `\\n` 而非真实换行 | 按单行 message 审查，并提示用户用真实换行提供 body 和 footer 后再复核。 |
| 粘贴内容或读取到的 message 为空或仅含空白 | 按“未提供完整 message”处理：停止审查，请求有效 message，不输出 PASS。 |
| 一次提供多条 message | 逐条独立审查，每条单独给出结论表；不合并成一个总体结论，也不拿一条的结果代替另一条。 |
| message 中疑似含密钥、令牌或密码 | 报告和“建议的完整 message”中用 `<已省略敏感内容>` 代替原文，提示用户移除后再提交；仍完成其余规则审查，并在覆盖范围写明“敏感信息未扫描”。 |

## Step 2：按规则审查 message

逐项检查，并区分必须修复与建议改进。

### 必须修复

| 检查项 | 通过条件 | 不通过时的修正方向 |
|---|---|---|
| Conventional Commits 标题 | 第一行符合 `<type>[(<scope>)][!]: <description>`，冒号后有一个空格。 | 改成合法标题，不保留自造前缀、缺失冒号或空描述。 |
| type | 必须是 `feat`、`fix`、`docs`、`style`、`refactor`、`perf`、`test`、`build`、`ci`、`chore` 或 `revert`，且能表达实际变更性质。 | 按实际意图替换 type；不要为了通过格式检查而随意选 `chore`。 |
| 变更意图 | 标题和 body 能说明变更做了什么、为何需要；不得是 `update`、单独的 `fix`、`wip` 或同等无意义描述。 | 写出对象和结果，必要时在 body 补充原因。 |
| 破坏性变更 | 若 message 或暂存改动明确移除、改名或改变兼容契约，必须在 header 使用 `!` 或在 footer 写 `BREAKING CHANGE: <迁移说明>`。 | 标记 breaking change，并提供受影响方可执行的迁移说明；两种标记可同时存在但不是强制。 |
| AI 协作者 | 本次改动或最终 message 由 AI 实质协助时，末尾必须有每位实际模型各一行的 `Co-Authored-By: <实际模型名> <noreply@供应商域名>` footer。 | 用户在请求中给出模型名和供应商域名时原样使用；未给出时，“建议的完整 message”中的 trailer 必须写成 `Co-Authored-By: <待确认的实际模型名> <noreply@待确认的供应商域名>`，并要求用户确认。禁止用审查者自身的模型名或常见邮箱填充。 |

### 建议改进

| 检查项 | 建议 |
|---|---|
| scope | scope 可选；跨模块或影响范围不清时建议补充简短 scope。scope 不应只重复 type。 |
| description | 英文 description 建议使用小写祈使语气、结尾不加句号；中文保持简洁且说明结果。 |
| body | 多行 message 的 body 与标题之间空一行；body 解释动机、影响或实现要点，避免逐行复述 diff。 |
| footer | 每个 footer 独占一行，与正文之间空一行；使用 `Refs: #123`、`Reviewed-by:` 等结构化 trailer，而不是混在正文。 |
| 原子性 | 用户要求核对暂存改动时，确认 message 只覆盖一个逻辑变更。无法从 message 本身判断时，明确写“未核对暂存改动，原子性未验证”。 |

不要把“有替代方案”误判为 breaking change。只有旧接口、命令、配置或行为被移除或不兼容改变时才要求 breaking 标记。

## Step 3：给出审查结论

按以下格式输出，引用用户原文时只摘录必要片段，避免泄露 message 中可能存在的敏感内容：

````markdown
## Commit message review

结论：PASS / NEEDS_CHANGES / ADVISORY

| 级别 | 规则 | 发现 | 建议 |
|---|---|---|---|
| 必须修复 / 建议 | 规则（对应 `references/commit-message-rules.md` 的条目） | 具体问题 | 可执行修正 |

### 建议的完整 message
```text
<仅在已有足够事实时给出；不编造 scope、原因、issue 编号、模型名或邮箱>
```

### 覆盖范围
- 已审查：标题 / body / footer / breaking-change 信号 / AI footer
- 未验证：<例如“未要求读取暂存 diff，原子性与提交内容安全性未验证”>
````

结论含义：

- `PASS`：没有发现规则参考中的必须修复项；可同时列出不阻塞提交的建议。
- `NEEDS_CHANGES`：存在格式、意图、breaking-change 信号或必需 AI footer 缺失等必须修复项。
- `ADVISORY`：message 本身可接受，但因为缺少 diff、AI 协作事实或迁移影响等信息而无法完成某些质量判断。

建议的完整 message 必须保留已经确认的事实。对未知的 scope、版本、issue、迁移步骤和 AI 身份使用明确占位提示或省略，不得编造。

## 不要做什么

- 不因标题格式通过就判定整个提交安全、原子或已通过 hook；这些结论需要提交内容、hook 或 CI 的独立证据。
- 不编造 scope、变更原因、issue 编号、迁移步骤、实际模型名或 AI 邮箱来凑一条“完整”message；审查者自身的模型名也不是用户确认过的事实，不得写入 trailer。
- 不把 `update`、单独的 `fix`、`wip` 等无意义描述换成另一句同样空泛的词；修正必须说明变更对象和结果。
- 不把新增替代方案直接标为 breaking change；只有旧契约被移除或发生不兼容变化才标记。
- 不执行 `git add`、`git commit`、`git commit --amend`、`git push`、强制推送或 `--no-verify`。本 skill 只审查，不替用户改写 Git 历史。

## 边界与交接

- 插件的 `PreToolUse` 提交门禁（仅 Claude Code）会要求 `git commit` 前先运行本 skill；PASS / ADVISORY 后由调用方按拦截提示执行 `mark` 并重新提交，本 skill 自身不写标记、不提交。
- 该 skill 不执行 `git commit`、`git commit --amend`、`git push`、`git add`、`git stash` 或 `--no-verify`。用户确认 message 后，将实际提交交给所在仓库既有的提交工作流。
- 不因 message 合规而宣称 hook、原子性、敏感信息或大文件检查已通过。提交内容安全检查仍由仓库 hook 与 CI 承担，且不得绕过。
- 已推送提交若缺 AI footer 或存在其他 message 问题，不建议擅自改写历史；说明问题并让用户决定后续修复方式。

## 使用示例

```text
审查这个提交信息：
feat(auth): add device authorization

Allow CLI clients to authenticate without storing a client secret.

Refs: #482

Co-Authored-By: <当前会话实际模型> <noreply@供应商域名>
```

```text
审查 HEAD 的提交信息，并和当前暂存改动核对是否一致。
```
