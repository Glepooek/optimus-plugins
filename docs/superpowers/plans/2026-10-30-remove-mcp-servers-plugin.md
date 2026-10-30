# 删除 旧 MCP 插件 并将 MCP 并入 optimus-frontend 实施计划

> 对应 spec：`docs/superpowers/specs/2026-10-30-remove-mcp-servers-plugin-design.md`（章节号 §N 均指该 spec）
> 分支：`refactor/remove-mcp-servers-plugin`（type 与 commit 的 Conventional Commits type 对齐）
> 提交：全程不手动 git 提交，完成后走 `commit-cc-plugin` → PR → 六项检查全绿 → squash merge

## Task 0：准备

- [ ] 0.1 `git switch -c refactor/remove-mcp-servers-plugin`（当前在 clean 的 master）
- [ ] 0.2 基线：`sh .githooks/pre-commit` 通过 → 验证：退出码 0（确认改动前是绿的）
- [ ] 0.3 记录基线残留清单：`grep -rIn "旧 MCP 插件" --exclude-dir=.git . > /tmp/before.txt`，作为 Task 9 对账依据

## Task 1：迁移 MCP 配置与 README（§6.1）

- [ ] 1.1 `git mv plugins/<旧 MCP 插件>/.mcp.json plugins/optimus-frontend/.mcp.json`
- [ ] 1.2 `git mv plugins/<旧 MCP 插件>/README.md plugins/optimus-frontend/README.md`
- [ ] 1.3 编辑 `plugins/optimus-frontend/.mcp.json`：删除整个 `FeishuProjectMcp` 对象；并把 `mastergo-magic-mcp.env` 改为 `"MG_MCP_TOKEN": "${MASTERGO_TOKEN}"`（`args` 中的占位符后改为 `--token=<MASTERGO_TOKEN>`，见 spec §5 第 5 条）→ 验证：`python -c "import json;d=json.load(open('plugins/optimus-frontend/.mcp.json'));print(list(d['mcpServers']))"` 输出 `['avalonia-docs', 'mastergo-magic-mcp']`

## Task 2：删除旧插件（§6.2）

- [ ] 2.1 `git rm -r plugins/<旧 MCP 插件>`（剩余文件：两份 `plugin.json`、`mcp.config.json`、`config.toml.example`、`scripts/`）
- [ ] 2.2 清理未跟踪残留（`scripts/__pycache__` 等）：`rm -rf plugins/<旧 MCP 插件>` → 验证：`ls plugins/<旧 MCP 插件>` 报不存在

## Task 3：重写 frontend README（§5 第 6 条）

分段编辑 `plugins/optimus-frontend/README.md`，每步一次 Edit：

- [ ] 3.1 标题与首段：改为"Optimus Frontend 内置 MCP 服务"，说明包含 2 个 server，且 MCP 配置**仅面向 Claude Code**
- [ ] 3.2 保留「Avalonia Docs MCP」「MasterGo Magic MCP」两节；**删除**「飞书项目 MCP」整节
- [ ] 3.3 删「配置说明」开头的"单一真源 / gen_mcp_config.py / config.toml.example"引言块
- [ ] 3.4 「Claude Code 使用方式」：`env` 示例只留 `MASTERGO_TOKEN`；安装命令改 `claude plugins install optimus-frontend@optimus-plugins`；`enabledMcpjsonServers` 改 `["avalonia-docs", "mastergo-magic-mcp"]`
- [ ] 3.5 **整段删除**「Codex 使用方式」（方式 A/B、环境变量表、注意事项、生效时机）
- [ ] 3.6 「Token 获取」只留 MasterGo，导出变量名统一写 `MASTERGO_TOKEN`；全文原 `MG_MCP_TOKEN` 改为 `MASTERGO_TOKEN`（含 3.2 的"环境变量"行）；删飞书 Token
- [ ] 3.7 新增「从 旧 MCP 插件 迁移」小节：先卸载旧插件避免重复注册；旧的 `enabledMcpjsonServers` / `permissions.allow` 需更新。**命名空间细节留到 Task 8 实测后回填，此处先写占位 TODO，Task 8 必须清掉**
- [ ] 验证：`grep -n "飞书\|Feishu\|Codex\|codex\|MCP_USER_TOKEN\|gen_mcp_config\|config.toml" plugins/optimus-frontend/README.md` 只可能命中 3.7 的迁移说明里的"飞书"字样（若有），不应有其他命中

## Task 4：frontend 与 qa 的 skill 说明（§6.3）

先 `ls` 各 skill 目录确认是否有 `CHANGELOG.md`；有则按 `doc-conventions.md` 格式补 Patch 条目。

