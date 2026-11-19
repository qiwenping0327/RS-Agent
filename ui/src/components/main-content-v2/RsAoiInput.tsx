/**
 * AOI (感兴趣区域) 输入组件
 */

import { MapPin } from 'lucide-react';
import { cn } from '../../lib/utils.js';

type Props = {
  value: string;
  onChange: (v: string) => void;
  show: boolean;
};

const PRESET_REGIONS = ['北京', '上海', '广州', '成都', '武汉', '深圳'];

export default function RsAoiInput({ value, onChange, show }: Props) {
  if (!show) return null;

  return (
    <div className="px-4 pb-3">
      <label className="mb-2 flex items-center gap-1.5 text-sm font-medium text-zinc-700 dark:text-zinc-300">
        <MapPin className="h-4 w-4" />
        感兴趣区域 (AOI)
      </label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="输入地名(如: 北京) 或 GeoJSON"
        className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-700 placeholder:text-zinc-400 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-300 dark:placeholder:text-zinc-500"
      />
      <div className="mt-2 flex flex-wrap gap-1.5">
        {PRESET_REGIONS.map((region) => (
          <button
            key={region}
            onClick={() => onChange(region)}
            className={cn(
              'rounded-full border px-2.5 py-0.5 text-xs transition-colors',
              value === region
                ? 'border-blue-500 bg-blue-50 text-blue-700 dark:border-blue-400 dark:bg-blue-900/30 dark:text-blue-300'
                : 'border-zinc-200 text-zinc-500 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-400 dark:hover:bg-zinc-800'
            )}
          >
            {region}
          </button>
        ))}
      </div>
    </div>
  );
}
