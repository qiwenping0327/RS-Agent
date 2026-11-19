import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Wrench,
  Search,
  Loader2,
  AlertCircle,
  Database,
} from 'lucide-react';
import { cn } from '../../lib/utils.js';
import { authenticatedFetch } from '../../utils/api.js';
import {
  getToolDescCN,
  getServerNameCN,
  getParamDescCN,
  extractToolName,
  TYPE_CN,
} from '../../utils/mcpToolTranslations';

type McpToolInfo = {
  name: string;
  description: string;
  inputSchema?: Record<string, unknown>;
  serverId?: string;
  pluginName?: string;
  command?: string;
  args?: string[];
  cwd?: string;
  type?: string;
  url?: string;
  isServerGroup?: boolean;
};

export default function ToolsV2() {
  const { t } = useTranslation();

  const [mcpTools, setMcpTools] = useState<McpToolInfo[]>([]);
  const [toolsSource, setToolsSource] = useState<string>('unknown');
  const [toolsNote, setToolsNote] = useState<string | null>(null);
  const [toolsLoading, setToolsLoading] = useState(true);
  const [toolsError, setToolsError] = useState<string | null>(null);
  const [toolSearch, setToolSearch] = useState('');
  const [selectedTool, setSelectedTool] = useState<McpToolInfo | null>(null);
  const [selectedServerId, setSelectedServerId] = useState<string | 'all'>('all');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setToolsLoading(true);
        const res = await authenticatedFetch('/api/tools');
        if (!res.ok) {
          const text = await res.text();
          throw new Error(
            text.startsWith('<!')
              ? '服务端返回了 HTML 而非 JSON，请重启 UI 服务'
              : `HTTP ${res.status}: ${text.slice(0, 200)}`,
          );
        }
        const data = await res.json();
        if (!cancelled) {
          setMcpTools(data.tools || []);
          setToolsSource(data.source || 'unknown');
          setToolsNote(data.note || null);
          setToolsError(null);
        }
      } catch (err) {
        if (!cancelled)
          setToolsError(err instanceof Error ? err.message : '获取工具列表失败');
      } finally {
        if (!cancelled) setToolsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const allServerIds = Array.from(
    new Set(mcpTools.map((tool) => tool.serverId).filter(Boolean) as string[]),
  ).sort();

  const filteredTools = mcpTools.filter((tool) => {
    if (selectedServerId !== 'all' && tool.serverId !== selectedServerId) {
      return false;
    }
    if (!toolSearch) return true;
    const q = toolSearch.toLowerCase();
    const cnDesc = getToolDescCN(tool.name, tool.description);
    return (
      tool.name.toLowerCase().includes(q) ||
      cnDesc.toLowerCase().includes(q) ||
      extractToolName(tool.name).toLowerCase().includes(q)
    );
  });

  const parseSchemaParams = (
    schema?: Record<string, unknown>,
  ): { name: string; type: string; required: boolean; description: string }[] => {
    if (!schema || !schema.properties) return [];
    const props = schema.properties as Record<string, unknown>;
    const required = (schema.required as string[]) || [];
    return Object.entries(props).map(([name, val]) => {
      const p = val as Record<string, unknown>;
      const originalDesc = (p.description as string) || '';
      return {
        name,
        type: (p.type as string) || 'any',
        required: required.includes(name),
        description: getParamDescCN(name, originalDesc),
      };
    });
  };

  const toolCountByServer = allServerIds.reduce((acc, serverId) => {
    acc[serverId] = mcpTools.filter((t) => t.serverId === serverId).length;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-3 border-b border-zinc-200 px-6 py-4 dark:border-zinc-700">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500">
          <Wrench className="h-5 w-5 text-white" />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
            {t('tabs.tools', { defaultValue: '工具' })}
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            MCP 工具列表 · 共 {mcpTools.length} 个可用工具
          </p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          {allServerIds.length > 0 && (
            <select
              value={selectedServerId}
              onChange={(e) => setSelectedServerId(e.target.value)}
              className="rounded-lg border border-zinc-300 bg-white px-3 py-1.5 text-sm text-zinc-700 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-300"
            >
              <option value="all">全部服务</option>
              {allServerIds.map((serverId) => (
                <option key={serverId} value={serverId}>
                  {getServerNameCN(serverId)} ({toolCountByServer[serverId]})
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        <div className="w-96 flex-shrink-0 overflow-y-auto border-r border-zinc-200 dark:border-zinc-700">
          <div className="px-4 pt-3 pb-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
              <input
                type="text"
                value={toolSearch}
                onChange={(e) => setToolSearch(e.target.value)}
                placeholder="搜索工具名称或描述..."
                className="w-full rounded-lg border border-zinc-300 bg-white py-2 pl-10 pr-3 text-sm text-zinc-700 placeholder:text-zinc-400 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-300 dark:placeholder:text-zinc-500"
              />
            </div>
          </div>

          {toolsNote && !toolsLoading && (
            <div className="mx-4 mb-2 rounded-lg bg-yellow-50 px-3 py-2 text-xs text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-300">
              {toolsNote}
            </div>
          )}

          {toolsLoading ? (
            <div className="flex items-center justify-center py-12 text-zinc-400 dark:text-zinc-500">
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              加载工具列表...
            </div>
          ) : toolsError ? (
            <div className="flex flex-col items-center justify-center py-12 text-red-400">
              <AlertCircle className="mb-2 h-8 w-8" />
              <p className="text-sm">{toolsError}</p>
            </div>
          ) : (
            <div className="px-4 pb-2">
              <p className="mb-2 text-xs text-zinc-500 dark:text-zinc-400">
                显示 {filteredTools.length}/{mcpTools.length} 个{' '}
                {toolsSource === 'gateway' ? '工具' : 'MCP 服务'}
              </p>
              <div className="space-y-1 overflow-y-auto max-h-[calc(100vh-220px)]">
                {filteredTools.map((tool) => (
                  <button
                    key={tool.name}
                    onClick={() =>
                      setSelectedTool(selectedTool?.name === tool.name ? null : tool)
                    }
                    className={cn(
                      'w-full rounded-lg border px-3 py-2 text-left transition-colors',
                      selectedTool?.name === tool.name
                        ? 'border-blue-500 bg-blue-50 dark:border-blue-400 dark:bg-blue-900/30'
                        : 'border-zinc-200 hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-800',
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <Wrench className="h-3.5 w-3.5 flex-shrink-0 text-zinc-500 dark:text-zinc-400" />
                      <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100 truncate">
                        {tool.name}
                      </span>
                      {tool.isServerGroup && (
                        <span className="text-xs rounded bg-blue-100 px-1.5 py-0.5 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300">
                          服务组
                        </span>
                      )}
                      {tool.serverId && !tool.isServerGroup && (
                        <span className="ml-auto text-xs text-zinc-400 dark:text-zinc-500 truncate max-w-[100px]">
                          {getServerNameCN(tool.serverId)}
                        </span>
                      )}
                    </div>
                    <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400 line-clamp-2">
                      {getToolDescCN(tool.name, tool.description)}
                    </p>
                  </button>
                ))}
                {filteredTools.length === 0 && !toolsLoading && (
                  <p className="py-8 text-center text-sm text-zinc-400">未找到匹配工具</p>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto bg-zinc-50 dark:bg-zinc-900">
          {selectedTool ? (
            <div className="p-6">
              <div className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-700 dark:bg-zinc-800">
                <div className="flex items-center gap-3 mb-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900/30">
                    <Wrench className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div>
                    <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
                      {extractToolName(selectedTool.name)}
                    </h2>
                    {selectedTool.serverId && (
                      <p className="text-xs text-zinc-500 dark:text-zinc-400">
                        来源: {getServerNameCN(selectedTool.serverId)}
                        {selectedTool.pluginName && ` · 插件: ${selectedTool.pluginName}`}
                      </p>
                    )}
                  </div>
                </div>
                <p className="mb-4 text-sm text-zinc-600 dark:text-zinc-300">
                  {getToolDescCN(selectedTool.name, selectedTool.description)}
                </p>

                {selectedTool.isServerGroup && (
                  <div className="mb-4 space-y-2">
                    <h3 className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                      服务配置
                    </h3>
                    {selectedTool.type && (
                      <div className="flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400">
                        <span className="font-medium">类型:</span>
                        <span>{TYPE_CN[selectedTool.type] || selectedTool.type}</span>
                      </div>
                    )}
                    {selectedTool.command && (
                      <div className="rounded-lg bg-zinc-50 px-3 py-2 dark:bg-zinc-900">
                        <code className="text-xs font-mono text-zinc-700 dark:text-zinc-300">
                          {selectedTool.command} {selectedTool.args?.join(' ') || ''}
                        </code>
                      </div>
                    )}
                    {selectedTool.url && (
                      <div className="rounded-lg bg-zinc-50 px-3 py-2 dark:bg-zinc-900">
                        <code className="text-xs font-mono text-blue-600 dark:text-blue-400">
                          {selectedTool.url}
                        </code>
                      </div>
                    )}
                    {selectedTool.cwd && (
                      <div className="flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400">
                        <span className="font-medium">工作目录:</span>
                        <span>{selectedTool.cwd}</span>
                      </div>
                    )}
                  </div>
                )}

                {parseSchemaParams(selectedTool.inputSchema).length > 0 && (
                  <div className="mb-4">
                    <h3 className="mb-2 text-sm font-medium text-zinc-700 dark:text-zinc-300">
                      参数定义
                    </h3>
                    <div className="space-y-1.5">
                      {parseSchemaParams(selectedTool.inputSchema).map((param) => (
                        <div
                          key={param.name}
                          className="flex items-start gap-2 rounded-lg bg-zinc-50 px-3 py-2 dark:bg-zinc-900"
                        >
                          <code className="text-sm font-mono text-blue-600 dark:text-blue-400">
                            {param.name}
                          </code>
                          <span className="text-xs text-zinc-400 dark:text-zinc-500">
                            {param.type}
                          </span>
                          {param.required && (
                            <span className="text-xs font-medium text-red-500 dark:text-red-400">
                              必填
                            </span>
                          )}
                          {param.description && (
                            <span className="ml-auto text-xs text-zinc-500 dark:text-zinc-400 truncate max-w-[200px]">
                              {param.description}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {selectedTool.inputSchema && (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-xs font-medium text-zinc-500 dark:text-zinc-400">
                      查看完整 Schema JSON
                    </summary>
                    <pre className="mt-2 overflow-x-auto rounded-lg bg-zinc-50 p-3 text-xs dark:bg-zinc-900 dark:text-zinc-300">
                      {JSON.stringify(selectedTool.inputSchema, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center p-6">
              <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20">
                <Database className="h-10 w-10 text-blue-500" />
              </div>
              <h3 className="mb-2 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
                MCP 工具浏览器
              </h3>
              <p className="max-w-sm text-sm text-zinc-500 dark:text-zinc-400">
                从左侧列表选择一个工具，查看其详细信息、参数定义和完整 Schema。
              </p>
              <div className="mt-6 grid grid-cols-2 gap-4 text-xs">
                <div className="rounded-lg border border-zinc-200 p-3 dark:border-zinc-700">
                  <p className="font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                    工具总数
                  </p>
                  <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                    {mcpTools.length}
                  </p>
                </div>
                <div className="rounded-lg border border-zinc-200 p-3 dark:border-zinc-700">
                  <p className="font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                    服务来源
                  </p>
                  <p className="text-2xl font-bold text-cyan-600 dark:text-cyan-400">
                    {allServerIds.length}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
