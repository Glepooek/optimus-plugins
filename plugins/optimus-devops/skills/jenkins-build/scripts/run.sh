#!/bin/bash
# Jenkins 构建触发脚本
# 用法：
#   ./run.sh                    # 触发默认 job
#   ./run.sh zk-api             # 触发指定 job
#   ./run.sh zk-api BRANCH=main # 触发带参数的 job

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# venv 放在 optimus 缓存目录（由 optimus_dirs.py 解析，跨平台/harness 中立）
CACHE_DIR="$(python3 "$SCRIPT_DIR/optimus_dirs.py" jenkins-build --create | python3 -c 'import json,sys; print(json.load(sys.stdin)["cache_dir"])')"
VENV_DIR="$CACHE_DIR/.venv"

# 兼容 Windows（Scripts/）和 Unix（bin/）的 venv 路径
if [ -f "$VENV_DIR/Scripts/python.exe" ]; then
    PYTHON="$VENV_DIR/Scripts/python.exe"
    PIP="$VENV_DIR/Scripts/pip.exe"
else
    PYTHON="$VENV_DIR/bin/python"
    PIP="$VENV_DIR/bin/pip"
fi

# 创建虚拟环境并安装依赖
if [ ! -f "$PYTHON" ]; then
    echo "[~] 创建虚拟环境..."
    python3 -m venv "$VENV_DIR"
    if [ -f "$VENV_DIR/Scripts/python.exe" ]; then
        PYTHON="$VENV_DIR/Scripts/python.exe"
        PIP="$VENV_DIR/Scripts/pip.exe"
    else
        PYTHON="$VENV_DIR/bin/python"
        PIP="$VENV_DIR/bin/pip"
    fi
fi

if ! "$PYTHON" -c "import requests, yaml" 2>/dev/null; then
    echo "[~] 安装依赖..."
    "$PIP" install requests pyyaml -q
fi

# 保存调用者工作目录，供 main.py 中的配置查找使用（cd 后 PWD 会变为 skill 目录）
export JENKINS_BUILD_PROJECT_DIR="$PWD"

# 执行构建（配置查找由 main.py 负责）
cd "$SKILL_DIR/jenkins_build"
PYTHONIOENCODING=utf-8 "$PYTHON" main.py "$@"
