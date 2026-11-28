"""check_skill_portability 的单元测试。每个断言都校验 rule 与 line。"""
import contextlib
import io
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import check_skill_portability as m  # noqa: E402

CLEAN_FM = (
    "---\nname: demo\ndescription: d\nlicense: MIT\n"
    "compatibility: any\nmetadata:\n  version: 1.0.0\nallowed-tools: Read\n---\n"
)


class PortabilityTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = pathlib.Path(self._tmp.name)

    def make_skill(self, plugin, name, skill_md, files=None):
        d = self.root / "plugins" / plugin / "skills" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(skill_md, encoding="utf-8", newline="\n")
        for rel, content in (files or {}).items():
            p = d / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8", newline="\n")
        return d

    def rules(self, findings):
        return [(f.rule, f.line) for f in findings]

    def test_clean_skill_passes(self):
        self.make_skill("p", "s", CLEAN_FM + "\n普通正文\n")
        self.assertEqual(m.scan_repo(self.root), [])

    def test_unknown_frontmatter_key(self):
        self.make_skill("p", "s", "---\nname: d\ntriggers: x\n---\nbody\n")
        self.assertEqual(self.rules(m.scan_repo(self.root)), [("frontmatter-key", 3)])

    def test_crlf_frontmatter_parsed(self):
        d = self.make_skill("p", "s", "x")
        (d / "SKILL.md").write_bytes(b"---\r\nname: d\r\ntriggers: x\r\n---\r\nbody\r\n")
        self.assertEqual(self.rules(m.scan_repo(self.root)), [("frontmatter-key", 3)])

    def test_bom_frontmatter_parsed(self):
        d = self.make_skill("p", "s", "x")
        (d / "SKILL.md").write_bytes(
            b"\xef\xbb\xbf" + "---\nname: x\ndescription: d\ntriggers: [a]\n---\nbody\n".encode()
        )
        self.assertEqual(self.rules(m.scan_repo(self.root)), [("frontmatter-key", 4)])

    def test_claude_skills_path_in_body(self):
        self.make_skill("p", "s", CLEAN_FM + "\n运行 .claude/skills/x/a.py\n")
        self.assertEqual(self.rules(m.scan_repo(self.root)), [("harness-path", 11)])

    def test_powershell_userprofile_path(self):
        self.make_skill("p", "s", CLEAN_FM + "\n$env:USERPROFILE\\.codex\\skills\n")
        self.assertEqual(self.rules(m.scan_repo(self.root)), [("harness-path", 11)])

    def test_home_path_in_script(self):
        self.make_skill("p", "s", CLEAN_FM, {"scripts/run.sh": "a\nls $HOME/.claude/cache\n"})
        fs = m.scan_repo(self.root)
        self.assertEqual(self.rules(fs), [("harness-path", 2)])
        self.assertTrue(fs[0].path.endswith("run.sh"))

    def test_nested_script_scanned(self):
        self.make_skill("p", "s", CLEAN_FM, {"jenkins_build/main.py": "p = '~/.claude/x'\n"})
        fs = m.scan_repo(self.root)
        self.assertEqual(self.rules(fs), [("harness-path", 1)])
        self.assertTrue(fs[0].path.endswith("main.py"))

    def test_test_files_excluded(self):
        self.make_skill("p", "s", CLEAN_FM, {"scripts/test_x.py": "p = '~/.claude/x'\n"})
        self.assertEqual(m.scan_repo(self.root), [])

    def test_marker_same_line_html_comment(self):
        line = "| ~/.claude/ | x | <!-- codex-portability: allow-harness-path reason=同步目标 -->\n"
        self.make_skill("p", "s", CLEAN_FM + "\n" + line)
        self.assertEqual(m.scan_repo(self.root), [])

    def test_marker_previous_line_comment(self):
        self.make_skill("p", "s", CLEAN_FM, {
            "scripts/run.sh": "# codex-portability: allow-harness-path reason=x\nls ~/.claude/a\n"})
        self.assertEqual(m.scan_repo(self.root), [])

    def test_one_marker_covers_both_hits_on_a_line(self):
        self.make_skill("p", "s", CLEAN_FM, {
            "scripts/run.sh": "# codex-portability: allow-harness-path reason=x\nls ~/.claude/a ~/.codex/b\n"})
        self.assertEqual(m.scan_repo(self.root), [])

    def test_marker_does_not_reach_two_lines(self):
        self.make_skill("p", "s", CLEAN_FM, {
            "scripts/run.sh": "# codex-portability: allow-harness-path reason=x\necho\nls ~/.claude/a\n"})
        self.assertEqual(sorted(self.rules(m.scan_repo(self.root))),
                         [("harness-path", 3), ("marker-orphan", 1)])

    def test_marker_without_reason(self):
        self.make_skill("p", "s", CLEAN_FM, {
            "scripts/run.sh": "# codex-portability: allow-harness-path reason=\nls ~/.claude/a\n"})
        self.assertEqual(self.rules(m.scan_repo(self.root)), [("marker-no-reason", 1)])

    def test_ask_user_question_in_body(self):
        self.make_skill("p", "s", CLEAN_FM + "\n用 AskUserQuestion 收集\n")
        self.assertEqual(self.rules(m.scan_repo(self.root)), [("tool-token", 11)])

    def test_ask_user_question_in_allowed_tools_ignored(self):
        fm = "---\nname: d\nallowed-tools: AskUserQuestion Read\n---\nbody\n"
        self.make_skill("p", "s", fm)
        self.assertEqual(m.scan_repo(self.root), [])

    def test_skill_dir_reference_missing(self):
        self.make_skill("p", "s", CLEAN_FM + "\n见 `<skill-dir>/scripts/nope.py`\n")
        self.assertEqual(self.rules(m.scan_repo(self.root)), [("skill-dir-missing", 11)])

    def test_skill_dir_reference_present(self):
        self.make_skill("p", "s", CLEAN_FM + "\n见 `<skill-dir>/scripts/ok.py`\n",
                        {"scripts/ok.py": "pass\n"})
        self.assertEqual(m.scan_repo(self.root), [])

    def test_skill_dir_reference_to_directory_rejected(self):
        self.make_skill("p", "s", CLEAN_FM + "\n<skill-dir>/scripts\n", {"scripts/a.py": "x\n"})
        self.assertEqual(self.rules(m.scan_repo(self.root)), [("skill-dir-missing", 11)])

    def test_skill_dir_reference_escaping_skill_rejected(self):
        self.make_skill("p", "other", CLEAN_FM, {"a.py": "x\n"})
        self.make_skill("p", "s", CLEAN_FM + "\n<skill-dir>/../other/a.py\n")
        self.assertEqual(self.rules(m.scan_repo(self.root)), [("skill-dir-missing", 11)])

    def test_test_prefixed_shell_script_scanned(self):
        self.make_skill("p", "s", CLEAN_FM, {"scripts/test_run.sh": "cd ~/.claude/x\n"})
        self.assertEqual(self.rules(m.scan_repo(self.root)), [("harness-path", 1)])

    def test_references_markdown_scanned(self):
        self.make_skill("p", "s", CLEAN_FM, {"references/a.md": "见\n~/.codex/skills/x\n"})
        findings = m.scan_repo(self.root)
        self.assertEqual(self.rules(findings), [("harness-path", 2)])
        self.assertTrue(findings[0].path.endswith("references/a.md"))

    def test_non_reference_markdown_not_scanned(self):
        self.make_skill("p", "s", CLEAN_FM, {"CHANGELOG.md": "~/.claude/x\n"})
        self.assertEqual(m.scan_repo(self.root), [])

    def test_unreadable_file_reported_under_own_rule(self):
        d = self.make_skill("p", "s", CLEAN_FM)
        (d / "run.sh").write_bytes(b"\xff\xfe\x00bad")
        self.assertEqual(self.rules(m.scan_repo(self.root)), [("unreadable", 0)])

    def test_list_mode_returns_zero(self):
        self.make_skill("p", "s", CLEAN_FM + "\n.claude/skills/x\n")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = m.main(["check_skill_portability.py", "--list", str(self.root)])
            rc2 = m.main(["check_skill_portability.py", str(self.root)])
        self.assertEqual(rc, 0)
        self.assertEqual(rc2, 1)
        self.assertIn("harness-path", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
