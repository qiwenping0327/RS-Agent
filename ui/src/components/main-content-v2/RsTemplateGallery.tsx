/**
 * 任务模板库组件
 */

import { useState } from 'react';
import { Sparkles, Download, Layers, BarChart3, ChevronRight } from 'lucide-react';
import { cn } from '../../lib/utils.js';

type Template = {
  id: string;
  name: string;
  description: string;
  category: string;
  tool: string;
  params: Record<string, unknown>;
  tags: string[];
};

type Props = {
  onApply: (template: Template) => void;
};

const BUILTIN_TEMPLATES: Template[] = [
  {
    id: 'sentinel2-ndvi',
    name: 'Sentinel-2 NDVI 分析',
    description: '下载 Sentinel-2 影像并计算 NDVI 植被指数',
    category: 'analyze',
    tool: 'rs_analyze',
    params: { sensor: 'sentinel2', analysisType: 'ndvi' },
    tags: ['sentinel2', 'ndvi', 'vegetation'],
  },
  {
    id: 'landsat8-download',
    name: 'Landsat-8 影像下载',
    description: '下载 Landsat-8 卫星影像',
    category: 'download',
    tool: 'rs_download',
    params: { sensor: 'landsat8', maxCloudCover: 20 },
    tags: ['landsat8', 'download'],
  },
  {
    id: 'atmospheric-correction',
    name: '大气校正',
    description: '对遥感影像执行大气校正处理',
    category: 'preprocess',
    tool: 'rs_preprocess',
    params: { operations: ['radiometric_correction', 'atmospheric_correction'] },
    tags: ['preprocess', 'atmospheric'],
  },
  {
    id: 'gf1-download',
    name: '高分一号影像下载',
    description: '下载高分一号卫星影像',
    category: 'download',
    tool: 'rs_download',
    params: { sensor: 'gf1' },
    tags: ['gf1', 'download'],
  },
  {
    id: 'water-detection',
    name: '水体检测 (NDWI)',
    description: '使用 NDWI 指数检测水体分布',
    category: 'analyze',
    tool: 'rs_analyze',
    params: { sensor: 'sentinel2', analysisType: 'ndwi' },
    tags: ['ndwi', 'water', '水体'],
  },
  {
    id: 'change-detection',
    name: '变化检测',
    description: '双时相遥感影像变化检测分析',
    category: 'analyze',
    tool: 'rs_analyze',
    params: { analysisType: 'change_detection' },
    tags: ['change', '变化', '检测'],
  },
];

const CATEGORY_ICONS: Record<string, typeof Download> = {
  download: Download,
  preprocess: Layers,
  analyze: BarChart3,
};

export default function RsTemplateGallery({ onApply }: Props) {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const categories = [...new Set(BUILTIN_TEMPLATES.map((t) => t.category))];
  const filtered = selectedCategory
    ? BUILTIN_TEMPLATES.filter((t) => t.category === selectedCategory)
    : BUILTIN_TEMPLATES;

  return (
    <div className="border-b border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-800">
      <div className="mb-4 flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-blue-500" />
        <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">任务模板</h2>
      </div>

      {/* 分类筛选 */}
      <div className="mb-4 flex gap-2">
        <button
          onClick={() => setSelectedCategory(null)}
          className={cn(
            'rounded-full px-3 py-1 text-xs font-medium transition-colors',
            !selectedCategory
              ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
              : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-700 dark:text-zinc-400'
          )}
        >
          全部
        </button>
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={cn(
              'rounded-full px-3 py-1 text-xs font-medium transition-colors',
              selectedCategory === cat
                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-700 dark:text-zinc-400'
            )}
          >
            {cat === 'download' ? '下载' : cat === 'preprocess' ? '预处理' : '分析'}
          </button>
        ))}
      </div>

      {/* 模板列表 */}
      <div className="grid grid-cols-2 gap-3">
        {filtered.map((tpl) => {
          const Icon = CATEGORY_ICONS[tpl.category] ?? BarChart3;
          return (
            <button
              key={tpl.id}
              onClick={() => onApply(tpl)}
              className="flex items-start gap-3 rounded-lg border border-zinc-200 p-3 text-left transition-colors hover:border-blue-300 hover:bg-blue-50/50 dark:border-zinc-700 dark:hover:border-blue-600 dark:hover:bg-blue-900/10"
            >
              <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-zinc-100 dark:bg-zinc-700">
                <Icon className="h-4 w-4 text-zinc-600 dark:text-zinc-400" />
              </div>
              <div className="flex-1">
                <div className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
                  {tpl.name}
                </div>
                <div className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
                  {tpl.description}
                </div>
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {tpl.tags.slice(0, 3).map((tag) => (
                    <span
                      key={tag}
                      className="rounded bg-zinc-100 px-1.5 py-0.5 text-[10px] text-zinc-500 dark:bg-zinc-700 dark:text-zinc-400"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
              <ChevronRight className="h-4 w-4 flex-shrink-0 text-zinc-400" />
            </button>
          );
        })}
      </div>
    </div>
  );
}
