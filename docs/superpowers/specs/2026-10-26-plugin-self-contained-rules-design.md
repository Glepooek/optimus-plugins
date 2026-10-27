# 设计：插件运行时可自包含——知识库判据内聚

> 状态：待评审
> 日期：2026-10-26
> 触发问题：安装插件后 skill 找不到 `knowledge-base/`，`csharp-code-review` 退化为通用知识审查

## 1. 问题与意图

### 1.1 现象

用户从 marketplace 安装插件后，skill 的运行时指令要求 Claude「打开 `knowledge-base/csharp/rules/02-coding-style.md` 读取具体条款」。该路径是相对仓库根的 `../../../../knowledge-base/`——**在 `--plugin-dir` 开发模式下能解析，安装后不能**。安装单元是 `plugins/<name>/`，根目录以上的内容不在包内。

受影响的是**运行时以知识库为判据**的 skill：

| 插件 | skill | 知识库 | 性质 |
|---|---|---|---|
| optimus-backend-plugin | `csharp-code-review` | `csharp/` | 17 rules / 2244 行，审查清单逐类指向具体文件锚点 |
| optimus-frontend-plugin | `wpf-code-review` | `wpf/` | 17 rules / 1992 行，同上 |
| optimus-devops-plugin | `dotnet-diagnose-triage`、`dotnet-diagnose-autopilot`、agent `dotnet-diagnose` | `dotnet-debugging/` | 74 条判据，全部住在 `reference/`（1852 行） |
| optimus-devops-plugin | `project-analyze` | `wpf/`（3 个 rules 文件） | WPF 画像的命名判定与框架识别 |
| optimus-media-plugin | 11 个 `media-*` skill | `media/reference/` | 概念背景（选读，非判据） |

### 1.2 为什么必须修

不是「锦上添花」：skill 的核心价值就在这些判据上。判据读不到时，Claude 会用自身泛型知识补全，审查结果的**权威性与可复现性同时丧失**，且这种退化是静默的——报告看起来正常，没人知道它没按团队规范审。

### 1.3 意图

**任何 skill 运行时所需的一切都必须在安装出的插件目录内。** 知识库从「运行时依赖」降级为「创作素材与领域知识的沉淀地」。

## 2. 目标与非目标

### 目标

- 受影响 skill 在**仅安装插件**的前提下功能完整，不出现「去读一个不存在的文件」的指令
- 每份判据在库内有且只有一份（不产生跨插件副本）
- 保留 `knowledge-base/` 作为领域知识沉淀与判据创作素材
- 修正因搬迁产生的全部悬空引用（hooks README、agent 文档、known-issues、test-prompts）

### 非目标

- 不重构判据内容本身（措辞、章节编号不动，只换位置与引用写法）
- 不改动与插件运行时无关的知识库领域（`architecture/`、`git/`、`skill-authoring/` 等）
- 不为已发布的旧版本做兼容层

### 反目标（做错的表现）

- 搬完以后 `knowledge-base/` 与插件内各存一份判据 → 两份必然漂移，比现在更糟
- 为了让路径解析，在 skill 里写「先 clone 本仓库」→ 把安装体验问题转嫁给用户
- 把 2244 行的 rules 塞进 SKILL.md 正文 → 违反行数上限与渐进披露原则

## 3. 现状事实

### 3.1 知识库全量盘点（16 个领域）

| 领域 | 内容 | 被插件 skill 运行时消费？ |
|---|---|---|
| `architecture/` | 64 条 | 否 |
| `claude-code-hooks/` | 43 条 | 否——但 3 个插件 `hooks/README.md` 以它为开发依据（构建期引用，随包不含不影响 hook 运行） |
| `claude-code-plugin-system/` | 68 条 | 否——`AGENTS.md` 的开发规范依据 |
| `csharp/` | 143 条 + `rules/` 17 文件 2244 行 + `reference/refit.md` 1474 行 | **是**（`csharp-code-review`） |
| `data-structures-algorithms/` | 39 条 | 否 |
| `design-patterns/` | 35 条 | 否 |
| `dotnet/` | 2 条（平台支持矩阵） | 否——无 skill 引用 |
| `dotnet-debugging/` | 74 条 + `reference/` 14 文件 1852 行 + `rules/01-dump-handling.md` 50 行 | **是**（triage / autopilot / agent） |
| `git/` | 15 条 | 否——分支命名等开发规范 |
| `host-diagnostics/` | 95 条 | 否 |
| `mcp/` | 14 条 | 否 |
| `media/` | 11 条 + `reference/` 9 文件共 934 行 | **是**（11 个 media skill，概念背景选读） |
| `skill-authoring/` | 55 条 | 否——skill 规范依据（`.claude/rules/` + 多个 skill 的 `known-issues.md` 维护文档指向它） |
| `tools/` | 8 条 | 否 |
| `wpf/` | 132 条 + `rules/` 17 文件 1992 行 | **是**（`wpf-code-review` 全量 + `project-analyze` 3 文件） |

