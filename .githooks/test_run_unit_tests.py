import io
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

import run_unit_tests
from run_unit_tests import REPOSITORY_ROOT, run_unit_tests as run_tests


def completed(code):
    return subprocess.CompletedProcess(args=[], returncode=code)


class TestRunUnitTests(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path("/repo")
        self.directories = (".githooks", "plugins/demo/skills/x/scripts")

    def run_quiet(self, runner, directories=None):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            result = run_tests(
                self.root,
                directories=self.directories if directories is None else directories,
                runner=runner,
            )
        return result, buffer.getvalue()

    def test_runs_every_directory_and_passes(self):
        runner = mock.Mock(return_value=completed(0))
        result, _ = self.run_quiet(runner)
        self.assertEqual(result, 0)
        self.assertEqual(runner.call_count, 2)

    def test_middle_failure_still_runs_rest(self):
        runner = mock.Mock(side_effect=[completed(1), completed(0)])
        result, output = self.run_quiet(runner)
        self.assertEqual(result, 1)
        self.assertEqual(runner.call_count, 2)
        self.assertIn("失败目录：.githooks\n", output)

    def test_launch_exception_counts_as_failure_and_continues(self):
        runner = mock.Mock(side_effect=[OSError("boom"), completed(0)])
        result, _ = self.run_quiet(runner)
        self.assertEqual(result, 1)
        self.assertEqual(runner.call_count, 2)

    def test_empty_discovery_fails(self):
        runner = mock.Mock(return_value=completed(0))
        result, output = self.run_quiet(runner, directories=())
        self.assertEqual(result, 1)
        runner.assert_not_called()
        self.assertIn("未发现任何测试目录", output)

    def test_command_shape_interpreter_and_cwd(self):
        runner = mock.Mock(return_value=completed(0))
        self.run_quiet(runner)
        call = runner.call_args_list[1]
        self.assertEqual(
            call.args[0],
            [sys.executable, "-m", "unittest", "discover",
             "-s", "plugins/demo/skills/x/scripts", "-p", "test_*.py"],
        )
        self.assertEqual(call.kwargs["cwd"], self.root)

    def test_github_actions_wraps_each_directory_in_a_log_group(self):
        runner = mock.Mock(return_value=completed(0))
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            _, output = self.run_quiet(runner)
        self.assertIn("::group::.githooks\n", output)
        self.assertIn("::group::plugins/demo/skills/x/scripts\n", output)
        self.assertEqual(output.count("::endgroup::\n"), 2)

    def test_no_log_group_markers_outside_github_actions(self):
        runner = mock.Mock(return_value=completed(0))
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITHUB_ACTIONS", None)
            _, output = self.run_quiet(runner)
        self.assertNotIn("::group::", output)


class TestRepositoryRoot(unittest.TestCase):
    def test_root_is_derived_from_script_location(self):
        expected = pathlib.Path(run_unit_tests.__file__).resolve().parents[1]
        self.assertEqual(REPOSITORY_ROOT, expected)

    def test_main_ignores_caller_cwd(self):
        previous = os.getcwd()
        with tempfile.TemporaryDirectory() as elsewhere:
            os.chdir(elsewhere)
            try:
                with mock.patch.object(run_unit_tests, "run_unit_tests", return_value=0) as fake:
                    self.assertEqual(run_unit_tests.main(), 0)
            finally:
                os.chdir(previous)
        self.assertEqual(fake.call_args.args[0], REPOSITORY_ROOT)


if __name__ == "__main__":
    unittest.main()
