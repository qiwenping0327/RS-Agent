/**
 * OpenEarthAgent HTTP API Router
 *
 * 提供 OpenEarthAgent 相关的 REST API 端点：
 * - POST /api/open-earth/route    - 任务路由判定
 * - POST /api/open-earth/decompose - 任务分解
 * - POST /api/open-earth/orchestrate - 执行编排
 * - GET  /api/open-earth/status/:taskId - 查询任务状态
 *
 * 当前使用 Mock 模式，后续可替换为真实 Python 后端调用。
 */

import type { IncomingMessage, ServerResponse } from "node:http";
import { readJsonBody, sendJson, isAuthorized } from "./httpRouter.js";

export type TaskRouteRequest = {
  task_description: string;
  input_data_meta?: Record<string, unknown>;
  manual_override?: "standard" | "open_earth" | "mixed";
};

export type TaskRouteResponse = {
  task_id: string;
  route: string;
  score: number;
  reasons: string[];
  explanation: string;
};

export type TaskDecomposeRequest = {
  task_description: string;
  context?: Record<string, unknown>;
  force_steps?: Array<{
    name: string;
    tool?: string;
    execution_mode?: string;
    dependencies?: string[];
  }>;
};

export type TaskStep = {
  step_id: string;
  step_number: number;
  description: string;
  tool_name?: string;
  tool_id?: string;
  execution_mode: "mcp" | "sandbox" | "mixed";
  dependencies: string[];
  reasoning?: string;
};

export type TaskDecomposeResponse = {
  task_id: string;
  steps: TaskStep[];
  total_steps: number;
};

export type OrchestrateRequest = {
  task_id?: string;
  task_description: string;
  steps?: TaskStep[];
  workspace_id?: string;
  config?: {
    use_mock_bridge?: boolean;
    cache_backend?: string;
    max_parallel?: number;
    enable_fallback?: boolean;
  };
};

export type DagNode = {
  node_id: string;
  step_number: number;
  description: string;
  tool_id?: string;
  execution_mode: string;
  status: "pending" | "running" | "completed" | "failed" | "skipped";
  dependencies: string[];
  output?: string;
  error?: string;
  duration_ms?: number;
  is_parallel?: boolean;
  parallel_group?: string;
};

export type OrchestrateResponse = {
  task_id: string;
  status: "success" | "failed" | "partial";
  dag_nodes: DagNode[];
  succeeded_count: number;
  failed_count: number;
  total_duration_ms: number;
  output_files?: string[];
  memory_summary?: Record<string, unknown>;
};

export type StatusResponse = {
  task_id: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  current_step?: string;
  dag_nodes?: DagNode[];
  logs?: Array<{
    timestamp: number;
    level: string;
    message: string;
  }>;
};

type OpenEarthApiOptions = {
  token: string;
  /** 是否使用 Mock 模式（默认 true） */
  use_mock?: boolean;
  /** Python 后端 URL（如果使用真实后端） */
  python_backend_url?: string;
};

const TASK_MEMORY = new Map<string, StatusResponse>();

export async function handleOpenEarthApiRequest(
  request: IncomingMessage,
  response: ServerResponse,
  options: OpenEarthApiOptions,
): Promise<boolean> {
  const url = new URL(request.url ?? "/", "http://127.0.0.1");
  if (!url.pathname.startsWith("/api/open-earth/")) {
    return false;
  }

  if (!isAuthorized(request, options.token)) {
    sendJson(response, 401, {
      error: { code: "unauthorized", message: "missing or invalid token" },
    });
    return true;
  }

  const path = url.pathname;

  try {
    if (path === "/api/open-earth/route" && request.method === "POST") {
      return await handleRoute(request, response, options);
    }
    if (path === "/api/open-earth/decompose" && request.method === "POST") {
      return await handleDecompose(request, response, options);
    }
    if (path === "/api/open-earth/orchestrate" && request.method === "POST") {
      return await handleOrchestrate(request, response, options);
    }
    if (path.startsWith("/api/open-earth/status/") && request.method === "GET") {
      return handleStatus(path, response, options);
    }
    if (path === "/api/open-earth/knowledge/search" && request.method === "POST") {
      return await handleKnowledgeSearch(request, response, options);
    }
  } catch (error) {
    sendJson(response, 500, {
      error: {
        code: "internal_error",
        message: error instanceof Error ? error.message : String(error),
      },
    });
    return true;
  }

  sendJson(response, 404, {
    error: { code: "not_found", message: `No /api/open-earth route for ${path}` },
  });
  return true;
}

