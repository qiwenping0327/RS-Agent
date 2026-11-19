"""
遥感智能分析 Agent - MCP Server 入口 (FastMCP 版)

通过 MCP 协议注册遥感工具，由 dsh / RS-Harness 以 stdio 方式启动。
工具注册后名称格式: mcp__rs_agent__<tool_name>

使用方式:
    python -m rs_engine.mcp_server

环境变量:
    RS_ENGINE_HOME    - rs-engine 项目根目录 (默认: /opt/rs-engine)
    RS_WORKSPACE     - 工作空间目录 (默认: <project>/data)
    RS_HOOK_PORT     - Hook HTTP 服务端口 (默认: 8000)
"""

import logging
import os
import sys
from typing import Any

from fastmcp import FastMCP
from fastmcp.tools.base import Tool

from rs_engine.tools import (
    RS_DOWNLOAD_TOOL, RS_PREPROCESS_TOOL, RS_ANALYZE_TOOL,
    RS_VISUALIZE_TOOL, RS_REPORT_TOOL,
    RS_SAR_ANALYSIS_TOOL, RS_MODEL_INFERENCE_TOOL,
)
from rs_engine.tools.rs_download import rs_download_tool
from rs_engine.tools.rs_preprocess import rs_preprocess_tool
from rs_engine.tools.rs_analyze import rs_analyze_tool
from rs_engine.tools.rs_visualize import rs_visualize_tool
from rs_engine.tools.rs_report import rs_report_tool
from rs_engine.tools.rs_sar_analysis import rs_sar_analysis_tool
from rs_engine.tools.rs_model_inference import rs_model_inference_tool

logger = logging.getLogger("rs-engine")


# ---------------------------------------------------------------------------
# SchemaBoundTool: 保留旧版 mcp.types.Tool 的 inputSchema，统一委托 execute(arguments) -> str
# ---------------------------------------------------------------------------

class SchemaBoundTool(Tool):
    """把现成 name/description/inputSchema + execute(arguments) 绑定为 FastMCP 工具。

    传 Tool 实例给 mcp.add_tool 时，fastmcp 跳过 from_function 的签名→schema 自动生成，
    parameters 字段原样成为 inputSchema；run() 覆盖基类（基类抛 NotImplementedError），
    统一调 execute(arguments) 并把 str 收尾为 ToolResult。
    """

    fn: object = None

    async def run(self, arguments: dict[str, Any]):
        result = await self.fn(arguments)
        return self.convert_result(result)


# ---------------------------------------------------------------------------
# 工具注册: schema(RS_*_TOOL) + 实现(*_tool 实例) 配对
# ---------------------------------------------------------------------------

TOOL_REGISTRY = [
    (RS_DOWNLOAD_TOOL, rs_download_tool),
    (RS_PREPROCESS_TOOL, rs_preprocess_tool),
    (RS_ANALYZE_TOOL, rs_analyze_tool),
    (RS_VISUALIZE_TOOL, rs_visualize_tool),
    (RS_REPORT_TOOL, rs_report_tool),
    (RS_SAR_ANALYSIS_TOOL, rs_sar_analysis_tool),
    (RS_MODEL_INFERENCE_TOOL, rs_model_inference_tool),
]

mcp = FastMCP("rs-agent")

for _schema, _impl in TOOL_REGISTRY:
    mcp.add_tool(
        SchemaBoundTool(
            name=_schema.name,
            description=_schema.description,
            parameters=_schema.input_schema,
            fn=_impl.execute,
        )
    )


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main() -> None:
    """启动 MCP Server (stdio 模式)"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )

    logger.info("rs-agent MCP Server (FastMCP) 启动, version=%s", "0.3.1")
    logger.info("RS_ENGINE_HOME=%s", os.environ.get("RS_ENGINE_HOME", "/opt/rs-engine"))
    logger.info("RS_WORKSPACE=%s", os.environ.get("RS_WORKSPACE", os.path.join(os.path.dirname(__file__), '..', '..', 'data')))

    mcp.run()


if __name__ == "__main__":
    main()