**结论：运行时消费的只有 4 个领域**——`csharp/`、`wpf/`、`dotnet-debugging/`、`media/`。其余 12 个是纯创作期/维护期资料。

### 3.2 关键语义陷阱：`reference/` 在不同领域含义不同

| 领域 | `reference/` 是什么 | 处理 |
|---|---|---|
| `csharp/` | 真·一手资料（`refit.md` 1474 行，取自 Refit 库约定） | 留下 |
| `media/` | 面向读者的概念说明（「CRF 机制」「关键帧与 GOP」） | 随 skill 走——被 skill 引用即需可见 |
| `dotnet-debugging/` | **判据本身**（74 条索引全部指向它，`rules/` 只有 1 个 50 行文件） | 随 skill 走——目录名起错了位，实质是 `rules/` |

机械按「rules 移走、reference 留下」会让 triage 装完照样是坏的。判据是**是不是运行时判据**，不是目录名。

### 3.3 消费方矩阵（含非 SKILL.md 的引用点）

| 消费方 | 引用的知识库 | 引用位置 |
|---|---|---|
| `csharp-code-review` | `csharp/rules/` 全量 | SKILL.md 审查清单 10 行 + 概述/权威参考 |
| `wpf-code-review` | `wpf/rules/` 全量 | SKILL.md 审查清单 12 行 + 概述/权威参考 |
| `project-analyze` | `wpf/rules/02`、`03`、`17` | SKILL.md 5 处（第 73/74/319/345 行等） |
| `dotnet-diagnose-triage` | `dotnet-debugging/reference/` + `rules/01` | SKILL.md 3 处 + `references/symptom-hypothesis-map.md`（路由表逐条指向文件名与 §）+ `references/verdict-forms.md` |
| `dotnet-diagnose-autopilot` | `dotnet-debugging/rules/01` | SKILL.md 1 处（敏感数据落盘路径约束） |
| agent `dotnet-diagnose` | `dotnet-debugging/` 整体 | `agents/dotnet-diagnose.md` 第 35 行 + `agent-docs/dotnet-diagnose/README.md` 2 处 |
| 11 个 `media-*` | `media/reference/` 9 文件 | 各 SKILL.md 的「参见」段 |
| 3 个插件 `hooks/README.md` | `claude-code-hooks/` | 开发依据，非运行时 |

### 3.4 校验机制牵涉

- `knowledge-base/<domain>/index.jsonl` 由 `check_index.py` / `check_refs.py` 校验（CI `gates-data` job + pre-commit）
- **移动 `rules/` 后对应 index 条目必须同步删除**，否则 `check_index.py` 报「索引指向不存在的文件」
- 删空的知识库领域目录需整目录移除，`check_index.py` 无参数时扫描所有含 `index.jsonl` 的子目录，删掉即不再扫
- 🔴 **`knowledge-base/catalog.json` 被 `check_index.py` 双向硬校验**（第 272 行起）：`domains` 数组与真实领域目录必须一一对应，缺一多一都报错；每个条目的 `status` 取值合法性与 `reviewed_at` 的 ISO 格式同样校验。**删除领域目录必须同步删 `catalog.json` 条目**，否则 `gates-data` 必然红。`test_check_index.py` 断言了 catalog 行为，schema 改动可能带动测试

### 3.5 搬迁判据文件内部的跨域引用（真实风险，非假设）

`dotnet-debugging/reference/` 的判据正文里有 **17 处**指向 `csharp/rules/` 与 `wpf/rules/` 的仓库相对路径，形如：

```
预防侧的编码规范（如何避免泄漏、如何正确实现 IDisposable）见 `knowledge-base/csharp/rules/06-memory-resource.md`。
```

搬迁后这些路径全部失效，而这些文件本身是 triage 每轮都要读的判据载体。**这不是「同目录相对引用不受影响」能覆盖的情形**——它是跨插件引用。

