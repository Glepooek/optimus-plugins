#!/usr/bin/env python3
"""校验每插件两份 plugin.json 的 version 是否同值。

版本真源是「两份 plugin.json 构成的一对」——改动插件内容后，两份在同一次改动内
一起升到同一个新值。不存在抄录关系与主从关系：新版本号由本次改动的性质决定
（见 AGENTS.md 版本管理规则的触发矩阵与幅度表），两份文件同等地是这个决定的记录。

因此发现不一致时，正确处置是回头判断本次改动该升什么号，然后把两份都写成那个号，
而不是拿一边覆盖另一边——那样有 50% 概率把正确的一边改错。

本文件同时承载仓库门禁的第 1 项（两份 plugin.json 版本同值）与第 9 项（Codex
manifest 契约）：Claude 侧真实存在的组件（.mcp.json、agents/*.md、hooks/hooks.json）
必须在 Codex manifest 中声明，或登记进 .githooks/codex_component_exclusions.json 的
Claude-only 排除表。两项合在一个脚本里，是因为它们读的是同一批 manifest——拆成两个
脚本要各自定位插件目录、各写一遍加载逻辑，且会牵动 .githooks/repository_gates.py
的 catalog 与本仓各处的检查项计数，没有对应收益。
"""
import json
import pathlib
import sys

CLAUDE_ALLOWED_KEYS = {
    "name", "version", "agents",
    # 以下元数据 Claude 侧确有独立消费方，不是 marketplace 条目的重复：
    # 已安装插件的描述渲染只读 manifest.description，不回退到 marketplace 条目；
    # homepage / repository 驱动插件详情页的「Open homepage」「View repository」菜单项；
    # author 缺失会被 `claude plugin validate` 报 warning。
    "description", "homepage", "repository", "author", "license", "keywords",
}


def _load(path):
    """返回 (data, err)。err 非 None 时 data 为 None。"""
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except json.JSONDecodeError as e:
        return None, f"无法解析 JSON：{e}"
    except OSError as e:
        return None, f"无法读取：{e}"


def check_plugin(plugin_dir):
    """校验单个插件目录，返回问题描述列表。"""
    name = plugin_dir.name
    claude_f = plugin_dir / ".claude-plugin" / "plugin.json"
    codex_f = plugin_dir / ".codex-plugin" / "plugin.json"

    # 两份都没有 → 不是本仓插件目录（如临时文件夹），跳过
    if not claude_f.exists() and not codex_f.exists():
        return []

    problems = []

    if not claude_f.exists():
        problems.append(
            f"[{name}] 缺 .claude-plugin/plugin.json"
            f"——Claude 侧会落到 git commit SHA 而非语义化版本")
        return problems
    if not codex_f.exists():
        problems.append(
            f"[{name}] 缺 .codex-plugin/plugin.json"
            f"——Codex 侧读不到该插件的版本号")
        return problems

    claude, err = _load(claude_f)
    if err:
        return [f"[{name}] .claude-plugin/plugin.json {err}"]
    codex, err = _load(codex_f)
    if err:
        return [f"[{name}] .codex-plugin/plugin.json {err}"]

    va, vb = claude.get("version"), codex.get("version")
    if va is None:
        problems.append(f"[{name}] .claude-plugin/plugin.json 缺 version 字段")
    if vb is None:
        problems.append(f"[{name}] .codex-plugin/plugin.json 缺 version 字段")

    if va is not None and vb is not None and va != vb:
        problems.append(
            f"[{name}] 两份 plugin.json 版本不一致："
            f".claude-plugin = {va}，.codex-plugin = {vb}。"
            f"请按本次改动的性质（见 AGENTS.md 版本管理规则的幅度表）确定应升到的版本号，"
            f"并把两份都改成该值")

    extra = set(claude) - CLAUDE_ALLOWED_KEYS
    if extra:
        problems.append(
            f"[{name}] .claude-plugin/plugin.json 有多余字段 {sorted(extra)}"
            f"——只应写 name / version / agents，其余元数据在 marketplace.json 声明，"
            f"重复维护会产生第二真源")

    return problems


SCAN_DIRS = ("plugins", "external_plugins")


def check_all(repo_root):
    """遍历 SCAN_DIRS 下所有插件目录，返回全部问题描述列表。

    external_plugins/ 是拷贝模式引入的外部 skill 的落点（见
    docs/superpowers/specs/2026-09-12-add-external-skill-design.md § 3.3）。
    它与 plugins/ 同样是双 harness 分发单元，因此同受两份同值规则约束；
    该目录不存在时跳过——拷贝模式尚未使用是正常状态。
    """
    repo_root = pathlib.Path(repo_root)
    plugins_dir = repo_root / "plugins"
    if not plugins_dir.is_dir():
        return [f"plugins/ 目录不存在：{plugins_dir}"]

    problems = []
    for rel in SCAN_DIRS:
        base = repo_root / rel
        if not base.is_dir():
            continue
        for d in sorted(base.iterdir()):
            if d.is_dir():
                problems.extend(check_plugin(d))
    return problems


