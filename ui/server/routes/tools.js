import express from 'express';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { fileURLToPath } from 'url';
import { parse as parseYaml } from 'yaml';
import { spawn } from 'child_process';

const router = express.Router();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');

const PILOT_HOME = process.env.PILOT_HOME || path.join(os.homedir(), '.pilotdeck');
const PILOTDECK_YAML = path.join(PILOT_HOME, 'pilotdeck.yaml');
const PRODUCTS_ROOT = path.resolve(process.env.PILOTDECK_REPO_ROOT || REPO_ROOT);

// ---------------------------------------------------------------------------
// Read MCP server definitions from plugin configs
// ---------------------------------------------------------------------------

function resolveEnvVars(str) {
  if (!str || typeof str !== 'string') return str;
  return str.replace(/\$\{([^}]+)\}/g, (_, varName) => {
    return process.env[varName] || `\${${varName}}`;
  });
}

function readMcpServersFromPlugins() {
  const servers = [];
  const pluginsDir = path.join(PILOT_HOME, 'plugins');

  // Scan ~/.pilotdeck/plugins/ for plugin.json (PilotDeck MCP plugin format)
  try {
    if (fs.existsSync(pluginsDir)) {
      const entries = fs.readdirSync(pluginsDir, { withFileTypes: true });
      for (const entry of entries) {
        if (!entry.isDirectory()) continue;
        const pluginJsonPath = path.join(pluginsDir, entry.name, 'plugin.json');
        if (!fs.existsSync(pluginJsonPath)) continue;
        try {
          const plugin = JSON.parse(fs.readFileSync(pluginJsonPath, 'utf-8'));
          if (plugin.mcpServers && typeof plugin.mcpServers === 'object') {
            for (const [serverId, serverConfig] of Object.entries(plugin.mcpServers)) {
              servers.push({
                serverId,
                pluginName: plugin.name || entry.name,
                description: plugin.description || '',
                command: serverConfig.command || '',
                args: serverConfig.args || [],
                cwd: resolveEnvVars(serverConfig.cwd) || '',
                env: serverConfig.env || {},
                type: serverConfig.type || (serverConfig.url ? 'http' : 'stdio'),
                url: serverConfig.url || '',
              });
            }
          }
        } catch { /* skip malformed plugin.json */ }
      }
    }
  } catch { /* plugins dir might not exist */ }

  // Also scan the products/ directory in the repo for plugin configs
  const productsDir = path.join(PRODUCTS_ROOT, 'products');
  try {
    if (fs.existsSync(productsDir)) {
      const productEntries = fs.readdirSync(productsDir, { withFileTypes: true });
      for (const product of productEntries) {
        if (!product.isDirectory()) continue;
        const pluginsSubDir = path.join(productsDir, product.name, 'plugins');
        if (!fs.existsSync(pluginsSubDir)) continue;
        const pluginDirs = fs.readdirSync(pluginsSubDir, { withFileTypes: true });
        for (const pluginDir of pluginDirs) {
          if (!pluginDir.isDirectory()) continue;
          const pluginJsonPath = path.join(pluginsSubDir, pluginDir.name, 'plugin.json');
          if (!fs.existsSync(pluginJsonPath)) continue;
          try {
            const plugin = JSON.parse(fs.readFileSync(pluginJsonPath, 'utf-8'));
            if (plugin.mcpServers && typeof plugin.mcpServers === 'object') {
              for (const [serverId, serverConfig] of Object.entries(plugin.mcpServers)) {
                if (servers.some(s => s.serverId === serverId && s.pluginName === plugin.name)) continue;
                servers.push({
                  serverId,
                  pluginName: plugin.name || pluginDir.name,
                  description: plugin.description || '',
                  command: serverConfig.command || '',
                  args: serverConfig.args || [],
                  cwd: resolveEnvVars(serverConfig.cwd) || '',
                  env: serverConfig.env || {},
                  type: serverConfig.type || (serverConfig.url ? 'http' : 'stdio'),
                  url: serverConfig.url || '',
                });
              }
            }
          } catch { /* skip */ }
        }
      }
    }
  } catch { /* products dir might not exist */ }

  return servers;
}

// ---------------------------------------------------------------------------
// Query an MCP Server for its tool list via stdio JSON-RPC
// ---------------------------------------------------------------------------

const MCP_LIST_TOOLS_TIMEOUT_MS = 15_000;

