"""
遥感智能体 Hook HTTP 服务

独立的 FastAPI 服务，接收 PilotDeck 的 HTTP 类型 Hook 回调。
MCP Server 使用 stdio 协议，Hook 使用 HTTP 协议，两者独立运行。

启动方式:
    python -m rs_engine.hook_server

端口由环境变量 RS_HOOK_PORT 控制 (默认: 8000)
"""

import asyncio
import logging
import os
import sys

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from rs_engine.hooks.route_task import handle_route_task
from rs_engine.hooks.pre_tool_use import handle_pre_tool_use
from rs_engine.hooks.tool_error import handle_tool_error

logger = logging.getLogger("rs-engine.hook-server")

app = FastAPI(title="rs-agent Hook Server", version="0.3.0")

HOOK_PORT = int(os.environ.get("RS_HOOK_PORT", "8000"))


# ---------------------------------------------------------------------------
# Hook 端点
# ---------------------------------------------------------------------------


@app.post("/hooks/route-task")
async def route_task(request: Request):
    """UserPromptSubmit Hook 端点"""
    hook_input = await request.json()
    logger.info("route-task: sessionId=%s", hook_input.get("sessionId", "unknown"))
    result = await handle_route_task(hook_input)
    return JSONResponse(content=result)


@app.post("/hooks/pre-tool-use")
async def pre_tool_use(request: Request):
    """PreToolUse Hook 端点"""
    hook_input = await request.json()
    logger.info(
        "pre-tool-use: tool=%s, sessionId=%s",
        hook_input.get("toolName", "unknown"),
        hook_input.get("sessionId", "unknown"),
    )
    result = await handle_pre_tool_use(hook_input)
    return JSONResponse(content=result)


@app.post("/hooks/tool-error")
async def tool_error(request: Request):
    """PostToolUseFailure Hook 端点"""
    hook_input = await request.json()
    logger.error(
        "tool-error: tool=%s, error=%s",
        hook_input.get("toolName", "unknown"),
        str(hook_input.get("error", ""))[:200],
    )
    result = await handle_tool_error(hook_input)
    return JSONResponse(content=result)


# ---------------------------------------------------------------------------
# 健康检查
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    """健康检查端点"""
    return {"status": "ok", "version": "0.3.0"}


# ---------------------------------------------------------------------------
# 资源状态端点
# ---------------------------------------------------------------------------


@app.get("/api/resource-status")
async def resource_status():
    """获取资源状态概览"""
    from rs_engine.resource.quota import QuotaChecker
    from rs_engine.resource.gpu_scheduler import GpuScheduler
    from rs_engine.resource.disk import DiskManager

    workspace = os.environ.get("RS_WORKSPACE", os.path.join(os.path.dirname(__file__), '..', '..', 'data'))

    quota = QuotaChecker(workspace)
    disk = DiskManager(workspace)
    gpu = GpuScheduler()

    return {
        "quota": quota.get_status(),
        "disk": disk.get_usage(),
        "gpu": gpu.get_status(),
    }


@app.get("/api/knowledge-stats")
async def knowledge_stats():
    """获取知识库统计"""
    from rs_engine.knowledge.rag import KNOWLEDGE_DOCS

    categories = {}
    for doc in KNOWLEDGE_DOCS:
        cat = doc.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    return {"total_docs": len(KNOWLEDGE_DOCS), "categories": categories}


# ---------------------------------------------------------------------------
# 模板管理 API
# ---------------------------------------------------------------------------

_template_manager = None


def _get_template_manager():
    """获取模板管理器（懒加载）"""
    global _template_manager
    if _template_manager is None:
        from rs_engine.template.manager import TemplateManager
        workspace = os.environ.get("RS_WORKSPACE", os.path.join(os.path.dirname(__file__), '..', '..', 'data'))
        template_dir = os.path.join(workspace, "templates")
        _template_manager = TemplateManager(template_dir)
    return _template_manager


@app.get("/api/templates")
async def list_templates(category: str | None = None):
    """列出所有模板"""
    mgr = _get_template_manager()
    return {"templates": mgr.list_templates(category)}


@app.get("/api/templates/{template_id}")
async def get_template(template_id: str):
    """获取单个模板"""
    mgr = _get_template_manager()
    tpl = mgr.get_template(template_id)
    if tpl is None:
        return {"error": f"模板 {template_id} 不存在"}
    return tpl


@app.post("/api/templates")
async def create_template(request: Request):
    """创建模板"""
    mgr = _get_template_manager()
    template = await request.json()
    try:
        result = mgr.create_template(template)
        return result
    except ValueError as e:
        return {"error": str(e)}


@app.put("/api/templates/{template_id}")
async def update_template(template_id: str, request: Request):
    """更新模板"""
    mgr = _get_template_manager()
    updates = await request.json()
    result = mgr.update_template(template_id, updates)
    if result is None:
        return {"error": f"模板 {template_id} 不存在"}
    return result


@app.delete("/api/templates/{template_id}")
async def delete_template(template_id: str):
    """删除模板"""
    mgr = _get_template_manager()
    deleted = mgr.delete_template(template_id)
    return {"deleted": deleted}


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------


async def serve() -> None:
    """启动 Hook HTTP 服务"""
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )

    logger.info("rs-agent Hook Server 启动, port=%d", HOOK_PORT)
    config = uvicorn.Config(app, host="0.0.0.0", port=HOOK_PORT, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(serve())
