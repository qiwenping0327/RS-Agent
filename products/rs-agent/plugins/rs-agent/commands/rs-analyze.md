# /rs-analyze

对遥感影像执行智能分析。

参数：
- `input_path`: 输入影像路径或目录
- `analysis_type`: 分析类型，支持 ndvi、ndwi、classification、change_detection
- `params`: 分析参数 (JSON)

示例：
```
/rs-analyze input_path=/workspace/sentinel2 output=ndvi params={"red_band":"B04","nir_band":"B08"}
```

调用 `mcp__rs_agent__rs_analyze` 工具执行分析。分析完成后自动生成缩略图预览。
