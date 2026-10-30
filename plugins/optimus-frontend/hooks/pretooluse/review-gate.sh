#!/usr/bin/env bash
# PreToolUse 门禁：拦截 git commit，要求 staged 的 .xaml / .axaml 改动先经对应 skill 审查。
#   wpf       *.xaml    wpf-code-review
#   avalonia  *.axaml   avalonia-code-review
# 两类各自独立判定、各自一个标记文件，审查一类不会放行另一类。
# 用法：
#   review-gate.sh                  默认检测模式，作为 PreToolUse hook 被调用（stdin 传入 hook JSON）
#   review-gate.sh mark <类别>      审查通过后，标记该类别当前 staged 内容为已审查（wpf | avalonia）

set -euo pipefail

CATEGORIES=(wpf avalonia)

# 不用关联数组：兼容 bash 3.2。
gate_pattern() {
    case "$1" in
        wpf) echo '*.xaml' ;;
        avalonia) echo '*.axaml' ;;
    esac
}

gate_skill() {
    case "$1" in
        wpf) echo 'wpf-code-review' ;;
        avalonia) echo 'avalonia-code-review' ;;
    esac
}

is_category() {
    local c
    for c in "${CATEGORIES[@]}"; do
        [[ "$c" == "${1:-}" ]] && return 0
    done
    return 1
}

staged_files() {
    git diff --cached --name-only -- "$(gate_pattern "$1")"
}

current_hash() {
    git diff --cached -- "$(gate_pattern "$1")" | sha256sum | cut -d' ' -f1
}

GIT_DIR="$(git rev-parse --git-dir 2>/dev/null || true)"
if [[ -z "$GIT_DIR" ]]; then
    # 不在 git 仓库内：没有可门禁的对象。必须干净 exit 0——`set -e` 下让
    # git rev-parse 失败会以 128 退出，被当成非阻断 hook 错误，虽然同样放行，
    # 但每次 Bash 调用都在 transcript 留一条错误通知。
    if [[ "${1:-}" == "mark" ]]; then
        echo "当前目录不在 git 仓库内，无法标记。" >&2
        exit 1
    fi
    exit 0
fi

MARK_DIR="$GIT_DIR/optimus-review-marks"

if [[ "${1:-}" == "mark" ]]; then
    if ! is_category "${2:-}"; then
        echo "用法: review-gate.sh mark <wpf|avalonia>" >&2
        exit 1
    fi
    mkdir -p "$MARK_DIR"
    current_hash "$2" > "$MARK_DIR/$2.hash"
    echo "已标记当前 staged 的 $(gate_pattern "$2") 改动为审查通过。"
    exit 0
fi

# 检测模式：两类都没有 staged 改动，直接放行，不必关心当前命令是不是 git commit
staged_cats=()
for cat in "${CATEGORIES[@]}"; do
    if [[ -n "$(staged_files "$cat")" ]]; then
        staged_cats+=("$cat")
    fi
done
if [[ ${#staged_cats[@]} -eq 0 ]]; then
    exit 0
fi

input="$(cat)"
# 只在 tool_input.command 的值内匹配，避免命中 description 等其他字段。
# 刻意不起解释器解析 JSON：Git Bash 自带环境没有 python3，解析失败会让门禁
# 静默放行；且每次 Bash 调用都要多付一个解释器的启动开销。
GIT_COMMIT_RE='"command"[[:space:]]*:[[:space:]]*"[^"]*git[[:space:]]+commit'
if [[ ! "$input" =~ $GIT_COMMIT_RE ]]; then
    exit 0
fi

blocked=()
for cat in "${staged_cats[@]}"; do
    hash_now="$(current_hash "$cat")"
    hash_marked="$(cat "$MARK_DIR/$cat.hash" 2>/dev/null || true)"
    if [[ -z "$hash_marked" || "$hash_now" != "$hash_marked" ]]; then
        blocked+=("$cat")
    fi
done
if [[ ${#blocked[@]} -eq 0 ]]; then
    exit 0
fi

{
    for cat in "${blocked[@]}"; do
        echo "检测到 staged 的 $(gate_pattern "$cat") 改动尚未经 $(gate_skill "$cat") 审查（或审查后内容又发生了变化）："
        staged_files "$cat"
        echo
        echo "请先调用 $(gate_skill "$cat") 完成审查并修复问题，再执行："
        echo "  bash \"${BASH_SOURCE[0]}\" mark $cat"
        echo
    done
    echo "标记通过后重新提交。"
} >&2
exit 2
