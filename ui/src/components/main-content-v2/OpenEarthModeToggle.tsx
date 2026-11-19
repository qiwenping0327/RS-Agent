/**
 * OpenEarthModeToggle - 模式切换开关组件
 *
 * 允许用户在以下模式之间切换：
 * - standard: 标准 MCP 工具模式
 * - open_earth: OpenEarth 增强模式（自动路由）
 * - mixed: 混合模式（手动选择）
 *
 * 同时显示路由判定结果和推荐解释。
 */

import { useState } from 'react';
import { Sparkles, Zap, GitBranch, ChevronDown, ChevronUp, Info, CheckCircle2, AlertCircle } from 'lucide-react';
import { cn } from '../../lib/utils.js';
import type { TaskRouteResponse } from '../../utils/openEarthAgent';

type ExecutionMode = 'standard' | 'open_earth' | 'mixed';

type ModeOption = {
  id: ExecutionMode;
  label: string;
  description: string;
  icon: typeof Zap;
  color: string;
  bgColor: string;
  borderColor: string;
};

const MODE_OPTIONS: ModeOption[] = [
  {
    id: 'standard',
    label: '标准模式',
    description: '使用预定义的 MCP 遥感工具',
    icon: Zap,
    color: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-50 dark:bg-blue-900/20',
    borderColor: 'border-blue-500 dark:border-blue-400',
  },
  {
    id: 'open_earth',
    label: 'OpenEarth 增强',
    description: '智能编排 + 自定义代码沙箱',
    icon: Sparkles,
    color: 'text-purple-600 dark:text-purple-400',
    bgColor: 'bg-purple-50 dark:bg-purple-900/20',
    borderColor: 'border-purple-500 dark:border-purple-400',
  },
  {
    id: 'mixed',
    label: '混合模式',
    description: '手动选择每步的执行方式',
    icon: GitBranch,
    color: 'text-green-600 dark:text-green-400',
    bgColor: 'bg-green-50 dark:bg-green-900/20',
    borderColor: 'border-green-500 dark:border-green-400',
  },
];

type Props = {
  selectedMode: ExecutionMode;
  onModeChange: (mode: ExecutionMode) => void;
  routeResult?: TaskRouteResponse | null;
  showRouteInfo?: boolean;
  isAnalyzing?: boolean;
};

export default function OpenEarthModeToggle({
  selectedMode,
  onModeChange,
  routeResult,
  showRouteInfo = true,
  isAnalyzing = false,
}: Props) {
  const [expanded, setExpanded] = useState(false);

  const recommendedMode = routeResult
    ? (routeResult.route as ExecutionMode)
    : undefined;

  return (
    <div className="rounded-xl border border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-800">
      {/* 头部 */}
      <div
        className="flex items-center gap-3 px-4 py-3 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-purple-500 to-blue-500">
          <Sparkles className="h-4 w-4 text-white" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              执行模式
            </h3>
            {isAnalyzing && (
              <span className="flex items-center gap-1 text-xs text-zinc-500">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-blue-500" />
                分析中...
              </span>
            )}
          </div>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            {MODE_OPTIONS.find((m) => m.id === selectedMode)?.label}
          </p>
        </div>
        {expanded ? (
          <ChevronUp className="h-4 w-4 text-zinc-400" />
        ) : (
          <ChevronDown className="h-4 w-4 text-zinc-400" />
        )}
      </div>

      {/* 展开内容 */}
      {expanded && (
        <div className="border-t border-zinc-200 dark:border-zinc-700 px-4 py-4">
          {/* 模式选择 */}
          <div className="space-y-2">
            {MODE_OPTIONS.map((option) => {
              const Icon = option.icon;
              const isSelected = selectedMode === option.id;
              const isRecommended = recommendedMode === option.id;

              return (
                <button
                  key={option.id}
                  onClick={(e) => {
                    e.stopPropagation();
                    onModeChange(option.id);
                  }}
                  className={cn(
                    'w-full rounded-lg border p-3 text-left transition-all',
                    isSelected
                      ? `${option.bgColor} ${option.borderColor}`
                      : 'border-zinc-200 hover:border-zinc-300 dark:border-zinc-700 dark:hover:border-zinc-600'
                  )}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={cn(
                        'flex h-8 w-8 items-center justify-center rounded-lg',
                        isSelected ? option.bgColor : 'bg-zinc-100 dark:bg-zinc-700'
                      )}
                    >
                      <Icon className={cn('h-4 w-4', isSelected ? option.color : 'text-zinc-500')} />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span
                          className={cn(
                            'text-sm font-medium',
                            isSelected
                              ? 'text-zinc-900 dark:text-zinc-100'
                              : 'text-zinc-700 dark:text-zinc-300'
                          )}
                        >
                          {option.label}
                        </span>
                        {isRecommended && (
                          <span className="flex items-center gap-1 rounded-full bg-green-100 px-1.5 py-0.5 text-[10px] font-medium text-green-700 dark:bg-green-900/30 dark:text-green-300">
                            <CheckCircle2 className="h-2.5 w-2.5" />
                            推荐
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-zinc-500 dark:text-zinc-400">
                        {option.description}
                      </p>
                    </div>
                    {isSelected && (
                      <div
                        className={cn(
                          'h-3 w-3 rounded-full',
                          option.id === 'standard' && 'bg-blue-500',
                          option.id === 'open_earth' && 'bg-purple-500',
                          option.id === 'mixed' && 'bg-green-500'
                        )}
                      />
                    )}
                  </div>
                </button>
              );
            })}
          </div>

          {/* 路由信息 */}
          {showRouteInfo && routeResult && (
            <div className="mt-4 rounded-lg bg-zinc-50 p-3 dark:bg-zinc-900">
              <div className="flex items-start gap-2">
                <Info className="mt-0.5 h-4 w-4 flex-shrink-0 text-zinc-400" />
                <div className="flex-1">
                  <p className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
                    路由判定
                  </p>
                  <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
                    {routeResult.explanation}
                  </p>
                  {routeResult.reasons.length > 0 && (
                    <ul className="mt-2 space-y-1">
                      {routeResult.reasons.map((reason, i) => (
                        <li key={i} className="flex items-center gap-1.5 text-xs text-zinc-500">
                          <span className="h-1 w-1 rounded-full bg-zinc-400" />
                          {reason}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* 对比说明 */}
          <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-lg bg-blue-50 p-2 dark:bg-blue-900/10">
              <p className="font-medium text-blue-700 dark:text-blue-300">标准模式</p>
              <p className="mt-0.5 text-blue-600 dark:text-blue-400">
                稳定、快速，适合已知任务
              </p>
            </div>
            <div className="rounded-lg bg-purple-50 p-2 dark:bg-purple-900/10">
              <p className="font-medium text-purple-700 dark:text-purple-300">OpenEarth 增强</p>
              <p className="mt-0.5 text-purple-600 dark:text-purple-400">
                智能、灵活，适合复杂任务
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