EXCLUSIONS_REL = ".githooks/codex_component_exclusions.json"
EXCLUSION_KINDS = ("agent", "hook", "mcp-server")
EXCLUSION_FIELDS = ("plugin", "kind", "id", "path", "reason")


def load_exclusions(repo_root):
    """读取 Claude-only 组件排除表，返回 (有效条目, 问题)。文件缺失视为空表。"""
    path = pathlib.Path(repo_root) / EXCLUSIONS_REL
    if not path.exists():
        return [], []

    data, err = _load(path)
    if err:
        return [], [f"[exclusions] {EXCLUSIONS_REL} {err}"]
    entries = data.get("exclusions") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return [], [f"[exclusions] {EXCLUSIONS_REL} 缺 exclusions 数组"]

    valid, problems = [], []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            problems.append(f"[exclusions] 排除表第 {index} 条不是 JSON 对象")
            continue
        label = entry.get("plugin") if isinstance(entry.get("plugin"), str) else "exclusions"
        label = label or "exclusions"
        missing = [
            field for field in EXCLUSION_FIELDS
            if not isinstance(entry.get(field), str) or not entry[field].strip()
        ]
        if missing:
            problems.append(
                f"[{label}] 排除表第 {index} 条缺必填字段 {missing}"
                f"（plugin / kind / id / path / reason 均不得为空）")
            continue
        if entry["kind"] not in EXCLUSION_KINDS:
            problems.append(
                f"[{label}] 排除表第 {index} 条的 kind {entry['kind']!r} 不在 {list(EXCLUSION_KINDS)} 内")
            continue
        valid.append(entry)

    grouped = {}
    for entry in valid:
        grouped.setdefault((entry["plugin"], entry["kind"], entry["id"]), []).append(entry)
    for (plugin, kind, ident), group in grouped.items():
        if len(group) > 1:
            problems.append(
                f"[{plugin}] 排除表重复登记了 {kind} {ident!r}（共 {len(group)} 条），请合并为一条")
    return valid, problems


def _frontmatter_name(path):
    """取 agent 文件首个 `---` 块里的 name 行；不引入 YAML 依赖。"""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip("'\"") or None
    return None


def _declared_path(plugin_dir, rel, expect_dir, label, prefix):
    """校验 Codex manifest 声明的路径，返回 (resolved, 问题)。"""
    if not isinstance(rel, str) or not rel.strip():
        return None, f"{prefix} 的 {label} 声明必须是非空字符串路径"
    candidate = pathlib.Path(rel)
    if not candidate.is_absolute():
        candidate = plugin_dir / candidate
    try:
        resolved = candidate.resolve()
        resolved.relative_to(plugin_dir.resolve())
    except ValueError:
        return None, f"{prefix} 的 {label} 路径越界：{rel} 解析后不在插件目录内"
    if not resolved.exists():
        return None, f"{prefix} 声明的 {label} 不存在：{rel}"
    if expect_dir and not resolved.is_dir():
        return None, f"{prefix} 声明的 {label} 不是目录：{rel}"
    if not expect_dir and not resolved.is_file():
        return None, f"{prefix} 声明的 {label} 不是文件：{rel}"
    return resolved, None


def _rel_posix(plugin_dir, resolved):
    return resolved.relative_to(plugin_dir.resolve()).as_posix()


def component_inventory(plugin_dir):
    """从 Claude 侧真实文件反推组件清单，返回 ({(kind, id, path)}, 问题)。"""
    plugin_dir = pathlib.Path(plugin_dir)
    name = plugin_dir.name
    inventory, problems = set(), []

    mcp_f = plugin_dir / ".mcp.json"
    if mcp_f.exists():
        data, err = _load(mcp_f)
        if err:
            problems.append(f"[{name}] .mcp.json {err}")
        elif not isinstance(data, dict) or not isinstance(data.get("mcpServers"), dict):
            problems.append(f"[{name}] .mcp.json 缺顶层 mcpServers 对象")
        else:
            for server_id in data["mcpServers"]:
                inventory.add(("mcp-server", server_id, ".mcp.json"))

    agents_dir = plugin_dir / "agents"
    if agents_dir.is_dir():
        for agent_f in sorted(agents_dir.glob("*.md")):
            rel = f"agents/{agent_f.name}"
            agent_name = _frontmatter_name(agent_f)
            if not agent_name:
                problems.append(f"[{name}] {rel} 的 frontmatter 缺 name")
                continue
            inventory.add(("agent", agent_name, rel))

    hooks_f = plugin_dir / "hooks" / "hooks.json"
    if hooks_f.exists():
        data, err = _load(hooks_f)
        if err:
            problems.append(f"[{name}] hooks/hooks.json {err}")
        elif not isinstance(data, dict) or not isinstance(data.get("hooks"), dict):
            problems.append(f"[{name}] hooks/hooks.json 缺顶层 hooks 对象")
        else:
            for event in data["hooks"]:
                inventory.add(("hook", event, "hooks/hooks.json"))

    return inventory, problems


