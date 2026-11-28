# 审查报告：仓库治理加固 spec 与实现计划

**日期：** 2026-11-28
**审查对象：**
- spec：`docs/superpowers/specs/2026-11-28-repository-governance-hardening-design.md`
- plan：`docs/superpowers/plans/2026-11-28-repository-governance-hardening.md`

**审查问题：** ① spec 所列问题是否真实存在、描述准确；② plan 能否从根上解决这些问题。

## 结论

spec 列的 8 个问题里，**6 个准确，1 个前提错误，1 个是把历史快照当成了过期数字**。此外 spec 漏掉了 3 处同类问题。plan 的主干（统一 runner、测试目录自动发现、eval policy）能解决对应问题，但还有三类问题：

- 1 个未经验证的关键假设：eval 的 target 能否用 skill 路径；
- 1 处会丢知识的改造：pre-commit 改成薄包装时，各检查项的说明注释没有去处；
- 2 个新增机制成本大于收益：能力矩阵生成器、必须全部出现的 marker。

**建议把这些问题改完再执行。**

### 已实测的基线

spec 写的基线数字全部吻合：

| 项 | spec 声明 | 实测 |
|---|---|---|
| 既有单元测试 | 757 | 757（8 个目录逐个 `unittest discover` 累加） |
| 知识库索引 | 439 | `check_index.py`：共检查 439 条记录 |
| 消费者引用 | 289 | `check_refs.py`：289 个消费者文件 |
| pre-commit | 通过 | `sh .githooks/pre-commit` 退出码 0 |
| 越界引用 | 已清零 | `check_plugin_self_contained.py`：9 个插件全部自包含 |
| 自建插件 / marketplace 条目 / 发布 skill / 维护 skill | 9 / 12 / 54 / 7 | 9 / 12 / 54 / 7 |
| eval case 分布 | 12 个 case 分布在 6 个 skill | 相符 |

## 一、spec 所列问题逐条核对

| # | spec 的说法 | 核对结果 | 依据 |
|---|---|---|---|
| 1 | ci.yml 写「9 个测试目录」，实际是 8 个 | ✅ 准确 | `ci.yml:85,87` 写的是 9，循环里实际列了 8 个；`actionlint.yml:75` 也写着「9 目录」 |
| 2 | AGENTS 写「八项门禁」，实际只有 6 项 | ❌ **前提错误** | `.githooks/README.md:17-28` 明确定义了 **8 个检查项、由 6 个脚本实现**（`check_skill_mirrors.py` 一个脚本覆盖第 4–6 项）。AGENTS 里「八项提交门禁」和「六个自检脚本」（`AGENTS.md:231`）两种说法是自洽的。spec 把检查项数和脚本数当成了同一个数 |
| 3 | CI 注释写 marketplace 有 13 个条目，实际 12 个 | ⚠️ 半准确 | `ci.yml:181` 原文是「本机按…复算（CLI 2.1.270 / marketplace 13 条目）」，记录的是当时的测量结果，那时确实是 13 个。应改写成带日期的过去时，而不是当作当前事实删掉 |
| 4 | pre-commit 注释仍称存在 48 处越界 | ✅ 准确 | 实测输出「9 个插件全部自包含」 |
| 5 | CI 注释写 48 个发布 skill，实际 54 个 | ✅ 准确 | `ci.yml:210` |
| 6 | PowerShell 下不能直接跑 `sh .githooks/pre-commit` | ✅ 准确 | 本机 pwsh 7.7 下 `Get-Command sh` 找不到命令 |
| 7 | skill-eval 缺 secret，并用 `--runs 1` 覆盖了 case 自己声明的 runs | ✅ 准确，但**漏了背景** | 这个冲突就是 `docs/todo-list/2026-09-12-todo.md` 里的 **B2**，原文写明「须显式裁决，不该默默生效」。去掉 `--runs 1` 后，wpf-code-review 会从 6 次运行变成 18 次；avalonia-wpf-migration 没有声明 runs，会按 CLI 默认值跑 3 次。spec 等于替用户做了 B2 的裁决，却没有引用 B2 |
| 8 | 能力与依赖矩阵靠 README 人工维护 | ⚠️ 属于偏好，不是缺陷 | 对照 README 依赖表和插件现状，没找到已经漂移的证据。依赖列本来就无法自动推导，挪进 JSON 后依然是人工维护的副本 |

