/**
 * OpenEarthMode - OpenEarthAgent 增强模式页面
 *
 * 提供完整的 OpenEarthAgent 工作流界面：
 * - 模式切换（标准/OpenEarth 增强/混合）
 * - 自然语言任务输入
 * - 任务路由判定
 * - 任务分解步骤预览
 * - DAG 工作流执行和可视化
 * - 执行结果和日志展示
 */

import { useState, useCallback } from 'react';
import {
  Sparkles,
  Send,
  Loader2,
  MessageSquare,
  Lightbulb,
  Play,
  CheckCircle2,
  AlertCircle,
  RotateCcw,
  Pencil,
  Plus,
  Trash2,
  Save,
  X,
  ChevronUp,
  ChevronDown,
  BookOpen,
} from 'lucide-react';
import { cn } from '../../lib/utils.js';
import { authenticatedFetch } from '../../utils/api.js';
import OpenEarthModeToggle from './OpenEarthModeToggle';
import DagVisualizer from './DagVisualizer';
import type {
  ExecutionMode,
  TaskRouteResponse,
  TaskStep,
  DagNode,
  OrchestrateResponse,
} from '../../utils/openEarthAgent';
import type { Project } from '../../types/app';

type TaskPhase = 'idle' | 'routing' | 'decomposing' | 'executing' | 'completed' | 'failed' | 'mixed';

type OpenEarthModeProps = {
  selectedProject: Project | null;
};

