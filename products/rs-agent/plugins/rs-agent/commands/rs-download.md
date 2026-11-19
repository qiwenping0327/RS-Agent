# /rs-download

下载卫星遥感影像。

参数：
- `sensor`: 传感器名称，支持 sentinel2、landsat8、gf1、gf2
- `aoi`: 感兴趣区域，GeoJSON 格式
- `start_date`: 起始日期 (YYYY-MM-DD)
- `end_date`: 结束日期 (YYYY-MM-DD)
- `max_cloud_cover`: 最大云覆盖百分比 (默认 20)

示例：
```
/rs-download sensor=sentinel2 aoi={"type":"Polygon","coordinates":[[[116.3,39.9],[116.4,39.9],[116.4,40.0],[116.3,40.0],[116.3,39.9]]]} start_date=2024-01-01 end_date=2024-06-30
```

调用 `mcp__rs_agent__rs_download` 工具执行下载。支持断点续跑：若任务中断，再次执行相同参数将从上次进度继续。