### 3.6 校验实测到的计数修正

| 文档早前写法 | 实测 |
|---|---|
| `media/reference/` 9 文件 | **11 文件**（`subtitles.md`、`video-container-formats.md` 无任何插件引用） |
| `project-analyze` 5 处 knowledge-base 引用 | **6 处**（第 20、57、73、74、319、345 行） |
| `media-ffmpeg-common/CLI-REFERENCE.md` 引用情况「若含」 | **确定含 7 处** |

## 4. 目标架构

### 4.1 一条判据原则

> **判据住在它唯一的运行时消费者身边；知识库只留不属于任何单一消费者、或只在创作期用的资料。**

具体到四个领域：

| 知识库 | 去向 | 理由 |
|---|---|---|
| `csharp/rules/`（17 文件 2244 行） | → `plugins/optimus-backend-plugin/skills/csharp-code-review/references/` | 唯一消费者 |
| `csharp/reference/refit.md`（1474 行） | **留在 `knowledge-base/csharp/reference/`** | 创作期素材，skill 不读；README/index 保留 |
| `wpf/rules/`（17 文件 1992 行） | → `plugins/optimus-frontend-plugin/skills/wpf-code-review/references/` | 主消费者 |
| `wpf/rules/02`、`03`、`17`（project-analyze 用） | → `plugins/optimus-devops-plugin/skills/project-analyze/references/`（**摘取所需条款，非整文件复制**） | 第二个消费者，用的只是判定要点 |
| `dotnet-debugging/reference/`（14 文件 1852 行）+ `rules/01-dump-handling.md` | → `plugins/optimus-devops-plugin/skills/dotnet-diagnose-triage/references/` | triage 是主要消费者；autopilot 与 agent 共享同一插件目录，用相对路径指向这里 |
| `media/reference/`（11 文件，934 行中 2 篇无消费者） | → `plugins/optimus-media-plugin/skills/media-ffmpeg-common/reference/`（**全部 11 篇**） | **插件内共享目录**——已有 `media-ffmpeg-common/` 承载 `CLI-REFERENCE.md` 的先例，11 个 skill 同插件内共享一份。`subtitles.md`、`video-container-formats.md` 虽当前无 skill 引用，但它们是媒体领域的成篇知识、且与该领域其余 9 篇互为体系；拆开留在知识库会让 `media/` 只剩两篇残卷且失去上下文（我的判断，可推翻） |
| `dotnet/`（2 条，无消费者） | 留在知识库 | 领域知识沉淀 |

**`media-ffmpeg-common/reference/` 沿用 `reference/` 子目录名**，与插件内既有 `CLI-REFERENCE.md` / `REFERENCE.md` 平级，与库内术语一致。

### 4.1.1 判据里的跨域引用怎么处理（§3.5 的应对）

17 处跨域引用分两类，分别处理：

| 类型 | 形态 | 处理 |
|---|---|---|
| **预防侧指针**（多数） | 「如何*避免*这个问题，见 `csharp/rules/06-memory-resource.md`」 | 保留下文语义，路径改为**插件外提示**：`（预防规范见 optimus-backend-plugin 的 csharp-code-review skill）`。判据本体是「怎么从 dump 里识别」，没有它也能完整执行；指针只在用户想深挖时才有用 |
| **判定表内的取值引用** | `sos-heap-and-objects.md:136` 表格「静态字段 → 见 `...06-memory-resource.md § 5. 静态引用`」 | 同上改写。**不摘抄对方内容**——摘抄就产生第二份副本 |

**统一原则：搬走的判据不得引用另一个插件包内的文件。** 提不到的内容宁可用「见 X 插件的 Y skill」这样的一跳提示，也不复制正文。实施时对 17 处逐一改写，改写后 `grep -rn "knowledge-base/" <搬入的 references/>` 必须为空。

⚠️ **`dotnet-diagnose-triage/test-cases/golden.md:103` 断言输出含字面串 `knowledge-base/wpf/rules/05-data-binding.md § 2`**。改写判据后该 fixture 必须同步更新，否则它就是一条恒失败的断言。

### 4.2 搬迁后的 `knowledge-base/` 形态

保留领域：`architecture`、`claude-code-hooks`、`claude-code-plugin-system`、`data-structures-algorithms`、`design-patterns`、`dotnet`、`git`、`host-diagnostics`、`mcp`、`skill-authoring`、`tools`，以及 `csharp/`（只剩 `reference/refit.md`）。

