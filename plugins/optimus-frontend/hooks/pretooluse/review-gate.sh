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

has_staged() {
    case "$1" in
        wpf) [[ ${#WPF_FILES[@]} -gt 0 ]] ;;
        avalonia) [[ ${#AVALONIA_FILES[@]} -gt 0 ]] ;;
    esac
}

# 打印某类别的 staged 文件，每行一个。空数组在 bash 3.2 + set -u 下展开会报错，故先判长度。
staged_files() {
    case "$1" in
        wpf)
            if [[ ${#WPF_FILES[@]} -gt 0 ]]; then printf '%s
' "${WPF_FILES[@]}"; fi ;;
        avalonia)
            if [[ ${#AVALONIA_FILES[@]} -gt 0 ]]; then printf '%s
' "${AVALONIA_FILES[@]}"; fi ;;
    esac
}

current_hash() {
    git diff --cached -- ":(icase)$(gate_pattern "$1")" | sha256sum | cut -d' ' -f1
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
# 后缀不区分大小写（Windows 文件系统下 A.XAML 与 a.xaml 是同一类文件），分类用 [xX] 括号式，哈希用 :(icase) pathspec。
# 一次 git 调用取全部 staged 路径，再在 bash 里按后缀归类，而不是每类各起一次 git——
# 本 hook 每次 Bash 调用都会触发，进程数就是成本。-z 让路径不被引号转义，
# 中文、空格文件名也能按后缀匹配，不会因此漏判。
WPF_FILES=()
AVALONIA_FILES=()
while IFS= read -r -d '' f; do
    case "$f" in
        *.[xX][aA][mM][lL]) WPF_FILES+=("$f") ;;
        *.[aA][xX][aA][mM][lL]) AVALONIA_FILES+=("$f") ;;
    esac
done < <(git diff --cached --name-only -z)

staged_cats=()
for category in "${CATEGORIES[@]}"; do
    if has_staged "$category"; then
        staged_cats+=("$category")
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
for category in "${staged_cats[@]}"; do
    hash_now="$(current_hash "$category")"
    hash_marked="$(cat "$MARK_DIR/$category.hash" 2>/dev/null || true)"
    if [[ -z "$hash_marked" || "$hash_now" != "$hash_marked" ]]; then
        blocked+=("$category")
    fi
done
if [[ ${#blocked[@]} -eq 0 ]]; then
    exit 0
fi

{
    for category in "${blocked[@]}"; do
        echo "检测到 staged 的 $(gate_pattern "$category") 改动尚未经 $(gate_skill "$category") 审查（或审查后内容又发生了变化）："
        staged_files "$category"
        echo
        echo "请先调用 $(gate_skill "$category") 完成审查并修复问题，再执行："
        echo "  bash \"${BASH_SOURCE[0]}\" mark $category"
        echo
    done
    echo "标记通过后重新提交。"
} >&2
exit 2
