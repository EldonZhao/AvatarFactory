# MCP Servers 配置指南

## 什么是 MCP Servers?

MCP (Model Context Protocol) Servers 允许 Claude Code 访问额外的工具和服务，比如：
- 文件系统操作
- GitHub API
- 数据库连接
- 网络搜索
- 自定义工具

## 配置格式

在 `.claude/settings.json` 中，`allowedMcpServers` 是一个数组，每个元素定义一个允许的 MCP 服务器：

```json
{
  "allowedMcpServers": [
    {
      "serverName": "服务器名称（必需）",
      "serverCommand": ["命令", "参数1", "参数2"],
      "serverUrl": "远程服务器URL（可选）"
    }
  ]
}
```

**注意**:
- `serverName`: 必需，只能包含字母、数字、下划线和连字符
- `serverCommand`: stdio 类型服务器使用，指定启动命令和参数
- `serverUrl`: 远程 MCP 服务器使用，支持通配符（如 `https://*.example.com/*`）

## 常用 MCP Servers 配置示例

### 1. Filesystem Server (文件系统访问)

允许 Claude 读写指定目录：

```json
{
  "serverName": "filesystem",
  "serverCommand": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "C:\\Users\\xueyongzhao\\Projects"]
}
```

**Windows 路径示例**:
```json
{
  "serverName": "filesystem-docs",
  "serverCommand": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "C:\\Users\\xueyongzhao\\Documents"]
}
```

**多个路径**（需要多个服务器实例）:
```json
{
  "allowedMcpServers": [
    {
      "serverName": "filesystem-projects",
      "serverCommand": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "C:\\Projects"]
    },
    {
      "serverName": "filesystem-docs",
      "serverCommand": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "C:\\Documents"]
    }
  ]
}
```

### 2. GitHub Server (GitHub API)

访问 GitHub 仓库、Issues、PRs：

```json
{
  "serverName": "github",
  "serverCommand": ["npx", "-y", "@modelcontextprotocol/server-github"]
}
```

**注意**: 需要设置环境变量 `GITHUB_PERSONAL_ACCESS_TOKEN` 在你的 `.env` 文件中。

### 3. Brave Search (网络搜索)

使用 Brave Search API 进行搜索：

```json
{
  "serverName": "brave-search",
  "serverCommand": ["npx", "-y", "@modelcontextprotocol/server-brave-search"]
}
```

**注意**: 需要 Brave API Key，在 `.env` 中设置 `BRAVE_API_KEY`。

### 4. PostgreSQL Server (数据库)

连接 PostgreSQL 数据库：

```json
{
  "serverName": "postgres",
  "serverCommand": ["npx", "-y", "@modelcontextprotocol/server-postgres", "postgresql://user:password@localhost/dbname"]
}
```

### 5. SQLite Server (轻量数据库)

访问 SQLite 数据库：

```json
{
  "serverName": "sqlite",
  "serverCommand": ["npx", "-y", "@modelcontextprotocol/server-sqlite", "C:\\path\\to\\database.db"]
}
```

### 6. Puppeteer Server (浏览器自动化)

使用 Puppeteer 进行网页操作：

```json
{
  "serverName": "puppeteer",
  "serverCommand": ["npx", "-y", "@modelcontextprotocol/server-puppeteer"]
}
```

### 7. 远程 MCP 服务器

使用 URL 模式配置远程服务器：

```json
{
  "serverName": "remote-api",
  "serverUrl": "https://mcp.example.com/api/*"
}
```

**使用通配符**:
```json
{
  "serverName": "company-mcps",
  "serverUrl": "https://*.mycompany.com/*"
}
```

## 完整配置示例

这是一个包含多个 MCP 服务器的完整 `settings.json` 示例：

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://localhost:23333/api/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "Powered by Agent Maestro",
    "ANTHROPIC_MODEL": "claude-opus-4-5",
    "ANTHROPIC_SMALL_FAST_MODEL": "claude-haiku-4-5",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
  },
  "allowedMcpServers": [
    {
      "serverName": "filesystem-project",
      "serverCommand": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "C:\\Users\\xueyongzhao\\AvatarFactory"]
    },
    {
      "serverName": "github",
      "serverCommand": ["npx", "-y", "@modelcontextprotocol/server-github"]
    }
  ]
}
```

## 如何启用 MCP Server

### 方法 1: 使用 Claude Code CLI

1. 启动 Claude Code 项目
2. MCP 服务器会自动启动（如果配置正确）
3. 你可以在对话中直接使用这些工具

### 方法 2: 验证配置

```bash
# 检查配置是否正确
cat .claude/settings.json

# 测试 npx 命令是否可用
npx -y @modelcontextprotocol/server-filesystem --help
```

## 环境变量配置

某些 MCP 服务器需要 API Keys，在项目根目录的 `.env` 文件中设置：

```bash
# GitHub
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token_here

# Brave Search
BRAVE_API_KEY=your_brave_api_key

# OpenAI (某些 MCP 服务器需要)
OPENAI_API_KEY=sk-your_openai_key
```

## 安全注意事项

### 1. Filesystem Server
- 只授予必要的目录访问权限
- 避免授予整个 C:\ 或用户主目录的访问权限
- 使用具体的项目目录

### 2. Database Servers
- 不要在配置文件中硬编码数据库密码
- 使用环境变量存储敏感信息
- 考虑使用只读用户权限

### 3. API Servers
- 定期轮换 API tokens
- 使用具有最小权限的 tokens
- 不要提交包含 tokens 的配置文件到 git

## 禁用 MCP Server

如果要禁用某个 MCP Server，从 `allowedMcpServers` 数组中删除对应的配置即可。

要完全禁用所有 MCP Servers：

```json
{
  "allowedMcpServers": []
}
```

## 常见问题

### Q: 为什么我的 MCP Server 没有启动？

**A**: 检查以下几点：
1. 确保 Node.js 和 npx 已安装
2. 检查配置文件语法是否正确（JSON 格式）
3. 查看 Claude Code 输出的错误信息
4. 验证环境变量是否正确设置

### Q: 可以使用自定义的 MCP Server 吗？

**A**: 可以！只需提供正确的启动命令：

```json
{
  "serverName": "my-custom-server",
  "serverCommand": ["node", "C:\\path\\to\\my-server.js"]
}
```

### Q: serverCommand 和 serverUrl 的区别？

**A**:
- `serverCommand`: 本地 stdio 类型的 MCP 服务器，通过命令行启动
- `serverUrl`: 远程 HTTP/HTTPS MCP 服务器，通过网络连接

## 更多资源

- [MCP 官方文档](https://modelcontextprotocol.io)
- [MCP Servers 列表](https://github.com/modelcontextprotocol/servers)
- [Claude Code 文档](https://docs.anthropic.com/claude/docs/claude-code)

## 推荐配置（AvatarFactory 项目）

对于你的 AvatarFactory 项目，推荐以下配置：

```json
{
  "allowedMcpServers": [
    {
      "serverName": "filesystem-avatarfactory",
      "serverCommand": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "C:\\Users\\xueyongzhao\\AvatarFactory"]
    },
    {
      "serverName": "github",
      "serverCommand": ["npx", "-y", "@modelcontextprotocol/server-github"]
    }
  ]
}
```

这将允许：
- 访问 AvatarFactory 项目目录
- 使用 GitHub API（用于创建 Issues、PRs 等）
