# DeepWiki MCP Server

使用 **FastMCP** 框架实现的 MCP 服务，允许通过标准 MCP 协议与已解析的代码仓库进行交互问答。

## 技术栈

- **FastMCP** - 标准 MCP 协议框架，提供简洁的装饰器 API
- **Streamable HTTP** - MCP 2025-03-26 标准传输协议

## 工具列表

### 1. `deepwiki_list_projects`

列出已解析的所有仓库，支持名称模糊查询。

```python
@mcp.tool()
async def deepwiki_list_projects(query: Optional[str] = None) -> str:
    """列出已解析的所有仓库"""
```

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | 否 | 仓库名称模糊查询关键词 |

### 2. `deepwiki_ask`

针对已解析的仓库提问，获取代码相关问题的答案。

```python
@mcp.tool()
async def deepwiki_ask(
    repo: str,
    question: str,
    deep_research: bool = False,
    language: str = "en",
    file_path: Optional[str] = None
) -> str:
    """针对已解析的仓库提问"""
```

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| repo | string | 是 | 仓库名称，支持 `owner/repo` 或 `repo` 格式 |
| question | string | 是 | 要问的问题 |
| deep_research | boolean | 否 | 是否启用深度研究模式（默认 false） |
| language | string | 否 | 回答语言（默认 en） |
| file_path | string | 否 | 指定要分析的文件路径 |

---

## 运行模式

### 模式一：集成模式

MCP服务集成到主API服务中，共用端口（默认8001）。

```bash
cd api
python main.py
```

访问: `http://localhost:8001/mcp/`

### 模式二：独立 HTTP 模式（推荐）

MCP服务独占端口运行，与后端服务分离。

```bash
cd api
python mcp_server.py --http --port 8002
```

访问: `http://localhost:8002/mcp/`

**参数说明：**
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--http` | - | 启用HTTP模式 |
| `--port` | 8002 | 监听端口 |
| `--host` | 0.0.0.0 | 监听地址 |

### 模式三：stdio 模式

适用于 Cursor、Claude Desktop 等客户端：

```bash
cd api
python mcp_server.py
```

### Docker 部署

**集成模式（默认）：** MCP与后端共用8001端口

```bash
docker run -p 8001:8001 -p 3000:3000 deepwiki
```

**独立端口模式：** MCP独占8002端口

```bash
docker run -p 8001:8001 -p 3000:3000 -p 8002:8002 \
  -e MCP_ENABLED=true \
  -e MCP_PORT=8002 \
  deepwiki
```

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `MCP_ENABLED` | false | 是否启用独立MCP服务 |
| `MCP_PORT` | 8002 | MCP服务端口 |

---

## 安装依赖

```bash
cd api
pip install fastmcp
# 或
poetry install
```

---

## 客户端配置

### Cursor 配置（stdio模式）

`.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "deepwiki": {
      "command": "python",
      "args": ["D:/project/local/deepwiki-open/api/mcp_server.py"],
      "env": {
        "GOOGLE_API_KEY": "your-api-key"
      }
    }
  }
}
```

### Cursor 配置（HTTP模式）

```json
{
  "mcpServers": {
    "deepwiki": {
      "url": "http://localhost:8001/mcp",
      "transport": "http"
    }
  }
}
```

### Claude Desktop 配置

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "deepwiki": {
      "command": "python",
      "args": ["D:/project/local/deepwiki-open/api/mcp_server.py"],
      "env": {
        "GOOGLE_API_KEY": "your-api-key"
      }
    }
  }
}
```

---

## 为什么使用 FastMCP

| 特性 | 手动实现 | FastMCP |
|------|----------|---------|
| 协议封装 | 需要手动处理 JSON-RPC | 自动处理 |
| 工具定义 | 手动构建 schema | 装饰器自动生成 |
| 传输协议 | 需要自己实现 | 内置多种传输 |
| 类型安全 | 手动验证 | Pydantic 集成 |
| 维护成本 | 高 | 低 |

**FastMCP 代码示例：**

```python
from fastmcp import FastMCP

mcp = FastMCP(name="deepwiki-mcp")

@mcp.tool()
async def my_tool(param: str) -> str:
    """工具描述会自动提取为 MCP schema"""
    return f"Result: {param}"

# 运行
mcp.run()  # stdio 模式
mcp.run(transport="http", port=8002)  # HTTP 模式
```

---

## 环境变量

| 变量名 | 说明 |
|--------|------|
| `GOOGLE_API_KEY` | Google Gemini API Key（默认） |
| `OPENAI_API_KEY` | OpenAI API Key |
| `OPENROUTER_API_KEY` | OpenRouter API Key |
| `DASHSCOPE_API_KEY` | 阿里云 Dashscope API Key |

---

## 使用流程

1. **启动 DeepWiki 服务** - `python main.py`
2. **解析仓库** - 在 Web 界面输入仓库 URL
3. **通过 MCP 查询** - 使用客户端调用工具

---

## 注意事项

1. 必须先通过 Web 界面解析仓库才能查询
2. 深度研究模式会进行多轮 LLM 调用
3. Dockerfile 无需修改，MCP 随主服务启动
