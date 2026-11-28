"""仓库事实发现：unittest 测试目录。

只认三类位置，不递归扫描整个仓库——否则 docs/ 里的样例、fixture 或第三方
目录中碰巧叫 test_*.py 的文件会被当成测试套件执行。

新增测试目录只要落在这三类位置之一，就会被 run_unit_tests.py 与 CI 的
gates-tests 自动执行，不需要再改任何清单。若要支持第四类位置，改这里的
TEST_PATTERNS，并同步改 test_repository_inventory.py。

反方向由 test_repository_inventory.TestRealRepositoryCoverage 守住：仓库里
任何不在三类位置的 test_*.py 都会让单测变红。真要放一个不该执行的样例，
就别给它起 test_ 前缀——宁可多一次改名，也不留一个静默漏跑的口子。
"""

from __future__ import annotations

import subprocess
from pathlib import Path, PurePosixPath

TEST_PATTERNS = (
    ".githooks/test_*.py",
    ".claude/skills/*/scripts/test_*.py",
    "plugins/*/skills/*/scripts/test_*.py",
)


def discover_unit_test_directories(root: Path) -> tuple[str, ...]:
    """返回含 test_*.py 的目录（仓库根相对 POSIX 路径），去重并排序。

    读的是 git 视图而非裸文件系统：已跟踪文件 + 未跟踪且未被 .gitignore
    排除的文件。被忽略的文件在 CI checkout 里根本不存在，若本地照样发现
    它们，本地与 CI 的执行范围就会静默分叉；未跟踪文件则保留，让新写的
    测试在 git add 之前也能在本地跑到。

    `:(glob)` 让 `*` 不跨越 `/`（git pathspec 默认的 `*` 会匹配多级目录），
    保持「只认三类位置、不递归」的语义。
    """
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z",
         "--", *(f":(glob){pattern}" for pattern in TEST_PATTERNS)],
        cwd=root, check=True, capture_output=True,
    ).stdout.decode("utf-8")
    directories: set[str] = set()
    for path in filter(None, listed.split("\0")):
        # --cached 会列出已从工作树删除、但仍在 index 里的文件
        if (root / path).is_file():
            directories.add(PurePosixPath(path).parent.as_posix())
    return tuple(sorted(directories))
