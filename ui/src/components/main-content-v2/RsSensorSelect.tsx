/**
 * 传感器选择器组件
 */

import { useState } from 'react';
import { Satellite } from 'lucide-react';
import { cn } from '../../lib/utils.js';

type Props = {
  value: string;
  onChange: (v: string) => void;
  show: boolean;
};

const SENSORS = [
  { id: 'sentinel2', name: 'Sentinel-2', resolution: '10m', bands: 13, color: 'bg-blue-500' },
  { id: 'landsat8', name: 'Landsat-8', resolution: '30m', bands: 11, color: 'bg-green-500' },
  { id: 'gf1', name: '高分一号', resolution: '2m/8m', bands: 4, color: 'bg-red-500' },
  { id: 'gf2', name: '高分二号', resolution: '1m/4m', bands: 4, color: 'bg-orange-500' },
];

export default function RsSensorSelect({ value, onChange, show }: Props) {
  if (!show) return null;

  return (
    <div className="px-4 pb-3">
      <label className="mb-2 flex items-center gap-1.5 text-sm font-medium text-zinc-700 dark:text-zinc-300">
        <Satellite className="h-4 w-4" />
        传感器
      </label>
      <div className="grid grid-cols-2 gap-2">
        {SENSORS.map((s) => (
          <button
            key={s.id}
            onClick={() => onChange(s.id)}
            className={cn(
              'flex items-center gap-2 rounded-lg border px-3 py-2 text-left transition-colors',
              value === s.id
                ? 'border-blue-500 bg-blue-50 dark:border-blue-400 dark:bg-blue-900/30'
                : 'border-zinc-200 hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-800'
            )}
          >
            <div className={cn('h-2 w-2 rounded-full', s.color)} />
            <div>
              <div className="text-sm font-medium text-zinc-800 dark:text-zinc-200">{s.name}</div>
              <div className="text-xs text-zinc-500 dark:text-zinc-400">{s.resolution} · {s.bands}波段</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
