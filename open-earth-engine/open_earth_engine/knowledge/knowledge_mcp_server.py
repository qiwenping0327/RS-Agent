"""
知识库检索 - MCP Server 入口

通过 MCP 协议注册知识库检索工具，由 PilotDeck 以 stdio 方式启动。
工具注册后名称格式: mcp__knowledge-base__<tool_name>

使用方式:
    python -m open_earth_engine.knowledge.knowledge_mcp_server
"""

import asyncio
import json
import logging
import os
import sys

import aiohttp

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from open_earth_engine.knowledge.knowledge_db import KnowledgeDatabase, ENTRY_TYPES
from open_earth_engine.knowledge.vector_store import VectorStore

logger = logging.getLogger("oea.knowledge_mcp")

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

KNOWLEDGE_DB_PATH = "/root/PilotDeck/data/knowledge.db"

# ---------------------------------------------------------------------------
# 全局实例（延迟初始化）
# ---------------------------------------------------------------------------

_knowledge_db: KnowledgeDatabase | None = None
_vector_store: VectorStore | None = None


def _get_knowledge_db() -> KnowledgeDatabase:
    global _knowledge_db
    if _knowledge_db is None:
        _knowledge_db = KnowledgeDatabase(KNOWLEDGE_DB_PATH)
        logger.info("Knowledge database initialized: %s", KNOWLEDGE_DB_PATH)
    return _knowledge_db


def _get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore(vocab_size=5000)
        _rebuild_vector_index()
    return _vector_store


def _rebuild_vector_index() -> None:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore(vocab_size=5000)
    db = _get_knowledge_db()
    docs = db.get_all_for_indexing()
    _vector_store.build_index(docs)
    stats = _vector_store.get_stats()
    logger.info("Vector index built: %s", stats)

# ---------------------------------------------------------------------------
# MCP Server 实例
# ---------------------------------------------------------------------------

server = Server("knowledge-base")

# ---------------------------------------------------------------------------
# 工具定义
# ---------------------------------------------------------------------------

ALL_TOOLS = [
    Tool(
        name="knowledge_search",
        description="搜索知识库，支持混合检索（向量+关键词）、纯向量检索和纯关键词检索三种模式",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询文本",
                },
                "limit": {
                    "type": "number",
                    "description": "返回结果数量上限",
                    "default": 5,
                },
                "mode": {
                    "type": "string",
                    "enum": ["hybrid", "vector", "keyword"],
                    "description": "搜索模式：hybrid=混合检索（默认），vector=纯向量检索，keyword=纯关键词检索",
                    "default": "hybrid",
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="knowledge_list",
        description="列出知识库中的条目，可按类型过滤或按关键词搜索",
        inputSchema={
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "description": "按条目类型过滤（geoknowledge / tool_doc / tool_fallback / best_practice / workflow / faq / custom）",
                },
                "search": {
                    "type": "string",
                    "description": "按关键词搜索（匹配标题和内容）",
                },
                "limit": {
                    "type": "number",
                    "description": "返回结果数量上限",
                    "default": 10,
                },
            },
        },
    ),
    Tool(
        name="knowledge_detail",
        description="获取指定知识条目的完整详情",
        inputSchema={
            "type": "object",
            "properties": {
                "entry_id": {
                    "type": "string",
                    "description": "知识条目 ID",
                },
            },
            "required": ["entry_id"],
        },
    ),
    Tool(
        name="web_search",
        description="搜索互联网获取最新资料，用于学习和研究。支持中文和英文搜索，返回搜索结果摘要",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询词",
                },
                "limit": {
                    "type": "number",
                    "description": "返回结果数量",
                    "default": 5,
                },
                "lang": {
                    "type": "string",
                    "enum": ["zh", "en"],
                    "description": "搜索语言",
                    "default": "zh",
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="knowledge_create",
        description="创建新的知识条目，将学习内容存入知识库。用于保存从网络搜索或其他来源获取的知识",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "知识标题",
                },
                "content": {
                    "type": "string",
                    "description": "知识内容（详细）",
                },
                "entry_type": {
                    "type": "string",
                    "enum": ENTRY_TYPES,
                    "description": "条目类型",
                    "default": "custom",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "标签列表",
                },
                "importance": {
                    "type": "number",
                    "description": "重要性评分(1-10)",
                    "default": 5,
                },
            },
            "required": ["title", "content"],
        },
    ),
    Tool(
        name="knowledge_update",
        description="更新已有的知识条目",
        inputSchema={
            "type": "object",
            "properties": {
                "entry_id": {
                    "type": "string",
                    "description": "知识条目 ID",
                },
                "title": {
                    "type": "string",
                    "description": "新标题",
                },
                "content": {
                    "type": "string",
                    "description": "新内容",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "新标签列表",
                },
                "importance": {
                    "type": "number",
                    "description": "新重要性评分",
                },
            },
            "required": ["entry_id"],
        },
    ),
]