### spec 漏掉的同类过期文本

- `ci.yml:162` 与 `ci.yml:186` 两处写「**10 个**自建插件在前」，实际是 9 个。
- `skill-eval.yml` 的注释整段都在讲「jenkins-build 那 20 个 case」，但现在 `plugins/optimus-devops/skills/jenkins-build/` 下**已经没有 `evals/` 目录**。`--ablation none` 的第 ② 条理由、`--runs 1` 的「兜底、无冲突」理由，依据的都是这批已经不存在的 case。
- `.githooks/README.md:98` 写的「当前八项检查」按它自己的定义目前是对的，但 plan 改造后会变错（见第二节问题 2）。

## 二、plan 能否从根上解决问题

| 问题 | plan 的处理 | 评价 |
|---|---|---|
| 1 测试目录数漂移 | Task 1 + Task 4：测试目录自动发现 | ✅ 能根治。用 `git ls-files` 核对过：全仓 8 个测试目录都落在三类 glob 范围内，不会漏收 |
| 2 「八项」 | catalog 里登记 8 个脚本 | ❌ **会造成新的漂移**。现有 6 个脚本加 2 个新 gate 正好是 8 个，但检查项会变成 10 个。`.githooks/README` 里 1–8 号检查项表格和「catalog 8 项」说的是两回事，两个数相等只是巧合 |
| 3/5 过期数字 | Task 5 删除 | ⚠️ 扫描正则没覆盖「10 个自建插件」和 jenkins-build 那段注释。Step 1 把「48 个发布 skill」改成「不少于一个…可能受到影响」，意思错了，原意是「全部发布 skill」 |
| 4 「48 处越界」注释 | pre-commit 改成薄包装 | ⚠️ **会丢失知识**。pre-commit 里每项检查都附有大段「为什么」的说明，比如第 1 项为什么不能拿一份覆盖另一份。plan 没交代这些说明迁到哪里，建议原样搬进 `repository_gates.py`，写在对应的 `Gate` 旁边 |
| 6 PowerShell | 统一用 Python runner | ✅ 能解决。但 `pre-commit.ps1` 是多余的：`python .githooks/run_repository_gates.py` 在 PowerShell 里本来就能直接跑。而且 Windows PowerShell 5.1 在客户端系统上默认执行策略是 Restricted，用 `-File` 运行脚本会被拦下；本机设成了 RemoteSigned，所以测不出来 |
| 7 eval | Task 6/7：policy 文件，先 baseline 再晋级 | ✅ 方向正确，但有一个关键假设还没验证，见第三节 |
| 8 矩阵 | Task 2：生成器 | ⚠️ 收益低，长期有摩擦。矩阵里含 skill 数量，以后**每个新增 skill 的 PR 都得顺带重新生成 docs**。生成出来的表也会丢掉 README 里「有本地缓存降级」「需图形显示环境」这类限定说明 |

### 实现层面的其他问题

1. **CI 不再执行 pre-commit 本身**。目前 `gates-hooks` 跑的是 `sh .githooks/pre-commit`，AGENTS 原文称之为「CI 逐字复用同一个文件」。plan 改成直接调用 runner 后，pre-commit 这层包装即使写坏了，CI 也发现不了。建议 CI 继续跑 `sh .githooks/pre-commit`。
2. **runner 没有规定如何定位仓库根**。每个 gate 都传 `.` 作为参数，如果 runner 用当前工作目录当仓库根，从其他目录调用时就会悄悄检查错误的位置。应固定为 `Path(__file__).resolve().parents[1]`。
3. **「六个 key 至少各出现一次」和 spec §4.1 矛盾**。§4.1 要求没有阅读价值的数字直接删掉，这条规则却强制把数字写进文档。例如测试目录改为自动发现后，AGENTS 里的「8 个测试目录」就失去了阅读价值。另外，claims 检查只能核对已经打了 marker 的数字，挡不住以后在注释里新写的、没有 marker 的数字，而这次发现的过期数字恰恰全是这种来源。
4. `check_claims` 的签名前后不一致：Interfaces 写的是两个参数，测试代码里传了三个（多了 `required_keys`）。
5. `upload-artifact@v4` 和本仓其他 action 的版本不一致（`checkout@v7`、`setup-python@v7`），实施时应按仓库惯例统一。

