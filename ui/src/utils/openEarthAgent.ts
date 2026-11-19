/**
 * OpenEarthAgent 前端服务层
 *
 * 提供对后端 OpenEarthAgent API 的封装：
 * - routeTask - 任务路由判定
 * - decomposeTask - 任务分解
 * - orchestrateTask - 执行编排
 * - getTaskStatus - 查询任务状态
 * - searchKnowledge - 知识库搜索
 * - Knowledge CRUD - 知识库管理
 */

import { authenticatedFetch } from "./api";

export type ExecutionMode = "standard" | "open_earth" | "mixed";

export type TaskRouteResponse = {
  task_id: string;
  route: ExecutionMode;
  score: number;
  reasons: string[];
  explanation: string;
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

export type KnowledgeEntryType =
  | "geoknowledge"
  | "tool_doc"
  | "tool_fallback"
  | "best_practice"
  | "workflow"
  | "faq"
  | "custom";

export type KnowledgeEntry = {
  entry_id: string;
  entry_type: KnowledgeEntryType;
  title: string;
  content: string;
  tags: string[];
  metadata: Record<string, unknown>;
  importance: number;
  created_at: string;
  updated_at: string;
  access_count: number;
  last_accessed_at?: string;
  is_active: boolean;
  version: number;
};

export type KnowledgeSearchResult = KnowledgeEntry & {
  score: number;
  search_mode: "vector" | "keyword";
};

export type KnowledgeStats = {
  total_entries: number;
  entries_by_type: Record<string, number>;
  total_accesses: number;
  entry_types: KnowledgeEntryType[];
};

export type KnowledgeListResponse = {
  entries: KnowledgeEntry[];
  total: number;
  limit: number;
  offset: number;
  entry_types: KnowledgeEntryType[];
};

export type TaskStatusResponse = {
  task_id: string;
  status: "pending" | "running" | "completed" | "failed" | "unknown";
  progress: number;
  current_step?: string;
  dag_nodes?: DagNode[];
  logs?: Array<{
    timestamp: number;
    level: string;
    message: string;
  }>;
};

export async function routeTask(
  taskDescription: string,
  options?: {
    input_data_meta?: Record<string, unknown>;
    manual_override?: ExecutionMode;
  },
): Promise<TaskRouteResponse> {
  const response = await authenticatedFetch("/api/open-earth/route", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      task_description: taskDescription,
      input_data_meta: options?.input_data_meta,
      manual_override: options?.manual_override,
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Task routing failed: ${text}`);
  }

  return response.json();
}

export async function decomposeTask(
  taskDescription: string,
  options?: {
    context?: Record<string, unknown>;
    force_steps?: Array<{
      name: string;
      tool?: string;
      execution_mode?: string;
      dependencies?: string[];
    }>;
  },
): Promise<TaskDecomposeResponse> {
  const response = await authenticatedFetch("/api/open-earth/decompose", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      task_description: taskDescription,
      context: options?.context,
      force_steps: options?.force_steps,
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Task decomposition failed: ${text}`);
  }

  return response.json();
}

export async function orchestrateTask(
  taskDescription: string,
  options?: {
    task_id?: string;
    steps?: TaskStep[];
    workspace_id?: string;
    config?: {
      use_mock_bridge?: boolean;
      cache_backend?: string;
      max_parallel?: number;
      enable_fallback?: boolean;
    };
  },
): Promise<OrchestrateResponse> {
  const response = await authenticatedFetch("/api/open-earth/orchestrate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      task_id: options?.task_id,
      task_description: taskDescription,
      steps: options?.steps,
      workspace_id: options?.workspace_id,
      config: options?.config,
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Task orchestration failed: ${text}`);
  }

  return response.json();
}

export async function getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  const response = await authenticatedFetch(`/api/open-earth/status/${encodeURIComponent(taskId)}`);

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Get task status failed: ${text}`);
  }

  return response.json();
}

