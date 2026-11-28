import io
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

import run_repository_gates
from repository_gates import GATES, Gate
from run_repository_gates import REPOSITORY_ROOT, run_gates


def completed(code):
    return subprocess.CompletedProcess(args=[], returncode=code)


class TestRunGates(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path("/repo")
        self.gates = (
            Gate("first", ".githooks/first.py", (".",)),
            Gate("second", ".githooks/second.py", ("--all", ".")),
            Gate("third", ".githooks/third.py"),
        )

    def run_quiet(self, runner):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            result = run_gates(self.root, self.gates, runner=runner)
        return result, buffer.getvalue()

    def test_all_pass_returns_zero(self):
        runner = mock.Mock(return_value=completed(0))
        result, output = self.run_quiet(runner)
        self.assertEqual(result, 0)
        self.assertEqual(runner.call_count, 3)
        self.assertIn("[pre-commit] 通过", output)

    def test_middle_failure_still_runs_rest_and_returns_one(self):
        runner = mock.Mock(side_effect=[completed(0), completed(1), completed(0)])
        result, output = self.run_quiet(runner)
        self.assertEqual(result, 1)
        self.assertEqual(runner.call_count, 3)
        self.assertIn("[pre-commit] 失败项：second\n", output)

    def test_launch_exception_counts_as_failure_and_continues(self):
        runner = mock.Mock(side_effect=[OSError("boom"), completed(0), completed(0)])
        result, output = self.run_quiet(runner)
        self.assertEqual(result, 1)
        self.assertEqual(runner.call_count, 3)
        self.assertIn("[pre-commit] 失败项：first\n", output)

    def test_failure_message_keeps_contract_with_commit_skill(self):
        # commit-cc-plugin 靠这行字判断 commit 被门禁拦下
        runner = mock.Mock(return_value=completed(1))
        _, output = self.run_quiet(runner)
        self.assertIn("[pre-commit] 未通过。修正后重新提交，不要用 --no-verify 绕过。", output)

    def test_command_uses_current_interpreter_and_fixed_cwd(self):
        runner = mock.Mock(return_value=completed(0))
        self.run_quiet(runner)
        command = runner.call_args_list[1].args[0]
        self.assertEqual(command[0], sys.executable)
        self.assertEqual(command[1], str(self.root / ".githooks/second.py"))
        self.assertEqual(command[2:], ["--all", "."])
        self.assertEqual(runner.call_args_list[1].kwargs["cwd"], self.root)


class TestRepositoryRoot(unittest.TestCase):
    def test_root_is_derived_from_script_location(self):
        expected = pathlib.Path(run_repository_gates.__file__).resolve().parents[1]
        self.assertEqual(REPOSITORY_ROOT, expected)

    def test_main_ignores_caller_cwd(self):
        previous = os.getcwd()
        with tempfile.TemporaryDirectory() as elsewhere:
            os.chdir(elsewhere)
            try:
                with mock.patch.object(run_repository_gates, "run_gates", return_value=0) as fake:
                    self.assertEqual(run_repository_gates.main(), 0)
            finally:
                os.chdir(previous)
        self.assertEqual(fake.call_args.args[0], REPOSITORY_ROOT)
        self.assertEqual(fake.call_args.args[1], GATES)


class TestCatalog(unittest.TestCase):
    def test_catalog_lists_seven_existing_scripts(self):
        self.assertEqual(len(GATES), 7)
        for gate in GATES:
            self.assertTrue((REPOSITORY_ROOT / gate.script).is_file(), gate.script)

    def test_gate_names_are_unique(self):
        names = [gate.name for gate in GATES]
        self.assertEqual(len(names), len(set(names)))


@unittest.skipIf(shutil.which("sh") is None, "需要 sh（CI 的 ubuntu 与本机 Git Bash 都有）")
class TestPreCommitWrapper(unittest.TestCase):
    def test_missing_python_still_prints_contract_line(self):
        # commit-cc-plugin 靠 "[pre-commit] 未通过" 识别门禁拦截；python 不在 PATH
        # 时若只剩 shell 的 command not found，它就认不出这是门禁失败
        hook = REPOSITORY_ROOT / ".githooks" / "pre-commit"
        with tempfile.TemporaryDirectory() as empty_bin:
            env = {key: value for key, value in os.environ.items()
                   if key.upper() in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP")}
            env["PATH"] = empty_bin
            completed = subprocess.run(
                [shutil.which("sh"), str(hook)], env=env,
                capture_output=True, text=True, encoding="utf-8",
            )
        self.assertEqual(completed.returncode, 1)
        self.assertIn("[pre-commit] 未通过", completed.stdout)


if __name__ == "__main__":
    unittest.main()
