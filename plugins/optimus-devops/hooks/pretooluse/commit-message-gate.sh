#!/usr/bin/env bash
# PreToolUse 门禁：拦截 git commit，要求该条提交命令（含其中的 message）先经 commit-message-review 审查。
# 用法：
#   commit-message-gate.sh              默认检测模式，作为 PreToolUse hook 被调用（stdin 传入 hook JSON）
#   commit-message-gate.sh mark <hash>  审查通过后，标记该 hash 对应的提交命令为已审查

set -euo pipefail

GIT_DIR="$(git rev-parse --git-dir 2>/dev/null || true)"
if [[ -z "$GIT_DIR" ]]; then
    # 不在 git 仓库内：没有可门禁的对象。必须干净 exit 0，避免 set -e 下以 128 退出
    # 在每次 Bash 调用的 transcript 里留一条非阻断错误通知。
    if [[ "${1:-}" == "mark" ]]; then
        echo "当前目录不在 git 仓库内，无法标记。" >&2
        exit 1
    fi
    exit 0
fi

MARK_DIR="$GIT_DIR/optimus-review-marks"
MARK_FILE="$MARK_DIR/commit-message.hash"
SKILL_NAME="optimus-devops:commit-message-review"

if [[ "${1:-}" == "mark" ]]; then
    if [[ ! "${2:-}" =~ ^[0-9a-f]{64}$ ]]; then
        echo "用法：commit-message-gate.sh mark <64 位十六进制 hash>（hash 取自拦截提示）" >&2
        exit 1
    fi
    mkdir -p "$MARK_DIR"
    printf '%s\n' "$2" > "$MARK_FILE"
    echo "已标记该提交命令为审查通过。"
    exit 0
fi

input="$(cat)"
# 只取 tool_input.command 的值（JSON 字符串，允许 \" 等转义），避免命中 description 等其他字段。
# 刻意不起解释器解析 JSON：Git Bash 自带环境没有 python3，解析失败会让门禁静默放行；
# 且每次 Bash 调用都要多付一个解释器的启动开销。
COMMAND_RE='"command"[[:space:]]*:[[:space:]]*"(([^"\\]|\\.)*)"'
if [[ ! "$input" =~ $COMMAND_RE ]]; then
    exit 0
fi
command_text="${BASH_REMATCH[1]}"

GIT_COMMIT_RE='git[[:space:]]+(-C[[:space:]]+[^[:space:]]+[[:space:]]+)?commit([[:space:]]|\\|$)'
if [[ ! "$command_text" =~ $GIT_COMMIT_RE ]]; then
    exit 0
fi

# 以整条命令文本为审查对象：message 改动、--amend、-F 文件名变化都会使 hash 变化，必须重新审查。
hash_now="$(printf '%s' "$command_text" | sha256sum | cut -d' ' -f1)"
hash_marked="$(cat "$MARK_FILE" 2>/dev/null || true)"

if [[ -n "$hash_marked" && "$hash_now" == "$hash_marked" ]]; then
    exit 0
fi

cat >&2 <<EOF
这条 git commit 命令尚未经 ${SKILL_NAME} 审查（或审查后命令内容又发生了变化）。

请先调用 ${SKILL_NAME} 审查本次提交信息：
  - 结论为 NEEDS_CHANGES：按建议修正 message 后，用修正后的命令重新提交（命令变化会重新触发本门禁，需再审一次）；
  - 结论为 PASS / ADVISORY：执行下面的命令标记后，原样重新提交：
      bash "${BASH_SOURCE[0]}" mark ${hash_now}
EOF
exit 2
