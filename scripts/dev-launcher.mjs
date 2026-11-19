#!/usr/bin/env node
/**
 * Dev launcher: probe the three dev ports (server / gateway / vite), find the
 * first free one for each starting from the project defaults, then exec the
 * existing `concurrently` script with the resolved values injected as env so
 * gateway / server / vite all bind/connect to matching numbers.
 *
 * This means a stale leftover process on 3001 (or another team member's tool
 * occupying 18789) no longer breaks `npm run dev` — the launcher just slides
 * over to 3002 / 18790 / etc. and prints the resolved map up top.
 *
 * Port resolution priority (highest wins):
 *   SERVER_PORT / VITE_PORT (env hard-pin, skips probing)
 *   > SERVER_PORT_BASE / VITE_PORT_BASE (env base override)
 *   > webui.runtime.serverPort / vitePort (from ~/.pilotdeck/pilotdeck.yaml)
 *   > 3001 / 5173 (hardcoded defaults)
 *
 * Hard-pinned ports still win — if SERVER_PORT / PILOTDECK_GATEWAY_PORT /
 * VITE_PORT are already exported the launcher trusts them and skips probing
 * (so prod-style setups don't accidentally slide).
 *
 * Enhanced features:
 * - Auto-detect Node.js installation paths for environments without Node in PATH
 * - Auto-start Python OpenEarthEngine service (oea_service.py) on port 8765
 */
import { spawn, execSync } from 'node:child_process';
import { readFileSync, existsSync } from 'node:fs';
import { createServer } from 'node:net';
import { homedir, platform } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse as parseYaml } from 'yaml';

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(__dirname, '..');
const isWindows = platform() === 'win32';

const NODE_CANDIDATES = [
  join(homedir(), '.workbuddy', 'binaries', 'node', 'versions', '22.12.0', 'bin', 'node'),
  join(homedir(), '.workbuddy', 'binaries', 'node', 'versions', '20.18.0', 'bin', 'node'),
  join(homedir(), '.trae-cn-server', 'bin', 'stable-2a1926816d08d71538a3de294bf301b26ac911e0-debian10', 'node'),
  join(homedir(), '.codebuddy-server-cn', 'bin', '3edf87df753e170de36ac84b22b49add86afd0b4', 'node'),
  '/usr/bin/node',
  '/usr/local/bin/node',
];

function findNodeBinary() {
  for (const candidate of NODE_CANDIDATES) {
    if (existsSync(candidate)) {
      return candidate;
    }
  }
  return null;
}

function ensureNodeInPath() {
  const nodeBin = findNodeBinary();
  if (nodeBin) {
    const nodeDir = dirname(nodeBin);
    if (!process.env.PATH.includes(nodeDir)) {
      console.log(`[dev-launcher] Adding Node to PATH: ${nodeDir}`);
      process.env.PATH = `${nodeDir}:${process.env.PATH}`;
    }
    try {
      const version = execSync(`"${nodeBin}" --version`, { encoding: 'utf8' }).trim();
      console.log(`[dev-launcher] Using Node.js: ${version}`);
    } catch (e) {}
  }
}

function startOpenEarthEngineService() {
  const oeaPath = join(repoRoot, 'open-earth-engine', 'oea_service.py');
  if (!existsSync(oeaPath)) {
    console.log('[dev-launcher] OpenEarthEngine service not found, skipping');
    return null;
  }

  console.log('[dev-launcher] Starting Python OpenEarthEngine service (port 8765)...');
  const pythonCmd = isWindows ? 'python' : 'python3';
  
  try {
    const oeaChild = spawn(pythonCmd, [oeaPath], {
      cwd: join(repoRoot, 'open-earth-engine'),
      stdio: ['ignore', 'pipe', 'pipe'],
      env: process.env,
      detached: false,
    });

    let ready = false;
    const checkReady = (data) => {
      const msg = data.toString();
      if (msg.includes('OpenEarthEngine 服务已启动') || msg.includes('http://127.0.0.1:8765')) {
        ready = true;
        console.log('[dev-launcher] Python OEA service is ready');
        oeaChild.stdout.off('data', checkReady);
        oeaChild.stderr.off('data', checkReady);
      }
    };

    oeaChild.stdout.on('data', checkReady);
    oeaChild.stderr.on('data', checkReady);

    oeaChild.stdout.on('data', (data) => {
      console.log(`[OEA-PYTHON] ${data.toString().trim()}`);
    });
    oeaChild.stderr.on('data', (data) => {
      console.log(`[OEA-PYTHON] ${data.toString().trim()}`);
    });

    setTimeout(() => {
      if (!ready) {
        console.log('[dev-launcher] OEA service starting (check logs for ready message)');
      }
    }, 3000);

    return oeaChild;
  } catch (e) {
    console.log(`[dev-launcher] Failed to start OEA service: ${e.message}`);
    return null;
  }
}

