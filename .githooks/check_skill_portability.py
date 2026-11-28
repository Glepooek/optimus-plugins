#!/usr/bin/env python3
"""skill 可移植性扫描（仓库门禁第 10 项）。

依据 docs/superpowers/specs/2026-11-28-codex-compatibility-hardening-design.md §6.2。
SKILL.md 是 Claude Code 与 Codex 共用的唯一真源，因此其中不应出现某一 harness 专属的
安装路径、专属工具名，也不应带 Agent Skills 规范之外的 frontmatter 键。

检查项（rule）：
  frontmatter-key    顶层键不在 ALLOWED_FRONTMATTER_KEYS 内
  harness-path       字面 .claude/.codex 安装路径（见 HARNESS_PATH_PATTERNS）
  tool-token         正文出现 BLOCKED_TOOL_TOKENS（allowed-tools 行不算正文）
  marker-no-reason   豁免标记缺 reason=
  marker-orphan      豁免标记旁没有任何 harness-path 命中
  skill-dir-missing  正文 <skill-dir>/<相对路径> 不是 skill 目录内的实际文件（目录、越界路径都不算）
  unreadable         文件无法按 UTF-8 读取（扫描不到即等于放行，所以单独报出）

扫描范围：skill 根目录的 SKILL.md；skill 内递归的 *.sh、*.ps1、*.py（不含 test_*.py）；
references/ 下递归的 *.md——它们随包分发、由模型按需读取，写死的路径同样会被照做。

三处取舍：
1. 排除 test_*.py（仅 .py）：测试夹具必须字面写出旧路径才能断言回退行为，扫它们只会逼出无意义豁免。
2. 阻断清单只有 AskUserQuestion：只收录已确认 Codex 无对应物、且会让 skill 在 Codex 下
   直接失效的工具名；宁缺毋滥，避免门禁变成噪声。已知盲区：拼接出来的路径（如
   os.path.join(expanduser("~"), ".claude")）正则扫不到，只认字面路径。
3. 标记以行为单位：标记在第 N 行，豁免 N 与 N+1 行的 harness-path 命中。YAML/bash/
   PowerShell 用 `#` 注释放在命中行前一行；Markdown 正文/表格用同行 HTML 注释。
   一个标记覆盖该行所有命中，不必逐个路径声明。

用法：check_skill_portability.py [--list] <repo_root>
  默认：有 Finding 则逐条打印并返回 1；--list 同样打印但返回 0（存量审计用）。
"""
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ALLOWED_FRONTMATTER_KEYS = frozenset(
    {"name", "description", "license", "compatibility", "metadata", "allowed-tools"})
MARKER = "codex-portability: allow-harness-path reason="


def _patterns():
    out = []
    for h in ("claude", "codex"):
        out.extend([
            re.compile(rf"\.{h}/skills/"),
            re.compile(rf"~/\.{h}/"),
            re.compile(rf"\$HOME/\.{h}/"),
            re.compile(rf"%USERPROFILE%\\\.{h}\\"),
            re.compile(rf"\$env:USERPROFILE\\\.{h}\\"),
        ])
    return tuple(out)


HARNESS_PATH_PATTERNS = _patterns()
BLOCKED_TOOL_TOKENS = ("AskUserQuestion",)
_TOOL_RES = tuple(re.compile(rf"\b{t}\b") for t in BLOCKED_TOOL_TOKENS)
_SKILL_DIR_RE = re.compile(r"<skill-dir>/([^\s`\"')]+)")
_SCRIPT_SUFFIXES = {".sh", ".ps1", ".py"}
_RULE_UNREADABLE = "unreadable"


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str
    text: str


def _frontmatter_end(lines):
    """返回结束 --- 的 0 基下标；无 frontmatter 返回 -1。"""
    if not lines or lines[0].strip() != "---":
        return -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return i
    return -1


