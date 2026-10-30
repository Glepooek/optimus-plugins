# Optimus Frontend 内置 MCP 服务

`optimus-frontend` 插件自带两个 MCP（Model Context Protocol）服务器，安装插件后由 Claude Code 自动加载。MCP 配置**仅面向 Claude Code**，不提供 Codex 版本。

## 包含的 MCP 服务器

### 1. Avalonia Docs MCP
- **类型**: HTTP
- **功能**: 提供 Avalonia UI 官方文档查询
- **环境变量**: 无需认证

### 2. MasterGo Magic MCP
- **类型**: stdio
- **功能**: MasterGo 设计协作工具集成
- **环境变量**: `MASTERGO_TOKEN`

## 使用方式

0. 前置要求

在全局配置文件 `~/.claude/settings.json` 中设置环境变量：

```json
{
  "env": {
    "MASTERGO_TOKEN": "your_mastergo_token_here"
  }
}
```

1. **安装插件**
   ```bash
   # 通过 marketplace 安装
   claude plugins install optimus-frontend@optimus-plugins
   ```

2. **启用插件**
   - 插件安装后会提示是否启用 MCP 服务器
   - 批准后即可在 Claude Code 中使用

3. **手动启用（可选）**
   如果需要手动管理，在项目 `.claude/settings.json` 中添加：
   ```json
   {
     "enabledMcpjsonServers": ["avalonia-docs", "mastergo-magic-mcp"]
   }
   ```

## Token 获取

### MasterGo Token
1. 登录 MasterGo (https://mastergo.com)
2. 进入用户设置 → 开发者设置
3. 创建 API Token

> 将生成的 token 导出为环境变量 `MASTERGO_TOKEN`。`.mcp.json` 会把它转交给 MasterGo MCP 子进程所读取的 `MG_MCP_TOKEN`，用户无需自行设置后者。

## 从旧 MCP 插件迁移

原先单独提供这些 MCP 的插件已删除，其中的 MCP 并入本插件：

1. **先卸载旧的 MCP 插件**（用 `claude plugins list` 查看已安装项），否则两个插件会各注册一份同名 MCP。
2. 安装本插件（见上文「使用方式」）。
3. 环境变量 `MG_MCP_TOKEN` 不再被读取，请改设 `MASTERGO_TOKEN`。
4. 飞书项目 MCP 不再由本仓提供；依赖它的 `optimus-qa` skill 需自行安装飞书项目 CLI 并完成授权。
5. 若你在 `permissions.allow` 或 `enabledMcpjsonServers` 中手写过旧插件提供的 MCP 条目，需按新的插件来源更新：服务器名形如 `plugin:optimus-frontend:mastergo-magic-mcp`（`claude mcp list` 实测）。