async function queryMcpServerTools(server) {
  if (server.type !== 'stdio' || !server.command) return [];

  const cmd = server.command;
  const cmdArgs = Array.isArray(server.args) ? server.args : [];
  const spawnOptions = {
    cwd: server.cwd || REPO_ROOT,
    stdio: ['pipe', 'pipe', 'pipe'],
    env: { ...process.env, ...server.env },
  };

  return new Promise((resolve) => {
    let stdout = '';
    let stderr = '';
    let resolved = false;
    const tools = [];

    try {
      const child = spawn(cmd, cmdArgs, spawnOptions);

      const timeout = setTimeout(() => {
        if (!resolved) {
          resolved = true;
          child.kill('SIGTERM');
          resolve([]);
        }
      }, MCP_LIST_TOOLS_TIMEOUT_MS);

      child.stderr.on('data', (data) => { stderr += data.toString(); });

      child.stdout.on('data', (data) => {
        stdout += data.toString();
        // Parse JSON-RPC responses line by line
        for (const line of stdout.split('\n')) {
          if (!line.trim()) continue;
          try {
            const msg = JSON.parse(line.trim());
            // Look for tools/list response
            if (msg.id === 2 && msg.result && Array.isArray(msg.result.tools)) {
              for (const tool of msg.result.tools) {
                tools.push({
                  name: `mcp__${server.serverId}__${tool.name}`,
                  description: tool.description || '',
                  inputSchema: tool.inputSchema || undefined,
                  serverId: server.serverId,
                  pluginName: server.pluginName,
                  isServerGroup: false,
                });
              }
              if (!resolved) {
                resolved = true;
                clearTimeout(timeout);
                child.kill('SIGTERM');
                resolve(tools);
              }
              return;
            }
          } catch { /* not a JSON line, skip */ }
        }
      });

      child.on('close', () => {
        if (!resolved) {
          resolved = true;
          clearTimeout(timeout);
          // Try parsing any remaining stdout
          for (const line of stdout.split('\n')) {
            if (!line.trim()) continue;
            try {
              const msg = JSON.parse(line.trim());
              if (msg.id === 2 && msg.result && Array.isArray(msg.result.tools)) {
                for (const tool of msg.result.tools) {
                  tools.push({
                    name: `mcp__${server.serverId}__${tool.name}`,
                    description: tool.description || '',
                    inputSchema: tool.inputSchema || undefined,
                    serverId: server.serverId,
                    pluginName: server.pluginName,
                    isServerGroup: false,
                  });
                }
                resolve(tools);
                return;
              }
            } catch { /* skip */ }
          }
          resolve([]);
        }
      });

      child.on('error', (err) => {
        if (!resolved) {
          resolved = true;
          clearTimeout(timeout);
          console.warn(`[tools] Failed to spawn MCP server ${server.serverId}:`, err.message);
          resolve([]);
        }
      });

      // Send MCP initialize + tools/list requests
      const initRequest = JSON.stringify({
        jsonrpc: '2.0',
        id: 1,
        method: 'initialize',
        params: {
          protocolVersion: '2024-11-05',
          capabilities: {},
          clientInfo: { name: 'pilotdeck-tools-api', version: '1.0.0' },
        },
      }) + '\n';

      const listToolsRequest = JSON.stringify({
        jsonrpc: '2.0',
        id: 2,
        method: 'tools/list',
        params: {},
      }) + '\n';

      // Small delay to let the server start, then send requests
      setTimeout(() => {
        child.stdin.write(initRequest);
        child.stdin.write(listToolsRequest);
        // Wait a bit then close stdin to signal we're done
        setTimeout(() => {
          try { child.stdin.end(); } catch { /* already closed */ }
        }, 2000);
      }, 500);

    } catch (err) {
      if (!resolved) {
        resolved = true;
        resolve([]);
      }
    }
  });
}

// ---------------------------------------------------------------------------
// Try Gateway RPC for actual tool list
// ---------------------------------------------------------------------------

async function tryGatewayListTools() {
  try {
    const bridge = await import('../pilotdeck-bridge.js');
    if (bridge.listToolsViaGateway) {
      const result = await bridge.listToolsViaGateway();
      return result.tools || [];
    }
  } catch (err) {
    console.warn('[tools] Gateway list_tools not available:', err?.message || err);
  }
  return null;
}

// ---------------------------------------------------------------------------
// GET / — List all MCP tools
// ---------------------------------------------------------------------------

router.get('/', async (_req, res) => {
  try {
    // 1. Try Gateway RPC first (returns individual tool names + descriptions)
    const gatewayTools = await tryGatewayListTools();

    if (gatewayTools && gatewayTools.length > 0) {
      return res.json({ success: true, source: 'gateway', tools: gatewayTools });
    }

    // 2. Fallback: query each MCP server directly for its tool list
    const mcpServers = readMcpServersFromPlugins();

    if (mcpServers.length > 0) {
      // Query all servers in parallel
      const toolResults = await Promise.all(
        mcpServers.map(async (server) => {
          const serverTools = await queryMcpServerTools(server);
          // If we couldn't get individual tools, return the server group entry
          if (serverTools.length === 0) {
            return [{
              name: `mcp__${server.pluginName}__${server.serverId}`,
              description: server.description || `MCP Server: ${server.serverId}`,
              serverId: server.serverId,
              pluginName: server.pluginName,
              command: server.command,
              args: server.args,
              cwd: server.cwd,
              type: server.type,
              isServerGroup: true,
            }];
          }
          return serverTools;
        })
      );

      const tools = toolResults.flat();

      return res.json({
        success: true,
        source: 'mcp-query',
        tools,
        note: gatewayTools === null
          ? `Queried ${mcpServers.length} MCP servers directly for tool listings.`
          : undefined,
      });
    }

    // 3. No servers found at all
    return res.json({
      success: true,
      source: 'empty',
      tools: [],
      note: 'No MCP servers configured. Install plugins or add mcpServers to pilotdeck.yaml.',
    });
  } catch (error) {
    console.error('[tools] Error listing tools:', error);
    res.status(500).json({
      error: 'Failed to list tools',
      details: error instanceof Error ? error.message : String(error),
    });
  }
});

export default router;