删除 3 个领域目录：`media/`、`dotnet-debugging/`、`wpf/`（搬迁后无剩余内容）。

**三处必须同步**：`knowledge-base/README.md` 总览表、`knowledge-base/catalog.json` 的 `domains` 数组、各保留领域的 `index.jsonl`。

**`wpf/` 的跨插件问题**：`project-analyze` 需要的是「命名怎么判、MVVM 框架怎么识别」这类**要点**，不是完整规范。整文件复制会产生两份必然漂移的副本。摘取成 `project-analyze/references/wpf-profile-rules.md`（约 30-50 行），并在该文件顶部注明「摘自 frontend-plugin 的 wpf-code-review，判定口径以彼为准」。

**`dotnet-debugging/` 的插件内共享**：三个消费方（triage、autopilot、agent）同属 optimus-devops-plugin。判据放 `dotnet-diagnose-triage/references/`（它是「判据承载层」，SKILL.md 第 16 行自述如此），其余两方用相对路径 `../dotnet-diagnose-triage/references/<file>` 指向。插件安装是整个 `plugins/optimus-devops-plugin/` 目录整体拷贝，插件内相对路径在安装后可解析——**这一点需要在实施时实测确认**（见 §7 风险 R1）。

### 4.2 搬迁后的 `knowledge-base/` 形态

保留 12 个领域：`architecture`、`claude-code-hooks`、`claude-code-plugin-system`、`data-structures-algorithms`、`design-patterns`、`dotnet`、`git`、`host-diagnostics`、`mcp`、`skill-authoring`、`tools`，以及 `csharp/`（只剩 `reference/refit.md`）。

删除 3 个领域目录：`media/`、`dotnet-debugging/`、`wpf/`（搬迁后无剩余内容）。

`knowledge-base/README.md` 的总览表与 `index.jsonl` 同步更新。

### 4.3 SKILL.md 里的引用写法

搬迁后 SKILL.md 不再写「打开 `knowledge-base/...`」，改为：

```
| # | 类别 | 参考文件 | 核对要点 |
|---|---|---|---|
| 1 | 命名约定 | `references/02-coding-style.md` § 1. 命名规范 | ... |
```

并在概述段补一句运行时自包含声明：

> 本 skill 的审查判据全部内置于 `references/`，安装后即可完整运行，不依赖外部仓库。

**渐进披露**：SKILL.md 正文不内联规则全文（2244 行远超上限），保留现有「审查清单定位 → 按需读 `references/<file>` 的 §」模式，只把路径从仓库相对改为 skill 相对。

## 5. 各部分怎么改

### 5.1 文件搬迁（git mv 保留历史）

1. `knowledge-base/csharp/rules/*.md`（17）→ `plugins/optimus-backend-plugin/skills/csharp-code-review/references/`
2. `knowledge-base/wpf/rules/*.md`（17）→ `plugins/optimus-frontend-plugin/skills/wpf-code-review/references/`
3. `knowledge-base/dotnet-debugging/reference/*.md`（14）+ `rules/01-dump-handling.md` → `plugins/optimus-devops-plugin/skills/dotnet-diagnose-triage/references/`
4. `knowledge-base/media/reference/*.md`（9）→ `plugins/optimus-media-plugin/skills/media-ffmpeg-common/reference/`
5. 新建 `plugins/optimus-devops-plugin/skills/project-analyze/references/wpf-profile-rules.md`（摘取，非搬运）

⚠️ 目标目录内已有同名文件时（如 triage 的 `references/` 已有 `evidence-precheck.md` 等 3 个文件），需检查文件名冲突；`symptom-hypothesis-map.md` 与知识库文件名不冲突。

### 5.2 判据搬迁后的引用修正（逐处清单）