# ---------------------------------------------------------------------------
# 工具注册
# ---------------------------------------------------------------------------


@server.list_tools()
async def list_tools() -> list[Tool]:
    """列出所有知识库工具"""
    return ALL_TOOLS


# ---------------------------------------------------------------------------
# 工具调度
# ---------------------------------------------------------------------------


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """统一工具调用入口"""
    logger.info("call_tool: name=%s, arguments=%s", name, arguments)

    dispatch = {
        "knowledge_search": _handle_knowledge_search,
        "knowledge_list": _handle_knowledge_list,
        "knowledge_detail": _handle_knowledge_detail,
        "web_search": _handle_web_search,
        "knowledge_create": _handle_knowledge_create,
        "knowledge_update": _handle_knowledge_update,
    }

    handler = dispatch.get(name)
    if handler is None:
        return [TextContent(type="text", text=f"未知工具: {name}")]

    try:
        result = await handler(arguments)
        return [TextContent(type="text", text=result)]
    except Exception as exc:
        logger.exception("工具 %s 执行失败", name)
        return [TextContent(type="text", text=f"工具 {name} 执行失败: {exc}")]


# ---------------------------------------------------------------------------
# 工具处理器
# ---------------------------------------------------------------------------


async def _handle_knowledge_search(arguments: dict) -> str:
    """搜索知识库"""
    query = arguments.get("query", "")
    limit = arguments.get("limit", 5)
    mode = arguments.get("mode", "hybrid")

    if not query:
        return "错误: query 参数不能为空"

    db = _get_knowledge_db()
    vector_store = _get_vector_store()

    if mode == "vector":
        results = vector_store.search(query, top_k=limit)
        final_results = []
        for r in results:
            entry = db.get_entry(r["doc_id"])
            if entry:
                final_results.append({
                    **entry.to_dict(),
                    "score": r["score"],
                    "search_mode": "vector",
                })
    elif mode == "keyword":
        entries = db.list_entries(search=query, limit=limit)
        final_results = [
            {**e.to_dict(), "score": 1.0, "search_mode": "keyword"}
            for e in entries
        ]
    else:
        # hybrid: 合并向量检索和关键词检索结果
        vector_results = vector_store.search(query, top_k=limit * 2)
        keyword_entries = db.list_entries(search=query, limit=limit * 2)

        seen_ids: set[str] = set()
        final_results = []

        for r in vector_results:
            if r["doc_id"] not in seen_ids:
                entry = db.get_entry(r["doc_id"])
                if entry:
                    seen_ids.add(r["doc_id"])
                    final_results.append({
                        **entry.to_dict(),
                        "score": r["score"],
                        "search_mode": "vector",
                    })

        for e in keyword_entries:
            if e.entry_id not in seen_ids:
                seen_ids.add(e.entry_id)
                final_results.append({
                    **e.to_dict(),
                    "score": 1.0,
                    "search_mode": "keyword",
                })

        final_results = final_results[:limit]

    if not final_results:
        return f"未找到与 '{query}' 相关的知识条目 (模式: {mode})"

    lines = [f"知识库搜索结果 (查询: '{query}', 模式: {mode}, 共 {len(final_results)} 条):\n"]
    for i, r in enumerate(final_results, 1):
        score = r.get("score", 0)
        search_mode = r.get("search_mode", "")
        lines.append(f"--- 结果 {i} ---")
        lines.append(f"标题: {r['title']}")
        lines.append(f"类型: {r['entry_type']}")
        lines.append(f"相似度: {score:.4f} ({search_mode})")
        lines.append(f"ID: {r['entry_id']}")
        lines.append(f"内容: {r['content']}")
        if r.get("tags"):
            lines.append(f"标签: {', '.join(r['tags'])}")
        lines.append("")

    return "\n".join(lines)


async def _handle_knowledge_list(arguments: dict) -> str:
    """列出知识条目"""
    entry_type = arguments.get("type")
    search = arguments.get("search")
    limit = arguments.get("limit", 10)

    db = _get_knowledge_db()
    entries = db.list_entries(entry_type=entry_type, search=search, limit=limit)

    if not entries:
        filter_desc = []
        if entry_type:
            filter_desc.append(f"类型={entry_type}")
        if search:
            filter_desc.append(f"搜索='{search}'")
        filter_str = ", ".join(filter_desc) if filter_desc else "无过滤"
        return f"未找到知识条目 (过滤条件: {filter_str})"

    lines = [f"知识条目列表 (共 {len(entries)} 条):\n"]
    for i, entry in enumerate(entries, 1):
        lines.append(f"{i}. [{entry.entry_type}] {entry.title}")
        lines.append(f"   ID: {entry.entry_id}")
        lines.append(f"   重要性: {entry.importance}")
        if entry.tags:
            lines.append(f"   标签: {', '.join(entry.tags)}")
        # 显示内容的前 100 字符
        preview = entry.content[:100].replace("\n", " ")
        if len(entry.content) > 100:
            preview += "..."
        lines.append(f"   内容预览: {preview}")
        lines.append("")

    return "\n".join(lines)


