# commit-message-review

> 版本：1.0.1 | 分类：quality

依据随 skill 分发的提交信息规则审查拟提交或已有提交信息，产出按严重程度排序的合规结论和不编造事实的修正建议。

## 所处层级

本 skill 位于质量保障层，作为提交动作之前的只读审查器使用。

```
┌────────────────────────────────────────────────────────────┐
│ skill 工作形态层级（按 metadata.category 取值）            │
│                                                            │
│ workflow   流程编排 · 多阶段 pipeline / 交接式工作流       │
│ ★ quality  质量保障 · review / 评分 / 一致性校验          │
│ generator  产物生成 · PRD / 代码 / 测试 / 报告            │
│ tool       工具类 · 数据同步 / 符号链接管理 / 脚本初始化   │
│ platform   平台专项 · android / ios / harmony              │
│ decision   决策支持 · 选型结论 / 适用性判断                │
│                                                            │
│ 上游：用户提供的 commit message 或 Git commit 引用         │
│ 下游：人工或仓库既有提交工作流执行确认后的提交动作          │
└────────────────────────────────────────────────────────────┘
```

## 触发词 / 调用方式

Claude Code：`/optimus-devops-plugin:commit-message-review`。Codex：自然语言触发或 `@optimus-devops-plugin:commit-message-review`。

常见触发词：审查提交信息、review commit message、检查 commit msg、改写 Git 提交说明、Conventional Commits 校验、检查 AI co-author footer。

## 业务逻辑流程图

```
Step 1  收集完整 message 或明确的 Git commit 引用
   │    可选：用户要求时才读取暂存 diff
   ▼
Step 2  按随附规则参考检查标题、type、意图、breaking change
   │    和 AI Co-Authored-By footer
   ▼
Step 3  输出 PASS / NEEDS_CHANGES / ADVISORY
   │    给出按严重程度排序的发现与修正建议
   ▼
Step 4  人工确认后交给所在仓库的提交工作流
         本 skill 不执行 commit、amend、push 或绕过 hook
```

## 产出物数据流

```
输入：粘贴的 commit message 或明确的 Git commit 引用
  │
  ▼
本 skill：随附规则参考审查（只读）
  │
  ▼
产出：审查结论、问题清单、建议的完整 message、未验证范围
  │
  ▼
下游消费者：人工确认或所在仓库的提交工作流
```

## 依赖关系图

```
用户会话 ──提供 message / commit 引用──▶ commit-message-review
                                               │
                                               ├──读取──▶ references/commit-message-rules.md
                                               └──可选只读──▶ Git repository（commit / staged diff）

commit-message-review ──审查结果──▶ 人工或仓库既有提交工作流
```