| 位置 | 改什么 |
|---|---|
| `csharp-code-review/SKILL.md` | 审查清单 10 行「knowledge-base 参考」列 → `references/<file>`；概述、权威参考段同步 |
| `wpf-code-review/SKILL.md` | 同上，12 行 |
| `project-analyze/SKILL.md` | **6 处**（20、57、73、74、319、345 行）→ `references/wpf-profile-rules.md § <章节>`；置信度表里「有 knowledge-base 完整规范支撑」的措辞调整 |
| `dotnet-diagnose-triage/SKILL.md` | description、compatibility、正文 3 处 → 指向 `references/`；删除「须与本仓库同处一个工作树才能读到」这句 |
| `dotnet-diagnose-triage/references/*.md`（搬入的 15 个判据文件） | §3.5 的 17 处跨域指针按 §4.1.1 改写 |
| `dotnet-diagnose-triage/references/verdict-forms.md` | 第 30 行跨领域引用回落表：`csharp/rules/...`、`wpf/rules/...` → 「跨插件规范不在本插件包内，如需查 C#/WPF 规范请安装对应插件」 |
| `dotnet-diagnose-triage/test-cases/golden.md` | 第 103 行断言的字面串同步改写 |
| `dotnet-diagnose-triage/README.md` | 第 72、76 行 |
| `dotnet-diagnose-autopilot/SKILL.md` | 第 158 行 → `../dotnet-diagnose-triage/references/01-dump-handling.md § 2` |
| `dotnet-diagnose-autopilot/README.md` | 第 98 行 |
| `agents/dotnet-diagnose.md` | 第 35 行 → 指向插件内 `references/` |
| `agent-docs/dotnet-diagnose/README.md` | 2 处（第 5、78 行），架构图里的 `knowledge-base/dotnet-debugging/` → 插件内路径 |
| 11 个 `media-*` SKILL.md | `knowledge-base/media/reference/<f>` → `../media-ffmpeg-common/reference/<f>` |
| `media-ffmpeg-common/CLI-REFERENCE.md` | **确定含 7 处**，同步改写 |
| `media-audio-convert/README.md:67`、`media-audio-extract/README.md:66`、`media-frame-extract/README.md:66`、`media-play/README.md:49` | 架构图内的路径 |
| 3 个插件 `hooks/README.md` | **不改**——指向 `claude-code-hooks/`，该领域保留不动 |
| 各 skill 的 `CHANGELOG.md` / `known-issues.md` | **不改**——历史记录，不追改 |

**范围判定（避免实施时摇摆）**：运行时指令（`SKILL.md` + `references/` + `agents/`）的路径**必须**改；插件内的插件用户文档（`README.md`、`agent-docs/`）**也要改**（它们随包分发，指向不存在的文件同样是缺陷）；`CHANGELOG.md`、`known-issues.md` 这类历史记录**不改**。

### 5.3 知识库侧同步

- 删除 `knowledge-base/{csharp,wpf,dotnet-debugging,media}/index.jsonl` 中被搬走的条目；`csharp/` 保留 `refit.md` 相关条目
- `knowledge-base/{wpf,media,dotnet-debugging}/` 整目录删除（含 README、CHANGELOG、index.jsonl）
- 🔴 **`knowledge-base/catalog.json`：删除这 3 个领域的条目**（不保留 `deprecated` 状态——领域已经不在了，留着条目会让 `check_index.py` 报「catalog 声明的领域目录不存在」）。同时把 `csharp`、`dotnet-debugging` 等条目的 `consumers` 数组里指向已搬迁路径的项删掉
- `knowledge-base/csharp/README.md` 改写：只描述 `reference/refit.md`，并注明 rules 已迁至 `plugins/optimus-backend-plugin/skills/csharp-code-review/references/`
- `knowledge-base/csharp/` 的 **README 版本行与 CHANGELOG 头部必须同步升版**——`check_domain_versions` 校验两者相等，且内容删除按 semver 至少 Minor
- `knowledge-base/README.md` 总览表同步
- 执行顺序：**先改文件、再删目录、最后跑校验**，避免中途状态被 pre-commit 拦
- 该领域的改动应走 `knowledge-base-maintain` skill 的既有流程（index/CHANGELOG/版本三步）

### 5.4 版本与门禁

| 项 | 判定 |
|---|---|
| 4 个插件 `plugin.json`（各两份） | **Patch**——判据搬迁与引用修正属于「修改已有内容」，不新增用户可见功能 |
| 4 个 skill 的 `metadata.version` | **Patch**：`csharp-code-review`、`wpf-code-review`、`dotnet-diagnose-triage`、`project-analyze`；autopilot 因改了一处路径同样 Patch |
| darwin-skill 评分门禁 | **不触发**——只对 Minor/Major 生效 |
| CI `gates-data` | 必须跑 `check_index.py`、`check_refs.py`、`validate_tips.py` |
| pre-commit 7 项 | 无新 plugin、无新 hook、无外部条目 sha 变化 → 应全过 |

