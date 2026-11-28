import json
import pathlib
import shutil
import tempfile
import unittest

from check_plugin_versions import check_all, check_codex_contract


def make_plugin(root, name, claude_ver, codex_ver, claude_extra=None, base_dir="plugins"):
    """在临时仓库里造一个插件。ver 传 None 表示不建该文件。"""
    base = root / base_dir / name
    if claude_ver is not None:
        d = base / ".claude-plugin"
        d.mkdir(parents=True, exist_ok=True)
        body = {"name": name, "version": claude_ver}
        if claude_extra:
            body.update(claude_extra)
        (d / "plugin.json").write_text(
            json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if codex_ver is not None:
        d = base / ".codex-plugin"
        d.mkdir(parents=True, exist_ok=True)
        (d / "plugin.json").write_text(
            json.dumps({"name": name, "version": codex_ver}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
    base.mkdir(parents=True, exist_ok=True)
    return base


class TestCheckPluginVersions(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        (self.root / "plugins").mkdir()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_two_files_same_version_passes(self):
        make_plugin(self.root, "p-ok", "1.2.3", "1.2.3")
        self.assertEqual(check_all(self.root), [])

    def test_version_mismatch_is_reported_with_both_values(self):
        make_plugin(self.root, "p-bad", "1.0.2", "1.0.1")
        problems = check_all(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("p-bad", problems[0])
        self.assertIn("1.0.2", problems[0])
        self.assertIn("1.0.1", problems[0])

    def test_error_message_does_not_name_an_authoritative_side(self):
        """报错措辞不得写「以某一份为准」——正确动作是回头判断本次改动该升什么号。"""
        make_plugin(self.root, "p-bad", "2.0.0", "1.0.0")
        msg = check_all(self.root)[0]
        for forbidden in ("以 .claude-plugin 为准", "以 .codex-plugin 为准", "为准"):
            self.assertNotIn(forbidden, msg)
        self.assertIn("本次改动", msg)

    def test_missing_claude_plugin_json_is_reported(self):
        make_plugin(self.root, "p-no-claude", None, "1.0.0")
        problems = check_all(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn(".claude-plugin/plugin.json", problems[0])

    def test_missing_codex_plugin_json_is_reported(self):
        make_plugin(self.root, "p-no-codex", "1.0.0", None)
        problems = check_all(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn(".codex-plugin/plugin.json", problems[0])

    def test_missing_version_field_is_reported(self):
        base = self.root / "plugins" / "p-no-ver" / ".claude-plugin"
        base.mkdir(parents=True)
        (base / "plugin.json").write_text('{"name": "p-no-ver"}\n', encoding="utf-8")
        codex = self.root / "plugins" / "p-no-ver" / ".codex-plugin"
        codex.mkdir(parents=True)
        (codex / "plugin.json").write_text(
            '{"name": "p-no-ver", "version": "1.0.0"}\n', encoding="utf-8")
        problems = check_all(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("version", problems[0])

    def test_invalid_json_is_reported_not_raised(self):
        base = self.root / "plugins" / "p-broken" / ".claude-plugin"
        base.mkdir(parents=True)
        (base / "plugin.json").write_text("{not json", encoding="utf-8")
        codex = self.root / "plugins" / "p-broken" / ".codex-plugin"
        codex.mkdir(parents=True)
        (codex / "plugin.json").write_text(
            '{"name": "p-broken", "version": "1.0.0"}\n', encoding="utf-8")
        problems = check_all(self.root)   # 不得抛异常
        self.assertEqual(len(problems), 1)
        self.assertIn("无法解析", problems[0])

    def test_multiple_plugins_all_reported(self):
        make_plugin(self.root, "p-ok", "1.0.0", "1.0.0")
        make_plugin(self.root, "p-bad1", "1.0.0", "2.0.0")
        make_plugin(self.root, "p-bad2", "3.0.0", "4.0.0")
        problems = check_all(self.root)
        self.assertEqual(len(problems), 2)

    def test_claude_side_unknown_fields_are_reported(self):
        """白名单外的字段仍要拦截。"""
        make_plugin(self.root, "p-extra", "1.0.0", "1.0.0",
                    claude_extra={"skills": "./skills/"})
        problems = check_all(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("skills", problems[0])

    def test_claude_side_metadata_fields_are_allowed(self):
        """description 等字段 Claude 侧有独立消费方，不算重复真源。"""
        make_plugin(self.root, "p-meta", "1.0.0", "1.0.0",
                    claude_extra={
                        "description": "插件描述",
                        "homepage": "https://example.com",
                        "repository": "https://example.com",
                        "author": {"name": "x"},
                        "license": "MIT",
                        "keywords": ["a"],
                    })
        self.assertEqual(check_all(self.root), [])

    def test_agents_field_is_allowed(self):
        make_plugin(self.root, "p-agents", "1.0.0", "1.0.0",
                    claude_extra={"agents": ["./agents/x.md"]})
        self.assertEqual(check_all(self.root), [])

    def test_directory_without_any_plugin_json_is_skipped(self):
        """plugins/ 下可能有非插件目录（如临时文件夹），不报错。"""
        (self.root / "plugins" / "not-a-plugin").mkdir()
        self.assertEqual(check_all(self.root), [])

    def test_external_plugins_dir_absent_passes(self):
        """拷贝模式尚未使用时该目录不存在，视为通过（保持幂等）。"""
        make_plugin(self.root, "p-ok", "1.0.0", "1.0.0")
        self.assertFalse((self.root / "external_plugins").exists())
        self.assertEqual(check_all(self.root), [])

    def test_vendored_plugin_same_version_passes(self):
        make_plugin(self.root, "v-ok", "2.0.0", "2.0.0", base_dir="external_plugins")
        self.assertEqual(check_all(self.root), [])

    def test_vendored_plugin_version_mismatch_is_reported(self):
        make_plugin(self.root, "v-bad", "2.0.0", "2.0.1", base_dir="external_plugins")
        problems = check_all(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("v-bad", problems[0])

    def test_vendored_plugin_missing_codex_side_is_reported(self):
        make_plugin(self.root, "v-no-codex", "2.0.0", None, base_dir="external_plugins")
        problems = check_all(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn(".codex-plugin/plugin.json", problems[0])

    def test_vendored_prerelease_version_pair_passes(self):
        """有本地改动时版本形如 <上游版本>-optimus.N，两份同值即通过。"""
        make_plugin(self.root, "v-patched", "2.0.0-optimus.1", "2.0.0-optimus.1",
                    base_dir="external_plugins")
        self.assertEqual(check_all(self.root), [])

    def test_both_dirs_scanned_in_one_run(self):
        make_plugin(self.root, "p-bad", "1.0.0", "1.0.1")
        make_plugin(self.root, "v-bad", "2.0.0", "2.0.1", base_dir="external_plugins")
        self.assertEqual(len(check_all(self.root)), 2)


def make_codex_plugin(root, name, codex_extra=None, mcp=None, agents=None, hooks=None):
    """造一个双侧插件；mcp 为 dict 时写 .mcp.json，agents 为名字列表，hooks 为事件名列表。"""
    base = root / "plugins" / name
    claude = base / ".claude-plugin"
    claude.mkdir(parents=True, exist_ok=True)
    (claude / "plugin.json").write_text(
        json.dumps({"name": name, "version": "1.0.0"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    codex = base / ".codex-plugin"
    codex.mkdir(parents=True, exist_ok=True)
    body = {"name": name, "version": "1.0.0", "skills": "./skills/"}
    if codex_extra:
        body.update(codex_extra)
    (codex / "plugin.json").write_text(
        json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (base / "skills").mkdir(exist_ok=True)
    if mcp is not None:
        (base / ".mcp.json").write_text(
            json.dumps({"mcpServers": mcp}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
    if agents:
        d = base / "agents"
        d.mkdir(exist_ok=True)
        for agent_name in agents:
            (d / f"{agent_name}.md").write_text(
                f"---\nname: {agent_name}\ndescription: 测试 agent\n---\n\n正文\n",
                encoding="utf-8")
    if hooks:
        d = base / "hooks"
        d.mkdir(exist_ok=True)
        (d / "hooks.json").write_text(
            json.dumps({"hooks": {event: [] for event in hooks}}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
    return base


def write_marketplace(root, names):
    d = root / ".agents" / "plugins"
    d.mkdir(parents=True, exist_ok=True)
    (d / "marketplace.json").write_text(
        json.dumps({"name": "test", "plugins": [
            {"name": n, "source": {"source": "local", "path": f"./plugins/{n}"}}
            for n in names
        ]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_exclusions(root, entries):
    d = root / ".githooks"
    d.mkdir(parents=True, exist_ok=True)
    (d / "codex_component_exclusions.json").write_text(
        json.dumps({"exclusions": entries}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")


def exclusion(plugin, kind, ident, path, reason="测试用排除"):
    return {"plugin": plugin, "kind": kind, "id": ident, "path": path, "reason": reason}


class TestCodexContract(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def declare_mcp_file(self, plugin_dir, content):
        (plugin_dir / "mcp.json").write_text(
            json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def test_minimal_plugin_passes(self):
        make_codex_plugin(self.root, "p")
        write_marketplace(self.root, ["p"])
        self.assertEqual(check_codex_contract(self.root), [])

    def test_codex_name_mismatch(self):
        make_codex_plugin(self.root, "p", codex_extra={"name": "other"})
        write_marketplace(self.root, ["p"])
        problems = check_codex_contract(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("name", problems[0])

    def test_marketplace_missing_plugin(self):
        make_codex_plugin(self.root, "p1")
        make_codex_plugin(self.root, "p2")
        write_marketplace(self.root, ["p1"])
        problems = check_codex_contract(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("marketplace", problems[0])

    def test_marketplace_extra_plugin(self):
        make_codex_plugin(self.root, "p")
        write_marketplace(self.root, ["p", "ghost"])
        problems = check_codex_contract(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("marketplace", problems[0])

    def test_declared_mcp_file_missing(self):
        make_codex_plugin(self.root, "p", codex_extra={"mcpServers": "./nope.json"})
        write_marketplace(self.root, ["p"])
        problems = check_codex_contract(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("nope.json", problems[0])

    def test_declared_path_escapes_plugin(self):
        make_codex_plugin(self.root, "p", codex_extra={"mcpServers": "../x.json"})
        write_marketplace(self.root, ["p"])
        problems = check_codex_contract(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("越界", problems[0])

    def test_codex_hooks_key_rejected(self):
        make_codex_plugin(self.root, "p", codex_extra={"hooks": "./hooks/hooks.json"})
        write_marketplace(self.root, ["p"])
        problems = check_codex_contract(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("plugin_hooks", problems[0])

    def test_mcp_server_uncovered(self):
        plugin_dir = make_codex_plugin(
            self.root, "p", codex_extra={"mcpServers": "./mcp.json"},
            mcp={"a": {"command": "x"}, "b": {"command": "y"}})
        self.declare_mcp_file(plugin_dir, {"mcpServers": {"a": {"command": "x"}}})
        write_marketplace(self.root, ["p"])
        problems = check_codex_contract(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("b", problems[0])

    def test_mcp_server_excluded_passes(self):
        plugin_dir = make_codex_plugin(
            self.root, "p", codex_extra={"mcpServers": "./mcp.json"},
            mcp={"a": {"command": "x"}, "b": {"command": "y"}})
        self.declare_mcp_file(plugin_dir, {"mcpServers": {"a": {"command": "x"}}})
        write_marketplace(self.root, ["p"])
        write_exclusions(self.root, [exclusion("p", "mcp-server", "b", ".mcp.json")])
        self.assertEqual(check_codex_contract(self.root), [])

    def test_agent_uncovered(self):
        make_codex_plugin(self.root, "p", agents=["x"])
        write_marketplace(self.root, ["p"])
        problems = check_codex_contract(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("x", problems[0])

    def test_hook_event_requires_exclusion(self):
        make_codex_plugin(self.root, "p", hooks=["PreToolUse"])
        write_marketplace(self.root, ["p"])
        problems = check_codex_contract(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("PreToolUse", problems[0])

    def test_stale_exclusion(self):
        make_codex_plugin(self.root, "p")
        write_marketplace(self.root, ["p"])
        write_exclusions(self.root, [exclusion("p", "agent", "ghost", "agents/ghost.md")])
        problems = check_codex_contract(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("陈旧", problems[0])

    def test_exclusion_conflicts_with_declaration(self):
        make_codex_plugin(self.root, "p", agents=["x"],
                          codex_extra={"agents": ["./agents/x.md"]})
        write_marketplace(self.root, ["p"])
        write_exclusions(self.root, [exclusion("p", "agent", "x", "agents/x.md")])
        problems = check_codex_contract(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("冲突", problems[0])

    def test_exclusion_missing_reason(self):
        make_codex_plugin(self.root, "p")
        write_marketplace(self.root, ["p"])
        write_exclusions(self.root, [exclusion("p", "agent", "ghost", "agents/ghost.md", reason="")])
        problems = check_codex_contract(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("reason", problems[0])

    def test_malformed_mcp_json_reported_not_raised(self):
        plugin_dir = make_codex_plugin(self.root, "p", mcp={"a": {"command": "x"}})
        (plugin_dir / ".mcp.json").write_text("{", encoding="utf-8")
        write_marketplace(self.root, ["p"])
        problems = check_codex_contract(self.root)   # 不得抛异常
        self.assertEqual(len(problems), 1)
        self.assertIn(".mcp.json", problems[0])


if __name__ == "__main__":
    unittest.main()
