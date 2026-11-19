/**
 * 遥感任务编辑器 - 主组件
 *
 * 提供遥感影像下载、预处理、分析的可视化任务编辑界面。
 * 支持传感器选择、AOI 输入、日期范围、分析类型等参数配置。
 *
 * 遵循 PilotDeck UI 约定：
 * - Tailwind CSS + cn() 样式
 * - 深色模式 dark: 前缀
 * - Lucide React 图标
 * - i18n 国际化
 */

import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Satellite,
  Download,
  Layers,
  BarChart3,
  Play,
  ChevronRight,
  MapPin,
  Calendar,
  CloudOff,
  Settings2,
  FileText,
  Eye,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Sparkles,
} from 'lucide-react';
import type { Project } from '../../types/app';
import { cn } from '../../lib/utils.js';
import RsSensorSelect from './RsSensorSelect';
import RsAoiInput from './RsAoiInput';
import RsDateRangePicker from './RsDateRangePicker';
import RsTemplateGallery from './RsTemplateGallery';
import OpenEarthMode from './OpenEarthMode';

type RsTaskType = 'download' | 'preprocess' | 'analyze' | 'visualize' | 'report';

type RsTaskConfig = {
  taskType: RsTaskType | string;
  sensor: string;
  aoi: string;
  startDate: string;
  endDate: string;
  maxCloudCover: number;
  operations: string[];
  analysisType: string;
  visType: string;
  reportFormat: string;
};

type RsTaskResult = {
  id: string;
  taskType: RsTaskType | string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  config: RsTaskConfig;
  output?: string;
  error?: string;
  timestamp: string;
};

type RemoteSensingV2Props = {
  selectedProject: Project | null;
  projects: Project[];
};

const DEFAULT_CONFIG: RsTaskConfig = {
  taskType: 'download',
  sensor: 'sentinel2',
  aoi: '',
  startDate: '',
  endDate: '',
  maxCloudCover: 20,
  operations: [],
  analysisType: 'ndvi',
  visType: 'thumbnail',
  reportFormat: 'markdown',
};

const BUILTIN_TASK_TYPES: { id: RsTaskType; label: string; icon: typeof Download; color: string }[] = [
  { id: 'download', label: '影像下载', icon: Download, color: 'text-blue-500' },
  { id: 'preprocess', label: '预处理', icon: Layers, color: 'text-purple-500' },
  { id: 'analyze', label: '智能分析', icon: BarChart3, color: 'text-green-500' },
  { id: 'visualize', label: '可视化', icon: Eye, color: 'text-orange-500' },
  { id: 'report', label: '报告生成', icon: FileText, color: 'text-pink-500' },
];