⚠️ `media-ffmpeg-common` 不是 skill（无 SKILL.md），只是共享目录，无 `metadata.version`。

## 6. 验收标准

每条都可机械验证：

1. **零仓库外引用**：`grep -rn "knowledge-base/" plugins/*/skills/*/SKILL.md plugins/*/agents/*.md` 在本次涉及的 skill 中查询结果为**空**
2. **判据文件齐全**：`csharp-code-review/references/` 有 17 个 `.md`；`wpf-code-review/references/` 17 个；`dotnet-diagnose-triage/references/` 原有 3 + 新增 15 个；`media-ffmpeg-common/reference/` 11 个
3. **无重复副本**：抽查关键章节标题（如 `## 1. 命名规范`），每份判据内容在库内只出现一次
4. **装载实测**：将 `plugins/optimus-backend-plugin/` 单独拷贝到一个空目录，作为插件加载，运行 `csharp-code-review`，确认它读得到 `references/02-coding-style.md`；同样验证 devops 插件内 `../dotnet-diagnose-triage/references/` 跨 skill 相对路径
5. **门禁全绿**：`sh .githooks/pre-commit` 通过；`check_index.py`、`check_refs.py` 无新增失败项；`catalog.json` 与领域目录一一对应
6. **悬空引用归零**：`grep -rn "knowledge-base/\(wpf\|media\|dotnet-debugging\)" plugins/ .claude/ knowledge-base/` 结果为空（`docs/` 下的历史文档不算）
7. **判据内部无跨插件路径**：`grep -rn "knowledge-base/" plugins/*/skills/*/references/` 结果为空

⚠️ 第 4 条是本次的核心验收——前三条都能「看起来对」，只有实装才能证明插件包真的自包含。

## 7. 风险与未决

| # | 风险 | 应对 |
|---|---|---|
| R1 | **插件内跨 skill 相对路径在安装后能否解析**（`../dotnet-diagnose-triage/references/...`、`../media-ffmpeg-common/reference/...`）——取决于插件安装时是否整目录拷贝且技能运行时 cwd 语义 | **实施第一步就实测**（验收标准 4 的同一手段）。若不可行，退化为：判据复制到各 skill 自己的 `references/`，并在文件头标注「唯一真源在 X」——但这是劣解，先验证再决定 |
| R2 | `project-analyze` 摘取的 30-50 行与 `wpf-code-review` 的完整规范漂移 | 摘取件顶部注明「口径以 wpf-code-review 为准」；后续若发现判定分歧，回改摘取件 |
| R3 | **搬迁判据内部的 17 处跨插件指针**（§3.5） | 按 §4.1.1 改写为「见 X 插件」的一跳提示，不摘抄。改完 `grep` 验证为零 |
| R4 | `knowledge-base/csharp/README.md` 描述 17 个 rules 章节，删掉后需重写 | 已列入 §5.3；README 版本行与 CHANGELOG 头部同步升 Minor |
| R5 | `catalog.json` 未同步 → `gates-data` 确定性失败 | 已列入 §5.3 与验收标准 5 |
| R6 | `media/reference/` 有两篇（`subtitles.md`、`video-container-formats.md`）无任何 skill 引用，按 §4.1 自己的规则应留在知识库 | **已裁决（用户）**：整批 11 篇一起搬，`media/` 领域目录删除。理由：11 篇互为体系，拆开留下残卷更难维护 |
| R7 | 改写判据后 `golden.md:103` 的断言失效 | 列入 §5.2，同步改 |

**误报（不要在验收时当成缺陷）**：`plugins/optimus-session-plugin/skills/session-handoff/references/insights-template.md:42` 含 `knowledge-base/` 字样，但那是**示例输出串**，不是指令；且它引用的 `knowledge-base/scripts/` 本就不存在。验收 grep 若覆盖全仓会撞到它。

## 8. 留给实施者的判断

- 搬迁用 `git mv` 还是先复制再删：沿用 `git mv` 保留 blame 历史
- `media-ffmpeg-common/reference/` 的子目录名——沿用知识库的 `reference/`（与插件现有 `CLI-REFERENCE.md` 平级）还是改名 `concepts/`；我倾向 `reference/`，与库内既有术语一致
- `dotnet/`（2 条、无消费者）是否也删——我倾向保留，它是有效的领域沉淀，且无搬迁成本

