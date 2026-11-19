/**
 * DagVisualizer - DAG 工作流可视化组件
 *
 * 展示 OpenEarthAgent 编排的工作流 DAG 图，包括：
 * - 节点状态（待处理/运行中/成功/失败）
 * - 执行模式（MCP 工具 / 沙箱代码）
 * - 依赖关系连线
 * - 并行分组标识
 * - 执行时长和输出
 */

import { useState } from 'react';
import {
  Play,
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  Wrench,
  Code,
  GitBranch,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  FileOutput,
} from 'lucide-react';
import { cn } from '../../lib/utils.js';
import type { DagNode } from '../../utils/openEarthAgent';

type NodeStatus = DagNode['status'];

const STATUS_CONFIG: Record<NodeStatus, {
  label: string;
  color: string;
  bgColor: string;
  borderColor: string;
  icon: typeof Play;
}> = {
  pending: {
    label: '待处理',
    color: 'text-zinc-500',
    bgColor: 'bg-zinc-100 dark:bg-zinc-700',
    borderColor: 'border-zinc-300 dark:border-zinc-600',
    icon: Clock,
  },
  running: {
    label: '运行中',
    color: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-100 dark:bg-blue-900/30',
    borderColor: 'border-blue-500 dark:border-blue-400',
    icon: Loader2,
  },
  completed: {
    label: '成功',
    color: 'text-green-600 dark:text-green-400',
    bgColor: 'bg-green-100 dark:bg-green-900/30',
    borderColor: 'border-green-500 dark:border-green-400',
    icon: CheckCircle2,
  },
  failed: {
    label: '失败',
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-100 dark:bg-red-900/30',
    borderColor: 'border-red-500 dark:border-red-400',
    icon: XCircle,
  },
  skipped: {
    label: '已跳过',
    color: 'text-gray-500 dark:text-gray-400',
    bgColor: 'bg-gray-100 dark:bg-gray-800',
    borderColor: 'border-gray-300 dark:border-gray-600',
    icon: AlertCircle,
  },
};

const EXECUTION_MODE_CONFIG: Record<string, {
  label: string;
  color: string;
  bgColor: string;
  icon: typeof Wrench;
}> = {
  mcp: {
    label: 'MCP 工具',
    color: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-100 dark:bg-blue-900/20',
    icon: Wrench,
  },
  sandbox: {
    label: '沙箱代码',
    color: 'text-purple-600 dark:text-purple-400',
    bgColor: 'bg-purple-100 dark:bg-purple-900/20',
    icon: Code,
  },
  mixed: {
    label: '混合模式',
    color: 'text-green-600 dark:text-green-400',
    bgColor: 'bg-green-100 dark:bg-green-900/20',
    icon: GitBranch,
  },
};

type Props = {
  nodes: DagNode[];
  title?: string;
  onNodeClick?: (node: DagNode) => void;
  expanded?: boolean;
  showDuration?: boolean;
};

