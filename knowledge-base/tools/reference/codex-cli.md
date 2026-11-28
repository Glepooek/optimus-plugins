# Codex CLI

- **简介**：OpenAI 的命令行 coding agent。本仓库把它作为与 Claude Code 并列的第二个 harness，插件经 `.agents/plugins/marketplace.json` 与每插件 `.codex-plugin/plugin.json` 分发。
- **安装方式**：`npm install -g @openai/codex@0.172.0`。CI 固定该版本，禁止 `latest`。
- **已验证行为**（0.172.0，Windows）：
  - `codex debug prompt-input "x"` 在未登录、无 API key 时可渲染模型可见的 skill 清单，条目格式 `\n- <plugin>:<skill>: <description>`，路径以别名根表加相对路径给出
  - `codex mcp list --json` 可零凭据列出插件 MCP，返回顶层数组，元素含 `name`
  - `codex plugin add` **不校验** manifest 组件路径（缺失与越界路径均安装成功），不能作为加载成功判据
  - `CODEX_HOME` 必须指向已存在的目录
- **已验证限制**：
  - 插件 `agents` 声明在 `multi_agent_v2` 开关下均未进入渲染提示
  - `.mcp.json` 的 `${VAR}` 不展开
  - `plugin_hooks` 为 removed，Claude 侧插件 Hook 不会在 Codex 生效
- **本仓使用位置**：`.githooks/codex_smoke.py`（CI 专用的零凭据冒烟）、`.github/workflows/ci.yml` 的 `plugin-validate` job。Claude-only 组件登记在 `.githooks/codex_component_exclusions.json`。
- **备注**：以上行为均为 0.172.0 的实测结论，升级版本后需重跑冒烟再沿用。
