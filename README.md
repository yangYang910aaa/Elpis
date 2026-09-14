# Mirage

一个能自己动手干活的个人 AI Agent。基于 LangChain + LangGraph，支持 OpenAI 兼容 API（可接硅基流动等第三方端点），内置文件操作、Shell 命令执行等工具。

> 海市蜃楼——虚幻却美丽，像 AI 生成的世界，远看是真实的绿洲，走近才发现是光的折射，但那一刻的震撼和向往是真的。

## 功能特性

- 💬 **自然语言对话** — 用中文/英文直接告诉它要做什么
- 🔧 **工具调用** — 自动调用工具完成任务，而不只是聊天
- 📁 **文件操作** — 读文件、写文件、浏览目录
- ⌨️ **Shell 执行** — 运行命令、安装依赖、执行脚本
- 🔄 **Agent 循环** — 思考→调工具→观察结果→继续行动，直到完成
- 🛡️ **安全机制** — 工作目录隔离、命令黑名单、输出截断
- 📊 **LangSmith 追踪** — 可选，可视化查看 Agent 的完整运行轨迹

## 快速开始

### 1. 配置 API Key

复制 `.env.example` 为 `.env`，填入你的 OpenAI 兼容 API Key：

```bash
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY
```

支持 OpenAI 官方 API，也支持硅基流动（SiliconFlow）等 OpenAI 兼容第三方服务，只需配置对应的 `OPENAI_BASE_URL`。

### 2. 创建虚拟环境并安装依赖

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate
pip install -e .

# macOS/Linux
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 3. 运行

```bash
# 方式一：全局命令（安装后可用，推荐）
mirage

# 方式二：直接运行启动脚本
python main.py

# 方式三：直接运行模块
python -m mirage.cli
```

## 项目结构

```
mirage/
├── .venv/                  # 虚拟环境（不提交 Git）
├── mirage/
│   ├── __init__.py
│   ├── config.py           # 配置管理（Pydantic v2）
│   ├── agent.py            # Agent 核心逻辑（LangChain create_agent）
│   ├── cli.py              # 命令行交互界面（Rich）
│   ├── tools/              # 工具模块（@tool 装饰器）
│   │   ├── __init__.py
│   │   ├── file_tools.py   # 文件操作工具
│   │   └── shell_tools.py  # Shell 执行工具
│   ├── prompts/            # 提示词管理（预留）
│   ├── memory/             # 记忆模块（预留）
│   ├── planning/           # 规划模块（预留）
│   ├── skills/             # 技能模块（预留）
│   ├── rag/                # RAG 检索增强（预留）
│   └── utils/              # 通用工具函数（预留）
├── tests/                  # 测试
├── .env                    # 环境变量（不提交 Git）
├── .env.example            # 环境变量模板
├── .gitignore
├── main.py                 # 启动入口
├── pyproject.toml          # 项目配置和依赖
└── README.md
```

## 已内置工具

| 工具名 | 功能 |
|--------|------|
| `read_file` | 读取文本文件内容 |
| `write_file` | 写入内容到文件（覆盖） |
| `list_directory` | 列出目录内容 |
| `run_shell_command` | 执行 Shell 命令 |

## 扩展新工具

在 `mirage/tools/` 下新建文件，用 `@tool` 装饰器定义函数，然后在 `tools/__init__.py` 的 `ALL_TOOLS` 列表中注册即可：

```python
# mirage/tools/my_tool.py
from langchain_core.tools import tool

@tool
def my_tool(param: str) -> str:
    """工具描述，会被 LLM 读取来决定是否调用。

    Args:
        param: 参数描述

    Returns:
        返回值描述
    """
    # 实现逻辑
    return "结果"
```

```python
# mirage/tools/__init__.py
from mirage.tools.my_tool import my_tool

ALL_TOOLS = [read_file, write_file, list_directory, run_shell_command, my_tool]
```

## 技术栈

- **LLM**: OpenAI 兼容 API（支持硅基流动等第三方端点）
- **Agent 编排**: LangChain `create_agent`（基于 LangGraph）
- **工具定义**: LangChain `@tool` 装饰器
- **终端 UI**: Rich
- **配置管理**: Pydantic v2 + pydantic-settings
- **Python**: >= 3.11

## LangSmith 追踪（可选）

在 `.env` 中配置 LangSmith 即可在 [smith.langchain.com](https://smith.langchain.com) 查看 Agent 的完整运行轨迹：

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_api_key
LANGCHAIN_PROJECT=mirage
```

## 安全说明

- Agent 只能在配置的工作目录内操作文件，无法通过 `../` 跳出
- Shell 命令有黑名单过滤
- 大文件和长输出会自动截断
- 建议在非重要目录下试用

## License

MIT