async function handleRoute(
  request: IncomingMessage,
  response: ServerResponse,
  options: OpenEarthApiOptions,
): Promise<boolean> {
  const body = await readJsonBody<TaskRouteRequest>(request);
  if (!body?.task_description) {
    sendJson(response, 400, {
      error: { code: "invalid_body", message: "Expected { task_description }" },
    });
    return true;
  }

  const result = mockRoute(body.task_description, body.input_data_meta, body.manual_override);
  sendJson(response, 200, result);
  return true;
}

async function handleDecompose(
  request: IncomingMessage,
  response: ServerResponse,
  options: OpenEarthApiOptions,
): Promise<boolean> {
  const body = await readJsonBody<TaskDecomposeRequest>(request);
  if (!body?.task_description) {
    sendJson(response, 400, {
      error: { code: "invalid_body", message: "Expected { task_description }" },
    });
    return true;
  }

  const result = mockDecompose(body.task_description, body.force_steps);
  sendJson(response, 200, result);
  return true;
}

async function handleOrchestrate(
  request: IncomingMessage,
  response: ServerResponse,
  options: OpenEarthApiOptions,
): Promise<boolean> {
  const body = await readJsonBody<OrchestrateRequest>(request);
  if (!body?.task_description) {
    sendJson(response, 400, {
      error: { code: "invalid_body", message: "Expected { task_description }" },
    });
    return true;
  }

  const result = mockOrchestrate(
    body.task_description,
    body.steps,
    body.workspace_id,
    body.task_id,
  );

  TASK_MEMORY.set(result.task_id, {
    task_id: result.task_id,
    status: "completed",
    progress: 100,
    dag_nodes: result.dag_nodes,
    logs: [
      { timestamp: Date.now(), level: "INFO", message: "任务执行完成" },
    ],
  });

  sendJson(response, 200, result);
  return true;
}

function handleStatus(
  path: string,
  response: ServerResponse,
  options: OpenEarthApiOptions,
): boolean {
  const taskId = path.replace("/api/open-earth/status/", "");
  const status = TASK_MEMORY.get(taskId);

  if (status) {
    sendJson(response, 200, status);
  } else {
    sendJson(response, 200, {
      task_id: taskId,
      status: "unknown",
      progress: 0,
    });
  }
  return true;
}

async function handleKnowledgeSearch(
  request: IncomingMessage,
  response: ServerResponse,
  options: OpenEarthApiOptions,
): Promise<boolean> {
  const body = await readJsonBody<{ query: string; limit?: number }>(request);
  if (!body?.query) {
    sendJson(response, 400, {
      error: { code: "invalid_body", message: "Expected { query }" },
    });
    return true;
  }

  const results = mockKnowledgeSearch(body.query, body.limit ?? 10);
  sendJson(response, 200, { results });
  return true;
}

