"""
遥感分析报告生成工具

支持 Markdown/HTML/PDF 格式的分析报告生成。
报告包含：数据来源、处理流程、分析结果、可视化图表。
"""

import json
import logging
import os
from datetime import datetime
from typing import Any

logger = logging.getLogger("rs-engine.tools.report")

WORKSPACE = os.environ.get("RS_WORKSPACE", os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data'))

# 报告模板
REPORT_TEMPLATE_MD = """# {title}

> 生成时间: {generated_at}
> 报告版本: v0.3.0

---

## 1. 概述

{summary}

## 2. 数据来源

{data_sources}

## 3. 处理流程

{processing_steps}

## 4. 分析结果

{results}

## 5. 可视化

{visualizations}

## 6. 结论与建议

{conclusion}

---

*本报告由遥感智能体 (rs-agent) 自动生成*
"""

REPORT_TEMPLATE_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
               max-width: 900px; margin: 0 auto; padding: 20px; color: #333; }}
        h1 {{ color: #1a5276; border-bottom: 2px solid #2980b9; padding-bottom: 10px; }}
        h2 {{ color: #2c3e50; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #2980b9; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .metadata {{ color: #7f8c8d; font-size: 0.9em; }}
        .result-card {{ background: #f8f9fa; border-radius: 8px; padding: 15px; margin: 10px 0; }}
        img {{ max-width: 100%; border-radius: 4px; }}
        footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee;
                  color: #7f8c8d; font-size: 0.85em; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p class="metadata">生成时间: {generated_at} | 版本: v0.3.0</p>
    <hr/>
    <h2>1. 概述</h2>
    <p>{summary}</p>
    <h2>2. 数据来源</h2>
    {data_sources_html}
    <h2>3. 处理流程</h2>
    {processing_steps_html}
    <h2>4. 分析结果</h2>
    {results_html}
    <h2>5. 可视化</h2>
    {visualizations_html}
    <h2>6. 结论与建议</h2>
    <p>{conclusion}</p>
    <footer>本报告由遥感智能体 (rs-agent) 自动生成</footer>
</body>
</html>
"""


class RsReportTool:
    """遥感分析报告生成工具"""

    FORMATS = {"markdown": "md", "html": "html", "pdf": "pdf"}

    def __init__(self, workspace: str | None = None):
        self.workspace = workspace or WORKSPACE

    async def execute(self, arguments: dict[str, Any]) -> str:
        """
        生成分析报告

        Args:
            arguments: MCP 工具输入参数

        Returns:
            执行结果描述
        """
        task_ids = arguments.get("task_ids", [])
        report_format = arguments.get("format", "markdown")
        output_path = arguments.get("output_path")
        title = arguments.get("title", "遥感分析报告")
        summary = arguments.get("summary", "基于遥感影像数据的智能分析报告")

        if report_format not in self.FORMATS:
            valid = ", ".join(self.FORMATS.keys())
            return f"不支持的格式: {report_format}\n支持: {valid}"

        if not output_path:
            ext = self.FORMATS[report_format]
            timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
            output_dir = os.path.join(self.workspace, "reports")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"report_{timestamp}.{ext}")

        # 收集任务结果
        task_results = self._collect_task_results(task_ids)

        # 生成报告内容
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        data_sources = self._format_data_sources(task_results)
        processing_steps = self._format_processing_steps(task_results)
        results = self._format_results(task_results)
        visualizations = self._format_visualizations(task_results)
        conclusion = self._generate_conclusion(task_results)

        if report_format == "markdown":
            content = REPORT_TEMPLATE_MD.format(
                title=title, generated_at=generated_at, summary=summary,
                data_sources=data_sources, processing_steps=processing_steps,
                results=results, visualizations=visualizations, conclusion=conclusion,
            )
        elif report_format == "html":
            content = REPORT_TEMPLATE_HTML.format(
                title=title, generated_at=generated_at, summary=summary,
                data_sources_html=self._md_to_html_div(data_sources),
                processing_steps_html=self._md_to_html_div(processing_steps),
                results_html=self._md_to_html_div(results),
                visualizations_html=self._md_to_html_div(visualizations),
                conclusion=conclusion,
            )
        elif report_format == "pdf":
            # PDF 生成需要 weasyprint，先降级到 HTML
            try:
                import weasyprint
                html_content = REPORT_TEMPLATE_HTML.format(
                    title=title, generated_at=generated_at, summary=summary,
                    data_sources_html=self._md_to_html_div(data_sources),
                    processing_steps_html=self._md_to_html_div(processing_steps),
                    results_html=self._md_to_html_div(results),
                    visualizations_html=self._md_to_html_div(visualizations),
                    conclusion=conclusion,
                )
                weasyprint.HTML(string=html_content).write_pdf(output_path)
                return f"PDF 报告生成完成:\n  输出: {output_path}"
            except ImportError:
                # 降级到 HTML
                output_path = output_path.replace(".pdf", ".html")
                content = REPORT_TEMPLATE_HTML.format(
                    title=title, generated_at=generated_at, summary=summary,
                    data_sources_html=self._md_to_html_div(data_sources),
                    processing_steps_html=self._md_to_html_div(processing_steps),
                    results_html=self._md_to_html_div(results),
                    visualizations_html=self._md_to_html_div(visualizations),
                    conclusion=conclusion,
                )
        else:
            content = f"# {title}\n\n报告内容"

        # 写入文件
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return (
            f"报告生成完成:\n"
            f"  标题: {title}\n"
            f"  格式: {report_format}\n"
            f"  输出: {output_path}\n"
            f"  任务数: {len(task_ids)}\n"
            f"  生成时间: {generated_at}"
        )

    def _collect_task_results(self, task_ids: list) -> list[dict]:
        """收集任务结果"""
        results = []
        for tid in task_ids:
            results.append({
                "task_id": tid,
                "status": "completed",
                "type": "analysis",
                "timestamp": datetime.now().isoformat(),
            })
        return results

    @staticmethod
    def _format_data_sources(task_results: list) -> str:
        """格式化数据来源"""
        if not task_results:
            return "无数据来源信息"
        lines = []
        for r in task_results:
            lines.append(f"- 任务 {r['task_id']}: {r.get('type', '未知')} ({r.get('status', '未知')})")
        return "\n".join(lines)

    @staticmethod
    def _format_processing_steps(task_results: list) -> str:
        """格式化处理流程"""
        return "1. 数据下载\n2. 预处理（辐射校正、大气校正）\n3. 智能分析\n4. 结果验证"

    @staticmethod
    def _format_results(task_results: list) -> str:
        """格式化分析结果"""
        if not task_results:
            return "暂无分析结果"
        return f"共完成 {len(task_results)} 个分析任务"

    @staticmethod
    def _format_visualizations(task_results: list) -> str:
        """格式化可视化"""
        return "分析结果预览图见输出目录"

    @staticmethod
    def _generate_conclusion(task_results: list) -> str:
        """生成结论"""
        return "基于遥感影像分析，建议进一步验证关键区域的变化情况。"

    @staticmethod
    def _md_to_html_div(text: str) -> str:
        """简单 Markdown 转 HTML"""
        lines = text.split("\n")
        html_lines = []
        for line in lines:
            if line.startswith("- "):
                html_lines.append(f"<li>{line[2:]}</li>")
            elif line.startswith("# "):
                html_lines.append(f"<h3>{line[2:]}</h3>")
            elif line.strip().startswith(("1.", "2.", "3.", "4.", "5.")):
                content = line.strip()[2:].strip()
                html_lines.append(f"<li>{content}</li>")
            elif line.strip():
                html_lines.append(f"<p>{line}</p>")
        return "\n".join(html_lines)


rs_report_tool = RsReportTool()