- [ ] 4.1 `avalonia/SKILL.md`：`compatibility`（L5）与故障表（L52）中 旧 MCP 插件 → `optimus-frontend` 内置的 Avalonia Docs MCP；`metadata.version 2.1.2→2.1.3`
- [ ] 4.2 `avalonia-code-review/SKILL.md`：L5、L93 同上；`1.0.3→1.0.4`
- [ ] 4.3 `avalonia-wpf-migration/SKILL.md`：L5 同上（先 grep 是否还有其他处）；`1.2.3→1.2.4`
- [ ] 4.4 `mastergo-icon-expoter/SKILL.md`（L8）：`本仓库 plugins/<旧 MCP 插件>/.mcp.json 内置` → `optimus-frontend 插件内置`；`1.1.2→1.1.3`
- [ ] 4.5 `mastergo-to-wpf-components/SKILL.md`（L8）：同上；`1.0.2→1.0.3`
- [ ] 4.6 `mastergo-to-wpf-page/SKILL.md`（L8）：同上；`2.0.3→2.0.4`
- [ ] 4.7 `optimus-qa-feishu-project-sync/SKILL.md`（L8）：把"需要已配置的飞书项目管理 MCP server（本仓库内置 FeishuProjectMcp）及有效鉴权"换成"需自行安装飞书项目 CLI，并完成授权"，**其余句子（如模式C依赖 Playwright/Midscene）原样保留**；不动 `allowed-tools`
- [ ] 4.8 `optimus-qa-test-report/SKILL.md`（L8）：整句换为"需自行安装飞书项目 CLI，并完成授权。"
- [ ] 4.9 `optimus-qa-test-design/SKILL.md`（L8）：`MasterGo 为本仓库内置 mastergo-magic-mcp` → `MasterGo 由 optimus-frontend 插件提供 mastergo-magic-mcp`
- [ ] 验证：`git diff --stat -- plugins/*/skills` 只含 frontmatter 的 `compatibility`/`metadata.version` 行与故障表两行；`git diff` 中无任何正文逻辑变动

## Task 5：清单、版本号与仓库级文档（§6.3、§7）

- [ ] 5.1 `.claude-plugin/marketplace.json`：删 旧 MCP 插件 条目；顶层 `version 15.0.0→16.0.0`；`optimus-frontend` 条目 `description` 与 5.3 的新 `description` 保持一致
- [ ] 5.2 `.agents/plugins/marketplace.json`：删 旧 MCP 插件 条目（注意前后逗号）
- [ ] 5.3 `optimus-frontend` 两份 `plugin.json`：`version 2.1.3→2.2.0`；`description` 补"内置 Avalonia Docs 与 MasterGo MCP"；`.codex-plugin` 另有 `interface.longDescription` 同步改；**不得出现 `mcpServers` 字段**
- [ ] 5.4 `optimus-qa` 两份 `plugin.json`：`version 2.0.1→2.0.2`，两份同值
- [ ] 5.5 仓库根 `README.md`：删 L19 插件行、L36 依赖行；L30 frontend 依赖行改为"自带 Avalonia Docs MCP（无需认证）与 MasterGo Magic MCP（`MASTERGO_TOKEN`）"；L32 qa 行"飞书项目 MCP"→"飞书项目 CLI（需自行安装并授权）"
- [ ] 5.6 `.claude/rules/skill-conventions.md` L61：先读上下文，若 旧 MCP 插件 仅作举例则改为 `optimus-frontend`
- [ ] 5.7 `.kiro/steering/plugins.md`：删 L89–98 的 旧 MCP 插件 整节（连同前后一条 `---` 分隔，保持相邻节间只有一条）；在 `optimus-frontend` 节末尾补一行"内置 MCP：Avalonia Docs、MasterGo Magic（`MASTERGO_TOKEN`）"
- [ ] 5.8 `.kiro/steering/structure.md`：删 L56 表行；L60 去掉"（MCP 例外：旧 MCP 插件）"；L74 路径改 `plugins/optimus-frontend/.mcp.json`
- [ ] 5.9 `.kiro/steering/tech.md`：删 MCP 服务器表中 `Feishu Project` 行
- [ ] 验证：`python -c "import json;[json.load(open(f)) for f in ('.claude-plugin/marketplace.json','.agents/plugins/marketplace.json','plugins/optimus-frontend/.claude-plugin/plugin.json','plugins/optimus-frontend/.codex-plugin/plugin.json','plugins/optimus-qa/.claude-plugin/plugin.json','plugins/optimus-qa/.codex-plugin/plugin.json')]"` 全部可解析；`grep -c mcpServers plugins/optimus-frontend/.codex-plugin/plugin.json` 为 0

## Task 6：CI 与 AGENTS.md（§6.3，"不报错的失效形态"重点）