function readYamlPortConfig() {
  const home = process.env.PILOT_HOME || join(homedir(), '.pilotdeck');
  const configPath = process.env.PILOTDECK_CONFIG_PATH || join(home, 'pilotdeck.yaml');
  try {
    const raw = readFileSync(configPath, 'utf8');
    const config = parseYaml(raw);
    return config?.webui?.runtime ?? {};
  } catch {
    return {};
  }
}

const yamlRuntime = readYamlPortConfig();
const SERVER_PORT_BASE = parsePort(process.env.SERVER_PORT_BASE, yamlRuntime.serverPort ?? 3001);
const GATEWAY_PORT_BASE = parsePort(process.env.PILOTDECK_GATEWAY_PORT_BASE, 18789);
const VITE_PORT_BASE = parsePort(process.env.VITE_PORT_BASE, yamlRuntime.vitePort ?? 5173);

const MAX_PORT_TRIES = 20;

function parsePort(value, fallback) {
  const parsed = Number.parseInt(value ?? '', 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function isPortFree(port, host = '0.0.0.0') {
  return new Promise((resolveCheck) => {
    const probe = createServer();
    probe.once('error', () => resolveCheck(false));
    probe.once('listening', () => {
      probe.close(() => resolveCheck(true));
    });
    probe.listen(port, host);
  });
}

async function findFreePort(label, base, hardOverride) {
  if (hardOverride !== undefined) {
    return { port: hardOverride, source: 'env-pinned' };
  }
  for (let offset = 0; offset < MAX_PORT_TRIES; offset += 1) {
    const candidate = base + offset;
    // eslint-disable-next-line no-await-in-loop
    const free = await isPortFree(candidate);
    if (free) {
      return {
        port: candidate,
        source: offset === 0 ? 'default' : `fallback (+${offset})`,
      };
    }
  }
  throw new Error(
    `[dev-launcher] Could not find a free ${label} port within ${MAX_PORT_TRIES} of ${base}.`,
  );
}

function envPortOverride(name) {
  const raw = process.env[name];
  if (raw === undefined || raw === '') return undefined;
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) return undefined;
  return parsed;
}

async function main() {
  ensureNodeInPath();

  const server = await findFreePort('server', SERVER_PORT_BASE, envPortOverride('SERVER_PORT'));
  const gateway = await findFreePort('gateway', GATEWAY_PORT_BASE, envPortOverride('PILOTDECK_GATEWAY_PORT'));
  const vite = await findFreePort('vite', VITE_PORT_BASE, envPortOverride('VITE_PORT'));

  const map = [
    ['server (express/ws)', server],
    ['gateway (pilotdeck)', gateway],
    ['vite client       ', vite],
  ];
  console.log('[dev-launcher] resolved dev ports:');
  for (const [label, info] of map) {
    console.log(`  ${label}  →  ${info.port}   ${info.source !== 'default' ? `(${info.source})` : ''}`);
  }
  console.log('');

  const oeaProcess = startOpenEarthEngineService();

  const env = {
    ...process.env,
    SERVER_PORT: String(server.port),
    PILOTDECK_GATEWAY_PORT: String(gateway.port),
    PILOTDECK_GATEWAY_URL:
      process.env.PILOTDECK_GATEWAY_URL ?? `ws://127.0.0.1:${gateway.port}/ws`,
    VITE_PORT: String(vite.port),
    PILOTDECK_SKIP_DEFAULT_PROJECT: '1',
  };

  const npmCmd = isWindows ? 'npm.cmd' : 'npm';
  const child = spawn(
    npmCmd,
    ['--workspace', 'ui', 'run', 'dev:concurrent'],
    { cwd: repoRoot, env, stdio: 'inherit', shell: isWindows },
  );

  const forward = (signal) => {
    if (oeaProcess && !oeaProcess.killed) oeaProcess.kill(signal);
    if (!child.killed) child.kill(signal);
  };
  process.on('SIGINT', () => forward('SIGINT'));
  process.on('SIGTERM', () => forward('SIGTERM'));

  child.on('exit', (code, signal) => {
    if (oeaProcess && !oeaProcess.killed) oeaProcess.kill('SIGTERM');
    if (signal) {
      process.kill(process.pid, signal);
      return;
    }
    process.exit(code ?? 0);
  });
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
