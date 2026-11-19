"""
LLM 客户端 - 读取 PilotDeck 配置，封装 OpenAI 兼容 API 调用

从 ~/.pilotdeck/pilotdeck.yaml 读取模型供应商配置，
支持 OpenAI 兼容协议（DeepSeek / OpenAI / Google / Moonshot 等）。
"""

import json
import logging
import os
from typing import Any, Optional

try:
    import aiohttp
except ImportError:
    raise ImportError("Please install aiohttp: pip install aiohttp")

try:
    import yaml
except ImportError:
    yaml = None

logger = logging.getLogger("oea.llm")

# 默认配置路径
PILOT_HOME = os.environ.get(
    "PILOT_HOME",
    os.path.join(os.path.expanduser("~"), ".pilotdeck"),
)
CONFIG_PATH = os.path.join(PILOT_HOME, "pilotdeck.yaml")


def load_model_config() -> dict[str, Any]:
    """
    从 pilotdeck.yaml 读取模型配置

    Returns:
        dict with keys: url, api_key, model, protocol, provider
    """
    config_path = os.environ.get("PILOTDECK_CONFIG_PATH", CONFIG_PATH)

    if not os.path.exists(config_path):
        logger.warning(f"Config not found: {config_path}, using defaults")
        return {
            "url": "https://api.deepseek.com/v1",
            "api_key": "",
            "model": "deepseek-chat",
            "protocol": "openai",
            "provider": "deepseek",
        }

    if yaml is None:
        logger.warning("PyYAML not installed, trying json fallback")
        return _fallback_config()

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # 解析 agent.model (格式: "provider/model")
    agent_model = config.get("agent", {}).get("model", "deepseek/deepseek-chat")
    parts = agent_model.split("/", 1)
    provider_id = parts[0] if len(parts) > 1 else "deepseek"
    model_id = parts[1] if len(parts) > 1 else parts[0]

    # 获取供应商配置
    providers = config.get("model", {}).get("providers", {})
    provider_config = providers.get(provider_id, {})

    url = provider_config.get("url", "https://api.deepseek.com/v1")
    api_key = provider_config.get("apiKey", "")
    protocol = provider_config.get("protocol", "openai")

    # 支持 ${ENV_VAR} 格式的 API Key 引用
    if api_key.startswith("${") and api_key.endswith("}"):
        env_var = api_key[2:-1]
        api_key = os.environ.get(env_var, "")

    return {
        "url": url,
        "api_key": api_key,
        "model": model_id,
        "protocol": protocol,
        "provider": provider_id,
    }


def _fallback_config() -> dict[str, Any]:
    """YAML 不可用时的回退配置"""
    return {
        "url": os.environ.get("LLM_URL", os.environ.get("VOLCENGINE_URL", "https://api.deepseek.com/v1")),
        "api_key": os.environ.get("LLM_API_KEY", os.environ.get("VOLCENGINE_API_KEY", "")),
        "model": os.environ.get("LLM_MODEL", os.environ.get("VOLCENGINE_MODEL", "deepseek-chat")),
        "protocol": "openai",
        "provider": os.environ.get("LLM_PROVIDER", os.environ.get("VOLCENGINE_PROVIDER", "deepseek")),
    }