async def _handle_knowledge_detail(arguments: dict) -> str:
    """获取知识条目详情"""
    entry_id = arguments.get("entry_id", "")

    if not entry_id:
        return "错误: entry_id 参数不能为空"

    db = _get_knowledge_db()
    entry = db.get_entry(entry_id)

    if not entry:
        return f"未找到知识条目: {entry_id}"

    # 记录访问
    db.record_access(entry_id)

    lines = [
        f"知识条目详情:",
        f"ID: {entry.entry_id}",
        f"类型: {entry.entry_type}",
        f"标题: {entry.title}",
        f"重要性: {entry.importance}",
        f"版本: {entry.version}",
        f"创建时间: {entry.created_at}",
        f"更新时间: {entry.updated_at}",
        f"访问次数: {entry.access_count}",
        f"标签: {', '.join(entry.tags) if entry.tags else '无'}",
        "",
        f"内容:",
        entry.content,
    ]

    if entry.metadata:
        lines.append("")
        lines.append("元数据:")
        for key, value in entry.metadata.items():
            lines.append(f"  {key}: {value}")

    return "\n".join(lines)


async def _handle_web_search(arguments: dict) -> str:
    """搜索互联网获取资料（使用博查搜索 API）"""
    query = arguments.get("query", "")
    limit = arguments.get("limit", 5)
    lang = arguments.get("lang", "zh")

    if not query:
        return "错误: query 参数不能为空"

    try:
        import os
        api_key = os.environ.get("BOCHA_API_KEY", "")

        search_url = "https://api.bochaai.com/v1/web-search"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "query": query,
            "count": int(limit),
            "freshness": "noLimit",
            "summary": True,
        }

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            async with session.post(search_url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    return f"搜索失败，HTTP状态码: {resp.status}, 错误信息: {error_text[:200]}"

                data = await resp.json()

        web_pages = data.get("data", {}).get("webPages", {}).get("value", [])

        if not web_pages:
            return f"未找到与 '{query}' 相关的搜索结果"

        lines = [f"网页搜索结果 (查询: '{query}', 共 {len(web_pages)} 条):\n"]
        for i, page in enumerate(web_pages[:limit], 1):
            lines.append(f"--- 结果 {i} ---")
            lines.append(f"标题: {page.get('name', '')}")
            lines.append(f"URL: {page.get('url', '')}")
            summary = page.get("summary", page.get("snippet", ""))
            if len(summary) > 300:
                summary = summary[:300] + "..."
            lines.append(f"摘要: {summary}")
            lines.append("")

        return "\n".join(lines)

    except Exception as exc:
        logger.exception("网页搜索失败")
        return f"网页搜索失败: {exc}"


async def _handle_knowledge_create(arguments: dict) -> str:
    """创建知识条目"""
    title = arguments.get("title", "")
    content = arguments.get("content", "")
    entry_type = arguments.get("entry_type", "custom")
    tags = arguments.get("tags", [])
    importance = arguments.get("importance", 5)

    if not title or not content:
        return "错误: title 和 content 参数不能为空"

    db = _get_knowledge_db()
    entry = db.create_entry(
        entry_type=entry_type,
        title=title,
        content=content,
        tags=tags,
        importance=importance,
    )

    _rebuild_vector_index()

    return f"知识条目创建成功！\nID: {entry.entry_id}\n标题: {entry.title}\n类型: {entry.entry_type}\n标签: {', '.join(entry.tags) if entry.tags else '无'}\n重要性: {entry.importance}"


async def _handle_knowledge_update(arguments: dict) -> str:
    """更新知识条目"""
    entry_id = arguments.get("entry_id", "")
    title = arguments.get("title")
    content = arguments.get("content")
    tags = arguments.get("tags")
    importance = arguments.get("importance")

    if not entry_id:
        return "错误: entry_id 参数不能为空"

    db = _get_knowledge_db()
    entry = db.update_entry(
        entry_id=entry_id,
        title=title,
        content=content,
        tags=tags,
        importance=importance,
    )

    if not entry:
        return f"未找到知识条目: {entry_id}"

    _rebuild_vector_index()

    return f"知识条目更新成功！\nID: {entry.entry_id}\n标题: {entry.title}\n内容已更新\n版本: {entry.version}"


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------


async def main() -> None:
    """启动 MCP Server (stdio 模式)"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )

    logger.info("knowledge-base MCP Server 启动")
    logger.info("KNOWLEDGE_DB_PATH=%s", KNOWLEDGE_DB_PATH)

    # 预初始化数据库和向量索引
    _get_knowledge_db()
    _get_vector_store()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