def codex_declared(plugin_dir, manifest):
    """解析 Codex manifest 的声明，返回 ({(kind, id, path)}, 问题)。"""
    plugin_dir = pathlib.Path(plugin_dir)
    prefix = f"[{plugin_dir.name}] Codex manifest"
    declared, problems = set(), []

    if "hooks" in manifest:
        problems.append(
            f"{prefix} 声明了 hooks——Codex CLI 0.172.0 的 plugin_hooks 已 removed，"
            f"Codex manifest 不得声明 hooks")

    if "skills" in manifest:
        _, problem = _declared_path(
            plugin_dir, manifest["skills"], True, "skills", prefix)
        if problem:
            problems.append(problem)

    agents = manifest.get("agents")
    if agents is not None and not isinstance(agents, list):
        problems.append(f"{prefix} 的 agents 必须是文件路径数组")
    elif agents:
        for rel in agents:
            resolved, problem = _declared_path(plugin_dir, rel, False, "agents", prefix)
            if problem:
                problems.append(problem)
                continue
            agent_name = _frontmatter_name(resolved)
            if not agent_name:
                problems.append(f"{prefix} 声明的 agent 文件 {rel} 缺 frontmatter name")
                continue
            declared.add(("agent", agent_name, _rel_posix(plugin_dir, resolved)))

    mcp_rel = manifest.get("mcpServers")
    if mcp_rel is not None:
        resolved, problem = _declared_path(plugin_dir, mcp_rel, False, "mcpServers", prefix)
        if problem:
            problems.append(problem)
        else:
            data, err = _load(resolved)
            if err:
                problems.append(f"{prefix} 声明的 mcpServers 文件 {mcp_rel} {err}")
            elif not isinstance(data, dict) or not isinstance(data.get("mcpServers"), dict):
                problems.append(f"{prefix} 声明的 mcpServers 文件 {mcp_rel} 缺顶层 mcpServers 对象")
            else:
                # 按 Claude 侧 id 比对，path 统一记 .mcp.json
                for server_id in data["mcpServers"]:
                    declared.add(("mcp-server", server_id, ".mcp.json"))

    return declared, problems


def _check_marketplace(repo_root, codex_plugin_names):
    problems = []
    mp_f = repo_root / ".agents" / "plugins" / "marketplace.json"
    if not mp_f.exists():
        return [f"[marketplace] 缺 {mp_f.relative_to(repo_root).as_posix()}"
                f"——Codex 侧没有安装入口"]

    data, err = _load(mp_f)
    if err:
        return [f"[marketplace] .agents/plugins/marketplace.json {err}"]
    entries = data.get("plugins") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return ["[marketplace] .agents/plugins/marketplace.json 缺 plugins 数组"]

    local_names = {
        entry["name"] for entry in entries
        if isinstance(entry, dict)
        and isinstance(entry.get("source"), dict)
        and entry["source"].get("source") == "local"
        and isinstance(entry.get("name"), str)
    }
    for missing in sorted(local_names - codex_plugin_names):
        problems.append(
            f"[marketplace] local 条目 {missing!r} 没有对应的 .codex-plugin/plugin.json，"
            f"Codex 侧装不上")
    for extra in sorted(codex_plugin_names - local_names):
        problems.append(
            f"[marketplace] 插件 {extra!r} 有 .codex-plugin/plugin.json "
            f"但未作为 local 条目登记在 .agents/plugins/marketplace.json")
    return problems


def _check_mcp_subset(plugin_dir, manifest):
    """Codex 独立 MCP 文件必须是 Claude .mcp.json 的内容一致子集。"""
    mcp_rel = manifest.get("mcpServers")
    if not isinstance(mcp_rel, str):
        return []
    resolved, _ = _declared_path(plugin_dir, mcp_rel, False, "mcpServers", "")
    claude_f = plugin_dir / ".mcp.json"
    if resolved is None or resolved == claude_f.resolve() or not claude_f.exists():
        return []
    codex_data, err1 = _load(resolved)
    claude_data, err2 = _load(claude_f)
    if err1 or err2 or not isinstance(codex_data, dict) or not isinstance(claude_data, dict):
        return []
    codex_servers, claude_servers = codex_data.get("mcpServers"), claude_data.get("mcpServers")
    if not isinstance(codex_servers, dict) or not isinstance(claude_servers, dict):
        return []
    name, problems = plugin_dir.name, []
    for server_id in sorted(codex_servers):
        if server_id not in claude_servers:
            problems.append(
                f"[{name}] Codex MCP 文件声明了 {server_id!r}，但 Claude .mcp.json 中没有该 server"
                f"（Codex 分发了 Claude 侧不存在的 server）")
        elif codex_servers[server_id] != claude_servers[server_id]:
            problems.append(
                f"[{name}] mcp-server {server_id!r} 在 Codex MCP 文件与 Claude .mcp.json 中的内容不一致（内容漂移）")
    return problems


