/**
 * MCP 工具中文翻译映射
 *
 * 将英文工具描述翻译为中文，用于前端 UI 显示。
 * key 为去掉 mcp__<serverId>__ 前缀的纯工具名。
 */

// ---------------------------------------------------------------------------
// 服务器中文名映射
// ---------------------------------------------------------------------------

export const SERVER_NAME_CN: Record<string, string> = {
  'rs-agent': '遥感核心服务',
  'rs-analysis': '时间序列分析',
  'rs-index': '光谱指数计算',
  'rs-inversion': '遥感反演',
  'rs-perception': '遥感感知与识别',
  'rs-statistics': '统计与数值计算',
};

// ---------------------------------------------------------------------------
// 工具描述中文映射（按 serverId 分组）
// ---------------------------------------------------------------------------

export const TOOL_DESC_CN: Record<string, string> = {
  // ── rs_agent（7 个）──
  rs_download: '下载卫星遥感影像。支持 Sentinel-2、Landsat-8、高分系列卫星。支持断点续跑：若任务中断，再次执行相同参数将从上次进度继续。返回下载文件列表和元数据信息。',
  rs_preprocess: '遥感影像预处理。支持辐射校正、几何校正、裁剪拼接、重采样等操作。可组合多个操作按顺序执行。',
  rs_analyze: '遥感影像智能分析。支持 NDVI/NDWI/EVI 等指数计算、地物分类、变化检测。分析完成后自动生成缩略图预览。',
  rs_visualize: '遥感影像可视化。支持缩略图生成、真彩色/假彩色合成、指数叠加显示。输出 PNG 格式图片。',
  rs_report: '生成遥感分析报告。支持 Markdown/HTML/PDF 格式。报告包含数据来源、处理流程、分析结果和可视化。',
  rs_sar_analysis: 'SAR 遥感影像分析。支持极化分解、InSAR 形变监测、建筑物提取、水体/船只检测。需要 Sentinel-1 数据。',
  rs_model_inference: '遥感深度学习模型推理。支持目标检测(YOLOv8)、语义分割(U-Net/DeepLabV3+)、变化检测(BIT/SNUNet)。自动 GPU/CPU 回退。',

  // ── rs_analysis（10 个）──
  compute_linear_trend: '计算时间序列的线性趋势（斜率和截距），使用最小二乘法拟合直线 y = a·x + b。返回斜率（>0 上升趋势，<0 下降趋势，≈0 无趋势）和截距。',
  mann_kendall_test: '执行非参数 Mann-Kendall 趋势检验，评估时间序列是否存在单调上升或下降趋势，不要求数据服从特定分布。返回趋势类型、p 值、z 统计量和 Kendall Tau。',
  sens_slope: '计算 Sen 斜率估计量，一种稳健的非参数方法，用于估计时间序列变化率的中位数，常与 Mann-Kendall 检验配合使用。',
  stl_decompose: '对时间序列进行 STL（基于 LOESS 的季节-趋势分解），将序列分解为趋势、季节和残差三个分量。需指定周期参数（如月度数据用 12）。',
  detect_change_points: '使用 PELT 算法检测时间序列中的结构变点，即统计特性发生显著变化的索引位置。支持 l1、l2、rbf 等代价模型。',
  autocorrelation_function: '计算时间序列的自相关函数（ACF），衡量序列与其滞后值的相关性，用于检测季节性、持续性和滞后依赖关系。',
  detect_seasonality_acf: '使用自相关函数（ACF）检测时间序列的主要季节性周期，搜索滞后>1处的显著峰值以识别循环模式。',
  getis_ord_gi_star: '计算栅格影像的 Getis-Ord Gi* 局部空间自相关统计量，识别高值（热点）或低值（冷点）的显著空间聚类。需指定空间权重核矩阵。',
  analyze_hotspot_direction: '分析热点图的主要方向集中趋势。统计地图中心各基本方向（北/南/东/西）上的热点像素数量，返回主要方向。',
  count_spikes_from_values: '统计数值序列中向上尖峰（spike）的数量。尖峰定义为连续有效值之间的正差值超过给定阈值的情况。',

  // ── rs_index（12 个）──
  calculate_batch_ndvi: '批量计算 NDVI（归一化植被指数），从多组近红外/红波段栅格文件计算并保存结果。公式：NDVI = (NIR - Red) / (NIR + Red)。',
  calculate_batch_ndwi: '批量计算 NDWI（归一化水体指数），从多组近红外/短波红外栅格文件计算并保存结果。公式：NDWI = (NIR - SWIR) / (NIR + SWIR)。',
  calculate_batch_ndbi: '批量计算 NDBI（归一化建筑指数），从多组短波红外/近红外栅格文件计算并保存结果。公式：NDBI = (SWIR - NIR) / (SWIR + NIR)。',
  calculate_batch_evi: '批量计算 EVI（增强植被指数），从多组近红外/红/蓝波段栅格文件计算并保存结果。可调整 G、C1、C2、L 系数。',
  calculate_batch_nbr: '批量计算 NBR（归一化燃烧比），从多组近红外/短波红外栅格文件计算并保存结果。公式：NBR = (NIR - SWIR) / (NIR + SWIR)。',
  calculate_batch_fvc: '批量计算 FVC（植被覆盖度），从多组近红外/红波段栅格文件计算并保存结果。基于 NDVI 阈值法估算植被覆盖百分比。',
  calculate_batch_wri: '批量计算 WRI（水体比值指数），从多组绿/红/近红外/短波红外栅格文件计算并保存结果。公式：WRI = (Green + Red) / (NIR + SWIR)。',
  calculate_batch_ndti: '批量计算 NDTI（归一化浊度指数），从多组红/绿波段栅格文件计算并保存结果。公式：NDTI = (Red - Green) / (Red + Green)。',
  calculate_batch_frp: '批量计算 FRP（火灾辐射功率）掩膜，从多个 FRP 栅格文件生成火灾掩膜并保存结果。可设置火灾阈值。',
  calculate_batch_ndsi: '批量计算 NDSI（归一化雪指数），从多组绿/短波红外波段栅格文件计算并保存结果。公式：NDSI = (Green - SWIR) / (Green + SWIR)。',
  calc_extreme_snow_loss_percentage_from_binary_map: '从二值栅格图计算极端冰雪流失面积的百分比。像素值 1.0 表示极端流失区域，返回流失像素占所有有效像素的比例（0.0~1.0）。',
  compute_tvdi: '计算 TVDI（温度植被干旱指数），基于 NDVI 和地表温度（LST）栅格数据，通过梯形空间方法量化土壤湿度条件。',

  // ── rs_inversion（17 个）──
  band_ratio: '波段比值法反演。通过两个波段的比值计算来提取特定地物信息或参数。',
  lst_single_channel: '单通道地表温度反演。利用单个热红外波段和大气参数估算地表温度。',
  lst_multi_channel: '多通道地表温度反演。利用多个热红外波段数据反演地表温度。',
  split_window: '劈窗法地表温度反演。使用两个相邻热红外波段（如 Landsat-8 的 10/11 波段）计算地表温度。',
  temperature_emissivity_separation: '温度-发射率分离反演。同时反演地表温度和发射率，无需预先知道发射率。',
  modis_day_night_lst: 'MODIS 昼夜地表温度反演。利用 MODIS 白天和夜间热红外数据反演地表温度。',
  ttm_lst: 'TTM 方法地表温度反演。使用温度独立热红外光谱指数方法反演地表温度。',
  calculate_mean_lst_by_ndvi: '按 NDVI 分段计算平均地表温度。将地表温度按 NDVI 区间分组统计均值。',
  calculate_max_lst_by_ndvi: '按 NDVI 分段计算最高地表温度。将地表温度按 NDVI 区间分组统计最大值。',
  ATI: '计算表观热惯性（ATI）。基于昼夜温差和反照率估算地表热惯性，用于干旱监测。',
  dual_polarization_differential: '双极化差分反演。利用微波数据的两个极化通道差分反演地表参数。',
  dual_frequency_diff: '双频率差分反演。利用两个频率的微波亮度温度差分反演地表参数。',
  multi_freq_bt: '多频率亮度温度反演。利用多个频率的微波亮度温度数据反演地表参数。',
  chang_single_param_inversion: 'Chang 单参数反演。使用单参数经验方法反演雪水当量。',
  nasa_team_sea_ice_concentration: 'NASA Team 海冰密集度反演。利用 AMSR-E 等微波数据反演海冰密集度。',
  dual_polarization_ratio: '双极化比值反演。利用微波数据的两个极化通道比值反演地表参数。',
  calculate_water_turbidity_ntu: '计算水体浊度（NTU 单位）。基于遥感反射率反演水体浊度数值。',

  // ── rs_perception（15 个）──
  threshold_segmentation: '阈值分割。对遥感影像进行阈值分割，将像素分为前景/背景两类。',
  bbox_expansion: '边界框扩展。将检测到的边界框按给定半径和地面采样距离（GSD）向外扩展。',
  count_above_threshold: '统计超过阈值的像素数量。计算影像中大于指定阈值的像素个数。',
  count_skeleton_contours: '统计骨架轮廓数量。提取影像骨架并计算轮廓连通域数量。',
  bboxes2centroids: '边界框转中心点。将边界框列表转换为对应的中心坐标列表。',
  centroid_distance_extremes: '计算中心点距离极值。计算中心点集合间的最小和最大距离。',
  calculate_bbox_area: '计算边界框面积。计算边界框面积，可选指定地面采样距离以获得真实面积。',
  get_model_output: '获取遥感模型推理输出。调用指定遥感 AI 模（如目标检测/分割）对影像进行推理。',
  MSCN: '计算 MSCN（均值减去归一化对比度）系数，用于影像质量评估。',
  RemoteCLIP: 'RemoteCLIP 遥感图文检索。使用 RemoteCLIP 模型进行遥感影像与文本描述的匹配检索。',
  Strip_R_CNN: 'Strip R-CNN 目标检测。使用 Strip R-CNN 模型检测遥感影像中的条状目标（如桥梁、跑道）。',
  SM3Det: 'SM3Det 多模态检测。使用 SM3Det 模型进行文本引导的遥感目标检测。',
  RemoteSAM: 'RemoteSAM 遥感分割。使用 RemoteSAM 模型进行文本引导的遥感影像语义分割。',
  InstructSAM: 'InstructSAM 指令分割。使用 InstructSAM 模型根据文本指令对遥感影像进行分割。',
  SAM2: 'SAM2 分割一切。使用 SAM2 模型根据边界框提示对遥感影像进行分割。',
  ChangeOS: 'ChangeOS 变化检测与分割。使用 ChangeOS 模型对前后时相影像进行变化检测和分割。',

  // ── rs_statistics（50 个）──
  coefficient_of_variation: '计算变异系数（CV）。变异系数定义为标准差与均值的比值，是归一化的离散程度度量。',
  skewness: '计算数据集的偏度。偏度衡量概率分布的不对称性：正值表示右偏长尾，负值表示左偏长尾，零值表示对称分布。',
  kurtosis: '计算数据集的峰度。峰度衡量概率分布尾部极端值的程度。Fisher 峰度减去 3，使正态分布峰度为 0。',
  calc_single_image_mean: '计算单幅栅格影像的均值。返回所有像素的平均值。',
  calc_batch_image_mean: '批量计算多幅栅格影像的均值。返回每幅影像的均值列表。',
  calc_single_image_std: '计算单幅栅格影像的标准差。返回所有像素的标准差。',
  calc_batch_image_std: '批量计算多幅栅格影像的标准差。返回每幅影像的标准差列表。',
  calc_single_image_median: '计算单幅栅格影像的中位数。返回所有像素的中位数值。',
  calc_batch_image_median: '批量计算多幅栅格影像的中位数。返回每幅影像的中位数列表。',
  calc_single_image_min: '计算单幅栅格影像的最小值。返回所有像素的最小值。',
  calc_batch_image_min: '批量计算多幅栅格影像的最小值。返回每幅影像的最小值列表。',
  calc_single_image_max: '计算单幅栅格影像的最大值。返回所有像素的最大值。',
  calc_batch_image_max: '批量计算多幅栅格影像的最大值。返回每幅影像的最大值列表。',
  calc_single_image_skewness: '计算单幅栅格影像的偏度。返回像素值分布的偏度系数。',
  calc_batch_image_skewness: '批量计算多幅栅格影像的偏度。返回每幅影像的偏度列表。',
  calc_single_image_kurtosis: '计算单幅栅格影像的峰度。返回像素值分布的峰度系数。',
  calc_batch_image_kurtosis: '批量计算多幅栅格影像的峰度。返回每幅影像的峰度列表。',
  calc_single_image_sum: '计算单幅栅格影像的像素总和。返回所有像素值的累加结果。',
  calc_batch_image_sum: '批量计算多幅栅格影像的像素总和。返回每幅影像的像素总和列表。',
  calc_single_image_hotspot_percentage: '计算单幅栅格影像的热点百分比。统计超过阈值的像素占总像素的比例。',
  calc_batch_image_hotspot_percentage: '批量计算多幅栅格影像的热点百分比。返回每幅影像的热点比例列表。',
  calc_single_image_hotspot_tif: '提取单幅栅格影像的热点区域并保存为 TIF。将超过阈值的像素标记输出。',
  calc_batch_image_hotspot_tif: '批量提取多幅栅格影像的热点区域并保存为 TIF。',
  difference: '计算两个数值的差值。返回 a - b 的结果。',
  division: '计算两个数值的商。返回 a / b 的结果。',
  percentage_change: '计算百分比变化率。返回从 b 到 a 的变化百分比。',
  kelvin_to_celsius: '将开尔文温度转换为摄氏度。公式：°C = K - 273.15。',
  celsius_to_kelvin: '将摄氏度转换为开尔文温度。公式：K = °C + 273.15。',
  max_value_and_index: '查找列表中的最大值及其索引位置。',
  min_value_and_index: '查找列表中的最小值及其索引位置。',
  multiply: '计算两个数值的乘积。返回 a × b 的结果。',
  ceil_number: '向上取整。返回大于或等于给定数值的最小整数。',
  get_list_object_via_indexes: '按索引列表从列表中提取对应元素。返回指定索引位置的子列表。',
  mean: '计算数值列表的算术平均值。',
  calculate_threshold_ratio: '计算影像中超过/低于阈值的像素比例。支持单幅或批量影像。',
  calc_single_image_fire_pixels: '计算单幅影像中的火灾像素数量。统计 FRP 值超过阈值的像素个数。',
  calc_batch_fire_pixels: '批量计算多幅影像中的火灾像素数量。返回每幅影像的火灾像素数列表。',
  create_fire_increase_map: '生成火灾增长地图。基于变化影像和阈值标识火灾增长区域。',
  identify_fire_prone_areas: '识别火灾易发区域。基于百分位数阈值提取火灾高风险区域。',
  get_percentile_value_from_image: '获取影像的指定百分位数值。',
  image_division_mean: '计算两幅影像或同一影像两个波段的比值均值。',
  calculate_intersection_percentage: '计算两个条件同时满足的像素交集百分比。',
  calc_batch_image_mean_mean: '批量计算多幅影像均值的均值。返回所有影像均值的平均值。',
  calc_batch_image_mean_max: '批量计算多幅影像均值中的最大值。返回所有影像均值中的最大均值。',
};

