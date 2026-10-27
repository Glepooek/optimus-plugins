#!/usr/bin/env python3
"""check_plugin_self_contained.py 的单元测试。

重点在**不误报**：一个会误报的门禁会被逐步加白名单直到形同虚设。故每个
「不该报」的形态都有用例锁住——占位符、用户项目输出路径、历史记录、
构建期文档、插件内合法交叉引用。
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_plugin_self_contained as gate  # noqa: E402


class Fixture:
    """搭一个最小仓库：仓库根 + 一个插件 + 若干被引用的仓库级文件。"""

    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.plugin = self.root / "plugins" / "p"
        self.skill = self.plugin / "skills" / "s"
        self.skill.mkdir(parents=True)

    def write(self, rel, text, base=None):
        target = (base or self.root) / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def problems(self):
        return gate.check_plugin(self.plugin, self.root)

    def close(self):
        self._tmp.cleanup()


class GateTestCase(unittest.TestCase):
    def setUp(self):
        self.f = Fixture()

    def tearDown(self):
        self.f.close()

    def assertNoProblem(self):
        self.assertEqual(self.f.problems(), [], "不该报出任何违规")

    def assertOneProblem(self, needle):
        problems = self.f.problems()
        self.assertEqual(len(problems), 1, f"应恰好 1 条，实得 {problems}")
        self.assertIn(needle, problems[0])


class TestCleanPlugin(GateTestCase):
    def test_plugin_with_only_internal_refs_passes(self):
        self.f.write("skills/s/references/judgement.md", "# 判据\n")
        self.f.write("skills/s/references/other.md", "# 其他\n")
        self.f.write(
            "skills/s/SKILL.md",
            "见 `references/judgement.md` § 1，以及 `../s/references/other.md`。\n",
            base=self.f.plugin)
        self.assertNoProblem()

    def test_plugin_with_no_markdown_passes(self):
        self.assertNoProblem()


class TestDetectsEscape(GateTestCase):
    def test_relative_traversal_out_of_plugin(self):
        self.f.write("knowledge-base/csharp/README.md", "# C#\n")
        self.f.write(
            "skills/s/SKILL.md",
            "判据见 [`knowledge-base/csharp/README.md`](../../../../knowledge-base/csharp/README.md)。\n",
            base=self.f.plugin)
        self.assertOneProblem("引用越出插件目录")

    def test_repo_relative_knowledge_base(self):
        self.f.write("knowledge-base/wpf/rules/03-mvvm.md", "# MVVM\n")
        self.f.write(
            "skills/s/SKILL.md",
            "见 `knowledge-base/wpf/rules/03-mvvm.md` § 2。\n", base=self.f.plugin)
        self.assertOneProblem("knowledge-base/wpf/rules/03-mvvm.md")

    def test_repo_relative_claude_rules(self):
        self.f.write(".claude/rules/hook-conventions.md", "# hook\n")
        self.f.write(
            "skills/s/SKILL.md",
            "约定见 `.claude/rules/hook-conventions.md`。\n", base=self.f.plugin)
        self.assertOneProblem(".claude/rules/hook-conventions.md")

    def test_repo_relative_docs_that_really_exists(self):
        self.f.write("docs/superpowers/specs/design.md", "# 设计\n")
        self.f.write(
            "skills/s/SKILL.md",
            "职责边界见 `docs/superpowers/specs/design.md` § 2。\n", base=self.f.plugin)
        self.assertOneProblem("docs/superpowers/specs/design.md")

    def test_knowledge_base_dir_without_suffix(self):
        self.f.write("knowledge-base/media/README.md", "# media\n")
        self.f.write(
            "skills/s/SKILL.md", "概念以 `knowledge-base/media/` 为准。\n", base=self.f.plugin)
        self.assertOneProblem("引用越出插件目录")


class TestNoFalsePositive(GateTestCase):
    def test_user_project_output_path_not_reported(self):
        """用户项目里的输出路径在本仓不存在——不该被当成插件引用。"""
        self.f.write(
            "skills/s/SKILL.md",
            "分析完成后生成报告到 `doc/project-overview.md`，或 `docs/project-overview.md`。\n",
            base=self.f.plugin)
        self.assertNoProblem()

    def test_placeholder_paths_not_reported(self):
        self.f.write(
            "skills/s/SKILL.md",
            "模板：`<slug>/SKILL.md`、`*.md`、`$HOME/report-<timestamp>.md`、`sos-*.md`。\n",
            base=self.f.plugin)
        self.assertNoProblem()

    def test_absolute_and_url_not_reported(self):
        self.f.write(
            "skills/s/SKILL.md",
            "见 [文档](https://example.com/a.md)、`~/.claude/skills/x/SKILL.md`、"
            "`C:\\repo\\notes.md`。\n",
            base=self.f.plugin)
        self.assertNoProblem()

    def test_bare_filename_is_not_a_repo_ref(self):
        """裸文件名 `progress.md` 是输出产物，不是仓库文件引用。"""
        self.f.write(
            "skills/s/SKILL.md",
            "产出 `progress.md`、`insights.md`、`summaries.md`。\n", base=self.f.plugin)
        self.assertNoProblem()

    def test_changelog_not_checked(self):
        self.f.write("knowledge-base/csharp/README.md", "# C#\n")
        self.f.write(
            "skills/s/CHANGELOG.md",
            "1.0.1 起判据改从 `knowledge-base/csharp/README.md` 读取。\n",
            base=self.f.plugin)
        self.assertNoProblem()

    def test_known_issues_not_checked(self):
        self.f.write("knowledge-base/wpf/README.md", "# WPF\n")
        self.f.write(
            "skills/s/known-issues.md",
            "历史问题：曾指向 `knowledge-base/wpf/README.md`。\n", base=self.f.plugin)
        self.assertNoProblem()

    def test_hooks_readme_not_checked(self):
        """hooks README 是构建期开发说明，harness 运行时不加载。"""
        self.f.write("knowledge-base/claude-code-hooks/README.md", "# hooks\n")
        self.f.write(
            "hooks/README.md",
            "规范依据见 `knowledge-base/claude-code-hooks/`。\n", base=self.f.plugin)
        self.assertNoProblem()

    def test_books_workspace_not_checked(self):
        """books/ 是书籍录入的中间产物工作区，不是分发内容。"""
        self.f.write("knowledge-base/dsa/reference/hello-algo-01-intro.md", "# 1\n")
        self.f.write(
            "books/hello-algo/BOOK_OVERVIEW.md",
            "版本来源 `knowledge-base/dsa/reference/hello-algo-01-intro.md`。\n",
            base=self.f.plugin)
        self.assertNoProblem()


class TestDedup(GateTestCase):
    def test_display_text_and_link_target_reported_once(self):
        """同一份文件常同时写成显示文本与链接目标，只该算一处。"""
        self.f.write("knowledge-base/media/reference/codecs.md", "# codecs\n")
        self.f.write(
            "skills/s/SKILL.md",
            "见 [`knowledge-base/media/reference/codecs.md`]"
            "(../../../../knowledge-base/media/reference/codecs.md) § 1。\n",
            base=self.f.plugin)
        self.assertOneProblem("codecs.md")

    def test_same_file_on_two_lines_reported_twice(self):
        self.f.write("knowledge-base/media/reference/codecs.md", "# codecs\n")
        self.f.write(
            "skills/s/SKILL.md",
            "见 `knowledge-base/media/reference/codecs.md`。\n"
            "再次见 `knowledge-base/media/reference/codecs.md`。\n",
            base=self.f.plugin)
        self.assertEqual(len(self.f.problems()), 2)


class TestMultiplePlugins(unittest.TestCase):
    def test_only_the_offending_plugin_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "knowledge-base" / "x").mkdir(parents=True)
            (root / "knowledge-base" / "x" / "a.md").write_text("# a\n", encoding="utf-8")
            good = root / "plugins" / "good"
            bad = root / "plugins" / "bad"
            for p in (good, bad):
                (p / "skills" / "s").mkdir(parents=True)

            (good / "skills" / "s" / "SKILL.md").write_text(
                "见 `references/a.md`。\n", encoding="utf-8")
            (bad / "skills" / "s" / "SKILL.md").write_text(
                "见 `knowledge-base/x/a.md`。\n", encoding="utf-8")

            self.assertEqual(gate.check_plugin(good, root), [])
            self.assertEqual(len(gate.check_plugin(bad, root)), 1)


if __name__ == "__main__":
    unittest.main()