def check_codex_contract(repo_root):
    """校验 Codex manifest 与 Claude 侧真实组件、排除表、marketplace 的契约。"""
    repo_root = pathlib.Path(repo_root)
    problems = []

    exclusions, exclusion_problems = load_exclusions(repo_root)
    problems.extend(exclusion_problems)

    plugins_dir = repo_root / "plugins"
    if not plugins_dir.is_dir():
        return problems + [f"plugins/ 目录不存在：{plugins_dir}"]

    codex_plugin_names = set()
    for plugin_dir in sorted(d for d in plugins_dir.iterdir() if d.is_dir()):
        codex_f = plugin_dir / ".codex-plugin" / "plugin.json"
        if not codex_f.exists():
            continue
        codex_plugin_names.add(plugin_dir.name)

        manifest, err = _load(codex_f)
        if err:
            problems.append(f"[{plugin_dir.name}] .codex-plugin/plugin.json {err}")
            continue
        if not isinstance(manifest, dict):
            problems.append(
                f"[{plugin_dir.name}] .codex-plugin/plugin.json 顶层不是 JSON 对象")
            continue

        if manifest.get("name") != plugin_dir.name:
            problems.append(
                f"[{plugin_dir.name}] Codex manifest 的 name 是 "
                f"{manifest.get('name')!r}，应等于插件目录名 {plugin_dir.name!r}")

        declared, declared_problems = codex_declared(plugin_dir, manifest)
        problems.extend(declared_problems)
        inventory, inventory_problems = component_inventory(plugin_dir)
        problems.extend(inventory_problems)

        problems.extend(_check_mcp_subset(plugin_dir, manifest))

        declared_ids = {(kind, ident) for kind, ident, _ in declared}
        inventory_ids = {(kind, ident) for kind, ident, _ in inventory}
        excluded_ids = {
            (entry["kind"], entry["id"])
            for entry in exclusions if entry["plugin"] == plugin_dir.name
        }
        # 陈旧与否按完整三元组比对：id 对、path 错同样描述的不是真实组件
        excluded_full = {
            (entry["kind"], entry["id"], entry["path"])
            for entry in exclusions if entry["plugin"] == plugin_dir.name
        }
        live_excluded_ids = {
            (kind, ident) for kind, ident, path in excluded_full if (kind, ident, path) in inventory
        }

        for kind, ident in sorted(inventory_ids - declared_ids - excluded_ids):
            problems.append(
                f"[{plugin_dir.name}] {kind} {ident!r} 未在 Codex manifest 声明，"
                f"也未登记到 {EXCLUSIONS_REL}")
        for kind, ident, path in sorted(excluded_full - inventory):
            problems.append(
                f"[{plugin_dir.name}] 排除表中的 {kind} {ident!r}（path={path}）在 Claude 侧组件中"
                f"不存在（陈旧排除项），请删除该条")
        for kind, ident in sorted(live_excluded_ids & declared_ids):
            problems.append(
                f"[{plugin_dir.name}] {kind} {ident!r} 既在排除表中又被 Codex manifest 声明"
                f"（排除项与 Codex 声明冲突），二者只能留一")

    for entry in exclusions:
        if entry["plugin"] not in codex_plugin_names:
            problems.append(
                f"[{entry['plugin']}] 排除表条目的 plugin 不是任何带 .codex-plugin/plugin.json "
                f"的插件（陈旧排除项），请删除该条")

    problems.extend(_check_marketplace(repo_root, codex_plugin_names))
    return problems


def main():
    root = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(".")
    code = 0

    problems = check_all(root)
    if problems:
        print("插件版本号校验未通过：")
        for p in problems:
            print(f"  - {p}")
        code = 1
    else:
        print("插件版本号校验通过：所有插件的两份 plugin.json 同值")

    contract = check_codex_contract(root)
    if contract:
        print("Codex manifest 契约校验未通过：")
        for p in contract:
            print(f"  - {p}")
        code = 1
    else:
        print("Codex manifest 契约校验通过")
    return code


if __name__ == "__main__":
    sys.exit(main())