export default function DagVisualizer({
  nodes,
  title = '工作流 DAG',
  onNodeClick,
  expanded: initialExpanded = true,
  showDuration = true,
}: Props) {
  const [expanded, setExpanded] = useState(initialExpanded);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  if (nodes.length === 0) {
    return (
      <div className="rounded-xl border border-zinc-200 bg-white p-8 text-center dark:border-zinc-700 dark:bg-zinc-800">
        <GitBranch className="mx-auto mb-3 h-10 w-10 text-zinc-400" />
        <p className="text-sm text-zinc-500 dark:text-zinc-400">暂无工作流数据</p>
      </div>
    );
  }

  const groupedNodes = groupByParallelGroup(nodes);
  const selectedNode = nodes.find((n) => n.node_id === selectedNodeId);

  const succeeded = nodes.filter((n) => n.status === 'completed').length;
  const failed = nodes.filter((n) => n.status === 'failed').length;
  const running = nodes.filter((n) => n.status === 'running').length;
  const totalDuration = nodes.reduce((sum, n) => sum + (n.duration_ms ?? 0), 0);

  return (
    <div className="rounded-xl border border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-800">
      {/* 头部 */}
      <div
        className="flex items-center gap-3 px-4 py-3 cursor-pointer border-b border-zinc-200 dark:border-zinc-700"
        onClick={() => setExpanded(!expanded)}
      >
        <GitBranch className="h-5 w-5 text-purple-500" />
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            {title}
          </h3>
          <div className="flex items-center gap-3 mt-0.5">
            <span className="text-xs text-zinc-500 dark:text-zinc-400">
              共 {nodes.length} 个步骤
            </span>
            <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
              <CheckCircle2 className="h-3 w-3" />
              {succeeded} 成功
            </span>
            {failed > 0 && (
              <span className="flex items-center gap-1 text-xs text-red-600 dark:text-red-400">
                <XCircle className="h-3 w-3" />
                {failed} 失败
              </span>
            )}
            {running > 0 && (
              <span className="flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400">
                <Loader2 className="h-3 w-3 animate-spin" />
                {running} 运行中
              </span>
            )}
            {showDuration && totalDuration > 0 && (
              <span className="text-xs text-zinc-400">
                总耗时 {formatDuration(totalDuration)}
              </span>
            )}
          </div>
        </div>
        {expanded ? (
          <ChevronUp className="h-4 w-4 text-zinc-400" />
        ) : (
          <ChevronDown className="h-4 w-4 text-zinc-400" />
        )}
      </div>

      {/* DAG 图 */}
      {expanded && (
        <div className="p-4">
          <div className="space-y-4">
            {groupedNodes.map((group, groupIdx) => (
              <div key={groupIdx}>
                {group.label && (
                  <div className="mb-2 flex items-center gap-2">
                    <div className="h-px flex-1 bg-zinc-200 dark:bg-zinc-700" />
                    <span className="px-2 text-xs font-medium text-zinc-500">
                      {group.label}
                    </span>
                    <div className="h-px flex-1 bg-zinc-200 dark:bg-zinc-700" />
                  </div>
                )}

                <div
                  className={cn(
                    'grid gap-2',
                    group.nodes.length === 1 ? 'grid-cols-1' : 'grid-cols-2'
                  )}
                >
                  {group.nodes.map((node) => (
                    <DagNodeCard
                      key={node.node_id}
                      node={node}
                      isSelected={selectedNodeId === node.node_id}
                      onClick={() => {
                        setSelectedNodeId(
                          selectedNodeId === node.node_id ? null : node.node_id
                        );
                        onNodeClick?.(node);
                      }}
                      showDuration={showDuration}
                    />
                  ))}
                </div>

                {groupIdx < groupedNodes.length - 1 && (
                  <div className="flex justify-center py-2">
                    <div className="h-6 w-px bg-zinc-300 dark:bg-zinc-600" />
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* 选中节点详情 */}
          {selectedNode && (
            <div className="mt-4 rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-600 dark:bg-zinc-900">
              <h4 className="mb-2 text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                步骤详情
              </h4>
              <div className="space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-zinc-500">节点 ID</span>
                  <span className="font-mono text-zinc-700 dark:text-zinc-300">
                    {selectedNode.node_id}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-500">工具 ID</span>
                  <span className="font-mono text-zinc-700 dark:text-zinc-300">
                    {selectedNode.tool_id || 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-500">依赖</span>
                  <span className="font-mono text-zinc-700 dark:text-zinc-300">
                    {selectedNode.dependencies.length > 0
                      ? selectedNode.dependencies.join(', ')
                      : '无'}
                  </span>
                </div>
                {selectedNode.output && (
                  <div className="mt-2 flex items-start gap-1.5 rounded bg-white p-2 dark:bg-zinc-800">
                    <FileOutput className="mt-0.5 h-3 w-3 flex-shrink-0 text-green-500" />
                    <span className="text-zinc-600 dark:text-zinc-400">
                      {selectedNode.output}
                    </span>
                  </div>
                )}
                {selectedNode.error && (
                  <div className="mt-2 flex items-start gap-1.5 rounded bg-red-50 p-2 dark:bg-red-900/20">
                    <AlertCircle className="mt-0.5 h-3 w-3 flex-shrink-0 text-red-500" />
                    <span className="text-red-700 dark:text-red-300">
                      {selectedNode.error}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 图例 */}
          <div className="mt-4 flex flex-wrap gap-4 border-t border-zinc-200 pt-3 text-xs dark:border-zinc-700">
            <div className="flex items-center gap-1.5">
              <div className="h-3 w-3 rounded bg-blue-100 dark:bg-blue-900/30" />
              <span className="text-zinc-500">MCP 工具</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="h-3 w-3 rounded bg-purple-100 dark:bg-purple-900/30" />
              <span className="text-zinc-500">沙箱代码</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="h-3 w-3 rounded-full bg-green-500" />
              <span className="text-zinc-500">成功</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="h-3 w-3 rounded-full bg-red-500" />
              <span className="text-zinc-500">失败</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="h-3 w-3 rounded-full bg-blue-500 animate-pulse" />
              <span className="text-zinc-500">运行中</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function DagNodeCard({
  node,
  isSelected,
  onClick,
  showDuration,
}: {
  node: DagNode;
  isSelected: boolean;
  onClick: () => void;
  showDuration: boolean;
}) {
  const statusConfig = STATUS_CONFIG[node.status];
  const modeConfig = EXECUTION_MODE_CONFIG[node.execution_mode] ?? EXECUTION_MODE_CONFIG.mcp;
  const StatusIcon = statusConfig.icon;
  const ModeIcon = modeConfig.icon;

  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full rounded-lg border p-3 text-left transition-all hover:shadow-md',
        statusConfig.borderColor,
        isSelected && 'ring-2 ring-offset-2 ring-blue-500 dark:ring-offset-zinc-800'
      )}
    >
      {/* 顶部：状态 + 执行模式 */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-1.5">
          <StatusIcon
            className={cn(
              'h-4 w-4',
              statusConfig.color,
              node.status === 'running' && 'animate-spin'
            )}
          />
          <span className={cn('text-xs font-medium', statusConfig.color)}>
            {statusConfig.label}
          </span>
        </div>
        <div
          className={cn(
            'flex items-center gap-1 rounded-full px-1.5 py-0.5',
            modeConfig.bgColor
          )}
        >
          <ModeIcon className={cn('h-2.5 w-2.5', modeConfig.color)} />
          <span className={cn('text-[10px] font-medium', modeConfig.color)}>
            {modeConfig.label}
          </span>
        </div>
      </div>

      {/* 中间：步骤信息 */}
      <div className="mb-1.5">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-zinc-400">
            #{node.step_number}
          </span>
          <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100 truncate">
            {node.description}
          </span>
        </div>
      </div>

      {/* 底部：工具 ID + 时长 */}
      <div className="flex items-center justify-between text-xs text-zinc-500 dark:text-zinc-400">
        {node.tool_id ? (
          <span className="font-mono truncate max-w-[150px]">
            {node.tool_id}
          </span>
        ) : (
          <span className="italic">自定义代码</span>
        )}
        {showDuration && node.duration_ms !== undefined && (
          <span>{formatDuration(node.duration_ms)}</span>
        )}
      </div>

      {/* 并行标签 */}
      {node.is_parallel && node.parallel_group && (
        <div className="mt-2">
          <span className="inline-flex items-center gap-1 rounded bg-zinc-100 px-1.5 py-0.5 text-[10px] text-zinc-600 dark:bg-zinc-700 dark:text-zinc-300">
            <GitBranch className="h-2.5 w-2.5" />
            并行组: {node.parallel_group}
          </span>
        </div>
      )}
    </button>
  );
}

function groupByParallelGroup(nodes: DagNode[]): Array<{
  label?: string;
  nodes: DagNode[];
}> {
  const sorted = [...nodes].sort((a, b) => a.step_number - b.step_number);

  const groups: Array<{ label?: string; nodes: DagNode[] }> = [];
  let currentGroup: DagNode[] = [];
  let currentLabel: string | undefined;

  for (const node of sorted) {
    const nodeLabel = node.is_parallel && node.parallel_group
      ? `并行执行 · ${node.parallel_group}`
      : undefined;

    if (currentLabel === nodeLabel && currentGroup.length > 0) {
      currentGroup.push(node);
    } else {
      if (currentGroup.length > 0) {
        groups.push({ label: currentLabel, nodes: currentGroup });
      }
      currentGroup = [node];
      currentLabel = nodeLabel;
    }
  }

  if (currentGroup.length > 0) {
    groups.push({ label: currentLabel, nodes: currentGroup });
  }

  return groups;
}

function formatDuration(ms: number): string {
  if (ms < 1000) {
    return `${ms}ms`;
  }
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) {
    return `${seconds}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
}
