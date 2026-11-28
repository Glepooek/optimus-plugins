"""仓库一致性门禁的 catalog——登记「跑哪些脚本」的唯一真源。

这里放的是「失效了会损害仓库长期状态」的检查——版本号真源一致性、
多 harness 镜像完整性。它们与某一次提交的内容无关，只是借提交这个
必经关口拦截。提交行为本身的规范（原子性、message 格式）不在这里，
由 commit-cc-plugin skill 承担。

挂在 hook 而非 skill 里，是因为 Codex 侧走标准 git 流程，读不到 skill 正文。

计数口径：下面登记 **6 个脚本**，覆盖 .githooks/README.md「检查项」表里的
**8 个逻辑检查**（check_skill_mirrors.py 一个脚本覆盖第 4–6 项）。两个数不是
同一个单位，不要互相换算。

执行方：run_repository_gates.py（pre-commit 与 CI 的 gates-hooks 都经它）。
新增检查时只改本文件的 GATES，并同步 .githooks/README.md 的检查项表。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Gate:
    name: str
    script: str
    args: tuple[str, ...] = ()


GATES: tuple[Gate, ...] = (
    # --- 检查项 1：每插件两份 plugin.json 版本同值 ---
    # 版本真源是「两份构成的一对」。不一致时不要拿一边覆盖另一边——错的可能恰好是
    # 「另一份」（该升 Minor 却升了 Patch），覆盖会把正确的一边也改错。
    # 正确处置：按 AGENTS.md 版本管理规则判断本次改动该升什么号，两份都写成该值。
    Gate("plugin-versions", ".githooks/check_plugin_versions.py", (".",)),

    # --- 检查项 2：hook 配置与 Claude Code 契约相符 ---
    # 只查机械可判定项：async 与展示类输出的错配、handler 类型与事件不符、
    # 非工具事件上的 if、永不匹配的 mcp__ matcher、拼错的事件名、PowerShell 裸占位符。
    # 这些错误全都不报错也不中断，只是静默失效——正是需要借提交关口拦的形态。
    # 完整判据见 knowledge-base/claude-code-hooks/。
    Gate("hook-configs", ".githooks/check_hook_configs.py", (".",)),

    # --- 检查项 3：marketplace 外部引用条目的结构合规 ---
    # 只查机械可判定项：sha 是否 40 位全长、条目是否误写 version、strict:false 是否配了
    # 非空 skills 数组、source 类型与 git-subdir 的 path、展示元数据是否齐备、是否登记进
    # 台账「已接入」表，以及台账 sha 与条目 sha 是否一致（不一致 = 上次更新做了一半）。
    # 这些错误都不报错：漏 sha 只是静默退回「跟随分支最新」，缺 skills 数组则整条加载失败。
    # 刻意不联网——不校验 sha 是否真存在于上游、上游有没有新 commit（后者正是要避免的）。
    # 完整判据见 docs/superpowers/specs/2026-09-12-add-external-skill-design.md § 5。
    Gate("external-entries", ".githooks/check_external_entries.py", (".",)),

    # --- 检查项 4–6：.claude/skills 的双 harness 符号链接镜像 ---
    # 每个**由本仓分发**的 skill 都要在 .kiro/skills（Claude/Kiro）与 .agents/skills
    # （Codex）有同名符号链接，且以 120000 模式入库；反向还要检出悬空镜像。
    #
    # 🔴 「由本仓分发」有两条**正交**的排除理由——没有 SKILL.md（镜像它无意义）、
    #    被 gitignore（刻意不分发）。判据与 `git check-ignore --no-index` 的必要性
    #    见 check_skill_mirrors.py 的 docstring，那里记着这次判据被撞出来的经过。
    #
    # ⚠️ 本项 2026-09-14 前是内联在 pre-commit 里的 sh，是当时唯一没有单测的一项；
    #    抽成脚本正是为了让那两条判据可被 test_check_skill_mirrors.py 覆盖。
    Gate("skill-mirrors", ".githooks/check_skill_mirrors.py", (".",)),

    # --- 检查项 7：eval case 目录没有建了一半的 ---
    # evals/ 下每个子目录都必须含 case.yaml 或 prompt.md。缺 marker 的子目录会被
    # claude plugin eval **静默忽略**——不报错，只是少跑一个 case，而总数只出现在
    # verbose 输出里。这与其余各项是同一形态：失效了不报错。
    #
    # ⚠️ 同一个脚本的另一个模式（<base> <head>）依赖 diff，**不能**登记在这里；
    #    --all 模式不看 diff、只读工作树，因此不破坏「pre-commit 暂存区无关」
    #    这条硬约定（见 .githooks/README.md「与 CI 的关系」）。
    #    两个模式查的不是同一件事：那个只在新增 SKILL.md 时触发，本项覆盖
    #    「给存量 skill 补 case 却补错形态」——那个缺口此前无人看守。
    Gate("eval-cases", ".githooks/check_new_skill_eval_case.py", ("--all", ".")),

    # --- 检查项 8：插件运行时自包含，不得引用插件目录以外的路径 ---
    # 插件安装单元是 plugins/<name>/，装出去的包里没有 knowledge-base/、没有
    # .claude/、也没有本仓 docs/。插件内指向这些位置的引用在开发期能解析，
    # 安装后必然失效——而且是静默失效：skill 读不到判据，Claude 用泛型知识补全，
    # 报告看起来正常，团队规范一条都没执行。
    #
    # 判据与「哪些文件不查」（CHANGELOG、hooks/README、books/）见脚本 docstring。
    # 该脚本自行由 __file__ 定位仓库根，因此不传 "."。
    Gate("plugin-self-contained", ".githooks/check_plugin_self_contained.py"),
)
