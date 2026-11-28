#!/usr/bin/env python3
"""optimus_dirs.py - 解析 optimus skill 的配置/缓存目录（仅标准库，跨平台）。

本文件在 plugins/optimus-devops/skills/jenkins-build/scripts/optimus_dirs.py
有一份逐字相同的副本（插件自包含要求）；改一处必须同步另一处。

解析优先级：
  1. 环境变量 OPTIMUS_CONFIG_DIR / OPTIMUS_CACHE_DIR（非空；相对路径按当前工作目录转绝对）
  2. Windows：%APPDATA%/optimus、%LOCALAPPDATA%/optimus/cache
     其他系统：$XDG_CONFIG_HOME/optimus、$XDG_CACHE_HOME/optimus（缺省 ~/.config、~/.cache）

用法：
  python optimus_dirs.py <skill-name> [--create]
  向 stdout 打印 {"config_dir": ..., "cache_dir": ...}；--create 时创建两个目录。
"""

import argparse
import json
import os
from pathlib import Path
from typing import Mapping, Optional


def _override(env: Mapping[str, str], key: str) -> Optional[Path]:
    value = env.get(key)
    if value:
        return Path(value).expanduser().resolve()
    return None


def config_root(env: Optional[Mapping[str, str]] = None,
                os_name: Optional[str] = None,
                home: Optional[Path] = None) -> Path:
    env = os.environ if env is None else env
    os_name = os.name if os_name is None else os_name
    home = Path.home() if home is None else home
    override = _override(env, "OPTIMUS_CONFIG_DIR")
    if override:
        return override
    if os_name == "nt":
        return Path(env.get("APPDATA") or home / "AppData" / "Roaming") / "optimus"
    return Path(env.get("XDG_CONFIG_HOME") or home / ".config") / "optimus"


def cache_root(env: Optional[Mapping[str, str]] = None,
               os_name: Optional[str] = None,
               home: Optional[Path] = None) -> Path:
    env = os.environ if env is None else env
    os_name = os.name if os_name is None else os_name
    home = Path.home() if home is None else home
    override = _override(env, "OPTIMUS_CACHE_DIR")
    if override:
        return override
    if os_name == "nt":
        return Path(env.get("LOCALAPPDATA") or home / "AppData" / "Local") / "optimus" / "cache"
    return Path(env.get("XDG_CACHE_HOME") or home / ".cache") / "optimus"


def skill_dirs(skill: str,
               env: Optional[Mapping[str, str]] = None,
               os_name: Optional[str] = None,
               home: Optional[Path] = None) -> dict:
    return {
        "config_dir": str(config_root(env, os_name, home) / skill),
        "cache_dir": str(cache_root(env, os_name, home) / skill),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="解析 optimus skill 的配置/缓存目录")
    parser.add_argument("skill", help="skill 名称")
    parser.add_argument("--create", action="store_true", help="创建两个目录")
    args = parser.parse_args()
    dirs = skill_dirs(args.skill)
    if args.create:
        for path in dirs.values():
            Path(path).mkdir(parents=True, exist_ok=True)
    print(json.dumps(dirs, ensure_ascii=False))


if __name__ == "__main__":
    main()