export async function getKnowledgeStats(): Promise<KnowledgeStats> {
  const response = await authenticatedFetch("/api/open-earth/knowledge/stats");
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Get knowledge stats failed: ${text}`);
  }
  return response.json();
}

export async function listKnowledgeEntries(
  options?: {
    type?: KnowledgeEntryType;
    tag?: string;
    search?: string;
    limit?: number;
    offset?: number;
    include_inactive?: boolean;
  },
): Promise<KnowledgeListResponse> {
  const params = new URLSearchParams();
  if (options?.type) params.set("type", options.type);
  if (options?.tag) params.set("tag", options.tag);
  if (options?.search) params.set("search", options.search);
  if (options?.limit) params.set("limit", String(options.limit));
  if (options?.offset) params.set("offset", String(options.offset));
  if (options?.include_inactive) params.set("include_inactive", "true");

  const query = params.toString();
  const url = `/api/open-earth/knowledge${query ? `?${query}` : ""}`;

  const response = await authenticatedFetch(url);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`List knowledge entries failed: ${text}`);
  }
  return response.json();
}

export async function getKnowledgeEntry(entryId: string): Promise<KnowledgeEntry> {
  const response = await authenticatedFetch(`/api/open-earth/knowledge/${encodeURIComponent(entryId)}`);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Get knowledge entry failed: ${text}`);
  }
  return response.json();
}

export async function createKnowledgeEntry(
  data: Partial<KnowledgeEntry> & {
    entry_type: KnowledgeEntryType;
    title: string;
    content: string;
  },
): Promise<KnowledgeEntry> {
  const response = await authenticatedFetch("/api/open-earth/knowledge", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Create knowledge entry failed: ${text}`);
  }
  return response.json();
}

export async function updateKnowledgeEntry(
  entryId: string,
  data: Partial<KnowledgeEntry>,
): Promise<KnowledgeEntry> {
  const response = await authenticatedFetch(`/api/open-earth/knowledge/${encodeURIComponent(entryId)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Update knowledge entry failed: ${text}`);
  }
  return response.json();
}

export async function deleteKnowledgeEntry(entryId: string): Promise<{ success: boolean; entry_id: string }> {
  const response = await authenticatedFetch(`/api/open-earth/knowledge/${encodeURIComponent(entryId)}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Delete knowledge entry failed: ${text}`);
  }
  return response.json();
}

export async function searchKnowledge(
  query: string,
  options?: {
    limit?: number;
    mode?: "hybrid" | "vector" | "keyword";
  },
): Promise<KnowledgeSearchResult[]> {
  const response = await authenticatedFetch("/api/open-earth/knowledge/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      limit: options?.limit ?? 10,
      mode: options?.mode ?? "hybrid",
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Knowledge search failed: ${text}`);
  }

  const data = await response.json();
  return data.results ?? [];
}

export async function exportKnowledge(
  entryIds?: string[],
): Promise<{ entries: KnowledgeEntry[]; count: number; exported_at: string }> {
  const response = await authenticatedFetch("/api/open-earth/knowledge/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ entry_ids: entryIds }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Export knowledge failed: ${text}`);
  }
  return response.json();
}

export async function importKnowledge(
  entries: KnowledgeEntry[],
  options?: { overwrite?: boolean },
): Promise<{ imported: number; total: number }> {
  const response = await authenticatedFetch("/api/open-earth/knowledge/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      entries,
      overwrite: options?.overwrite ?? false,
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Import knowledge failed: ${text}`);
  }
  return response.json();
}

export async function rebuildKnowledgeIndex(): Promise<{
  success: boolean;
  stats: { document_count: number; vocab_size: number };
}> {
  const response = await authenticatedFetch("/api/open-earth/knowledge/rebuild-index", {
    method: "POST",
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Rebuild knowledge index failed: ${text}`);
  }
  return response.json();
}

export async function enhanceWithKnowledge(
  query: string,
  options?: {
    limit?: number;
  },
): Promise<{
  context: Array<{
    title: string;
    content: string;
    type: string;
    score: number;
    tags: string[];
  }>;
  enhanced: boolean;
  query: string;
}> {
  const response = await authenticatedFetch("/api/open-earth/knowledge/enhance", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      limit: options?.limit ?? 5,
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Knowledge enhancement failed: ${text}`);
  }
  return response.json();
}
