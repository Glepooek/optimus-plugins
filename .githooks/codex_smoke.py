"""Codex 零凭据安装冒烟（CI 专用）。

1. CI 专用：只在 ci.yml 的 plugin-validate job 里跑，不调用模型、不需要任何凭据。
2. 不进 repository_gates.py：它要联网装 CLI，违反「门禁只读工作树」约定，
   因此也不计入门禁项数。
3. `codex debug prompt-input` 是调试面而非公开契约：CLI 升级时先复核
   rendered_text 的解析与 "- <plugin>:<skill>: " 列表项前缀。

用法：CODEX_HOME=<隔离目录> python .githooks/codex_smoke.py <仓库根>
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Mapping

MARKETPLACE = "optimus-plugins"


def local_plugin_names(repo_root: Path) -> list[str]:
    data = json.loads((repo_root / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
    return [
        p["name"]
        for p in data.get("plugins", [])
        if isinstance(p.get("source"), dict) and p["source"].get("source") == "local"
    ]


def _frontmatter_name(text: str) -> str | None:
    m = re.match(r"\ufeff?---\r?\n(.*?)\r?\n---", text, re.S)
    if not m:
        return None
    nm = re.search(r"^name:\s*(.+?)\s*$", m.group(1), re.M)
    return nm.group(1).strip("\"'") if nm else None


def expected_skill_ids(repo_root: Path) -> set[str]:
    ids: set[str] = set()
    for skill in repo_root.glob("plugins/*/skills/*/SKILL.md"):
        name = _frontmatter_name(skill.read_text(encoding="utf-8"))
        if name:
            ids.add(f"{skill.parts[-4]}:{name}")
    return ids


def rendered_text(prompt_input_stdout: str) -> str:
    parts: list[str] = []

    def walk(node):
        if isinstance(node, str):
            parts.append(node)
        elif isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(json.loads(prompt_input_stdout))
    return "\n".join(parts)


def missing_skill_ids(rendered: str, expected: set[str]) -> list[str]:
    return sorted(i for i in expected if f"\n- {i}: " not in rendered)


def mcp_problems(mcp_list_stdout: str, expected: set[str], forbidden: set[str]) -> list[str]:
    names = {e.get("name") for e in json.loads(mcp_list_stdout)}
    problems = [f"缺少期望的 MCP: {n}" for n in sorted(expected - names)]
    problems += [f"出现禁止的 MCP: {n}" for n in sorted(forbidden & names)]
    return problems


def require_isolated_codex_home(env: Mapping[str, str]) -> str | None:
    value = env.get("CODEX_HOME", "")
    if not value.strip():
        return "CODEX_HOME 未设置：拒绝在用户真实 ~/.codex 上运行冒烟"
    if Path(value).resolve() == (Path.home() / ".codex").resolve():
        return "CODEX_HOME 指向用户真实 ~/.codex：拒绝运行冒烟"
    return None


def _run(codex: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [codex, *args], capture_output=True, text=True, encoding="utf-8"
    )


def main(argv: list[str]) -> int:
    import os

    root = Path(argv[1]).resolve()
    err = require_isolated_codex_home(os.environ)
    if err:
        print(err, file=sys.stderr)
        return 1
    Path(os.environ["CODEX_HOME"]).mkdir(parents=True, exist_ok=True)
    codex = shutil.which("codex")
    if not codex:
        print("[plugin-install] 找不到 codex 可执行文件")
        return 1

    failures: dict[str, list[str]] = {"plugin-install": [], "skill-visibility": [], "mcp-enumeration": []}
    plugins = local_plugin_names(root)

    r = _run(codex, "plugin", "marketplace", "add", str(root), "--json")
    if r.returncode != 0:
        failures["plugin-install"].append(f"marketplace add 失败: {r.stderr.strip()}")
    for p in plugins:
        r = _run(codex, "plugin", "add", f"{p}@{MARKETPLACE}", "--json")
        if r.returncode != 0:
            failures["plugin-install"].append(f"{p}: {r.stderr.strip()}")

    r = _run(codex, "plugin", "list", "--json")
    if r.returncode != 0:
        failures["plugin-install"].append(f"plugin list 失败: {r.stderr.strip()}")
    else:
        try:
            enabled = {
                e.get("name")
                for e in json.loads(r.stdout).get("installed", [])
                if e.get("installed") and e.get("enabled")
            }
        except (ValueError, AttributeError, TypeError) as exc:
            failures["plugin-install"].append(f"plugin list 输出无法解析: {exc!r}")
        else:
            for p in plugins:
                if p not in enabled and not any(f.startswith(f"{p}:") for f in failures["plugin-install"]):
                    failures["plugin-install"].append(f"{p}: 未安装或未启用")

    mcp_cfg = json.loads((root / "plugins/optimus-frontend/.codex-mcp.json").read_text(encoding="utf-8"))
    expected_mcp = set(mcp_cfg["mcpServers"])
    excl = json.loads((root / ".githooks/codex_component_exclusions.json").read_text(encoding="utf-8"))
    forbidden_mcp = {e["id"] for e in excl["exclusions"] if e.get("kind") == "mcp-server"}

    r = _run(codex, "mcp", "list", "--json")
    if r.returncode != 0:
        failures["mcp-enumeration"].append(f"mcp list 失败: {r.stderr.strip()}")
    else:
        try:
            failures["mcp-enumeration"] += mcp_problems(r.stdout, expected_mcp, forbidden_mcp)
        except (ValueError, AttributeError, TypeError) as exc:
            failures["mcp-enumeration"].append(f"mcp list 输出无法解析: {exc!r}")

    expected_skills = expected_skill_ids(root)
    r = _run(codex, "debug", "prompt-input", "x")
    if r.returncode != 0:
        failures["skill-visibility"].append(f"prompt-input 失败: {r.stderr.strip()}")
    else:
        try:
            failures["skill-visibility"] += [
                f"skill 不可见: {i}" for i in missing_skill_ids(rendered_text(r.stdout), expected_skills)
            ]
        except (ValueError, AttributeError, TypeError) as exc:
            failures["skill-visibility"].append(f"prompt-input 输出无法解析: {exc!r}")

    bad = False
    for cat, items in failures.items():
        for item in items:
            bad = True
            print(f"[{cat}] {item}")
    if bad:
        return 1
    print(f"Codex 冒烟通过：{len(plugins)} 插件 / {len(expected_skills)} skill / {len(expected_mcp)} MCP")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