# MCP 工具注册表 - 从 plugin.json 提取的工具描述
MCP_TOOLS_REGISTRY = {
    "rs-agent": {
        "description": "遥感核心服务",
        "tools": {
            "rs_download": "下载卫星影像 (sensor: sentinel2/landsat8/gf1/gf2, aoi: 支持中文地名)",
            "rs_preprocess": "影像预处理 (辐射校正/几何校正/裁剪/重采样/大气校正)",
            "rs_analyze": "智能分析 (NDVI/NDWI/EVI/SAVI等指数计算、地物分类、变化检测)",
            "rs_visualize": "可视化 (缩略图/真彩色/假彩色/分类结果渲染)",
            "rs_report": "生成报告 (markdown/html/pdf)",
            "rs_sar_analysis": "SAR 数据分析 (极化分解/干涉测量/变化检测)",
            "rs_model_inference": "AI 模型推理 (YOLOv8目标检测/U-Net语义分割/BIT变化检测)",
        },
    },
    "rs-index": {
        "description": "光谱指数计算服务",
        "tools": {
            "ndvi_calc": "计算 NDVI 归一化植被指数 (需要 Red+NIR 波段)",
            "ndwi_calc": "计算 NDWI 归一化水体指数 (需要 Green+NIR 波段)",
            "evi_calc": "计算 EVI 增强植被指数 (需要 Red+NIR+Blue 波段)",
            "savi_calc": "计算 SAVI 土壤调节植被指数",
            "mndwi_calc": "计算 MNDWI 改进归一化水体指数 (需要 Green+SWIR 波段)",
            "ndbi_calc": "计算 NDBI 归一化建筑指数",
            "band_math": "自定义波段运算",
        },
    },
    "rs-perception": {
        "description": "感知与分割服务",
        "tools": {
            "threshold_segmentation": "阈值分割 (指定波段和阈值提取目标区域)",
            "extract_water_bodies": "一步式水体提取 (阈值分割+矢量化，NIR波段用invert=True)",
            "raster_to_vector": "栅格转矢量 (将二值掩膜转为SHP矢量文件)",
            "SAM2": "SAM2 语义分割 (需要预计算结果或模型权重)",
            "count_skeleton_contours": "轮廓统计",
            "count_above_threshold": "阈值以上像素计数",
        },
    },
    "rs-analysis": {
        "description": "时间序列分析服务",
        "tools": {
            "compute_linear_trend": "计算线性趋势",
            "mann_kendall_test": "Mann-Kendall 趋势检验",
            "sens_slope": "Sen 斜率估计",
            "stl_decompose": "STL 季节分解",
            "detect_change_points": "变点检测",
            "getis_ord_gi_star": "Getis-Ord Gi* 热点分析",
            "analyze_hotspot_direction": "热点方向分析",
        },
    },
    "rs-inversion": {
        "description": "反演服务",
        "tools": {
            "land_surface_temperature": "地表温度反演",
            "soil_moisture": "土壤水分反演",
            "vegetation_parameters": "植被参数反演",
        },
    },
    "rs-statistics": {
        "description": "统计分析服务",
        "tools": {
            "descriptive_stats": "描述性统计 (均值/方差/标准差/中位数/分位数)",
            "histogram": "直方图计算",
            "zonal_stats": "分区统计",
            "reclassify": "重分类",
            "anomaly_detection": "异常值检测",
            "band_correlation": "波段相关性计算",
        },
    },
    "knowledge-base": {
        "description": "知识库检索服务",
        "tools": {
            "knowledge_search": "知识库检索 (hybrid/vector/keyword 三种模式)",
            "knowledge_list": "知识条目列表",
            "knowledge_detail": "知识条目详情",
            "web_search": "搜索互联网获取最新资料",
            "knowledge_create": "创建知识条目，将学习内容存入知识库",
            "knowledge_update": "更新已有的知识条目",
        },
    },
}


def build_tools_description() -> str:
    """构建 MCP 工具表描述，用于注入 LLM prompt"""
    lines = []
    for server_name, server_info in MCP_TOOLS_REGISTRY.items():
        lines.append(f"\n### {server_name} - {server_info['description']}")
        for tool_name, tool_desc in server_info["tools"].items():
            full_id = f"{server_name}.{tool_name}"
            lines.append(f"- `{full_id}`: {tool_desc}")
    return "\n".join(lines)


