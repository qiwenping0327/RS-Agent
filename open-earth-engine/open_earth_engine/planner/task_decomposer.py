from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("oea.decomposer")


@dataclass
class TaskStep:
    step_id: str
    step_number: int
    description: str
    tool_name: Optional[str] = None
    tool_id: Optional[str] = None
    execution_mode: str = "mcp"
    estimated_duration: int = 60
    gpu_memory: float = 0.0
    dependencies: list[str] = field(default_factory=list)
    args: dict[str, Any] = field(default_factory=dict)
    reasoning: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "step_number": self.step_number,
            "description": self.description,
            "tool_name": self.tool_name,
            "tool_id": self.tool_id,
            "execution_mode": self.execution_mode,
            "estimated_duration": self.estimated_duration,
            "gpu_memory": self.gpu_memory,
            "dependencies": self.dependencies,
            "args": self.args,
            "reasoning": self.reasoning,
        }


@dataclass
class DecomposerConfig:
    use_mock: bool = True
    llm_endpoint: Optional[str] = None
    llm_api_key: Optional[str] = None
    model_name: str = "gpt-4"
    max_steps: int = 10
    enable_reasoning: bool = True


class TaskDecomposer:
    """
    任务分解器 - LLM层自然语言拆业务步骤

    职责:
    1. 将自然语言任务描述分解为可执行的步骤序列
    2. 为每个步骤推荐合适的工具
    3. 识别步骤间的依赖关系
    4. 生成步骤执行的推理依据

    与 SpaceOrchestrator 的关系:
    - TaskDecomposer: LLM层，自然语言拆业务步骤
    - SpaceOrchestrator: 空间编排核心，解析工具依赖、构建DAG、校验坐标等
    """

    def __init__(self, config: DecomposerConfig = None):
        self.config = config or DecomposerConfig()

        self._tool_patterns = {
            "download": ["下载", "获取", "download", "fetch", "拉取"],
            "preprocess": ["预处理", "校正", "辐射校正", "大气校正", "preprocess", "correct"],
            "analyze": ["分析", "计算", "分析", "analyze", "calculate"],
            "ndvi": ["ndvi", "植被指数", "归一化植被指数"],
            "ndwi": ["ndwi", "水体指数", "归一化水体指数"],
            "classify": ["分类", "classify", "classification"],
            "segment": ["分割", "segment", "segmentation"],
            "visualize": ["可视化", "渲染", "显示", "visualize", "render", "display"],
        }

        self._default_workflows = {
            "ndvi": [
                {"desc": "下载影像数据", "tool": "rs_download", "mode": "mcp"},
                {"desc": "影像预处理", "tool": "rs_preprocess", "mode": "mcp", "depends": [0]},
                {"desc": "计算NDVI指数", "tool": "rs_analyze", "mode": "mcp", "depends": [1]},
            ],
            "水体": [
                {"desc": "下载影像数据", "tool": "rs_download", "mode": "mcp"},
                {"desc": "影像预处理", "tool": "rs_preprocess", "mode": "mcp", "depends": [0]},
                {"desc": "计算NDWI水体指数", "tool": "rs_analyze", "mode": "mcp", "depends": [1]},
            ],
            "变化检测": [
                {"desc": "下载时相1影像", "tool": "rs_download", "mode": "mcp"},
                {"desc": "下载时相2影像", "tool": "rs_download", "mode": "mcp"},
                {"desc": "时相1预处理", "tool": "rs_preprocess", "mode": "mcp", "depends": [0]},
                {"desc": "时相2预处理", "tool": "rs_preprocess", "mode": "mcp", "depends": [1]},
                {"desc": "执行变化检测", "tool": "rs_analyze", "mode": "mcp", "depends": [2, 3]},
            ],
        }

    async def decompose(
        self,
        task_description: str,
        context: dict[str, Any] = None,
        force_steps: list[dict] = None,
    ) -> list[TaskStep]:
        """
        主分解方法

        Args:
            task_description: 自然语言任务描述
            context: 额外上下文（数据元数据、传感器信息等）
            force_steps: 强制指定的步骤（用于测试或手动规划）

        Returns:
            任务步骤列表
        """
        if force_steps:
            return self._steps_from_force(force_steps)

        if self.config.use_mock:
            return self._mock_decompose(task_description, context or {})

        return await self._llm_decompose(task_description, context or {})

    def _steps_from_force(self, force_steps: list[dict]) -> list[TaskStep]:
        """
        从强制指定的步骤生成 TaskStep 列表
        """
        steps = []
        for i, step_data in enumerate(force_steps):
            step = TaskStep(
                step_id=f"step_{i:03d}",
                step_number=i + 1,
                description=step_data.get("description", step_data.get("name", f"步骤 {i+1}")),
                tool_name=step_data.get("tool_name", step_data.get("tool")),
                tool_id=step_data.get("tool_id"),
                execution_mode=step_data.get("execution_mode", "mcp"),
                estimated_duration=step_data.get("estimated_duration", 60),
                gpu_memory=step_data.get("gpu_memory", 0.0),
                dependencies=step_data.get("dependencies", []),
                args=step_data.get("args", {}),
                reasoning=step_data.get("reasoning"),
            )
            steps.append(step)
        return steps

    def _mock_decompose(
        self,
        task_description: str,
        context: dict[str, Any],
    ) -> list[TaskStep]:
        """
        Mock分解 - 基于规则的任务分解
        """
        logger.info(f"Mock decomposing task: {task_description}")

        task_lower = task_description.lower()

        for key, workflow in self._default_workflows.items():
            if key in task_lower or key in task_description:
                return self._workflow_to_steps(workflow, task_description)

        steps = self._general_decompose(task_description, context)
        return steps

    def _workflow_to_steps(
        self,
        workflow: list[dict],
        task_description: str,
    ) -> list[TaskStep]:
        """
        将预定义工作流转换为 TaskStep 列表
        """
        steps = []
        for i, step_def in enumerate(workflow):
            dep_ids = []
            for dep_idx in step_def.get("depends", []):
                if dep_idx < len(steps):
                    dep_ids.append(f"step_{dep_idx:03d}")

            step = TaskStep(
                step_id=f"step_{i:03d}",
                step_number=i + 1,
                description=step_def["desc"],
                tool_name=step_def.get("tool"),
                tool_id=f"rs-agent.{step_def.get('tool')}" if step_def.get("tool") else None,
                execution_mode=step_def.get("mode", "mcp"),
                dependencies=dep_ids,
                reasoning=f"标准工作流步骤 {i+1}",
            )
            steps.append(step)

        logger.info(f"Using predefined workflow: {len(steps)} steps")
        return steps

    def _general_decompose(
        self,
        task_description: str,
        context: dict[str, Any],
    ) -> list[TaskStep]:
        """
        通用任务分解
        """
        steps = []
        step_idx = 0

        task_lower = task_description.lower()

        needs_download = any(
            kw in task_lower or kw in task_description
            for kw in ["下载", "获取", "需要", "download", "fetch"]
        ) or not context.get("input_path")

        if needs_download:
            steps.append(TaskStep(
                step_id=f"step_{step_idx:03d}",
                step_number=step_idx + 1,
                description="下载影像数据",
                tool_name="rs_download",
                tool_id="rs-agent.rs_download",
                execution_mode="mcp",
                reasoning="任务需要获取遥感影像数据",
            ))
            step_idx += 1

        needs_preprocess = any(
            kw in task_lower
            for kw in ["预处理", "校正", "preprocess", "correct", "大气"]
        ) or "分析" in task_description or "计算" in task_description

        if needs_preprocess:
            deps = [f"step_000"] if step_idx > 0 else []
            steps.append(TaskStep(
                step_id=f"step_{step_idx:03d}",
                step_number=step_idx + 1,
                description="影像预处理",
                tool_name="rs_preprocess",
                tool_id="rs-agent.rs_preprocess",
                execution_mode="mcp",
                dependencies=deps,
                reasoning="遥感分析前通常需要辐射校正和大气校正",
            ))
            step_idx += 1

        analysis_keywords = ["分析", "计算", "提取", "检测", "分类", "分割", "analyze", "calculate", "extract", "detect", "classify", "segment"]
        needs_analysis = any(kw in task_lower or kw in task_description for kw in analysis_keywords)

        if needs_analysis:
            deps = [f"step_{step_idx-1:03d}"] if step_idx > 0 else []
            execution_mode = "sandbox" if self._needs_custom_code(task_description) else "mcp"

            steps.append(TaskStep(
                step_id=f"step_{step_idx:03d}",
                step_number=step_idx + 1,
                description="执行分析计算",
                tool_name="rs_analyze" if execution_mode == "mcp" else None,
                tool_id="rs-agent.rs_analyze" if execution_mode == "mcp" else None,
                execution_mode=execution_mode,
                dependencies=deps,
                reasoning="任务需要执行地理空间分析",
            ))
            step_idx += 1

        if not steps:
            steps.append(TaskStep(
                step_id="step_000",
                step_number=1,
                description="执行任务",
                execution_mode="sandbox",
                reasoning="通用任务处理",
            ))

        logger.info(f"General decomposition: {len(steps)} steps")
        return steps

    def _needs_custom_code(self, task_description: str) -> bool:
        """
        判断是否需要自定义代码（沙箱执行）
        """
        custom_keywords = [
            "自定义", "custom", "脚本", "script", "编程", "code",
            "缓冲区", "相交", "擦除", "分区统计", "buffer", "intersect",
            "栅格转矢量", "矢量转栅格", "polygonize", "rasterize",
        ]
        task_lower = task_description.lower()
        return any(kw.lower() in task_lower for kw in custom_keywords)

    async def _llm_decompose(
        self,
        task_description: str,
        context: dict[str, Any],
    ) -> list[TaskStep]:
        """
        LLM驱动的任务分解（预留接口）
        """
        if not self.config.llm_endpoint:
            logger.warning("No LLM endpoint configured, falling back to mock decomposition")
            return self._mock_decompose(task_description, context)

        prompt = self._build_prompt(task_description, context)
        logger.info(f"LLM decomposition prompt prepared (length={len(prompt)})")

        return self._mock_decompose(task_description, context)

    def _build_prompt(
        self,
        task_description: str,
        context: dict[str, Any],
    ) -> str:
        """
        构建LLM提示词
        """
        return f"""你是一个遥感分析任务规划专家。请将以下任务分解为可执行的步骤：

任务描述: {task_description}

上下文信息: {json.dumps(context, ensure_ascii=False, indent=2)}

请以JSON格式输出步骤列表，每个步骤包含:
- step_number: 步骤编号
- description: 步骤描述
- tool_name: 推荐使用的工具名
- execution_mode: 执行模式 (mcp 或 sandbox)
- depends_on: 依赖的步骤编号列表
- reasoning: 推理依据
"""

    def steps_to_dag_format(self, steps: list[TaskStep]) -> list[dict]:
        """
        将步骤转换为 SpaceOrchestrator 需要的 DAG 格式
        """
        return [step.to_dict() for step in steps]

    def validate_steps(self, steps: list[TaskStep]) -> tuple[bool, list[str]]:
        """
        验证步骤的完整性和依赖关系
        """
        errors = []
        step_ids = {step.step_id for step in steps}

        for step in steps:
            for dep in step.dependencies:
                if dep not in step_ids:
                    errors.append(f"Step {step.step_id} depends on missing step {dep}")

            if step.execution_mode not in ["mcp", "sandbox", "mixed"]:
                errors.append(f"Step {step.step_id} has invalid execution_mode: {step.execution_mode}")

        return (len(errors) == 0, errors)