def _scan_file(path, rel, lines, is_skill_md, skill_dir):
    out = []
    fm_end = _frontmatter_end(lines) if is_skill_md else -1

    if is_skill_md and fm_end > 0:
        for i in range(1, fm_end):
            ln = lines[i]
            if not ln or ln[0] in " \t#":
                continue
            m = re.match(r"([^:\s][^:]*):", ln)
            if m and m.group(1).strip() not in ALLOWED_FRONTMATTER_KEYS:
                out.append(Finding(rel, i + 1, "frontmatter-key", ln.strip()))

    marker_lines = {}
    for i, ln in enumerate(lines):
        pos = ln.find(MARKER)
        if pos >= 0:
            reason = ln[pos + len(MARKER):].replace("-->", "").strip()
            marker_lines[i] = reason
    hit_lines = {i for i, ln in enumerate(lines)
                 if any(p.search(ln) for p in HARNESS_PATH_PATTERNS)}

    for i in sorted(hit_lines):
        if i in marker_lines or (i - 1) in marker_lines:
            continue
        out.append(Finding(rel, i + 1, "harness-path", lines[i].strip()))
    for i, reason in marker_lines.items():
        if not reason:
            out.append(Finding(rel, i + 1, "marker-no-reason", lines[i].strip()))
        if i not in hit_lines and (i + 1) not in hit_lines:
            out.append(Finding(rel, i + 1, "marker-orphan", lines[i].strip()))

    if is_skill_md:
        body_start = fm_end + 1 if fm_end >= 0 else 0
        for i in range(body_start, len(lines)):
            ln = lines[i]
            if any(r.search(ln) for r in _TOOL_RES):
                out.append(Finding(rel, i + 1, "tool-token", ln.strip()))
            for m in _SKILL_DIR_RE.finditer(ln):
                sub = m.group(1).rstrip(".,;:，。；：")
                target = (skill_dir / sub).resolve()
                inside = target.is_relative_to(skill_dir.resolve())
                if not (inside and target.is_file()):
                    out.append(Finding(rel, i + 1, "skill-dir-missing",
                                       f"<skill-dir>/{sub}"))
    return out


def scan_skill(skill_dir, repo_root):
    skill_dir, repo_root = Path(skill_dir), Path(repo_root)
    findings = []
    files = []
    for p in sorted(skill_dir.rglob("*")):
        if not p.is_file():
            continue
        if p.name == "SKILL.md" and p.parent == skill_dir:
            files.append(p)
        elif p.suffix in _SCRIPT_SUFFIXES:
            if not (p.suffix == ".py" and p.name.startswith("test_")):
                files.append(p)
        elif p.suffix == ".md" and p.relative_to(skill_dir).parts[0] == "references":
            files.append(p)
    for p in files:
        try:
            text = p.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as e:
            findings.append(Finding(p.relative_to(repo_root).as_posix(), 0,
                                    _RULE_UNREADABLE, f"无法读取：{e}"))
            continue
        rel = p.relative_to(repo_root).as_posix()
        findings.extend(_scan_file(
            p, rel, text.split("\n"), p.name == "SKILL.md" and p.parent == skill_dir,
            skill_dir))
    return findings


def scan_repo(repo_root):
    repo_root = Path(repo_root)
    findings = []
    for d in sorted((repo_root / "plugins").glob("*/skills/*/")):
        if d.is_dir():
            findings.extend(scan_skill(d, repo_root))
    return findings


def main(argv):
    args = argv[1:]
    list_mode = "--list" in args
    args = [a for a in args if a != "--list"]
    if len(args) != 1:
        print("用法：check_skill_portability.py [--list] <repo_root>", file=sys.stderr)
        return 2
    findings = scan_repo(args[0])
    for f in findings:
        print(f"{f.path}:{f.line}: [{f.rule}] {f.text}")
    if findings and not list_mode:
        print(f"skill 可移植性：共 {len(findings)} 处问题", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
