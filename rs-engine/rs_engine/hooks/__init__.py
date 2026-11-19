"""
Hook 处理模块 - HTTP 端点处理器

提供三个 Hook 端点:
- /hooks/route-task       (UserPromptSubmit)
- /hooks/pre-tool-use     (PreToolUse)
- /hooks/tool-error       (PostToolUseFailure)

由 rs_engine.hook_server 独立启动的 FastAPI 服务调用。
"""

from rs_engine.hooks.route_task import handle_route_task
from rs_engine.hooks.pre_tool_use import handle_pre_tool_use
from rs_engine.hooks.tool_error import handle_tool_error

__all__ = ["handle_route_task", "handle_pre_tool_use", "handle_tool_error"]