// ---------------------------------------------------------------------------
// 参数描述中文映射（通用关键词）
// ---------------------------------------------------------------------------

export const PARAM_DESC_CN: Record<string, string> = {
  'sensor': '传感器名称',
  'aoi': '感兴趣区域 (GeoJSON 格式)',
  'start_date': '起始日期 (YYYY-MM-DD)',
  'end_date': '结束日期 (YYYY-MM-DD)',
  'max_cloud_cover': '最大云覆盖百分比 (默认 20)',
  'output_dir': '输出目录',
  'input_path': '输入影像路径或目录',
  'input_nir_path': '近红外波段 (NIR) 影像路径',
  'input_red_path': '红波段影像路径',
  'input_blue_path': '蓝波段影像路径',
  'input_green_path': '绿波段影像路径',
  'input_swir_path': '短波红外波段 (SWIR) 影像路径',
  'input_frp_path': '火灾辐射功率 (FRP) 影像路径',
  'operations': '预处理操作列表（按顺序执行）',
  'analysis_type': '分析类型',
  'vis_type': '可视化类型 (默认缩略图)',
  'params': '操作/分析参数',
  'task_type': '推理任务类型',
  'model_name': '模型名称 (默认自动选择)',
  'format': '报告格式 (默认 Markdown)',
  'title': '报告标题',
  'summary': '报告摘要',
  'task_ids': '任务 ID 列表',
  'output_path': '输出文件路径',
  'x': '输入数据值列表',
  'y': '因变量（时间序列数据）',
  'signal': '输入时间序列数据',
  'values': '输入数值序列',
  'period': '周期长度（如月度数据用 12）',
  'nlags': '自相关滞后期数 (默认 20)',
  'min_acf': 'ACF 显著性阈值 (默认 0.3)',
  'penalty': '变点检测惩罚值（越大越保守）',
  'model': '代价模型类型 (l1/l2/rbf)',
  'ddof': '自由度修正 (0=总体标准差, 1=样本标准差)',
  'bias': '是否使用有偏估计 (默认 True)',
  'fisher': '是否使用 Fisher 峰度 (默认 True)',
  'threshold': '阈值',
  'spike_threshold': '尖峰检测阈值 (默认 0.1)',
  'image_path': '影像路径',
  'file_path': '文件路径',
  'file_list': '文件列表',
  'uint8': '是否将数据转换为 uint8',
  'hotspot_map_path': '热点地图路径',
  'weight_matrix': '空间权重核矩阵',
  'ndvi_path': 'NDVI 影像路径',
  'lst_path': '地表温度 (LST) 影像路径',
  'ndvi_min': '最小 NDVI 值（非植被阈值, 默认 0.1）',
  'ndvi_max': '最大 NDVI 值（全植被阈值, 默认 0.9）',
  'fire_threshold': '火灾检测阈值 (默认 0)',
  'binary_map_path': '二值栅格图路径',
  'input_nir_paths': '近红外波段影像路径列表',
  'input_red_paths': '红波段影像路径列表',
  'input_blue_paths': '蓝波段影像路径列表',
  'input_green_paths': '绿波段影像路径列表',
  'input_swir_paths': '短波红外波段影像路径列表',
  'input_frp_paths': 'FRP 影像路径列表',
  'output_paths': '输出路径列表',
  'indexes': '索引列表',
  'input_list': '输入列表',
  'input_image_path': '输入影像路径',
  'bboxes': '边界框列表',
  'centroids': '中心点列表',
  'gsd': '地面采样距离 (米/像素)',
  'radius': '扩展半径',
  'text_prompt': '文本提示',
  'bbox': '边界框',
  'pre_image_path': '前时相影像路径',
  'post_image_path': '后时相影像路径',
  'percentage': '百分位数',
  'path1': '影像路径 1',
  'path2': '影像路径 2',
  'threshold1': '阈值 1',
  'threshold2': '阈值 2',
  'a': '数值 a',
  'b': '数值 b',
  'kelvin': '开尔文温度',
  'celsius': '摄氏温度',
  'n': '数值',
  'band1': '波段 1',
  'band2': '波段 2',
  'mode': '计算模式 (above/below)',
  'band_index': '波段索引 (默认 0)',
  'change_image_path': '变化影像路径',
  'threshold_percentile': '百分位阈值 (默认 75)',
  'red_path': '红波段影像路径',
  'nir_path': '近红外波段影像路径',
};

