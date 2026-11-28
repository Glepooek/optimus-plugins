"""按 repository_gates.GATES 逐项执行仓库一致性门禁。

入口：
- 本地 hook：.githooks/pre-commit（薄包装，exec 本脚本）
- CI：gates-hooks 执行 `sh .githooks/pre-commit`，从而连 shell 包装一起验证
- PowerShell / 人工：python .githooks/run_repository_gates.py

语义与旧版 pre-commit 一致：每一项都执行，一项失败不遮住后面的问题，
最后统一返回 0/1。仓库根由本文件位置推出，不依赖调用者的当前目录——
各脚本都接收 "." 作参数，若沿用调用者 cwd，从别处调用会悄悄检查错位置。

🔴 输出中的 `[pre-commit] 未通过` 是与 commit-cc-plugin skill 的契约
   （它据此判断 commit 被门禁拦下），改措辞前先改那边。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from repository_gates import GATES, Gate

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def run_gates(root: Path, gates: tuple[Gate, ...], runner=subprocess.run) -> int:
    print("[pre-commit] 仓库一致性检查")
    failed: list[str] = []
    for index, gate in enumerate(gates, start=1):
        print(f"[gate {index}/{len(gates)}] {gate.name}", flush=True)
        command = [sys.executable, str(root / gate.script), *gate.args]
        try:
            completed = runner(command, cwd=root, check=False)
        except OSError as error:
            print(f"[gate {index}/{len(gates)}] {gate.name} 无法启动：{error}")
            failed.append(gate.name)
            continue
        if completed.returncode != 0:
            failed.append(gate.name)

    if failed:
        print(f"[pre-commit] 失败项：{', '.join(failed)}")
        print("[pre-commit] 未通过。修正后重新提交，不要用 --no-verify 绕过。")
        return 1
    print("[pre-commit] 通过")
    return 0


def main() -> int:
    return run_gates(REPOSITORY_ROOT, GATES)


if __name__ == "__main__":
    sys.exit(main())
