"""
遥感智能分析 Agent - MCP Server & 执行引擎

基于 PilotDeck MCP 协议的遥感数据处理服务，提供：
- 影像下载（Sentinel/Landsat/高分系列）
- 预处理（辐射校正、几何校正、裁剪拼接）
- 智能分析（NDVI/NDWI 等指数计算、地物分类、变化检测）
- SAR 分析（极化处理、InSAR 形变监测）
- 深度学习模型推理
- 可视化与报告生成
"""

__version__ = "0.3.0"
