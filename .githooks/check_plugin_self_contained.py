#!/usr/bin/env python3
"""校验插件运行时自包含：插件内的运行时文件不得引用插件目录以外的路径。

## 为什么需要这个检查

插件安装单元是 `plugins/<name>/`——marketplace 安装时整个目录被复制进用户缓存
（`knowledge-base/` 不在其中）。因此插件内任何指向仓库其它位置的路径，在开发期
（`--plugin-dir` 加载整个仓库）能解析，安装后必然失效。

失效形态是**静默**的：skill 运行时读不到判据，Claude 会用自身泛型知识补全，
报告看起来正常，但团队规范一条都没执行。这类退化没有任何报错，只能靠静态检查拦截。

`check_refs.py` 校验的是「引用的章节号是否对得上」，管不到「这个路径在安装后还在不在」。
两者互补，缺一不可。

## 判据：怎么区分「引用」与「输出路径」

插件正文里两种写法长得一模一样：

- `知识库判据见 knowledge-base/csharp/rules/02-coding-style.md` —— 引用，安装后失效
- 报告写入 `docs/project-overview.md` —— 让用户在**自己项目**里产出的路径，与插件无关

区别不在语法，在**该路径能不能在本仓命中一个真实文件**。后者只指向用户项目的未来产物，
本仓自然没有；前者指向的是本仓既有内容。故本脚本只判「解析后命中的、位于插件目录之外的
真实文件」——「本仓恰好存在同名文件」与「用户项目输出路径」同时为真的概率极低。

两种解析基准都要试，因为两种写法都出现过：

| 写法 | 解析基准 | 例 |
|---|---|---|
| 相对穿越 | 消费者所在目录 | `../../../../knowledge-base/csharp/README.md` |
| 仓库相对 | 仓库根 | `knowledge-base/csharp/README.md`、`.claude/rules/hook-conventions.md` |

仓库相对这一类只在**本仓自有根目录**下判定（见 `REPO_OWNED_PREFIXES`）——`docs/`
既可能是本仓的 `docs/`，也可能是任意用户项目的文档目录，只有前者算违规。

## 不检查的范围

| 对象 | 理由 |
|---|---|
| `CHANGELOG.md`、`known-issues*.md` | 历史记录。它们记的是「当时发生了什么」，不是「现在按什么办」；改写等于伪造记录 |
| `hooks/*/README.md` | 写给改 hook 的人看的开发说明，harness 运行时从不加载，死链不影响任何 skill 行为 |
| `books/**` | 书籍录入的中间产物工作区（候选、摘要、流水线状态），不是 skill 分发内容 |

排除是**按文件性质**逐个列举的，不是按模式批量放行——新增一类排除前先问：
这个文件装进去会被 harness 在运行时读取吗？答案是否，才排除。

用法：
    python check_plugin_self_contained.py           # 检查全部插件
    python check_plugin_self_contained.py <plugin>  # 只查一个插件
    python check_plugin_self_contained.py --list    # 只列出问题，不因失败退出
"""
import re
import sys
from pathlib import Path

# 历史记录：不追改，也不参与本门禁
EXCLUDED_NAMES = re.compile(r'^(CHANGELOG\.md|known-issues.*\.md)$')

# 目录级排除：(相对插件根的路径模式, 理由见模块 docstring)
EXCLUDED_PATH_PARTS = ("books",)
EXCLUDED_REL_SUFFIXES = ("hooks/README.md",)

# 本仓自有根目录：只有这些前缀才按「仓库相对」解析判定。
# `docs/` 夹在中间是刻意的——用户项目里的 docs/ 与它同名，靠「本仓是否存在该文件」区分。
REPO_OWNED_PREFIXES = (
    "knowledge-base/",
    "docs/",
    ".claude/",
    ".githooks/",
    ".github/",
    ".agents/",
    ".kiro/",
    "external_plugins/",
    "plugins/",
)

# 反引号内与 markdown 链接里的路径 token
CODE_SPAN_RE = re.compile(r'`(?P<path>[^`\s]+)`')
LINK_RE = re.compile(r'\[[^\]]*\]\((?P<path>[^)\s]+)\)')

# 占位符与通配：模板里的 `<slug>`、`*.md`、`$HOME` 不是真实路径
PLACEHOLDER_CHARS = frozenset("<>*$[]{}")

# 路径结尾可能粘上标点（`见 xxx.md。`、`见 xxx.md,`）
TRAILING_PUNCT = '.,;:。)」”\'"'


