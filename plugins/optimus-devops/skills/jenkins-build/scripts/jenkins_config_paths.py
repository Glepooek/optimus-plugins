"""jenkins_config_paths.py - jenkins-build 配置文件查找路径（仅标准库，跨平台）。

优先级（顺序固定）：
  1. $JENKINS_BUILD_PROJECT_DIR/jenkins-config.yaml  （项目级，is_legacy=False）
     若未设置 JENKINS_BUILD_PROJECT_DIR，使用传入的 cwd。
  2. <optimus-config-dir>/jenkins-build/jenkins-config.yaml  （用户级，is_legacy=False）
     由 optimus_dirs.skill_dirs("jenkins-build") 解析。
  3. <home>/.claude/jenkins-config.yaml  （旧位置，is_legacy=True，只读兼容）
"""

import os
import sys
from pathlib import Path
from typing import List, Mapping, Optional, Tuple

# 确保 scripts/ 目录在 sys.path 中，以便导入同目录的 optimus_dirs
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import optimus_dirs  # noqa: E402

PROJECT_DIR_ENV = "JENKINS_BUILD_PROJECT_DIR"


def config_search_paths(
    env: Optional[Mapping[str, str]] = None,
    os_name: Optional[str] = None,
    home: Optional[Path] = None,
    cwd: Optional[Path] = None,
) -> List[Tuple[Path, bool]]:
    """返回 [(路径, 是否旧路径)] 顺序固定的三项查找列表。"""
    env = os.environ if env is None else env
    home = Path.home() if home is None else home
    cwd = Path.cwd() if cwd is None else cwd

    # 优先级 1：JENKINS_BUILD_PROJECT_DIR 或 cwd
    project_dir = env.get(PROJECT_DIR_ENV)
    base_dir = Path(project_dir) if project_dir else cwd
    path1 = base_dir / "jenkins-config.yaml"

    # 优先级 2：optimus 配置目录（平台中立）
    dirs = optimus_dirs.skill_dirs("jenkins-build", env=env, os_name=os_name, home=home)
    path2 = Path(dirs["config_dir"]) / "jenkins-config.yaml"

    # 优先级 3：旧位置，只读兼容
    path3 = home / ".claude" / "jenkins-config.yaml"

    return [
        (path1, False),
        (path2, False),
        (path3, True),
    ]


def find_config(
    env: Optional[Mapping[str, str]] = None,
    os_name: Optional[str] = None,
    home: Optional[Path] = None,
    cwd: Optional[Path] = None,
) -> Optional[Tuple[Path, bool]]:
    """返回第一个存在的配置条目，若都不存在则返回 None。"""
    for path, is_legacy in config_search_paths(env=env, os_name=os_name, home=home, cwd=cwd):
        if path.exists():
            return path, is_legacy
    return None
