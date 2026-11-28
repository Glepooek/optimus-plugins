import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from codex_smoke import (  # noqa: E402
    expected_skill_ids,
    local_plugin_names,
    mcp_problems,
    missing_skill_ids,
    rendered_text,
    require_isolated_codex_home,
)


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

    def test_codex_home_unset_refused(self):
        self.assertIsNotNone(require_isolated_codex_home({}))

    def test_codex_home_user_default_refused(self):
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


if __name__ == "__main__":
    unittest.main()