export default function RemoteSensingV2({ selectedProject }: RemoteSensingV2Props) {
  const { t } = useTranslation();
  const [config, setConfig] = useState<RsTaskConfig>({ ...DEFAULT_CONFIG });
  const [results, setResults] = useState<RsTaskResult[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [toast, setToast] = useState<{ kind: 'success' | 'error' | 'info'; text: string } | null>(null);
  const [showTemplates, setShowTemplates] = useState(false);

  const [activeTab, setActiveTab] = useState<'open_earth' | 'builtin'>('open_earth');

  const updateConfig = useCallback((key: keyof RsTaskConfig, value: unknown) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleRun = useCallback(() => {
    if (!selectedProject) {
      setToast({ kind: 'error', text: '请先选择项目' });
      return;
    }

    setIsRunning(true);
    const taskId = `task_${Date.now()}`;
    const newResult: RsTaskResult = {
      id: taskId,
      taskType: config.taskType,
      status: 'running',
      config: { ...config },
      timestamp: new Date().toLocaleString(),
    };

    setResults((prev) => [newResult, ...prev]);

    setTimeout(() => {
      const label = BUILTIN_TASK_TYPES.find((tt) => tt.id === config.taskType)?.label ?? config.taskType;
      setResults((prev) =>
        prev.map((r) =>
          r.id === taskId
            ? { ...r, status: 'completed', output: `${label}已完成 (模拟)` }
            : r
        )
      );
      setIsRunning(false);
      setToast({ kind: 'success', text: '任务执行完成' });
      setTimeout(() => setToast(null), 3000);
    }, 1500);
  }, [config, selectedProject]);

  const handleApplyTemplate = useCallback(
    (template: { tool: string; params: Record<string, unknown> }) => {
      const typeMap: Record<string, RsTaskType> = {
        rs_download: 'download',
        rs_preprocess: 'preprocess',
        rs_analyze: 'analyze',
        rs_visualize: 'visualize',
        rs_report: 'report',
      };

      const taskType = typeMap[template.tool] ?? 'download';
      const newConfig = { ...DEFAULT_CONFIG, taskType, ...template.params };
      setConfig(newConfig as RsTaskConfig);
      setShowTemplates(false);
      setToast({ kind: 'info', text: '模板已应用' });
      setTimeout(() => setToast(null), 2000);
    },
    []
  );

  return (
    <div className="flex h-full flex-col">
      {toast && (
        <div
          className={cn(
            'absolute top-4 right-4 z-50 flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium shadow-lg',
            toast.kind === 'success' && 'bg-green-500/90 text-white',
            toast.kind === 'error' && 'bg-red-500/90 text-white',
            toast.kind === 'info' && 'bg-blue-500/90 text-white'
          )}
        >
          {toast.kind === 'success' && <CheckCircle2 className="h-4 w-4" />}
          {toast.kind === 'error' && <AlertCircle className="h-4 w-4" />}
          {toast.text}
        </div>
      )}

      <div className="flex items-center gap-3 border-b border-zinc-200 px-6 py-4 dark:border-zinc-700">
        <Satellite className="h-6 w-6 text-blue-500" />
        <div>
          <h1 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
            遥感任务编辑器
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            卫星影像下载 · 预处理 · 智能分析 · 可视化 · 报告
          </p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <div className="flex items-center gap-1 mr-4">
            <button
              onClick={() => setActiveTab('open_earth')}
              className={cn(
                'flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors',
                activeTab === 'open_earth'
                  ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300'
                  : 'text-zinc-500 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800'
              )}
            >
              <Sparkles className="h-4 w-4" />
              OpenEarth 增强
            </button>
            <button
              onClick={() => setActiveTab('builtin')}
              className={cn(
                'flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors',
                activeTab === 'builtin'
                  ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                  : 'text-zinc-500 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800'
              )}
            >
              <Satellite className="h-4 w-4" />
              遥感任务
            </button>
          </div>
          {activeTab !== 'open_earth' && (
            <button
              onClick={() => setShowTemplates(!showTemplates)}
              className="flex items-center gap-1.5 rounded-lg border border-zinc-300 px-3 py-1.5 text-sm text-zinc-600 hover:bg-zinc-100 dark:border-zinc-600 dark:text-zinc-300 dark:hover:bg-zinc-800"
            >
              <Settings2 className="h-4 w-4" />
              模板库
            </button>
          )}
        </div>
      </div>

      {activeTab === 'open_earth' ? (
        <OpenEarthMode selectedProject={selectedProject} />
      ) : (
        <div className="flex flex-1 overflow-hidden">
          <div className="w-96 flex-shrink-0 overflow-y-auto border-r border-zinc-200 dark:border-zinc-700">
            <div className="p-4 pt-2">
              <label className="mb-2 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                任务类型
              </label>
              <div className="grid grid-cols-2 gap-2">
                {BUILTIN_TASK_TYPES.map((tt) => (
                  <button
                    key={tt.id}
                    onClick={() => updateConfig('taskType', tt.id)}
                    className={cn(
                      'flex items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors',
                      config.taskType === tt.id
                        ? 'border-blue-500 bg-blue-50 text-blue-700 dark:border-blue-400 dark:bg-blue-900/30 dark:text-blue-300'
                        : 'border-zinc-200 text-zinc-600 hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-400 dark:hover:bg-zinc-800'
                    )}
                  >
                    <tt.icon className={cn('h-4 w-4', tt.color)} />
                    {tt.label}
                  </button>
                ))}
              </div>
            </div>

            <RsSensorSelect
              value={config.sensor}
              onChange={(v) => updateConfig('sensor', v)}
              show={config.taskType === 'download' || config.taskType === 'analyze'}
            />

            <RsAoiInput
              value={config.aoi}
              onChange={(v) => updateConfig('aoi', v)}
              show={config.taskType === 'download'}
            />

            <RsDateRangePicker
              startDate={config.startDate}
              endDate={config.endDate}
              onStartChange={(v) => updateConfig('startDate', v)}
              onEndChange={(v) => updateConfig('endDate', v)}
              show={config.taskType === 'download'}
            />

            {config.taskType === 'download' && (
              <div className="px-4 pb-3">
                <label className="mb-2 flex items-center gap-1.5 text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  <CloudOff className="h-4 w-4" />
                  最大云覆盖
                </label>
                <div className="flex items-center gap-3">
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={config.maxCloudCover}
                    onChange={(e) => updateConfig('maxCloudCover', Number(e.target.value))}
                    className="h-2 flex-1 cursor-pointer appearance-none rounded-lg bg-zinc-200 dark:bg-zinc-700"
                  />
                  <span className="w-10 text-right text-sm text-zinc-600 dark:text-zinc-400">
                    {config.maxCloudCover}%
                  </span>
                </div>
              </div>
            )}

            {config.taskType === 'analyze' && (
              <div className="px-4 pb-3">
                <label className="mb-2 flex items-center gap-1.5 text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  <BarChart3 className="h-4 w-4" />
                  分析类型
                </label>
                <select
                  value={config.analysisType}
                  onChange={(e) => updateConfig('analysisType', e.target.value)}
                  className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-700 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-300"
                >
                  <option value="ndvi">NDVI 植被指数</option>
                  <option value="ndwi">NDWI 水体指数</option>
                  <option value="evi">EVI 增强植被指数</option>
                  <option value="savi">SAVI 土壤调节指数</option>
                  <option value="classification">地物分类</option>
                  <option value="change_detection">变化检测</option>
                </select>
              </div>
            )}

            <div className="p-4">
              <button
                onClick={handleRun}
                disabled={isRunning}
                className={cn(
                  'flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium text-white transition-colors',
                  isRunning
                    ? 'bg-zinc-400 dark:bg-zinc-600'
                    : 'bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600'
                )}
              >
                {isRunning ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                {isRunning ? '执行中...' : '执行任务'}
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto bg-zinc-50 dark:bg-zinc-900">
            {showTemplates && <RsTemplateGallery onApply={handleApplyTemplate} />}

            <div className="p-6">
              <h2 className="mb-4 text-sm font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
                任务历史
              </h2>
              {results.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-zinc-400 dark:text-zinc-600">
                  <Satellite className="mb-3 h-12 w-12" />
                  <p className="text-sm">暂无任务记录</p>
                  <p className="mt-1 text-xs">配置参数后点击"执行任务"开始</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {results.map((result) => (
                    <div
                      key={result.id}
                      className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-800"
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={cn(
                            'flex h-8 w-8 items-center justify-center rounded-full',
                            result.status === 'completed' && 'bg-green-100 dark:bg-green-900/30',
                            result.status === 'running' && 'bg-blue-100 dark:bg-blue-900/30',
                            result.status === 'failed' && 'bg-red-100 dark:bg-red-900/30',
                            result.status === 'pending' && 'bg-zinc-100 dark:bg-zinc-700'
                          )}
                        >
                          {result.status === 'completed' && <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />}
                          {result.status === 'running' && <Loader2 className="h-4 w-4 animate-spin text-blue-600 dark:text-blue-400" />}
                          {result.status === 'failed' && <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400" />}
                          {result.status === 'pending' && <ChevronRight className="h-4 w-4 text-zinc-400" />}
                        </div>
                        <div className="flex-1">
                          <div className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                            {BUILTIN_TASK_TYPES.find((tt) => tt.id === result.taskType)?.label ?? result.taskType}
                          </div>
                          <div className="text-xs text-zinc-500 dark:text-zinc-400">
                            {result.timestamp}
                            {result.config.sensor && ` · ${result.config.sensor}`}
                          </div>
                        </div>
                        {result.output && (
                          <div className="max-w-xs truncate text-xs text-zinc-500 dark:text-zinc-400">
                            {result.output}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
