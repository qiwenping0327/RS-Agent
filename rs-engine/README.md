# 遥感智能分析 Agent (rs-engine)

遥感数据处理 MCP Server，为 RsAgent 提供遥感影像下载、预处理、智能分析、SAR 处理、模型推理等能力。

## 快速开始

### 1. 环境检查

```bash
python check_rs_env.py
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

> GDAL 需要系统级安装，建议使用 conda: `conda install gdal`

### 3. 启动 MCP Server

```bash
# 由 RsAgent 自动启动 (推荐)
# 在 plugin.json 中配置 mcpServers 即可

# 手动测试
python -m rs_engine.mcp_server
```

### 4. 启动 Hook HTTP 服务

```bash
python -m rs_engine.hook_server
```

## 项目结构

```
rs-engine/
├── rs_engine/
│   ├── __init__.py
│   ├── mcp_server.py          # MCP Server 入口 (stdio 协议)
│   ├── hook_server.py         # Hook HTTP 服务 (FastAPI)
│   ├── tools/                 # MCP 工具定义与实现
│   │   ├── __init__.py        # 工具 Schema 定义
│   │   ├── rs_download.py
│   │   ├── rs_preprocess.py
│   │   └── rs_analyze.py
│   ├── hooks/                 # Hook 处理器
│   │   ├── route_task.py      # UserPromptSubmit
│   │   ├── pre_tool_use.py    # PreToolUse
│   │   └── tool_error.py      # PostToolUseFailure
│   ├── fault/                 # 故障容错层
│   │   ├── breakpoint.py      # SQLite 断点存储
│   │   ├── retry.py           # 指数退避重试
│   │   └── degrade.py         # 降级策略
│   ├── resource/              # 资源管控层
│   │   ├── quota.py           # 配额检查
│   │   ├── gpu_scheduler.py  # GPU 调度
│   │   └── disk.py            # 磁盘管控
│   ├── knowledge/             # 遥感知识库
│   │   ├── spatial_geocode.py # 空间编码
│   │   └── band_mapping.py    # 波段映射
│   └── template/              # 任务模板
│       ├── manager.py         # 模板 CRUD
│       └── schema.py          # 模板 Schema
├── data/
│   └── templates/             # 模板文件存储
├── requirements.txt
├── check_rs_env.py
└── README.md
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `RS_ENGINE_HOME` | `/opt/rs-engine` | rs-engine 项目根目录 |
| `RS_WORKSPACE` | `/workspace` | 工作空间目录 |
| `RS_HOOK_PORT` | `8000` | Hook HTTP 服务端口 |

## 工具列表

| 工具名 | MCP 注册名 | 说明 |
|--------|-----------|------|
| rs_download | mcp__rs_agent__rs_download | 卫星影像下载 |
| rs_preprocess | mcp__rs_agent__rs_preprocess | 影像预处理 |
| rs_analyze | mcp__rs_agent__rs_analyze | 智能分析 |

> Phase 3 将新增: rs_sar_analysis, rs_model_inference, rs_visualize, rs_report, rs_eco_adapter

## 开发说明

- MCP Server 使用 `mcp` Python SDK，通过 stdio 协议与 RsAgent 通信
- Hook 服务使用 FastAPI，通过 HTTP 接收 RsAgent 回调
- 所有业务逻辑在 Python 侧实现，RsAgent 侧仅做声明式配置
- 断点存储使用 SQLite，位于 `{workspace}/.rs_breakpoints.db`