// ---------------------------------------------------------------------------
// 类型翻译映射
// ---------------------------------------------------------------------------

export const TYPE_CN: Record<string, string> = {
  'stdio': '标准输入输出',
  'http': 'HTTP 网络服务',
};

// ---------------------------------------------------------------------------
// 工具函数：从完整工具名中提取纯名
// ---------------------------------------------------------------------------

export function extractToolName(fullName: string): string {
  // mcp__<serverId>__<toolName> → <toolName>
  const parts = fullName.split('__');
  return parts.length >= 3 ? parts[2] : fullName;
}

export function extractServerId(fullName: string): string {
  // mcp__<serverId>__<toolName> → <serverId>
  const parts = fullName.split('__');
  return parts.length >= 3 ? parts[1] : '';
}

// ---------------------------------------------------------------------------
// 获取中文描述（优先使用翻译，无则回退原文）
// ---------------------------------------------------------------------------

export function getToolDescCN(fullName: string, originalDesc: string): string {
  const toolName = extractToolName(fullName);
  const cn = TOOL_DESC_CN[toolName];
  if (cn) return cn;
  // 如果原文已经是中文，直接返回
  if (originalDesc && /[\u4e00-\u9fff]/.test(originalDesc)) return originalDesc;
  return originalDesc || '暂无描述';
}

export function getServerNameCN(serverId: string): string {
  return SERVER_NAME_CN[serverId] || serverId;
}

export function getParamDescCN(paramName: string, originalDesc: string): string {
  const cn = PARAM_DESC_CN[paramName];
  if (cn) return cn;
  // 如果原文已经是中文，直接返回
  if (originalDesc && /[\u4e00-\u9fff]/.test(originalDesc)) return originalDesc;
  return originalDesc || '';
}