/**
 * 知识库管理组件
 *
 * 提供完整的知识库管理功能：
 * - 知识条目列表（支持筛选、搜索）
 * - 创建、编辑、删除条目
 * - 向量检索测试
 * - 导入/导出功能
 */

import { useState, useEffect, useCallback } from 'react';
import {
  BookOpen,
  Search,
  Plus,
  Edit2,
  Trash2,
  Download,
  Upload,
  RefreshCw,
  Save,
  X,
  ChevronLeft,
  ChevronRight,
  Tag,
  Star,
  Clock,
  FileText,
  Zap,
  Database,
  Check,
  AlertCircle,
} from 'lucide-react';
import { cn } from '../../lib/utils.js';
import {
  type KnowledgeEntry,
  type KnowledgeEntryType,
  type KnowledgeSearchResult,
  type KnowledgeStats,
  listKnowledgeEntries,
  createKnowledgeEntry,
  updateKnowledgeEntry,
  deleteKnowledgeEntry,
  searchKnowledge,
  getKnowledgeStats,
  exportKnowledge,
  importKnowledge,
  rebuildKnowledgeIndex,
} from '../../utils/openEarthAgent';

const ENTRY_TYPE_LABELS: Record<KnowledgeEntryType, { label: string; color: string }> = {
  geoknowledge: { label: '地理知识', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' },
  tool_doc: { label: '工具文档', color: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300' },
  tool_fallback: { label: '工具回退', color: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300' },
  best_practice: { label: '最佳实践', color: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' },
  workflow: { label: '工作流', color: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300' },
  faq: { label: '常见问题', color: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300' },
  custom: { label: '自定义', color: 'bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300' },
};

const SEARCH_MODES = [
  { value: 'hybrid', label: '混合检索' },
  { value: 'vector', label: '向量检索' },
  { value: 'keyword', label: '关键词检索' },
];

type EntryFormData = {
  entry_type: KnowledgeEntryType;
  title: string;
  content: string;
  tags: string;
  importance: number;
};

const defaultFormData: EntryFormData = {
  entry_type: 'custom',
  title: '',
  content: '',
  tags: '',
  importance: 0,
};

export function KnowledgeManager() {
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [filterType, setFilterType] = useState<KnowledgeEntryType | ''>('');
  const [searchText, setSearchText] = useState('');
  const [page, setPage] = useState(0);
  const pageSize = 10;

  const [selectedEntry, setSelectedEntry] = useState<KnowledgeEntry | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState<EntryFormData>(defaultFormData);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [searchQuery, setSearchQuery] = useState('');
  const [searchMode, setSearchMode] = useState<'hybrid' | 'vector' | 'keyword'>('hybrid');
  const [searchResults, setSearchResults] = useState<KnowledgeSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [showSearchPanel, setShowSearchPanel] = useState(false);

  const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const loadStats = useCallback(async () => {
    try {
      const data = await getKnowledgeStats();
      setStats(data);
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  }, []);

  const loadEntries = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await listKnowledgeEntries({
        type: filterType || undefined,
        search: searchText || undefined,
        limit: pageSize,
        offset: page * pageSize,
      });
      setEntries(response.entries);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load entries');
      console.error('Failed to load entries:', err);
    } finally {
      setLoading(false);
    }
  }, [filterType, searchText, page]);

  useEffect(() => {
    loadStats();
    loadEntries();
  }, [loadStats, loadEntries]);

  const handleCreate = () => {
    setFormData(defaultFormData);
    setFormError(null);
    setIsCreating(true);
    setIsEditing(false);
    setSelectedEntry(null);
  };

  const handleEdit = (entry: KnowledgeEntry) => {
    setFormData({
      entry_type: entry.entry_type,
      title: entry.title,
      content: entry.content,
      tags: entry.tags.join(', '),
      importance: entry.importance,
    });
    setFormError(null);
    setSelectedEntry(entry);
    setIsEditing(true);
    setIsCreating(false);
  };

  const handleView = (entry: KnowledgeEntry) => {
    setSelectedEntry(entry);
    setIsEditing(false);
    setIsCreating(false);
  };

  const handleCloseForm = () => {
    setIsCreating(false);
    setIsEditing(false);
    setFormData(defaultFormData);
    setFormError(null);
    setSelectedEntry(null);
  };

  const handleSave = async () => {
    if (!formData.title.trim()) {
      setFormError('请输入标题');
      return;
    }
    if (!formData.content.trim()) {
      setFormError('请输入内容');
      return;
    }

    setSaving(true);
    setFormError(null);

    try {
      const tags = formData.tags
        .split(/[,\s]+/)
        .map((t) => t.trim())
        .filter((t) => t);

      const entryData = {
        entry_type: formData.entry_type,
        title: formData.title.trim(),
        content: formData.content.trim(),
        tags,
        importance: formData.importance,
        metadata: {},
      };

      if (isCreating) {
        await createKnowledgeEntry(entryData);
        setActionMessage({ type: 'success', text: '知识条目创建成功' });
      } else if (isEditing && selectedEntry) {
        await updateKnowledgeEntry(selectedEntry.entry_id, entryData);
        setActionMessage({ type: 'success', text: '知识条目更新成功' });
      }

      handleCloseForm();
      await loadStats();
      await loadEntries();

      setTimeout(() => setActionMessage(null), 3000);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (entry: KnowledgeEntry) => {
    if (!confirm(`确定要删除 "${entry.title}" 吗？`)) {
      return;
    }

    try {
      await deleteKnowledgeEntry(entry.entry_id);
      setActionMessage({ type: 'success', text: '知识条目已删除' });

      if (selectedEntry?.entry_id === entry.entry_id) {
        setSelectedEntry(null);
      }

      await loadStats();
      await loadEntries();

      setTimeout(() => setActionMessage(null), 3000);
    } catch (err) {
      setActionMessage({ type: 'error', text: err instanceof Error ? err.message : '删除失败' });
      setTimeout(() => setActionMessage(null), 3000);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      return;
    }

    setSearching(true);
    try {
      const results = await searchKnowledge(searchQuery.trim(), {
        limit: 10,
        mode: searchMode,
      });
      setSearchResults(results);
      setShowSearchPanel(true);
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setSearching(false);
    }
  };

  const handleExport = async () => {
    try {
      const result = await exportKnowledge();
      const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `knowledge_export_${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      setActionMessage({ type: 'success', text: `已导出 ${result.count} 条知识` });
      setTimeout(() => setActionMessage(null), 3000);
    } catch (err) {
      setActionMessage({ type: 'error', text: '导出失败' });
      setTimeout(() => setActionMessage(null), 3000);
    }
  };

  const handleImport = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;

      try {
        const text = await file.text();
        const data = JSON.parse(text);
        const entries = data.entries || data;

        if (!Array.isArray(entries)) {
          throw new Error('无效的导入格式');
        }

        const overwrite = confirm('是否覆盖已存在的同名条目？');
        const result = await importKnowledge(entries, { overwrite });

        setActionMessage({ type: 'success', text: `已导入 ${result.imported}/${result.total} 条知识` });
        await loadStats();
        await loadEntries();
        setTimeout(() => setActionMessage(null), 3000);
      } catch (err) {
        setActionMessage({ type: 'error', text: '导入失败：' + (err instanceof Error ? err.message : '未知错误') });
        setTimeout(() => setActionMessage(null), 3000);
      }
    };
    input.click();
  };

  const handleRebuildIndex = async () => {
    if (!confirm('确定要重建向量索引吗？这可能需要一些时间。')) {
      return;
    }

    try {
      const result = await rebuildKnowledgeIndex();
      setActionMessage({ type: 'success', text: `索引重建完成，共 ${result.stats.document_count} 个文档` });
      await loadStats();
      setTimeout(() => setActionMessage(null), 3000);
    } catch (err) {
      setActionMessage({ type: 'error', text: '索引重建失败' });
      setTimeout(() => setActionMessage(null), 3000);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="h-full flex flex-col bg-white dark:bg-zinc-900">
      <div className="border-b border-zinc-200 px-4 py-3 dark:border-zinc-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-blue-500" />
            <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">知识库管理</h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleRebuildIndex}
              className="flex items-center gap-1 rounded-md px-2 py-1.5 text-xs text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
              title="重建向量索引"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              重建索引
            </button>
            <button
              onClick={handleExport}
              className="flex items-center gap-1 rounded-md px-2 py-1.5 text-xs text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
            >
              <Download className="h-3.5 w-3.5" />
              导出
            </button>
            <button
              onClick={handleImport}
              className="flex items-center gap-1 rounded-md px-2 py-1.5 text-xs text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
            >
              <Upload className="h-3.5 w-3.5" />
              导入
            </button>
            <button
              onClick={handleCreate}
              className="flex items-center gap-1 rounded-md bg-blue-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-600"
            >
              <Plus className="h-3.5 w-3.5" />
              新建条目
            </button>
          </div>
        </div>

        {stats && (
          <div className="mt-3 flex flex-wrap gap-3">
            <div className="flex items-center gap-1.5 rounded-md bg-blue-50 px-2 py-1 text-xs text-blue-700 dark:bg-blue-900/20 dark:text-blue-300">
              <Database className="h-3 w-3" />
              共 {stats.total_entries} 条
            </div>
            {Object.entries(stats.entries_by_type).map(([type, count]) => {
              const info = ENTRY_TYPE_LABELS[type as KnowledgeEntryType];
              if (!info || count === 0) return null;
              return (
                <div
                  key={type}
                  className={cn('flex items-center gap-1.5 rounded-md px-2 py-1 text-xs', info.color)}
                >
                  <FileText className="h-3 w-3" />
                  {info.label}: {count}
                </div>
              );
            })}
          </div>
        )}

        {actionMessage && (
          <div
            className={cn(
              'mt-3 flex items-center gap-2 rounded-md px-3 py-2 text-sm',
              actionMessage.type === 'success'
                ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300'
                : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300'
            )}
          >
            {actionMessage.type === 'success' ? (
              <Check className="h-4 w-4" />
            ) : (
              <AlertCircle className="h-4 w-4" />
            )}
            {actionMessage.text}
          </div>
        )}
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 flex flex-col min-w-0">
          <div className="border-b border-zinc-200 px-4 py-2 dark:border-zinc-800">
            <div className="flex items-center gap-2 flex-wrap">
              <select
                value={filterType}
                onChange={(e) => {
                  setFilterType(e.target.value as KnowledgeEntryType | '');
                  setPage(0);
                }}
                className="rounded-md border border-zinc-300 bg-white px-2 py-1 text-sm dark:border-zinc-600 dark:bg-zinc-800"
              >
                <option value="">全部类型</option>
                {Object.entries(ENTRY_TYPE_LABELS).map(([value, info]) => (
                  <option key={value} value={value}>
                    {info.label}
                  </option>
                ))}
              </select>

              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
                <input
                  type="text"
                  placeholder="搜索标题或内容..."
                  value={searchText}
                  onChange={(e) => {
                    setSearchText(e.target.value);
                    setPage(0);
                  }}
                  className="w-full rounded-md border border-zinc-300 bg-white py-1.5 pl-8 pr-2 text-sm dark:border-zinc-600 dark:bg-zinc-800"
                />
              </div>

              <div className="flex items-center gap-2 ml-auto">
                <select
                  value={searchMode}
                  onChange={(e) => setSearchMode(e.target.value as any)}
                  className="rounded-md border border-zinc-300 bg-white px-2 py-1 text-xs dark:border-zinc-600 dark:bg-zinc-800"
                >
                  {SEARCH_MODES.map((m) => (
                    <option key={m.value} value={m.value}>
                      {m.label}
                    </option>
                  ))}
                </select>
                <div className="relative">
                  <input
                    type="text"
                    placeholder="向量检索测试..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                    className="w-48 rounded-md border border-zinc-300 bg-white px-2 py-1 text-xs dark:border-zinc-600 dark:bg-zinc-800"
                  />
                </div>
                <button
                  onClick={handleSearch}
                  disabled={searching || !searchQuery.trim()}
                  className="flex items-center gap-1 rounded-md bg-zinc-100 px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-200 disabled:opacity-50 dark:bg-zinc-700 dark:text-zinc-200"
                >
                  {searching ? <RefreshCw className="h-3 w-3 animate-spin" /> : <Zap className="h-3 w-3" />}
                  检索
                </button>
              </div>
            </div>
          </div>

          <div className="flex-1 overflow-auto">
            {loading ? (
              <div className="flex h-full items-center justify-center">
                <RefreshCw className="h-6 w-6 animate-spin text-zinc-400" />
              </div>
            ) : error ? (
              <div className="flex h-full items-center justify-center text-red-500">{error}</div>
            ) : entries.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center text-zinc-400">
                <BookOpen className="mb-2 h-12 w-12" />
                <p>暂无知识条目</p>
              </div>
            ) : (
              <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
                {entries.map((entry) => {
                  const typeInfo = ENTRY_TYPE_LABELS[entry.entry_type];
                  return (
                    <div
                      key={entry.entry_id}
                      className={cn(
                        'flex items-start justify-between gap-4 px-4 py-3 hover:bg-zinc-50 dark:hover:bg-zinc-800/50',
                        selectedEntry?.entry_id === entry.entry_id && 'bg-blue-50 dark:bg-blue-900/20'
                      )}
                    >
                      <div className="flex-1 min-w-0 cursor-pointer" onClick={() => handleView(entry)}>
                        <div className="flex items-center gap-2">
                          <span className={cn('rounded px-1.5 py-0.5 text-[10px] font-medium', typeInfo.color)}>
                            {typeInfo.label}
                          </span>
                          <h3 className="font-medium text-zinc-900 dark:text-zinc-100 truncate">{entry.title}</h3>
                          {entry.importance > 0 && (
                            <div className="flex items-center">
                              {Array.from({ length: entry.importance }).map((_, i) => (
                                <Star key={i} className="h-3 w-3 fill-amber-400 text-amber-400" />
                              ))}
                            </div>
                          )}
                        </div>
                        <p className="mt-1 line-clamp-2 text-sm text-zinc-500 dark:text-zinc-400">
                          {entry.content}
                        </p>
                        {entry.tags.length > 0 && (
                          <div className="mt-1 flex flex-wrap gap-1">
                            {entry.tags.slice(0, 5).map((tag) => (
                              <span
                                key={tag}
                                className="inline-flex items-center gap-0.5 rounded bg-zinc-100 px-1.5 py-0.5 text-[10px] text-zinc-600 dark:bg-zinc-700 dark:text-zinc-300"
                              >
                                <Tag className="h-2.5 w-2.5" />
                                {tag}
                              </span>
                            ))}
                            {entry.tags.length > 5 && (
                              <span className="text-[10px] text-zinc-400">+{entry.tags.length - 5}</span>
                            )}
                          </div>
                        )}
                        <div className="mt-1 flex items-center gap-3 text-[10px] text-zinc-400">
                          <span className="flex items-center gap-0.5">
                            <Clock className="h-2.5 w-2.5" />
                            {entry.updated_at ? new Date(entry.updated_at).toLocaleDateString() : '-'}
                          </span>
                          <span>访问 {entry.access_count} 次</span>
                          <span>v{entry.version}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleEdit(entry)}
                          className="rounded-md p-1.5 text-zinc-400 hover:bg-zinc-100 hover:text-blue-500 dark:hover:bg-zinc-700"
                          title="编辑"
                        >
                          <Edit2 className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(entry)}
                          className="rounded-md p-1.5 text-zinc-400 hover:bg-zinc-100 hover:text-red-500 dark:hover:bg-zinc-700"
                          title="删除"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-zinc-200 px-4 py-2 dark:border-zinc-800">
              <span className="text-xs text-zinc-500">
                共 {total} 条，第 {page + 1}/{totalPages} 页
              </span>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="rounded-md p-1 text-zinc-500 hover:bg-zinc-100 disabled:opacity-50 dark:hover:bg-zinc-800"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="text-sm text-zinc-500">
                  {page + 1} / {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                  disabled={page >= totalPages - 1}
                  className="rounded-md p-1 text-zinc-500 hover:bg-zinc-100 disabled:opacity-50 dark:hover:bg-zinc-800"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </div>

        {(isCreating || isEditing || selectedEntry) && (
          <div className="w-96 border-l border-zinc-200 flex flex-col bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-800/50">
            <div className="flex items-center justify-between border-b border-zinc-200 px-3 py-2 dark:border-zinc-700">
              <h3 className="font-medium text-zinc-900 dark:text-zinc-100">
                {isCreating ? '新建知识条目' : isEditing ? '编辑知识条目' : '知识详情'}
              </h3>
              <button
                onClick={handleCloseForm}
                className="rounded p-1 text-zinc-400 hover:bg-zinc-200 dark:hover:bg-zinc-700"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="flex-1 overflow-auto p-4">
              {(isCreating || isEditing) ? (
                <div className="space-y-4">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-zinc-600 dark:text-zinc-400">
                      条目类型
                    </label>
                    <select
                      value={formData.entry_type}
                      onChange={(e) =>
                        setFormData({ ...formData, entry_type: e.target.value as KnowledgeEntryType })
                      }
                      className="w-full rounded-md border border-zinc-300 bg-white px-2 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800"
                    >
                      {Object.entries(ENTRY_TYPE_LABELS).map(([value, info]) => (
                        <option key={value} value={value}>
                          {info.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="mb-1 block text-xs font-medium text-zinc-600 dark:text-zinc-400">
                      标题 <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.title}
                      onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                      className="w-full rounded-md border border-zinc-300 bg-white px-2 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800"
                      placeholder="输入标题..."
                    />
                  </div>

                  <div>
                    <label className="mb-1 block text-xs font-medium text-zinc-600 dark:text-zinc-400">
                      内容 <span className="text-red-500">*</span>
                    </label>
                    <textarea
                      value={formData.content}
                      onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                      rows={12}
                      className="w-full rounded-md border border-zinc-300 bg-white px-2 py-1.5 text-sm font-mono dark:border-zinc-600 dark:bg-zinc-800"
                      placeholder="输入详细内容，支持 Markdown..."
                    />
                  </div>

                  <div>
                    <label className="mb-1 block text-xs font-medium text-zinc-600 dark:text-zinc-400">
                      标签（用逗号或空格分隔）
                    </label>
                    <input
                      type="text"
                      value={formData.tags}
                      onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
                      className="w-full rounded-md border border-zinc-300 bg-white px-2 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800"
                      placeholder="例如: ndvi, 植被, 遥感"
                    />
                  </div>

                  <div>
                    <label className="mb-1 block text-xs font-medium text-zinc-600 dark:text-zinc-400">
                      重要性: {formData.importance}
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="5"
                      value={formData.importance}
                      onChange={(e) => setFormData({ ...formData, importance: parseInt(e.target.value) })}
                      className="w-full"
                    />
                    <div className="flex justify-between text-[10px] text-zinc-400">
                      <span>0 (普通)</span>
                      <span>5 (最高)</span>
                    </div>
                  </div>

                  {formError && (
                    <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-300">
                      {formError}
                    </div>
                  )}
                </div>
              ) : (
                selectedEntry && (
                  <div className="space-y-4">
                    <div>
                      <span
                        className={cn(
                          'rounded px-2 py-0.5 text-xs font-medium',
                          ENTRY_TYPE_LABELS[selectedEntry.entry_type].color
                        )}
                      >
                        {ENTRY_TYPE_LABELS[selectedEntry.entry_type].label}
                      </span>
                      <h3 className="mt-2 text-lg font-medium text-zinc-900 dark:text-zinc-100">
                        {selectedEntry.title}
                      </h3>
                      {selectedEntry.importance > 0 && (
                        <div className="mt-1 flex items-center">
                          {Array.from({ length: selectedEntry.importance }).map((_, i) => (
                            <Star key={i} className="h-4 w-4 fill-amber-400 text-amber-400" />
                          ))}
                        </div>
                      )}
                    </div>

                    {selectedEntry.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {selectedEntry.tags.map((tag) => (
                          <span
                            key={tag}
                            className="inline-flex items-center gap-0.5 rounded bg-zinc-100 px-2 py-0.5 text-xs text-zinc-600 dark:bg-zinc-700 dark:text-zinc-300"
                          >
                            <Tag className="h-3 w-3" />
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}

                    <div className="rounded-md bg-white p-3 whitespace-pre-wrap text-sm text-zinc-700 dark:bg-zinc-900 dark:text-zinc-300">
                      {selectedEntry.content}
                    </div>

                    <div className="space-y-1 text-xs text-zinc-500">
                      <p>创建时间: {new Date(selectedEntry.created_at).toLocaleString()}</p>
                      <p>更新时间: {new Date(selectedEntry.updated_at).toLocaleString()}</p>
                      <p>访问次数: {selectedEntry.access_count}</p>
                      <p>版本: v{selectedEntry.version}</p>
                    </div>

                    <div className="flex gap-2">
                      <button
                        onClick={() => handleEdit(selectedEntry)}
                        className="flex-1 flex items-center justify-center gap-1 rounded-md bg-blue-500 px-3 py-2 text-sm text-white hover:bg-blue-600"
                      >
                        <Edit2 className="h-4 w-4" />
                        编辑
                      </button>
                      <button
                        onClick={() => handleDelete(selectedEntry)}
                        className="flex items-center justify-center gap-1 rounded-md border border-red-300 px-3 py-2 text-sm text-red-600 hover:bg-red-50 dark:border-red-700 dark:hover:bg-red-900/20"
                      >
                        <Trash2 className="h-4 w-4" />
                        删除
                      </button>
                    </div>
                  </div>
                )
              )}
            </div>

            {(isCreating || isEditing) && (
              <div className="border-t border-zinc-200 px-3 py-2 dark:border-zinc-700">
                <div className="flex gap-2">
                  <button
                    onClick={handleCloseForm}
                    className="flex-1 rounded-md border border-zinc-300 px-3 py-2 text-sm text-zinc-600 hover:bg-zinc-100 dark:border-zinc-600 dark:text-zinc-400 dark:hover:bg-zinc-700"
                  >
                    取消
                  </button>
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    className="flex-1 flex items-center justify-center gap-1 rounded-md bg-blue-500 px-3 py-2 text-sm text-white hover:bg-blue-600 disabled:opacity-50"
                  >
                    {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                    保存
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {showSearchPanel && !isCreating && !isEditing && (
          <div className="w-80 border-l border-zinc-200 flex flex-col bg-amber-50 dark:border-zinc-800 dark:bg-amber-900/10">
            <div className="flex items-center justify-between border-b border-zinc-200 px-3 py-2 dark:border-zinc-700">
              <h3 className="font-medium text-zinc-900 dark:text-zinc-100">检索结果</h3>
              <button
                onClick={() => setShowSearchPanel(false)}
                className="rounded p-1 text-zinc-400 hover:bg-zinc-200 dark:hover:bg-zinc-700"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="flex-1 overflow-auto p-3">
              {searchResults.length === 0 ? (
                <div className="text-center text-zinc-500">
                  <p>未找到匹配的知识</p>
                  <p className="mt-1 text-xs">尝试使用其他关键词</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {searchResults.map((result, index) => {
                    const typeInfo = ENTRY_TYPE_LABELS[result.entry_type];
                    return (
                      <div
                        key={result.entry_id}
                        className="rounded-md bg-white p-3 shadow-sm dark:bg-zinc-800 cursor-pointer hover:ring-2 hover:ring-blue-300"
                        onClick={() => handleView(result)}
                      >
                        <div className="flex items-center justify-between">
                          <span className={cn('rounded px-1.5 py-0.5 text-[10px]', typeInfo.color)}>
                            {typeInfo.label}
                          </span>
                          <span className="text-xs text-zinc-500">
                            得分: {(result.score * 100).toFixed(1)}%
                          </span>
                        </div>
                        <h4 className="mt-1 font-medium text-zinc-900 dark:text-zinc-100">{result.title}</h4>
                        <p className="mt-1 line-clamp-2 text-xs text-zinc-500 dark:text-zinc-400">
                          {result.content}
                        </p>
                        <div className="mt-1 flex items-center gap-1">
                          <span className="text-[10px] text-zinc-400">
                            {result.search_mode === 'vector' ? '向量检索' : '关键词检索'}
                          </span>
                          {index === 0 && (
                            <span className="text-[10px] text-amber-500">最佳匹配</span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
