# C# 开发规范（创作素材存档）

> 版本：8.0.0

> ⚠️ **团队 C# 规范正文已不在本目录。** 17 篇规范（`01`–`17`）已迁入 `optimus-backend-plugin` 的 `csharp-code-review` skill 的 `references/`，随插件分发，安装后即可完整运行、不依赖本仓库。

## 本领域现状

本目录只保留 **`reference/refit.md`**——Refit 的权威技术参考，属**创作期素材**：它不进插件包，也没有 skill 读取它，留在这里供后续编辑规范时查阅。

判断依据：判据文件必须能被安装后的 skill 读到，因此随插件走；纯参考资料没有消费者，留在知识库不产生成本。

## 需要 C# 规范时去哪里

| 你要找 | 去处 |
|---|---|
| 编码风格、异步、异常、内存、性能、并发、数据访问、依赖管理、可观测性、测试、API 设计、安全、审查、协作、注释 | `csharp-code-review` skill 的 `references/<编号>-<主题>.md`（`optimus-backend-plugin`） |
| 逐类审查清单与核对要点 | 同 skill 的 `SKILL.md` |
| 平台与运行时事实（目标框架、SDK、生命周期） | `knowledge-base/dotnet/` |
| 语言无关的架构风格、分层契约、设计原则 | `knowledge-base/architecture/` |
| 设计模式的选用判据与误用识别 | `knowledge-base/design-patterns/` |
| WPF/XAML 专属规则 | `wpf-code-review` skill（`optimus-frontend-plugin`） |

**不要在本目录新增规范正文**——那会与插件内的判据形成两份必然漂移的副本，而安装后的 skill 读不到这里。

## 索引

`index.jsonl` 现只有一条 `csharp.ref.refit`，对应 `reference/refit.md`。字段说明与维护约定见仓库根 `knowledge-base/README.md`。

## 更新与维护

- 修改 `reference/refit.md` 时同一次提交里同步 `index.jsonl`，并升本文件版本行与 `CHANGELOG.md` 最新条目（两者须同值，`check_index.py` 会校验）
- 改动后运行 `python .claude/skills/knowledge-base-maintain/scripts/check_index.py csharp`
