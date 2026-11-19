# /rs-report

生成遥感分析报告。

参数：
- `task_ids`: 任务 ID 列表 (JSON 数组)
- `format`: 报告格式，支持 markdown、html、pdf (默认 markdown)
- `output_path`: 输出路径 (可选)

示例：
```
/rs-report task_ids=["task_001","task_002"] format=html
```

调用 `mcp__rs_agent__rs_report` 工具生成报告。报告包含：数据来源、处理流程、分析结果、可视化图表。
