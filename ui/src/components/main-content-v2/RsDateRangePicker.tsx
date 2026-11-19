/**
 * 日期范围选择器组件
 */

import { Calendar } from 'lucide-react';

type Props = {
  startDate: string;
  endDate: string;
  onStartChange: (v: string) => void;
  onEndChange: (v: string) => void;
  show: boolean;
};

export default function RsDateRangePicker({
  startDate,
  endDate,
  onStartChange,
  onEndChange,
  show,
}: Props) {
  if (!show) return null;

  return (
    <div className="px-4 pb-3">
      <label className="mb-2 flex items-center gap-1.5 text-sm font-medium text-zinc-700 dark:text-zinc-300">
        <Calendar className="h-4 w-4" />
        时间范围
      </label>
      <div className="flex items-center gap-2">
        <input
          type="date"
          value={startDate}
          onChange={(e) => onStartChange(e.target.value)}
          className="flex-1 rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-700 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-300"
        />
        <span className="text-sm text-zinc-400">至</span>
        <input
          type="date"
          value={endDate}
          onChange={(e) => onEndChange(e.target.value)}
          className="flex-1 rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-700 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-300"
        />
      </div>
    </div>
  );
}
