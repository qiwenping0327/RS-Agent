from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .mcp_bridge import McpBridgeClient, BridgeResult

logger = logging.getLogger("oea.registry")


class ExecutionMode(str, Enum):
    MCP = "mcp"
    SANDBOX = "sandbox"
    MIXED = "mixed"


@dataclass
class ToolMetadata:
    tool_id: str
    name: str
    description: str
    server_id: str
    execution_mode: ExecutionMode
    capabilities: list[str] = field(default_factory=list)
    sensors: list[str] = field(default_factory=list)
    input_schema: dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    fallback_tool: Optional[str] = None


class UnifiedToolRegistry:
    """
    统一工具注册表

    职责:
    1. 全局工具索引（MCP + 沙箱代码）
    2. 工具匹配（任务意图 → 最佳工具）
    3. MCP 桥接调用（通过 McpBridgeClient）
    4. 沙箱代码执行
    5. 回退机制
    """

    def __init__(self, config: dict):
        self.config = config
        self._tools: dict[str, ToolMetadata] = {}
        self._capability_index: dict[str, list[str]] = {}
        self._sensor_index: dict[str, list[str]] = {}
        self._initialized = False

        bridge_url = config.get("bridge_url", "http://localhost:3000/api/oea-bridge")
        self._mcp_bridge = McpBridgeClient(
            bridge_url=bridge_url,
            timeout=config.get("bridge_timeout", 60.0),
            max_retries=config.get("bridge_max_retries", 3),
            use_mock=config.get("use_mock_bridge", True),
        )

        self._sandbox_executor = None

    async def initialize(self) -> None:
        if self._initialized:
            return

        logger.info("Initializing UnifiedToolRegistry...")

        tools_list = await self._mcp_bridge.list_tools()

        for tool_info in tools_list:
            tool_id = tool_info.get("tool_id")
            if not tool_id:
                continue

            metadata = ToolMetadata(
                tool_id=tool_id,
                name=tool_info.get("tool_name", tool_id),
                description=f"Tool from {tool_info.get('server_id', 'unknown')}",
                server_id=tool_info.get("server_id", "unknown"),
                execution_mode=ExecutionMode.MCP,
                capabilities=self._infer_capabilities(tool_info),
                sensors=self._infer_sensors(tool_info),
            )

            self.register_tool(metadata)

        self._initialized = True
        logger.info(f"Initialized with {len(self._tools)} tools")

    def register_tool(self, metadata: ToolMetadata) -> None:
        self._tools[metadata.tool_id] = metadata

        for capability in metadata.capabilities:
            if capability not in self._capability_index:
                self._capability_index[capability] = []
            self._capability_index[capability].append(metadata.tool_id)

        for sensor in metadata.sensors:
            if sensor not in self._sensor_index:
                self._sensor_index[sensor] = []
            self._sensor_index[sensor].append(metadata.tool_id)

    def _infer_capabilities(self, tool_info: dict) -> list[str]:
        tool_id = tool_info.get("tool_id", "").lower()
        tool_name = tool_info.get("tool_name", "").lower()
        combined = f"{tool_id} {tool_name}"

        capabilities = []
        if "download" in combined:
            capabilities.extend(["data_download", "data_acquisition"])
        if "preprocess" in combined:
            capabilities.extend(["preprocessing", "radiometric_correction", "atmospheric_correction"])
        if "analyze" in combined or "analysis" in combined:
            capabilities.extend(["analysis", "spectral_index"])
        if "ndvi" in combined:
            capabilities.extend(["ndvi", "vegetation_index"])
        if "ndwi" in combined:
            capabilities.extend(["ndwi", "water_index"])
        if "classify" in combined:
            capabilities.extend(["classification", "image_classification"])
        if "segment" in combined:
            capabilities.extend(["segmentation", "object_detection"])
        if "visualize" in combined:
            capabilities.extend(["visualization", "rendering"])

        if not capabilities:
            capabilities.append("general_geospatial")

        return capabilities

    def _infer_sensors(self, tool_info: dict) -> list[str]:
        tool_id = tool_info.get("tool_id", "").lower()
        sensors = []
        if "sentinel" in tool_id:
            sensors.extend(["Sentinel-1", "Sentinel-2"])
        if "landsat" in tool_id:
            sensors.extend(["Landsat-8", "Landsat-9"])
        if "gf" in tool_id:
            sensors.extend(["GF-1", "GF-2", "GF-5"])
        return sensors

    def match_tool(
        self,
        task_intent: str,
        sensor: Optional[str] = None,
        data_type: Optional[str] = None,
    ) -> Optional[ToolMetadata]:
        intent_lower = task_intent.lower()

        keywords_in_intent = []
        if "下载" in intent_lower or "download" in intent_lower:
            keywords_in_intent.extend(["download", "数据下载"])
        if "预处理" in intent_lower or "preprocess" in intent_lower:
            keywords_in_intent.extend(["preprocess", "预处理"])
        if "分析" in intent_lower or "分析" in task_intent:
            keywords_in_intent.extend(["analyze", "分析"])
        if "ndvi" in intent_lower:
            keywords_in_intent.extend(["ndvi", "植被指数"])

        all_tools = list(self._tools.values())

        for tool in all_tools:
            tool_text = f"{tool.tool_id} {tool.name} {tool.description}".lower()
            for kw in keywords_in_intent:
                if kw.lower() in tool_text:
                    return tool

        for tool in all_tools:
            if self._intent_matches(tool, intent_lower):
                return tool

        if all_tools:
            return all_tools[0]

        return None

    def _intent_matches(self, tool: ToolMetadata, intent_lower: str) -> bool:
        for capability in tool.capabilities:
            if capability.lower() in intent_lower:
                return True
        if tool.name.lower() in intent_lower:
            return True
        if tool.tool_id.lower() in intent_lower:
            return True
        return False

    def list_tools(self) -> list[ToolMetadata]:
        return list(self._tools.values())

    def get_tool(self, tool_id: str) -> Optional[ToolMetadata]:
        return self._tools.get(tool_id)

    async def execute_tool(
        self,
        tool_id: str,
        args: dict[str, Any],
        mode: ExecutionMode = ExecutionMode.MCP,
        workspace_id: str = "default",
    ) -> BridgeResult:
        logger.info(f"Executing tool: {tool_id} in mode: {mode.value}")

        if mode == ExecutionMode.MCP:
            return await self._execute_mcp(tool_id, args, workspace_id)
        else:
            return await self._execute_sandbox(tool_id, args, workspace_id)

    async def _execute_mcp(
        self,
        tool_id: str,
        args: dict[str, Any],
        workspace_id: str,
    ) -> BridgeResult:
        logger.info(f"Executing MCP tool via bridge: {tool_id}")

        result = await self._mcp_bridge.execute_tool(
            tool_id=tool_id,
            args=args,
            workspace_id=workspace_id,
            timeout_ms=self.config.get("mcp_timeout_ms", 120000),
        )

        if not result.success:
            logger.warning(f"MCP tool failed: {tool_id}, trying fallback")
            fallback = await self._try_fallback(tool_id, args, workspace_id)
            if fallback:
                return fallback

        return result

    async def _execute_sandbox(
        self,
        tool_id: str,
        args: dict[str, Any],
        workspace_id: str,
    ) -> BridgeResult:
        if self._sandbox_executor is None:
            try:
                from ..executor.sandbox_executor import SandboxExecutor
                self._sandbox_executor = SandboxExecutor(self.config)
            except Exception as e:
                logger.error(f"Failed to create sandbox executor: {e}")
                return BridgeResult(
                    success=False,
                    error=f"Sandbox not available: {e}",
                    error_code="SANDBOX_UNAVAILABLE",
                )

        code = args.get("code", "")
        params = args.get("params", {})

        if not code:
            return BridgeResult(
                success=False,
                error="No code provided for sandbox execution",
                error_code="NO_CODE_PROVIDED",
            )

        try:
            result = await self._sandbox_executor.execute(
                code=code,
                params=params,
                workspace_id=workspace_id,
            )
            return BridgeResult(
                success=result.get("success", False),
                result=result.get("output_files", []),
                error=result.get("error"),
            )
        except Exception as e:
            logger.exception(f"Sandbox execution failed: {e}")
            return BridgeResult(
                success=False,
                error=str(e),
                error_code="SANDBOX_EXECUTION_ERROR",
            )

    async def _try_fallback(
        self,
        tool_id: str,
        args: dict[str, Any],
        workspace_id: str,
    ) -> Optional[BridgeResult]:
        tool = self._tools.get(tool_id)
        if not tool or not tool.fallback_tool:
            return None

        fallback_tool = self._tools.get(tool.fallback_tool)
        if not fallback_tool:
            return None

        logger.info(f"Trying fallback: {tool.fallback_tool}")

        if fallback_tool.execution_mode == ExecutionMode.SANDBOX:
            return await self._execute_sandbox(
                fallback_tool.tool_id,
                args,
                workspace_id,
            )
        else:
            return await self._execute_mcp(
                fallback_tool.tool_id,
                args,
                workspace_id,
            )

    async def get_health_status(self) -> dict:
        return await self._mcp_bridge.get_health()

    async def close(self) -> None:
        await self._mcp_bridge.close()
