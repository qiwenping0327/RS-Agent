from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger("oea.mcp_bridge")


@dataclass
class BridgeResult:
    success: bool
    result: Any = None
    error: Optional[str] = None
    error_code: Optional[str] = None


class McpBridgeClient:
    """
    MCP 桥接客户端 - Python 端调用 PilotDeck TypeScript 层

    通过 HTTP API 与 OpenEarthToolBridge 通信
    设计为可插拔，支持 mock 测试模式
    """

    def __init__(
        self,
        bridge_url: str = "http://localhost:3000/api/oea-bridge",
        timeout: float = 120.0,
        max_retries: int = 3,
        use_mock: bool = False,
    ):
        self.bridge_url = bridge_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.use_mock = use_mock
        self._http_client = None
        self._mock_tools: dict[str, MockToolHandler] = {}

    def register_mock_tool(self, tool_id: str, handler: MockToolHandler) -> None:
        self._mock_tools[tool_id] = handler

    async def _get_http_client(self):
        if self._http_client is None:
            try:
                import httpx
                self._http_client = httpx.AsyncClient(timeout=self.timeout)
            except ImportError:
                logger.warning("httpx not available, using mock mode")
                self.use_mock = True
        return self._http_client

    async def execute_tool(
        self,
        tool_id: str,
        args: dict[str, Any],
        workspace_id: Optional[str] = None,
        timeout_ms: Optional[int] = None,
    ) -> BridgeResult:
        logger.info(f"Executing MCP tool via bridge: {tool_id}")

        if self.use_mock or tool_id in self._mock_tools:
            return await self._execute_mock(tool_id, args, workspace_id)

        return await self._execute_http(tool_id, args, workspace_id, timeout_ms)

    async def _execute_http(
        self,
        tool_id: str,
        args: dict[str, Any],
        workspace_id: Optional[str],
        timeout_ms: Optional[int],
    ) -> BridgeResult:
        client = await self._get_http_client()
        if not client:
            return BridgeResult(
                success=False,
                error="HTTP client not available",
                error_code="HTTP_CLIENT_ERROR",
            )

        payload = {
            "tool_id": tool_id,
            "args": args,
            "workspace_id": workspace_id,
            "timeout_ms": timeout_ms,
        }

        for attempt in range(self.max_retries):
            try:
                response = await client.post(
                    f"{self.bridge_url}/execute",
                    json=payload,
                )
                data = response.json()

                if data.get("success"):
                    return BridgeResult(
                        success=True,
                        result=data.get("result"),
                    )

                if data.get("error_code") in [
                    "SERVER_NOT_CONNECTED",
                    "mcp_session_expired",
                    "mcp_handshake_failed",
                ]:
                    if attempt < self.max_retries - 1:
                        wait = 1.0 * (2 ** attempt)
                        logger.warning(
                            f"Retry {attempt + 1}/{self.max_retries} "
                            f"for {tool_id}: {data.get('error')}"
                        )
                        await self._async_sleep(wait)
                        continue

                return BridgeResult(
                    success=False,
                    error=data.get("error"),
                    error_code=data.get("error_code"),
                )

            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait = 1.0 * (2 ** attempt)
                    logger.warning(
                        f"Bridge connection error (attempt {attempt + 1}): {e}"
                    )
                    await self._async_sleep(wait)
                    continue

                return BridgeResult(
                    success=False,
                    error=str(e),
                    error_code="BRIDGE_CONNECTION_ERROR",
                )

        return BridgeResult(
            success=False,
            error="Max retries exceeded",
            error_code="MAX_RETRIES_EXCEEDED",
        )

    async def _execute_mock(
        self,
        tool_id: str,
        args: dict[str, Any],
        workspace_id: Optional[str],
    ) -> BridgeResult:
        logger.debug(f"Mock execution: {tool_id}")

        if tool_id in self._mock_tools:
            return await self._mock_tools[tool_id].execute(args, workspace_id)

        return BridgeResult(
            success=True,
            result={
                "mock": True,
                "tool_id": tool_id,
                "args": args,
                "workspace_id": workspace_id,
                "output_files": [f"/mock/output/{tool_id}_result.tif"],
            },
        )

    async def list_tools(self) -> list[dict]:
        if self.use_mock:
            return [
                {"tool_id": "rs-agent.rs_download", "server_id": "rs-agent", "tool_name": "rs_download"},
                {"tool_id": "rs-agent.rs_preprocess", "server_id": "rs-agent", "tool_name": "rs_preprocess"},
                {"tool_id": "rs-agent.rs_analyze", "server_id": "rs-agent", "tool_name": "rs_analyze"},
                {"tool_id": "rs-index.ndvi_calc", "server_id": "rs-index", "tool_name": "ndvi_calc"},
            ]

        client = await self._get_http_client()
        if not client:
            return []

        try:
            response = await client.get(f"{self.bridge_url}/tools")
            data = response.json()
            return data.get("tools", [])
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return []

    async def get_health(self) -> dict:
        if self.use_mock:
            return {
                "rs-agent": {"status": "ready", "failures": 0},
                "rs-index": {"status": "ready", "failures": 0},
            }

        client = await self._get_http_client()
        if not client:
            return {}

        try:
            response = await client.get(f"{self.bridge_url}/health")
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get health: {e}")
            return {}

    async def _async_sleep(self, seconds: float) -> None:
        await self._asyncio_sleep(seconds)

    async def _asyncio_sleep(self, seconds: float) -> None:
        import asyncio
        await asyncio.sleep(seconds)

    async def close(self) -> None:
        if self._http_client:
            try:
                await self._http_client.aclose()
            except Exception:
                pass
            self._http_client = None


class MockToolHandler:
    async def execute(self, args: dict[str, Any], workspace_id: Optional[str]) -> BridgeResult:
        return BridgeResult(success=True, result={"handled": True})