export default function OpenEarthMode({ selectedProject }: OpenEarthModeProps) {
  const [mode, setMode] = useState<ExecutionMode>('open_earth');
  const [taskDescription, setTaskDescription] = useState('');
  const [taskPhase, setTaskPhase] = useState<TaskPhase>('idle');

  const [routeResult, setRouteResult] = useState<TaskRouteResponse | null>(null);
  const [decomposedSteps, setDecomposedSteps] = useState<TaskStep[]>([]);
  const [orchestrateResult, setOrchestrateResult] = useState<OrchestrateResponse | null>(null);
  const [decompositionMethod, setDecompositionMethod] = useState<string>('');
  const [routingMethod, setRoutingMethod] = useState<string>('');
  const [routeIntent, setRouteIntent] = useState<any>(null);

  const [isEditingSteps, setIsEditingSteps] = useState(false);
  const [editingStepIndex, setEditingStepIndex] = useState<number | null>(null);
  const [editingStep, setEditingStep] = useState<TaskStep | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<Array<{ time: string; level: string; message: string }>>([]);
  const [knowledgeContext, setKnowledgeContext] = useState<Array<{
    title: string;
    content: string;
    type: string;
    score: number;
    tags: string[];
  }>>([]);

  const addLog = useCallback((level: string, message: string) => {
    const time = new Date().toLocaleTimeString();
    setLogs((prev) => [...prev, { time, level, message }]);
  }, []);

  const handleModeChange = useCallback(
    async (newMode: ExecutionMode) => {
      setMode(newMode);
      addLog('INFO', `切换执行模式: ${newMode === 'standard' ? '标准模式' : newMode === 'open_earth' ? 'OpenEarth 增强' : '混合模式'}`);
    },
    [addLog]
  );

  const handleRouteTask = useCallback(async () => {
    if (!taskDescription.trim()) {
      addLog('WARN', '请输入任务描述');
      return;
    }

    setTaskPhase('routing');
    setError(null);
    addLog('INFO', `正在分析任务复杂度: "${taskDescription.slice(0, 50)}..."`);

    try {
      const response = await authenticatedFetch('/api/open-earth/route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_description: taskDescription,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result: TaskRouteResponse = await response.json();
      setRouteResult(result);
      setRoutingMethod((result as any).routing_method || 'rule');
      setRouteIntent((result as any).intent || null);
      addLog('INFO', `路由判定结果: ${result.route} (分数: ${result.score}, 方法: ${(result as any).routing_method || '规则'})`);

      if (result.reasons.length > 0) {
        result.reasons.forEach((r) => addLog('DETAIL', `- ${r}`));
      }

      if ((result as any).explanation) {
        addLog('DETAIL', `路由说明: ${(result as any).explanation}`);
      }

      await handleDecomposeTask(result);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '任务路由失败';
      setError(errorMsg);
      addLog('ERROR', errorMsg);
      setTaskPhase('failed');
    }
  }, [taskDescription, mode, addLog]);

  const handleDecomposeTask = useCallback(async (routeInfo?: TaskRouteResponse) => {
    setTaskPhase('decomposing');
    addLog('INFO', '正在分解任务为执行步骤...');

    try {
      const response = await authenticatedFetch('/api/open-earth/decompose', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_description: taskDescription,
          route_info: routeInfo ? {
            route: routeInfo.route,
            score: routeInfo.score,
            intent: (routeInfo as any).intent,
          } : undefined,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();
      setDecomposedSteps(result.steps);
      setDecompositionMethod(result.decomposition_method || 'rule');
      setKnowledgeContext(result.knowledge_context || []);
      if (result.knowledge_enhanced) {
        addLog('INFO', `知识库增强: 找到 ${result.knowledge_context.length} 条相关知识`);
        result.knowledge_context.forEach((k: any) => {
          addLog('DETAIL', `  - [${k.type}] ${k.title} (相关度: ${k.score})`);
        });
      }
      addLog('INFO', `任务已分解为 ${result.total_steps} 个步骤 (方法: ${result.decomposition_method || '规则'})`);
      result.steps.forEach((step: TaskStep, i: number) => {
        addLog('DETAIL', `  ${i + 1}. ${step.description} [${step.execution_mode}] → ${step.tool_id || 'N/A'}`);
        if (step.reasoning) {
          addLog('DETAIL', `     理由: ${step.reasoning}`);
        }
      });
      setTaskPhase('completed');
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '任务分解失败';
      setError(errorMsg);
      addLog('ERROR', errorMsg);
      setTaskPhase('failed');
    }
  }, [taskDescription, addLog]);

  const handleExecute = useCallback(async () => {
    if (decomposedSteps.length === 0) {
      addLog('WARN', '没有可执行的步骤，请先分解任务');
      return;
    }

    setTaskPhase('executing');
    setError(null);
    addLog('INFO', '开始执行工作流...');

    try {
      const response = await authenticatedFetch('/api/open-earth/orchestrate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_description: taskDescription,
          steps: decomposedSteps,
          workspace_id: selectedProject?.id,
          config: {
            use_mock_bridge: true,
            max_parallel: 4,
            enable_fallback: true,
          },
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result: OrchestrateResponse = await response.json();
      setOrchestrateResult(result);

      const status = result.status === 'success' ? 'completed' : 'failed';
      setTaskPhase(status);

      addLog(
        status === 'completed' ? 'INFO' : 'ERROR',
        `工作流执行完成: ${result.succeeded_count}/${result.dag_nodes.length} 成功`
      );

      if (result.output_files?.length) {
        addLog('INFO', '输出文件:');
        result.output_files.forEach((f) => addLog('DETAIL', `  - ${f}`));
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '工作流执行失败';
      setError(errorMsg);
      addLog('ERROR', errorMsg);
      setTaskPhase('failed');
    }
  }, [decomposedSteps, taskDescription, selectedProject, addLog]);

  const handleReset = useCallback(() => {
    setTaskPhase('idle');
    setRouteResult(null);
    setDecomposedSteps([]);
    setOrchestrateResult(null);
    setError(null);
    setLogs([]);
    setKnowledgeContext([]);
    setIsEditingSteps(false);
    setEditingStepIndex(null);
    setEditingStep(null);
    setDecompositionMethod('');
    setRoutingMethod('');
    setRouteIntent(null);
  }, []);

  const generateStepId = useCallback(() => {
    return `step_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;
  }, []);

  const handleStartEdit = useCallback(() => {
    setIsEditingSteps(true);
    addLog('INFO', '进入工作流编辑模式');
  }, [addLog]);

  const handleCancelEdit = useCallback(() => {
    setIsEditingSteps(false);
    setEditingStepIndex(null);
    setEditingStep(null);
    addLog('INFO', '取消工作流编辑');
  }, [addLog]);

  const handleAddStep = useCallback(() => {
    const newStep: TaskStep = {
      step_id: generateStepId(),
      step_number: decomposedSteps.length + 1,
      description: '新步骤',
      tool_name: 'custom',
      tool_id: '',
      execution_mode: 'mcp',
      dependencies: [],
      reasoning: '用户自定义步骤',
    };
    setDecomposedSteps((prev) => [...prev, newStep]);
    setEditingStepIndex(decomposedSteps.length);
    setEditingStep(newStep);
    addLog('INFO', '添加新步骤');
  }, [decomposedSteps.length, generateStepId, addLog]);

  const handleEditStep = useCallback((index: number) => {
    setEditingStepIndex(index);
    setEditingStep({ ...decomposedSteps[index] });
  }, [decomposedSteps]);

  const handleSaveStep = useCallback(() => {
    if (editingStepIndex !== null && editingStep) {
      setDecomposedSteps((prev) => {
        const newSteps = [...prev];
        newSteps[editingStepIndex] = editingStep;
        return newSteps.map((s, i) => ({ ...s, step_number: i + 1 }));
      });
      setEditingStepIndex(null);
      setEditingStep(null);
      addLog('INFO', `保存步骤 ${editingStepIndex + 1}`);
    }
  }, [editingStepIndex, editingStep, addLog]);

  const handleCancelEditStep = useCallback(() => {
    setEditingStepIndex(null);
    setEditingStep(null);
  }, []);

  const handleDeleteStep = useCallback((index: number) => {
    const stepId = decomposedSteps[index].step_id;
    setDecomposedSteps((prev) => {
      const newSteps = prev.filter((_, i) => i !== index);
      return newSteps
        .map((s, i) => ({ ...s, step_number: i + 1 }))
        .map((s) => ({
          ...s,
          dependencies: s.dependencies.filter((d) => d !== stepId),
        }));
    });
    if (editingStepIndex === index) {
      setEditingStepIndex(null);
      setEditingStep(null);
    }
    addLog('WARN', `删除步骤 ${index + 1}`);
  }, [decomposedSteps, editingStepIndex, addLog]);

  const handleMoveStep = useCallback((index: number, direction: 'up' | 'down') => {
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= decomposedSteps.length) return;

    setDecomposedSteps((prev) => {
      const newSteps = [...prev];
      [newSteps[index], newSteps[newIndex]] = [newSteps[newIndex], newSteps[index]];
      return newSteps.map((s, i) => ({ ...s, step_number: i + 1 }));
    });
    addLog('INFO', `步骤 ${index + 1} ${direction === 'up' ? '上移' : '下移'}`);
  }, [decomposedSteps.length, addLog]);

  const handleUpdateEditingStep = useCallback((field: keyof TaskStep, value: string | string[]) => {
    if (editingStep) {
      setEditingStep({ ...editingStep, [field]: value });
    }
  }, [editingStep]);

  const handleSaveWorkflow = useCallback(() => {
    setIsEditingSteps(false);
    setEditingStepIndex(null);
    setEditingStep(null);
    addLog('INFO', `工作流已保存，共 ${decomposedSteps.length} 个步骤`);
  }, [decomposedSteps.length, addLog]);

  const exampleTasks = [
    '计算北京地区 Sentinel-2 影像的 NDVI 植被指数',
    '对两个时相的影像进行变化检测，然后分区统计变化区域',
    '同时使用 SAR 雷达影像、光学影像和矢量数据进行叠加分析',
  ];

  const displayNodes: DagNode[] = orchestrateResult?.dag_nodes ?? [];

  return (
    <div className="flex h-full flex-col">
      {/* 头部 */}
      <div className="flex items-center gap-3 border-b border-zinc-200 px-6 py-4 dark:border-zinc-700">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-purple-500 to-blue-500">
          <Sparkles className="h-5 w-5 text-white" />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
            OpenEarth 增强模式
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            智能任务编排 · DAG 工作流 · 自定义代码沙箱
          </p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          {taskPhase !== 'idle' && (
            <button
              onClick={handleReset}
              className="flex items-center gap-1.5 rounded-lg border border-zinc-300 px-3 py-1.5 text-sm text-zinc-600 hover:bg-zinc-100 dark:border-zinc-600 dark:text-zinc-300 dark:hover:bg-zinc-800"
            >
              <RotateCcw className="h-4 w-4" />
              重置
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* 左侧 - 任务输入和控制 */}
        <div className="w-[420px] flex-shrink-0 overflow-y-auto border-r border-zinc-200 dark:border-zinc-700">
          {/* 模式切换 */}
          <div className="p-4 pb-2">
            <OpenEarthModeToggle
              selectedMode={mode}
              onModeChange={handleModeChange}
              routeResult={routeResult}
              isAnalyzing={taskPhase === 'routing' || taskPhase === 'decomposing'}
            />
          </div>

          {/* 任务输入 */}
          <div className="px-4 py-3">
            <label className="mb-2 flex items-center gap-1.5 text-sm font-medium text-zinc-700 dark:text-zinc-300">
              <MessageSquare className="h-4 w-4" />
              任务描述
            </label>
            <textarea
              value={taskDescription}
              onChange={(e) => setTaskDescription(e.target.value)}
              placeholder="用自然语言描述你的遥感任务，例如：计算北京 Sentinel-2 影像的 NDVI 植被指数..."
              className="mb-3 h-28 w-full resize-none rounded-lg border border-zinc-300 bg-white p-3 text-sm text-zinc-900 placeholder:text-zinc-400 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100 dark:placeholder:text-zinc-500"
              disabled={taskPhase === 'executing'}
            />

            {/* 示例任务 */}
            <div className="mb-3">
              <p className="mb-1.5 text-xs text-zinc-500 dark:text-zinc-400">
                <Lightbulb className="inline h-3 w-3 mr-1" />
                示例任务：
              </p>
              <div className="space-y-1">
                {exampleTasks.map((task, i) => (
                  <button
                    key={i}
                    onClick={() => setTaskDescription(task)}
                    disabled={taskPhase === 'executing'}
                    className="w-full truncate rounded-lg border border-zinc-200 px-2 py-1.5 text-left text-xs text-zinc-600 hover:border-blue-300 hover:bg-blue-50/50 dark:border-zinc-700 dark:text-zinc-400 dark:hover:bg-blue-900/10"
                  >
                    {task}
                  </button>
                ))}
              </div>
            </div>

            {/* 执行按钮 */}
            <div className="flex gap-2">
              {taskPhase === 'idle' && (
                <button
                  onClick={handleRouteTask}
                  disabled={!taskDescription.trim()}
                  className={cn(
                    'flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium text-white transition-colors',
                    taskDescription.trim()
                      ? 'bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700'
                      : 'bg-zinc-300 cursor-not-allowed dark:bg-zinc-600'
                  )}
                >
                  <Sparkles className="h-4 w-4" />
                  开始分析
                </button>
              )}

              {taskPhase === 'routing' && (
                <button
                  disabled
                  className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-zinc-300 px-4 py-2.5 text-sm font-medium text-zinc-600 dark:bg-zinc-600 dark:text-zinc-300"
                >
                  <Loader2 className="h-4 w-4 animate-spin" />
                  分析任务中...
                </button>
              )}

              {taskPhase === 'decomposing' && (
                <button
                  disabled
                  className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-zinc-300 px-4 py-2.5 text-sm font-medium text-zinc-600 dark:bg-zinc-600 dark:text-zinc-300"
                >
                  <Loader2 className="h-4 w-4 animate-spin" />
                  分解任务中...
                </button>
              )}

              {(taskPhase === 'completed' ||
                (decomposedSteps.length > 0 && taskPhase !== 'executing')) && (
                <>
                  <button
                    onClick={handleExecute}
                    disabled={taskPhase === 'executing'}
                    className={cn(
                      'flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium text-white transition-colors',
                      taskPhase === 'executing'
                        ? 'bg-zinc-300 dark:bg-zinc-600'
                        : 'bg-green-600 hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600'
                    )}
                  >
                    {taskPhase === 'executing' ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Play className="h-4 w-4" />
                    )}
                    执行工作流
                  </button>
                </>
              )}

              {taskPhase === 'executing' && (
                <button
                  disabled
                  className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-zinc-300 px-4 py-2.5 text-sm font-medium text-zinc-600 dark:bg-zinc-600 dark:text-zinc-300"
                >
                  <Loader2 className="h-4 w-4 animate-spin" />
                  执行中...
                </button>
              )}
            </div>
          </div>

          {/* 分解步骤预览 */}
          {decomposedSteps.length > 0 && (
            <div className="border-t border-zinc-200 px-4 py-3 dark:border-zinc-700">
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
                  {isEditingSteps ? '编辑工作流' : `分解步骤 (${decomposedSteps.length})`}
                </h4>
                <div className="flex items-center gap-2">
                  {decompositionMethod && (
                    <span className={cn(
                      'text-[10px] px-1.5 py-0.5 rounded',
                      decompositionMethod === 'llm'
                        ? 'bg-purple-100 text-purple-600 dark:bg-purple-900/20 dark:text-purple-300'
                        : 'bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400'
                    )}>
                      {decompositionMethod === 'llm' ? 'LLM 智能分解' : decompositionMethod === 'rule_fallback' ? '规则回退' : '规则分解'}
                    </span>
                  )}
                  {routingMethod && (
                    <span className={cn(
                      'text-[10px] px-1.5 py-0.5 rounded',
                      routingMethod === 'llm'
                        ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/20 dark:text-blue-300'
                        : 'bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400'
                    )}>
                      {routingMethod === 'llm' ? 'LLM 路由' : '规则路由'}
                    </span>
                  )}
                  {mode === 'mixed' && taskPhase !== 'executing' && (
                    <div className="flex gap-1">
                      {!isEditingSteps ? (
                        <button
                          onClick={handleStartEdit}
                          className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-blue-600 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-900/20"
                        >
                          <Pencil className="h-3 w-3" />
                          编辑
                        </button>
                      ) : (
                        <>
                          <button
                            onClick={handleSaveWorkflow}
                            className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-green-600 hover:bg-green-50 dark:text-green-400 dark:hover:bg-green-900/20"
                          >
                            <Save className="h-3 w-3" />
                            保存
                          </button>
                          <button
                            onClick={handleCancelEdit}
                            className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-zinc-500 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
                          >
                            <X className="h-3 w-3" />
                            取消
                          </button>
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* LLM 路由意图信息 */}
              {routeIntent && (
                <div className="mb-3 rounded-lg border border-blue-200 bg-blue-50 p-2 dark:border-blue-700 dark:bg-blue-900/20">
                  <div className="flex items-center gap-2 mb-1">
                    <Sparkles className="h-3.5 w-3.5 text-blue-500" />
                    <span className="text-xs font-medium text-blue-700 dark:text-blue-300">AI 分析</span>
                  </div>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-[10px] text-blue-600 dark:text-blue-400">
                    {routeIntent.task_type && (
                      <span>任务类型: {routeIntent.task_type}</span>
                    )}
                    {routeIntent.estimated_steps && (
                      <span>预估步骤: {routeIntent.estimated_steps}</span>
                    )}
                    {routeIntent.data_sources?.length > 0 && (
                      <span className="col-span-2">数据源: {routeIntent.data_sources.join(', ')}</span>
                    )}
                    {routeIntent.key_operations?.length > 0 && (
                      <span className="col-span-2">关键操作: {routeIntent.key_operations.join(', ')}</span>
                    )}
                  </div>
                </div>
              )}

              {isEditingSteps && (
                <button
                  onClick={handleAddStep}
                  disabled={taskPhase === 'executing'}
                  className="mb-3 flex w-full items-center justify-center gap-2 rounded-lg border-2 border-dashed border-zinc-300 py-2 text-sm text-zinc-500 hover:border-blue-300 hover:text-blue-500 dark:border-zinc-600 dark:hover:border-blue-500"
                >
                  <Plus className="h-4 w-4" />
                  添加步骤
                </button>
              )}

              <div className="space-y-2">
                {decomposedSteps.map((step, i) => {
                  const isCompleted = orchestrateResult?.dag_nodes.some(
                    (n) => n.node_id === step.step_id && n.status === 'completed'
                  );
                  const isFailed = orchestrateResult?.dag_nodes.some(
                    (n) => n.node_id === step.step_id && n.status === 'failed'
                  );
                  const isEditingThis = editingStepIndex === i;

                  if (isEditingThis && editingStep) {
                    return (
                      <div
                        key={step.step_id}
                        className="rounded-lg border border-blue-300 bg-blue-50 p-3 dark:border-blue-600 dark:bg-blue-900/20"
                      >
                        <div className="mb-2">
                          <label className="mb-1 block text-xs font-medium text-zinc-600 dark:text-zinc-400">
                            步骤描述
                          </label>
                          <input
                            type="text"
                            value={editingStep.description}
                            onChange={(e) =>
                              handleUpdateEditingStep('description', e.target.value)
                            }
                            className="w-full rounded-md border border-zinc-300 px-2 py-1 text-sm dark:border-zinc-600 dark:bg-zinc-800"
                          />
                        </div>
                        <div className="mb-2 grid grid-cols-2 gap-2">
                          <div>
                            <label className="mb-1 block text-xs font-medium text-zinc-600 dark:text-zinc-400">
                              工具名称
                            </label>
                            <input
                              type="text"
                              value={editingStep.tool_name || ''}
                              onChange={(e) =>
                                handleUpdateEditingStep('tool_name', e.target.value)
                              }
                              className="w-full rounded-md border border-zinc-300 px-2 py-1 text-sm dark:border-zinc-600 dark:bg-zinc-800"
                            />
                          </div>
                          <div>
                            <label className="mb-1 block text-xs font-medium text-zinc-600 dark:text-zinc-400">
                              工具 ID
                            </label>
                            <input
                              type="text"
                              value={editingStep.tool_id || ''}
                              onChange={(e) =>
                                handleUpdateEditingStep('tool_id', e.target.value)
                              }
                              className="w-full rounded-md border border-zinc-300 px-2 py-1 text-sm dark:border-zinc-600 dark:bg-zinc-800"
                            />
                          </div>
                        </div>
                        <div className="mb-3">
                          <label className="mb-1 block text-xs font-medium text-zinc-600 dark:text-zinc-400">
                            执行模式
                          </label>
                          <select
                            value={editingStep.execution_mode}
                            onChange={(e) =>
                              handleUpdateEditingStep(
                                'execution_mode',
                                e.target.value as 'mcp' | 'sandbox' | 'mixed'
                              )
                            }
                            className="w-full rounded-md border border-zinc-300 px-2 py-1 text-sm dark:border-zinc-600 dark:bg-zinc-800"
                          >
                            <option value="mcp">MCP 工具</option>
                            <option value="sandbox">沙箱代码</option>
                            <option value="mixed">混合模式</option>
                          </select>
                        </div>
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={handleCancelEditStep}
                            className="rounded-md px-2 py-1 text-xs text-zinc-500 hover:bg-zinc-200 dark:hover:bg-zinc-700"
                          >
                            取消
                          </button>
                          <button
                            onClick={handleSaveStep}
                            className="rounded-md bg-blue-500 px-2 py-1 text-xs text-white hover:bg-blue-600"
                          >
                            保存
                          </button>
                        </div>
                      </div>
                    );
                  }

                  return (
                    <div
                      key={step.step_id}
                      className={cn(
                        'flex items-start gap-2 rounded-lg border p-2',
                        isCompleted
                          ? 'border-green-300 bg-green-50 dark:border-green-600 dark:bg-green-900/20'
                          : isFailed
                          ? 'border-red-300 bg-red-50 dark:border-red-600 dark:bg-red-900/20'
                          : 'border-zinc-200 dark:border-zinc-700'
                      )}
                    >
                      <div className="mt-0.5 flex flex-col items-center gap-0.5">
                        {isCompleted ? (
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                        ) : isFailed ? (
                          <AlertCircle className="h-4 w-4 text-red-500" />
                        ) : (
                          <span className="flex h-4 w-4 items-center justify-center rounded-full bg-zinc-200 text-[10px] font-bold text-zinc-500 dark:bg-zinc-700">
                            {i + 1}
                          </span>
                        )}
                        {isEditingSteps && (
                          <div className="flex flex-col">
                            <button
                              onClick={() => handleMoveStep(i, 'up')}
                              disabled={i === 0}
                              className="p-0.5 text-zinc-400 hover:text-zinc-600 disabled:opacity-30"
                            >
                              <ChevronUp className="h-3 w-3" />
                            </button>
                            <button
                              onClick={() => handleMoveStep(i, 'down')}
                              disabled={i === decomposedSteps.length - 1}
                              className="p-0.5 text-zinc-400 hover:text-zinc-600 disabled:opacity-30"
                            >
                              <ChevronDown className="h-3 w-3" />
                            </button>
                          </div>
                        )}
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                          {step.description}
                        </p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span
                            className={cn(
                              'text-[10px] px-1.5 py-0.5 rounded',
                              step.execution_mode === 'mcp'
                                ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/20 dark:text-blue-300'
                                : step.execution_mode === 'sandbox'
                                ? 'bg-purple-100 text-purple-600 dark:bg-purple-900/20 dark:text-purple-300'
                                : 'bg-amber-100 text-amber-600 dark:bg-amber-900/20 dark:text-amber-300'
                            )}
                          >
                            {step.execution_mode === 'mcp'
                              ? 'MCP 工具'
                              : step.execution_mode === 'sandbox'
                              ? '沙箱代码'
                              : '混合模式'}
                          </span>
                          {step.tool_id && (
                            <span className="text-[10px] text-zinc-500 font-mono">
                              {step.tool_id}
                            </span>
                          )}
                        </div>
                        {step.reasoning && (
                          <p className="mt-1 text-[10px] text-zinc-400 dark:text-zinc-500 italic">
                            {step.reasoning}
                          </p>
                        )}
                      </div>
                      {isEditingSteps && (
                        <div className="flex gap-1">
                          <button
                            onClick={() => handleEditStep(i)}
                            className="p-1 rounded text-zinc-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20"
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={() => handleDeleteStep(i)}
                            className="p-1 rounded text-zinc-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* 知识库上下文 */}
          {knowledgeContext.length > 0 && (
            <div className="border-t border-zinc-200 px-4 py-3 dark:border-zinc-700">
              <h4 className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-zinc-500 uppercase tracking-wider">
                <BookOpen className="h-3.5 w-3.5" />
                知识库增强
              </h4>
              <div className="space-y-2">
                {knowledgeContext.map((k, i) => (
                  <div
                    key={i}
                    className="rounded-lg border border-amber-200 bg-amber-50 p-2 dark:border-amber-700 dark:bg-amber-900/20"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-200 text-amber-700 dark:bg-amber-800 dark:text-amber-200">
                        {k.type}
                      </span>
                      <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                        {k.title}
                      </span>
                      <span className="ml-auto text-[10px] text-amber-600 dark:text-amber-400">
                        {Math.round(k.score * 100)}%
                      </span>
                    </div>
                    <p className="text-xs text-zinc-600 dark:text-zinc-400 line-clamp-2">
                      {k.content}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 日志 */}
          <div className="border-t border-zinc-200 px-4 py-3 dark:border-zinc-700">
            <h4 className="mb-2 text-xs font-semibold text-zinc-500 uppercase tracking-wider">
              执行日志
            </h4>
            <div className="max-h-48 overflow-y-auto space-y-1 rounded-lg bg-zinc-900 p-2 font-mono text-xs">
              {logs.length === 0 ? (
                <p className="text-zinc-500">暂无日志...</p>
              ) : (
                logs.map((log, i) => (
                  <div key={i} className="flex gap-2">
                    <span className="text-zinc-500">[{log.time}]</span>
                    <span
                      className={cn(
                        log.level === 'ERROR'
                          ? 'text-red-400'
                          : log.level === 'WARN'
                          ? 'text-yellow-400'
                          : log.level === 'DETAIL'
                          ? 'text-zinc-400'
                          : 'text-green-400'
                      )}
                    >
                      [{log.level}]
                    </span>
                    <span className="text-zinc-300">{log.message}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* 右侧 - DAG 可视化和结果 */}
        <div className="flex-1 overflow-y-auto bg-zinc-50 dark:bg-zinc-900">
          <div className="p-6 space-y-6">
            {/* 任务状态 */}
            {taskPhase !== 'idle' && (
              <div
                className={cn(
                  'rounded-xl border p-4',
                  taskPhase === 'failed'
                    ? 'border-red-300 bg-red-50 dark:border-red-700 dark:bg-red-900/20'
                    : 'border-green-300 bg-green-50 dark:border-green-700 dark:bg-green-900/20'
                )}
              >
                <div className="flex items-center gap-3">
                  {taskPhase === 'failed' ? (
                    <AlertCircle className="h-6 w-6 text-red-500" />
                  ) : (
                    <CheckCircle2 className="h-6 w-6 text-green-500" />
                  )}
                  <div>
                    <h3
                      className={cn(
                        'text-sm font-semibold',
                        taskPhase === 'failed'
                          ? 'text-red-700 dark:text-red-300'
                          : 'text-green-700 dark:text-green-300'
                      )}
                    >
                      {taskPhase === 'failed'
                        ? '执行失败'
                        : taskPhase === 'completed'
                        ? '执行完成'
                        : '执行中...'}
                    </h3>
                    {orchestrateResult && (
                      <p className="text-xs text-zinc-500 dark:text-zinc-400">
                        {orchestrateResult.succeeded_count}/{orchestrateResult.dag_nodes.length} 步骤成功 · 总耗时{' '}
                        {orchestrateResult.total_duration_ms
                          ? `${Math.round(orchestrateResult.total_duration_ms / 1000)}s`
                          : 'N/A'}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* DAG 可视化 */}
            {displayNodes.length > 0 && (
              <DagVisualizer nodes={displayNodes} title="工作流 DAG" />
            )}

            {/* 空状态 */}
            {taskPhase === 'idle' && displayNodes.length === 0 && (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-purple-500/20 to-blue-500/20">
                  <Sparkles className="h-10 w-10 text-purple-500" />
                </div>
                <h3 className="mb-2 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
                  OpenEarth 增强模式
                </h3>
                <p className="max-w-sm text-sm text-zinc-500 dark:text-zinc-400">
                  使用自然语言描述你的遥感任务，系统将自动分析复杂度、分解步骤、构建 DAG 工作流并执行。
                </p>
                <div className="mt-6 grid grid-cols-3 gap-4">
                  <div className="text-center">
                    <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-900/30">
                      <MessageSquare className="h-5 w-5 text-blue-500" />
                    </div>
                    <p className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
                      1. 任务输入
                    </p>
                    <p className="text-[10px] text-zinc-500">
                      自然语言描述
                    </p>
                  </div>
                  <div className="text-center">
                    <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-900/30">
                      <Sparkles className="h-5 w-5 text-purple-500" />
                    </div>
                    <p className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
                      2. 智能编排
                    </p>
                    <p className="text-[10px] text-zinc-500">
                      自动路由+分解
                    </p>
                  </div>
                  <div className="text-center">
                    <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-green-100 dark:bg-green-900/30">
                      <Send className="h-5 w-5 text-green-500" />
                    </div>
                    <p className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
                      3. 执行输出
                    </p>
                    <p className="text-[10px] text-zinc-500">
                      DAG 可视化执行
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* 错误信息 */}
            {error && (
              <div className="rounded-lg border border-red-300 bg-red-50 p-4 dark:border-red-700 dark:bg-red-900/20">
                <div className="flex items-start gap-2">
                  <AlertCircle className="mt-0.5 h-5 w-5 text-red-500" />
                  <div>
                    <h4 className="text-sm font-semibold text-red-700 dark:text-red-300">
                      执行错误
                    </h4>
                    <p className="mt-1 text-xs text-red-600 dark:text-red-400">
                      {error}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