- [ ] 6.1 `.github/workflows/ci.yml`：从 `gates-tests` 的目录列表删 `plugins/<旧 MCP 插件>/scripts`，同时把倒数第二项末尾的续行 `\` 保持正确（原最后一项无 `\`，删后新的最后一项 `svg-to-xaml-path/scripts` 不能带 `\`，否则 `do` 被吞）
- [ ] 6.2 ci.yml 的 `plugin-validate` 注释（约 L224–226）：删"旧 MCP 插件 无 skills/，被 -d 判断跳过"的例外说法，并核对"9 个含 skills/ 的插件"计数与 `ls -d plugins/*/skills | wc -l` 一致后再写
- [ ] 6.3 `AGENTS.md`：①"全仓共 **9 个**测试目录"→**8 个**；②删 `python -m unittest discover -s plugins/<旧 MCP 插件>/scripts ...` 一行；③「重要约束」加一条：MCP 配置（`plugins/*/.mcp.json`）只面向 Claude Code，不为 Codex 维护 `config.toml` 镜像
- [ ] 验证：`grep -n "unittest discover" AGENTS.md | wc -l` 与 ci.yml 目录数一致（均为 8）；`python -c "import yaml,sys;yaml.safe_load(open('.github/workflows/ci.yml'))"` 可解析（无 yaml 模块则用 `actionlint` 以外的肉眼核对续行）

## Task 7：知识库（§6.3）

先读 `knowledge-base-maintain` skill 再动手。

- [ ] 7.1 `knowledge-base/mcp/README.md` L7、L69：改指 `plugins/optimus-frontend/`，去掉"飞书项目"
- [ ] 7.2 `knowledge-base/mcp/CHANGELOG.md` 补 `[1.0.1]` 条目；README 若含版本号一并改为 1.0.1（两处一致）
- [ ] 7.3 `knowledge-base/tools/reference/github-cli.md` L14：读该行，仅当它断言"现状含 旧 MCP 插件"才改；纯历史引用则不动（若改，按 tools 领域规则升版并同步 index/CHANGELOG）
- [ ] 验证：`python .claude/skills/knowledge-base-maintain/scripts/check_index.py` 与 `check_refs.py` 退出码 0

## Task 8：本地验证（§9）

- [ ] 8.1 `sh .githooks/pre-commit` → 退出码 0
- [ ] 8.2 逐个跑 8 个 unittest 目录（AGENTS.md「本地测试」清单，已无 mcp-servers 项）→ 全部 OK
- [ ] 8.3 `python .claude/skills/sync-cc-tips/scripts/validate_tips.py` → 通过
- [ ] 8.4 `test-locally`：`claude --plugin-dir .` 加载，`/mcp` 看到 frontend 提供的 `avalonia-docs`、`mastergo-magic-mcp`，**没有** `FeishuProjectMcp`；记录实际的 server 显示名/命名空间
- [ ] 8.5 把 8.4 实测的命名空间回填 README「迁移」小节，清除 Task 3.7 的占位 TODO → 验证：`grep -n TODO plugins/optimus-frontend/README.md` 无输出
- [ ] 8.5b 令牌实测：仅设 `MASTERGO_TOKEN` 启动，`/mcp` 中 MasterGo server 应为已连接；失败则回到 `.mcp.json` 调整 env/args 映射（需用户提供有效令牌配合）
- [ ] 8.6 残留对账：`grep -rIn "旧 MCP 插件" --exclude-dir=.git .` 命中项必须全部落在 spec §6.4 白名单 + 本 spec/plan 内；`grep -rIn "MG_MCP_TOKEN"` 只剩 `.mcp.json` 的 env 键与 README 迁移说明；`.kiro/steering/` 无 旧 MCP 插件；`grep -rIn "FeishuProjectMcp\|MCP_USER_TOKEN"` 只剩两个 qa skill 的 `allowed-tools` 与历史文档

## Task 9：提交与合并

- [ ] 9.1 触发 `commit-cc-plugin`（说"提交"），type 用 `refactor`，scope 用 `plugins`；分支名 `refactor/remove-mcp-servers-plugin`
- [ ] 9.2 PR 描述必须写明：①破坏性变更（旧插件消失，需卸载重装 `optimus-frontend`）；②已知缺口：两个 qa 飞书 skill 的 `allowed-tools` 仍引用 `FeishuProjectMcp`，未改写为 CLI 流程；③MasterGo 令牌环境变量统一为 `MASTERGO_TOKEN`，旧用户设置的 `MG_MCP_TOKEN` 需改名
- [ ] 9.3 等 `gates-hooks`、`gates-tests`、`gates-data`、`plugin-validate`、`new-skill-eval-case`、`actionlint` 六项全绿后 squash merge
- [ ] 9.4 合并后 `gh api repos/:owner/:repo/rulesets/23134670` 无需改动（本次未改任何 job 名），仅确认 `gates-tests` 仍为必需检查

## 任务依赖

Task 1→2→3 顺序执行；Task 4、5、7 互相独立，均依赖 Task 2 完成；Task 6 独立；Task 8 依赖 1–7 全部完成；Task 9 依赖 8。