class LLMClient:
    """OpenAI 兼容协议的 LLM 客户端"""

    def __init__(self, config: dict[str, Any] = None):
        self._config = config or load_model_config()
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def is_configured(self) -> bool:
        return bool(self._config.get("api_key"))

    @property
    def model_name(self) -> str:
        return self._config.get("model", "deepseek-chat")

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=60)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        response_format: Optional[dict] = None,
    ) -> str:
        """
        单次 LLM 完成调用

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户消息
            temperature: 采样温度
            max_tokens: 最大输出 token 数
            response_format: 响应格式 (如 {"type": "json_object"})

        Returns:
            LLM 输出的文本内容
        """
        if not self.is_configured:
            raise ValueError("LLM API key not configured")

        url = self._config["url"].rstrip("/")
        endpoint = f"{url}/chat/completions"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        payload = {
            "model": self._config["model"],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            payload["response_format"] = response_format

        headers = {
            "Authorization": f"Bearer {self._config['api_key']}",
            "Content-Type": "application/json",
        }

        session = await self._get_session()
        try:
            async with session.post(endpoint, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"LLM API error {resp.status}: {error_text[:500]}")
                    raise RuntimeError(f"LLM API returned {resp.status}: {error_text[:200]}")

                data = await resp.json()
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                logger.info(
                    f"LLM call: model={self._config['model']}, "
                    f"tokens={usage.get('total_tokens', '?')}, "
                    f"prompt_len={len(user_prompt)}, response_len={len(content)}"
                )
                return content

        except aiohttp.ClientError as e:
            logger.error(f"LLM request failed: {e}")
            raise RuntimeError(f"LLM request failed: {e}") from e

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        """
        调用 LLM 并解析 JSON 输出

        Returns:
            解析后的 dict
        """
        # 在 system prompt 中追加 JSON 输出要求
        enhanced_system = (
            system_prompt
            + "\n\n重要：你必须以纯 JSON 格式输出，不要包含 markdown 代码块标记或其他文本。"
        )

        raw = await self.complete(
            system_prompt=enhanced_system,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # 清理可能的 markdown 代码块标记
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # 去掉首行 ```json 和末行 ```
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning(f"LLM output is not valid JSON: {cleaned[:200]}")
            # 尝试提取 JSON 部分
            import re
            json_match = re.search(r'\{[\s\S]*\}', cleaned)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
        raise ValueError(f"LLM output is not valid JSON: {e}") from e

    async def extract_knowledge(
        self,
        search_results: str,
        topic: str,
    ) -> list[dict[str, Any]]:
        """
        从搜索结果中提取结构化知识点，用于学习和存储

        Args:
            search_results: 网页搜索结果文本
            topic: 学习主题

        Returns:
            list of {title, content, tags, importance, entry_type}
        """
        system_prompt = """你是一个专业的知识整理助手。
你的任务是从搜索结果中提取结构化的知识点，用于存入知识库。

每个知识点需要包含：
1. title: 清晰的标题，概括知识点内容
2. content: 详细的内容解释，包含关键概念、原理、公式、示例等
3. tags: 相关标签列表（3-5个），用于后续检索
4. importance: 重要性评分（1-10），10表示最重要
5. entry_type: 条目类型，可选值：geoknowledge（地理知识）、best_practice（最佳实践）、workflow（工作流程）、faq（常见问题）、custom（自定义）

提取原则：
- 每个知识点独立、完整，不依赖其他知识点
- 内容要详细，包含足够的技术细节
- 标签要准确，便于搜索和分类
- 重要性根据知识点在主题中的核心程度评估

输出格式为纯 JSON 数组，不要包含 markdown 代码块标记：
[{"title": "...", "content": "...", "tags": ["..."], "importance": 5, "entry_type": "custom"}, ...]
"""

        user_prompt = f"""学习主题: {topic}

搜索结果:
{search_results}

请从上述搜索结果中提取关键知识点，每个知识点包含标题、详细内容、标签、重要性评分和条目类型。"""

        try:
            result = await self.complete_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=4096,
            )

            if isinstance(result, list):
                return result
            elif isinstance(result, dict) and "knowledge_points" in result:
                return result["knowledge_points"]
            else:
                logger.warning(f"Unexpected format from extract_knowledge: {type(result)}")
                return []

        except Exception as e:
            logger.error(f"extract_knowledge failed: {e}")
            return []

    async def learn_and_summarize(
        self,
        topic: str,
        search_results: str,
    ) -> str:
        """
        学习搜索结果并生成总结报告

        Args:
            topic: 学习主题
            search_results: 网页搜索结果文本

        Returns:
            学习总结报告文本
        """
        system_prompt = """你是一个专业的学习助手。
请阅读搜索结果，对学习主题进行全面总结。

输出格式：
1. 主题概述：简要介绍学习主题的核心概念
2. 关键知识点：列出3-5个最重要的知识点
3. 学习总结：总结学习收获和重点
4. 推荐后续学习方向：建议进一步学习的内容

语言要清晰、专业，适合存入知识库。"""

        user_prompt = f"""学习主题: {topic}

搜索结果:
{search_results}

请基于上述搜索结果，为我生成一份详细的学习总结报告。"""

        return await self.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=2048,
        )


# 全局单例
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """获取全局 LLM 客户端实例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
        logger.info(
            f"LLM client initialized: provider={_llm_client._config.get('provider')}, "
            f"model={_llm_client.model_name}, "
            f"configured={_llm_client.is_configured}"
        )
    return _llm_client
