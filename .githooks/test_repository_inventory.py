import pathlib
import shutil
import subprocess
import tempfile
import unittest

from repository_inventory import discover_unit_test_directories

REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]


def git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class TestDiscoverUnitTestDirectories(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        # 发现器读的是 git 视图（已跟踪 + 未跟踪且未被忽略），测试仓库必须是真 git 仓库
        git(self.root, "init", "-q")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def touch(self, relative):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    def test_discovers_all_three_supported_roots(self):
        self.touch(".githooks/test_gate.py")
        self.touch(".claude/skills/demo/scripts/test_demo.py")
        self.touch("plugins/p/skills/s/scripts/test_s.py")

        self.assertEqual(
            discover_unit_test_directories(self.root),
            (
                ".claude/skills/demo/scripts",
                ".githooks",
                "plugins/p/skills/s/scripts",
            ),
        )

    def test_rejects_test_files_outside_supported_roots(self):
        self.touch("docs/examples/test_sample.py")
        self.touch("plugins/p/scripts/test_plugin_level.py")
        self.touch("plugins/p/skills/s/scripts/nested/test_nested.py")
        self.touch(".claude/skills/demo/test_not_in_scripts.py")

        self.assertEqual(discover_unit_test_directories(self.root), ())

    def test_deduplicates_directory_with_multiple_test_files(self):
        self.touch(".githooks/test_a.py")
        self.touch(".githooks/test_b.py")

        self.assertEqual(discover_unit_test_directories(self.root), (".githooks",))

    def test_ignores_non_test_python_files(self):
        self.touch(".githooks/check_something.py")
        self.touch("plugins/p/skills/s/scripts/helper.py")

        self.assertEqual(discover_unit_test_directories(self.root), ())

    def test_order_is_stable_and_sorted(self):
        self.touch("plugins/z/skills/s/scripts/test_z.py")
        self.touch("plugins/a/skills/s/scripts/test_a.py")
        self.touch(".githooks/test_gate.py")

        result = discover_unit_test_directories(self.root)
        self.assertEqual(result, tuple(sorted(result)))
        self.assertEqual(result, discover_unit_test_directories(self.root))

    def test_excludes_gitignored_test_files(self):
        # CI checkout 里不存在被忽略的文件；本地若照样发现它们，两侧范围就分叉了
        (self.root / ".gitignore").write_text(".claude/skills/scratch/\n", encoding="utf-8")
        self.touch(".claude/skills/scratch/scripts/test_local_only.py")
        self.touch(".githooks/test_gate.py")

        self.assertEqual(discover_unit_test_directories(self.root), (".githooks",))

    def test_includes_untracked_but_not_ignored_test_files(self):
        # 新写的测试在 git add 之前也要能在本地跑到
        self.touch(".githooks/test_new.py")
        self.assertEqual(discover_unit_test_directories(self.root), (".githooks",))

    def test_skips_tracked_file_deleted_from_worktree(self):
        self.touch(".githooks/test_gone.py")
        git(self.root, "add", ".")
        (self.root / ".githooks/test_gone.py").unlink()

        self.assertEqual(discover_unit_test_directories(self.root), ())


class TestRealRepositoryCoverage(unittest.TestCase):
    """守卫：仓库里每个 test_*.py 都必须落在发现器覆盖的目录里。

    自动发现只认三类位置；测试放到别处会被静默漏跑——这正是它替换掉的手写
    清单的失效形态。这条测试把「漏跑」变成红灯：要么挪到受支持的位置，要么
    扩展 repository_inventory.TEST_PATTERNS。
    """

    def test_every_test_file_is_in_a_discovered_directory(self):
        listed = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard",
             "-z", "--", "*test_*.py"],
            cwd=REPOSITORY_ROOT, check=True, capture_output=True,
        ).stdout.decode("utf-8").split("\0")
        test_files = [
            path for path in listed
            if path and pathlib.PurePosixPath(path).name.startswith("test_")
            and (REPOSITORY_ROOT / path).is_file()
        ]
        self.assertTrue(test_files, "未在仓库中找到任何 test_*.py，仓库根定位可能有误")

        discovered = set(discover_unit_test_directories(REPOSITORY_ROOT))
        uncovered = sorted(
            path for path in test_files
            if pathlib.PurePosixPath(path).parent.as_posix() not in discovered
        )
        self.assertEqual(uncovered, [], "以下测试文件不在自动发现范围内，会被静默漏跑")


if __name__ == "__main__":
    unittest.main()
