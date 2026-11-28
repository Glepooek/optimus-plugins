"""逐目录运行全仓 unittest——本地与 CI 的 gates-tests 共用这一个入口。

`unittest discover` 不跨目录递归，所以每个测试目录要单独调用一次。目录清单
不再手写：由 repository_inventory.discover_unit_test_directories() 按固定的
三类位置发现，新增测试目录落在这些位置就会被自动执行。

所有目录都执行完才返回，一个目录失败不遮住其他目录的结果。发现结果为空
直接判失败——那几乎一定是仓库根定位错了，不能让它变成假绿。
仓库根由本文件位置推出，不依赖调用者的当前目录。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from repository_inventory import discover_unit_test_directories

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def run_unit_tests(root: Path, directories: tuple[str, ...] | None = None,
                   runner=subprocess.run) -> int:
    if directories is None:
        directories = discover_unit_test_directories(root)
    if not directories:
        print(f"[unit-tests] 未发现任何测试目录（仓库根：{root}）")
        return 1

    print(f"[unit-tests] 发现 {len(directories)} 个测试目录")
    # Actions 日志里按目录折叠（旧的手写 shell 循环就有），本地输出保持干净
    in_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    failed: list[str] = []
    for index, directory in enumerate(directories, start=1):
        if in_actions:
            print(f"::group::{directory}", flush=True)
        print(f"[unit-tests {index}/{len(directories)}] {directory}", flush=True)
        command = [sys.executable, "-m", "unittest", "discover",
                   "-s", directory, "-p", "test_*.py"]
        try:
            completed = runner(command, cwd=root, check=False)
        except OSError as error:
            print(f"[unit-tests] {directory} 无法启动：{error}")
            failed.append(directory)
            continue
        finally:
            if in_actions:
                print("::endgroup::", flush=True)
        if completed.returncode != 0:
            failed.append(directory)

    if failed:
        print(f"[unit-tests] 失败目录：{', '.join(failed)}")
        return 1
    print("[unit-tests] 全部通过")
    return 0


def main() -> int:
    return run_unit_tests(REPOSITORY_ROOT)


if __name__ == "__main__":
    sys.exit(main())