def iter_markdown_files(plugin_dir):
    """产出插件内需要检查的 markdown 文件。"""
    for path in sorted(plugin_dir.rglob("*.md")):
        if EXCLUDED_NAMES.match(path.name):
            continue
        rel = path.relative_to(plugin_dir).as_posix()
        if any(part in EXCLUDED_PATH_PARTS for part in path.relative_to(plugin_dir).parts):
            continue
        if any(rel.endswith(suffix) for suffix in EXCLUDED_REL_SUFFIXES):
            continue
        yield path


def candidate_refs(line):
    """产出一行里 (列号, 路径文本) 的候选引用。"""
    for regex in (CODE_SPAN_RE, LINK_RE):
        for m in regex.finditer(line):
            raw = m.group("path")
            if raw.startswith(("http://", "https://", "mailto:", "#")):
                continue
            yield m.start("path"), raw.rstrip(TRAILING_PUNCT)


def looks_like_ref(raw):
    """粗筛：是不是一个可能指向仓库文件的相对路径。"""
    if not raw or raw.startswith(("~", "/", "\\")):
        return False
    if re.match(r'^[a-zA-Z]:[\\/]', raw):     # Windows 绝对路径
        return False
    if PLACEHOLDER_CHARS & set(raw):
        return False
    return raw.endswith(".md") or raw.startswith("knowledge-base/")


def resolve_outside(raw, file_dir, repo_root, plugin_root):
    """返回该引用越界命中的真实路径；不越界则 None。

    两种基准都试：先按消费者所在目录（相对穿越的写法），再按仓库根（仓库相对的写法）。
    """
    for base, target in (("relative", file_dir / raw), ("repo-root", repo_root / raw)):
        try:
            resolved = target.resolve()
        except OSError:
            continue
        if not resolved.exists():
            continue
        if resolved.is_relative_to(plugin_root):
            return None                       # 落在插件内，自包含成立
        if base == "relative":
            return resolved                   # 相对穿越出插件，确定越界
        if any(raw.startswith(p) for p in REPO_OWNED_PREFIXES):
            return resolved                   # 仓库相对写法指向本仓其它目录，确定越界
        return None
    return None


def check_file(path, plugin_root, repo_root):
    """返回该文件的越界问题列表。"""
    problems = []
    rel = path.relative_to(repo_root).as_posix()
    shown_plugin = plugin_root.relative_to(repo_root).as_posix()

    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        seen = set()
        for _, raw in candidate_refs(line):
            if not looks_like_ref(raw):
                continue
            hit = resolve_outside(raw, path.parent, repo_root, plugin_root)
            # 按解析后的真实路径去重：同一份文件常同时以显示文本与链接目标出现
            # （``[`knowledge-base/x.md`](../../../../knowledge-base/x.md)``），
            # 两者 raw 不同但指向同一处，只该报一次。
            if hit is None or (line_no, hit) in seen:
                continue
            seen.add((line_no, hit))
            problems.append(
                f"{rel}:{line_no}: 引用越出插件目录：{raw}\n"
                f"    解析为 {hit}——不在 {shown_plugin}/ 内，安装后读不到。"
                f"判据须随 skill 分发到该插件自己的 references/。")
    return problems


def check_plugin(plugin_dir, repo_root):
    problems = []
    for path in iter_markdown_files(plugin_dir):
        problems.extend(check_file(path, plugin_dir.resolve(), repo_root))
    return problems


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    list_only = "--list" in sys.argv[1:]

    repo_root = Path(__file__).resolve().parents[1]
    plugins_root = repo_root / "plugins"

    if args:
        targets = [plugins_root / name for name in args]
    else:
        targets = sorted(p for p in plugins_root.iterdir() if p.is_dir())

    all_problems, checked = [], []
    for plugin_dir in targets:
        if not plugin_dir.is_dir():
            print(f"跳过不存在的插件目录：{plugin_dir}", file=sys.stderr)
            continue
        all_problems.extend(check_plugin(plugin_dir, repo_root))
        checked.append(plugin_dir.name)

    if all_problems:
        for p in all_problems:
            print(p, file=sys.stderr)
        print(f"\n共 {len(all_problems)} 处引用越出插件目录（检查 {len(checked)} 个插件）",
              file=sys.stderr)
        print("判据：插件安装单元是 plugins/<name>/，其中一切引用必须在包内可解析。",
              file=sys.stderr)
        sys.exit(0 if list_only else 1)

    print(f"OK: {len(checked)} 个插件全部自包含（无引用越出插件目录）")
    sys.exit(0)


if __name__ == "__main__":
    main()