function generateTaskId(): string {
  return `oea_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function mockRoute(
  taskDescription: string,
  inputDataMeta?: Record<string, unknown>,
  manualOverride?: string,
): TaskRouteResponse {
  const taskId = generateTaskId();
  const taskLower = taskDescription.toLowerCase();

  const complexKeywords = [
    "缓冲区", "buffer",
    "相交", "intersect",
    "擦除", "erase", "difference",
    "分区统计", "zonal",
    "栅格转矢量", "polygonize",
    "矢量转栅格", "rasterize",
    "sar", "雷达",
    "时序", "变化检测",
    "自定义波段", "多源",
  ];

  const isComplex = complexKeywords.some(
    (kw) => taskLower.includes(kw.toLowerCase()),
  );

  if (manualOverride === "standard") {
    return {
      task_id: taskId,
      route: "standard",
      score: 0,
      reasons: ["手动切换到标准模式"],
      explanation: "用户强制使用标准 MCP 工具模式",
    };
  }

  if (manualOverride === "open_earth") {
    return {
      task_id: taskId,
      route: "open_earth",
      score: 5,
      reasons: ["手动切换到 OpenEarth 增强模式"],
      explanation: "用户强制使用 OpenEarthAgent 增强模式",
    };
  }

  const reasons: string[] = [];
  let score = 0;

  if (isComplex) {
    score += 3;
    reasons.push("检测到复杂 GIS 运算需求");
  }

  if (taskDescription.includes("NDVI") || taskDescription.includes("植被指数")) {
    score += 1;
  }

  if (taskDescription.includes("NDWI") || taskDescription.includes("水体")) {
    score += 1;
  }

  if (taskDescription.includes("变化检测") || taskDescription.includes("时序")) {
    score += 2;
    reasons.push("检测到时序/变化检测需求");
  }

  const route = score >= 2 ? "open_earth" : "standard";
  const explanation = route === "open_earth"
    ? `任务复杂度评分 ${score} >= 2，建议使用 OpenEarth 增强模式`
    : `任务复杂度评分 ${score} < 2，适合使用标准 MCP 工具`;

  return {
    task_id: taskId,
    route,
    score,
    reasons,
    explanation,
  };
}

function mockDecompose(
  taskDescription: string,
  forceSteps?: TaskDecomposeRequest["force_steps"],
): TaskDecomposeResponse {
  const taskId = generateTaskId();
  const taskLower = taskDescription.toLowerCase();

  if (forceSteps && forceSteps.length > 0) {
    return {
      task_id: taskId,
      steps: forceSteps.map((s, i) => ({
        step_id: `step_${i.toString().padStart(3, "0")}`,
        step_number: i + 1,
        description: s.name,
        tool_name: s.tool,
        tool_id: s.tool ? `rs-agent.${s.tool}` : undefined,
        execution_mode: (s.execution_mode as "mcp" | "sandbox") || "mcp",
        dependencies: s.dependencies || [],
        reasoning: "用户自定义步骤",
      })),
      total_steps: forceSteps.length,
    };
  }

  const steps: TaskStep[] = [];

  const workflows: Array<{
    pattern: RegExp;
    steps: Array<{ desc: string; tool: string; deps?: number[]; mode: "mcp" | "sandbox" }>;
  }> = [
    {
      pattern: /ndvi|植被指数/,
      steps: [
        { desc: "下载影像数据", tool: "rs_download", mode: "mcp" },
        { desc: "影像预处理", tool: "rs_preprocess", deps: [0], mode: "mcp" },
        { desc: "计算 NDVI 植被指数", tool: "rs_analyze", deps: [1], mode: "mcp" },
      ],
    },
    {
      pattern: /ndwi|水体/,
      steps: [
        { desc: "下载影像数据", tool: "rs_download", mode: "mcp" },
        { desc: "影像预处理", tool: "rs_preprocess", deps: [0], mode: "mcp" },
        { desc: "计算 NDWI 水体指数", tool: "rs_analyze", deps: [1], mode: "mcp" },
      ],
    },
    {
      pattern: /变化检测|时序/,
      steps: [
        { desc: "下载时相 1 影像", tool: "rs_download", mode: "mcp" },
        { desc: "下载时相 2 影像", tool: "rs_download", mode: "mcp" },
        { desc: "时相 1 预处理", tool: "rs_preprocess", deps: [0], mode: "mcp" },
        { desc: "时相 2 预处理", tool: "rs_preprocess", deps: [1], mode: "mcp" },
        { desc: "执行变化检测", tool: "rs_analyze", deps: [2, 3], mode: "sandbox" },
      ],
    },
  ];

  let matchedSteps: typeof workflows[0]["steps"] | null = null;
  for (const wf of workflows) {
    if (wf.pattern.test(taskLower)) {
      matchedSteps = wf.steps;
      break;
    }
  }

  const finalSteps = matchedSteps ?? [
    { desc: "下载影像数据", tool: "rs_download", mode: "mcp" },
    { desc: "影像预处理", tool: "rs_preprocess", deps: [0], mode: "mcp" },
    { desc: "执行分析计算", tool: "rs_analyze", deps: [1], mode: "mcp" },
  ];

  for (let i = 0; i < finalSteps.length; i++) {
    const step = finalSteps[i];
    const deps = step.deps?.map((d) => `step_${d.toString().padStart(3, "0")}`) ?? [];

    steps.push({
      step_id: `step_${i.toString().padStart(3, "0")}`,
      step_number: i + 1,
      description: step.desc,
      tool_name: step.tool,
      tool_id: `rs-agent.${step.tool}`,
      execution_mode: step.mode,
      dependencies: deps,
      reasoning: `标准工作流步骤 ${i + 1}`,
    });
  }

  return {
    task_id: taskId,
    steps,
    total_steps: steps.length,
  };
}

function mockOrchestrate(
  taskDescription: string,
  steps?: TaskStep[],
  workspaceId?: string,
  existingTaskId?: string,
): OrchestrateResponse {
  const taskId = existingTaskId ?? generateTaskId();
  const inputSteps = steps ?? mockDecompose(taskDescription).steps;

  const dagNodes: DagNode[] = inputSteps.map((step, i) => {
    const isParallel = step.dependencies.length === 0;
    return {
      node_id: step.step_id,
      step_number: step.step_number,
      description: step.description,
      tool_id: step.tool_id,
      execution_mode: step.execution_mode,
      status: "completed",
      dependencies: step.dependencies,
      output: `${step.description} 执行成功`,
      duration_ms: Math.floor(Math.random() * 5000) + 1000,
      is_parallel: isParallel,
      parallel_group: isParallel ? "group_A" : undefined,
    };
  });

  const totalDuration = dagNodes.reduce((sum, n) => sum + (n.duration_ms ?? 0), 0);

  return {
    task_id: taskId,
    status: "success",
    dag_nodes: dagNodes,
    succeeded_count: dagNodes.length,
    failed_count: 0,
    total_duration_ms: totalDuration,
    output_files: workspaceId
      ? [
          `${workspaceId}/output/result.tif`,
          `${workspaceId}/output/report.md`,
        ]
      : undefined,
    memory_summary: {
      task_id: taskId,
      workspace_id: workspaceId,
      tool_executions: dagNodes.length,
    },
  };
}

function mockKnowledgeSearch(query: string, limit: number): Array<{
  entry_id: string;
  title: string;
  content: string;
  tags: string[];
  importance: number;
}> {
  const queryLower = query.toLowerCase();

  const allKnowledge = [
    {
      entry_id: "geo_001",
      title: "NDVI 指数计算",
      content: "NDVI = (NIR - Red) / (NIR + Red)。范围 [-1, 1]，正值表示植被。",
      tags: ["ndvi", "植被指数", "spectral"],
      importance: 5,
    },
    {
      entry_id: "geo_002",
      title: "NDWI 水体指数",
      content: "NDWI = (Green - NIR) / (Green + NIR)。用于提取水体信息。",
      tags: ["ndwi", "水体指数", "spectral"],
      importance: 5,
    },
    {
      entry_id: "geo_003",
      title: "坐标系投影转换",
      content: "WGS84 (EPSG:4326) → UTM (如 EPSG:32650)。使用 GDAL 进行转换。",
      tags: ["projection", "坐标系", "gdal"],
      importance: 5,
    },
    {
      entry_id: "geo_004",
      title: "分区统计 (Zonal Statistics)",
      content: "使用矢量图层作为分区，统计栅格值的均值、总和、最大值等。",
      tags: ["zonal", "分区统计", "statistics"],
      importance: 6,
    },
    {
      entry_id: "geo_005",
      title: "变化检测最佳实践",
      content: "确保两个时相影像物候期相近、云量低、坐标系一致、辐射归一化。",
      tags: ["change_detection", "best_practice"],
      importance: 7,
    },
  ];

  return allKnowledge
    .filter((k) => {
      const text = `${k.title} ${k.content} ${k.tags.join(" ")}`.toLowerCase();
      return text.includes(queryLower);
    })
    .slice(0, limit);
}
