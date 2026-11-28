import contextlib
import io
import json
import os
import subprocess
import pathlib
import sys
import tempfile
import unittest
import unittest.mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import codex_smoke  # noqa: E402
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


class TestMainMalformedOutput(unittest.TestCase):
    def _run_main(self, fake):
        root = pathlib.Path(__file__).resolve().parent.parent
        env = {"CODEX_HOME": tempfile.mkdtemp()}
        out = io.StringIO()
        with unittest.mock.patch.dict(os.environ, env),                 unittest.mock.patch.object(codex_smoke.shutil, "which", return_value="codex"),                 unittest.mock.patch.object(codex_smoke, "_run", side_effect=fake),                 contextlib.redirect_stdout(out):
            rc = codex_smoke.main(["codex_smoke.py", str(root)])
        return rc, out.getvalue()

    @staticmethod
    def _cp(stdout="", rc=0):
        return subprocess.CompletedProcess([], rc, stdout=stdout, stderr="")

    def test_non_json_mcp_list_categorized_and_later_checks_run(self):
        def fake(codex, *args):
            if args[:2] == ("mcp", "list"):
                return self._cp("not json")
            if args[:2] == ("plugin", "list"):
                return self._cp(json.dumps({"installed": []}))
            if args[:2] == ("debug", "prompt-input"):
                return self._cp("also not json")
            return self._cp("{}")
        rc, out = self._run_main(fake)
        self.assertEqual(rc, 1)
        self.assertIn("[mcp-enumeration]", out)
        self.assertIn("[skill-visibility]", out)
        self.assertIn("[plugin-install]", out)

    def test_wrong_shape_plugin_list_categorized(self):
        def fake(codex, *args):
            if args[:2] == ("plugin", "list"):
                return self._cp("[1, 2]")
            if args[:2] == ("mcp", "list"):
                return self._cp("{}")
            return self._cp("[]")
        rc, out = self._run_main(fake)
        self.assertEqual(rc, 1)
        self.assertIn("[plugin-install] plugin list 输出无法解析", out)
        self.assertIn("[mcp-enumeration]", out)


class TestRunFailureCategorization(unittest.TestCase):
    def test_timeout_becomes_nonzero_result(self):
        exc = subprocess.TimeoutExpired(["codex"], 120)
        with unittest.mock.patch.object(codex_smoke.subprocess, "run", side_effect=exc):
            r = codex_smoke._run("codex", "mcp", "list")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("超时", r.stderr)

    def test_oserror_becomes_nonzero_result(self):
        with unittest.mock.patch.object(codex_smoke.subprocess, "run", side_effect=OSError("boom")):
            r = codex_smoke._run("codex", "mcp", "list")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("boom", r.stderr)


if __name__ == "__main__":
    unittest.main()
