# MCP 服务器安装指南

本超级 skill 仅依赖 1 个 MCP 服务器：`zotero`（Zotero 文献库）。**必须安装后才能启动工作流**，缺失会导致 literature-review 子 skill 无法正常工作（本 skill 禁止降级运行）。

## 必需 MCP 清单

| MCP server | 用途 | 必需性 | 影响的子 skill |
|------------|------|--------|---------------|
| `zotero` | Zotero 文献库（集合/标签/注释/BibTeX/语义搜索） | **必需** | literature-review |

> ℹ️ 其他 MCP（obsidian-vault / codex / claude-review / llm-chat / minimax-chat / illustrator）是旧版宿主环境的内部机制，本超级 skill 不依赖。子 skill 内对这些 MCP 的调用已作废，详见 SKILL.md 的"子 skill 内的其他 MCP 调用一律作废"段。

## 安装步骤

### 1. 安装前置依赖

```bash
# Node.js 18+（npx 依赖）
node --version  # 应 ≥ 18

# Zotero 本体（zotero MCP 依赖）
# 从 https://www.zotero.org/download 下载并安装
# 启动 Zotero 后启用本地 API：编辑 → 首选项 → 高级 → 通用 → 编辑器 → extensions.zotero.httpServer.enabled = true
```

### 2. 配置 MCP 服务器

将本 skill 根目录的 `.mcp.json` 合并到 agent 宿主的 MCP 配置中：

| 宿主 | 配置文件位置 | 合并方式 |
|------|------------|---------|
| Claude Desktop | `%APPDATA%\Claude\claude_desktop_config.json`（Windows） / `~/Library/Application Support/Claude/claude_desktop_config.json`（macOS） | 把 `.mcp.json` 的 `mcpServers` 对象合并进去 |
| Cursor | 项目根 `.cursor/mcp.json` 或全局 `~/.cursor/mcp.json` | 同上 |
| Codex CLI | `~/.codex/mcp.json` | 同上 |
| Trae | 项目根 `.trae/mcp.json` 或全局 `~/.trae/mcp.json` | 同上 |
| Claude Code | 项目根 `.mcp.json` 或 `~/.claude/mcp.json` | 同上 |

### 3. 填写环境变量

打开合并后的配置文件，填写 zotero 的 `env` 字段：

```json
"zotero": {
  "command": "npx",
  "args": ["-y", "zotero-mcp"],
  "env": {
    "ZOTERO_LOCAL_API_KEY": "你的Zotero本地API密钥",
    "ZOTERO_LIBRARY_TYPE": "user",
    "ZOTERO_LIBRARY_ID": "你的Zotero用户ID（登录 zotero.org → Settings → UserID）"
  }
}
```

### 4. 重启宿主并验证

1. 完全退出并重启 agent 宿主（Claude Desktop / Cursor / Codex CLI / Trae）
2. 在对话中让 agent 检测 MCP 可用性：
   ```
   请检测 zotero MCP 服务器是否可用
   ```
3. agent 应尝试调用 `mcp__zotero__search_items` 或任一 `mcp__zotero__*` 工具，并报告可用/不可用
4. 可用后，才能调 `mm_flow.py start` 启动工作流

## 常见问题

### Q: MCP server 启动失败怎么办？
A: 检查：
1. Node.js 版本 ≥ 18
2. `npx` 命令可用：`npx --version`
3. `zotero-mcp` 包存在：`npm view zotero-mcp`
4. 环境变量已填写且非空
5. Zotero 本体已启动并启用本地 API

### Q: Zotero 本地 API 怎么开？
A: 
- Zotero 6：编辑 → 首选项 → 高级 → 通用 → 编辑器 → 搜索 `httpServer.enabled` 设为 `true`，`httpServer.port` 默认 23119
- Zotero 7+：默认启用本地 API

### Q: 可以不装 zotero 直接跑吗？
A: **不可以**。本超级 skill 禁止降级运行。如果不装 zotero，literature-review 子 skill 会因缺 MCP 报错，工作流无法启动。

### Q: 如果我不跑文献检索类工作流（比如只跑 comp_cumcm 国赛），还需要 zotero 吗？
A: comp_cumcm 工作流的 sub_steps 是 comp-prob-analysis → comp-modeling → comp-code → paper-figure → comp-paper-zh → comp-compile，不含文献检索步骤，理论上不需要 zotero。但启动前检测协议仍会要求 zotero 就绪——如果你确定工作流不触发文献检索子 skill，可以临时跳过 MCP 检测，但风险自负。

### Q: 我可以用其他文献管理工具替代 zotero 吗？
A: 目前不支持。子 skill 的 SKILL.md 是针对 zotero MCP 写的，调用 `mcp__zotero__*` 工具。如果你用 EndNote / Mendeley / NoteExpress，需要自行编写对应 MCP server 并修改子 skill，不在本 skill 范围内。