## 三、尚未确认的问题：eval 的 target 能否用 skill 路径

`claude plugin eval --help`（CLI 2.1.332）的原文是：eval 目录默认是 `<target>/evals/`，target 可以是一个路径。已做过的零成本探测：

- 用 `plugins/optimus-devops/skills/jenkins-build` 作 target 时，CLI 报「Cases are expected in a evals/ directory under …/jenkins-build」。可见以 skill 目录作 target 时，CLI 会去 `<skill>/evals/` 下找 case，**能找到 case**。
- **还没确认的是**：一个没有 `plugin.json` 的 skill 目录被当作插件加载后，这个 skill 能否正常触发。同一个 CLI 的 `validate` 子命令对单个 skill 目录会报「No manifest found」（见 `ci.yml:217`）。如果加载不正常，所有基线分数都没有意义。

**备选方案**：target 仍然用插件目录，再加 `--eval-dir skills/<skill>/evals`。插件按完整形态加载，case 范围又只限于这一个 skill。

**最小实验**（只改 target 形态这一个变量，预计花费不到 $1，执行前需用户批准这笔费用）：

- A：`claude plugin eval plugins/optimus-devops/skills/commit-message-review --trust-plugin --no-publish --ablation none --json a.json`
- B：`claude plugin eval plugins/optimus-devops --eval-dir skills/commit-message-review/evals --trust-plugin --no-publish --ablation none --json b.json`
- **怎么判断**：对比两份 JSON 里 skill 是否被调用、grader 判定结果。A 没加载到 skill 而 B 加载到了，就改用 B；两者表现一样，就保留 spec 的写法。
- **结论回填到哪里**：plan Task 6 Step 5 的 eval 命令，以及 spec §5.5 的 target 定义。

## 四、需要用户拍板的问题

1. **B2 怎么裁决**：是否接受去掉 `--runs 1`？代价是 wpf-code-review 每次评测的成本变成原来的约 3 倍。如果接受，spec 应明确引用 B2，plan 里补一步：到 `docs/todo-list/2026-09-12-todo.md` 把 B2 标为已关闭。
2. **矩阵和 marker 两个新机制要不要砍掉或缩小范围**。建议：能力矩阵先不做；claims 检查只保留「marker 值必须等于实际值」这一条，去掉「每个 key 都必须出现」，README 也不新增规模快照。这样 plan 的工作量能减少约三分之一，问题 1–7 照样能解决。
3. **门禁数量按什么口径算**：「N 项门禁」是数 gate 脚本，还是沿用 `.githooks/README` 现有的检查项编号？建议以检查项为准，并取消 `precommit_checks` 这个 marker。

## 五、修订建议汇总

| 改哪份 | 修订项 |
|---|---|
| spec §1 | 删除问题 2（「八项」并没有过期）；问题 3 改为「历史测量记录应注明日期」；问题 7 引用 B2；补上 `10 个自建插件`、jenkins-build 那段 eval 注释两处遗漏 |
| spec §5.3 | 去掉「六个事实键至少各出现一次」；去掉 `precommit_checks`，至少要把计数单位和 `.githooks/README` 的编号表对齐 |
| spec §5.5 | target 的形态以第三节实验的结论为准 |
| spec §5.6 | 根据用户在第四节问题 2 的决定，保留或删掉 |
| plan Task 4 | 规定 runner 用 `Path(__file__).resolve().parents[1]` 定位仓库根；CI 继续跑 `sh .githooks/pre-commit`；pre-commit 里的注释迁进 `repository_gates.py`；考虑去掉 `pre-commit.ps1` |
| plan Task 5 | 扫描正则补上 `10 个自建插件`、`jenkins-build`；改正「不少于一个」这处措辞；`13 条目` 改为注明日期，不删除 |
| plan Task 6 | 实施前先做第三节的实验；改写 workflow 时一并删掉已过时的 jenkins-build 注释；action 版本按仓库惯例统一 |
