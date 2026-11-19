"use strict";
/**
 * ServerManager — owns the rsagentui Express server child process.
 *
 * Adapted from OpenClaw's GatewayManager (apps/electron/src/gateway-manager.ts).
 * Key differences:
 *   - Spawns `node-bin/node rsagentui/server/index.js` (instead of entry.js gateway)
 *   - Three tarballs to extract (rsagentui/server resolves rsagent-memory-core
 *     via `../../../rsagent-memory-core/lib/index.js`, so all three must be siblings):
 *       Resources/rsagentui-bundle.tar         → Resources/rsagentui/
 *       Resources/rsagent-main-bundle.tar     → Resources/rsagent-main/
 *       Resources/rsagent-memory-core-bundle.tar → Resources/edgeclaw-memory-core/
 *   - Sets BUN_BIN, PILOTDECK_MAIN_DIR so the server can spawn `bun` subprocesses
 *   - rsagentui /health responds with `{status: "ok", ...}` (not `{ok: true}`)
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.ServerManager = void 0;
const node_child_process_1 = require("node:child_process");
const node_util_1 = require("node:util");
const node_child_process_2 = require("node:child_process");
const execFile = (0, node_util_1.promisify)(node_child_process_2.execFile);
const node_events_1 = require("node:events");
const fs = __importStar(require("node:fs/promises"));
const fsSync = __importStar(require("node:fs"));
const net = __importStar(require("node:net"));
const os = __importStar(require("node:os"));
const path = __importStar(require("node:path"));
const DEFAULT_PORT_START = 18790;
const DEFAULT_PORT_END = 18799;
const PROXY_PORT = 18080;
const GATEWAY_PORT = 18789;
const HEALTH_POLL_MS = 1500;
const HEALTH_REQUEST_TIMEOUT_MS = 2000;
const STARTUP_HEALTH_TIMEOUT_MS = 60_000;
const GATEWAY_STARTUP_TIMEOUT_MS = 45_000;
const SHUTDOWN_SIGTERM_WAIT_MS = 5000;
const ORPHAN_TERM_WAIT_MS = 3000;
const STABLE_RUN_RESET_MS = 60_000;
const MAX_RESTART_ATTEMPTS = 3;
const RESTART_BACKOFF_MS = [2000, 4000, 8000];
// Reasoning models (e.g. MiniMax-M2.7-highspeed, DeepSeek-R1) emit large
// <think>/reasoning blocks that consume the output budget BEFORE the actual
// answer. Anthropic SDK's getMaxOutputTokensForModel falls back to 32_000 for
// unknown model names but a downstream GrowthBook gate (tengu_otk_slot_v1) can
// silently cap that to 8_000. 8k is barely enough room for thinking + a short
// answer; 16k leaves headroom without risking provider rejections (MiniMax
// caps at ~64k, OpenAI-compatible Chat caps at 32k for most providers).
//
// User can override via PILOTDECK_MAX_OUTPUT_TOKENS env or
// agents.main.params.maxOutputTokens in ~/.rsagent/rsagent.yaml (the latter is
// wired up in ui/server/services/rsagentConfig.js → buildRuntimeEnv).
const REASONING_FRIENDLY_MAX_OUTPUT_TOKENS = "16000";
function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}
function bundledBinary(binDir, name) {
    if (process.platform === "win32") {
        const exePath = path.join(binDir, `${name}.exe`);
        if (fsSync.existsSync(exePath))
            return exePath;
    }
    return path.join(binDir, name);
}
function linkDirectory(link, target) {
    if (fsSync.existsSync(link) || !fsSync.existsSync(target))
        return;
    try {
        if (process.platform === "win32") {
            fsSync.symlinkSync(target, link, "junction");
        }
        else {
            fsSync.symlinkSync(target, link);
        }
    }
    catch (err) {
        console.warn(`[RsAgent] Failed to create symlink ${link} -> ${target}, copying instead:`, err instanceof Error ? err.message : err);
        try {
            fsSync.cpSync(target, link, { recursive: true, dereference: true });
        }
        catch (copyErr) {
            console.error(`[RsAgent] Failed to copy ${target} to ${link}:`, copyErr instanceof Error ? copyErr.message : copyErr);
        }
    }
}
function getRsAgentDir() {
    return path.join(os.homedir(), ".rsagent");
}
function getPidFilePath() {
    return path.join(getRsAgentDir(), "desktop.server.pid");
}
async function ensureRsAgentDir() {
    await fs.mkdir(getRsAgentDir(), { recursive: true });
}
/**
 * Per-version runtime extraction root.
 *
 * macOS protects `/Applications/<App>.app/Contents/Resources/` via SIP+TCC
 * (App Management gate, macOS 14+); writing extracted bundles there works on
 * first launch but can be wiped silently on app upgrade and is technically a
 * violation of Apple's "app bundle is read-only after install" guideline.
 *
 * The proper home is `~/Library/Application Support/<App>/runtime/<version>/`,
 * which is per-user, writable, survives macOS upgrades, and is the standard
 * location Electron's `app.getPath('userData')` resolves to.
 *
 * We key on the RsAgent bundle version so that upgrading the app forces a
 * fresh extraction (otherwise stale source files from the previous version
 * would silently win). Old version dirs are GC'd on next startup via
 * `cleanupStaleRuntimeVersions()`.
 */
function getRuntimeBaseDir(version) {
    if (process.platform === "win32") {
        return path.join(process.env.APPDATA || path.join(os.homedir(), "AppData", "Roaming"), "RsAgent", "runtime", version);
    }
    return path.join(os.homedir(), "Library", "Application Support", "RsAgent", "runtime", version);
}
function getCronDaemonSocketPath() {
    return path.join(process.env.PILOTDECK_CONFIG_DIR || process.env.PILOT_HOME || path.join(os.homedir(), ".rsagent"), "cron-daemon.sock");
}
async function isPortFree(port) {
    return new Promise((resolve, reject) => {
        const server = net.createServer();
        server.once("error", (err) => {
            if (err.code === "EADDRINUSE") {
                resolve(false);
            }
            else {
                reject(err);
            }
        });
        server.listen(port, "127.0.0.1", () => {
            server.close(() => resolve(true));
        });
    });
}
async function pickAvailablePort() {
    for (let port = DEFAULT_PORT_START; port <= DEFAULT_PORT_END; port++) {
        if (await isPortFree(port)) {
            return port;
        }
    }
    throw new Error(`No free desktop server port in range ${DEFAULT_PORT_START}-${DEFAULT_PORT_END}`);
}
function getServerLogPath() {
    return path.join(os.homedir(), ".rsagent", "desktop.server.log");
}
function readTailSafe(filePath, maxBytes) {
    try {
        const stat = fsSync.statSync(filePath);
        const fd = fsSync.openSync(filePath, "r");
        try {
            const start = Math.max(0, stat.size - maxBytes);
            const len = stat.size - start;
            const buf = Buffer.alloc(len);
            fsSync.readSync(fd, buf, 0, len, start);
            return buf.toString("utf8");
        }
        finally {
            fsSync.closeSync(fd);
        }
    }
    catch {
        return "(no log)";
    }
}
async function readPidFile() {
    try {
        const raw = await fs.readFile(getPidFilePath(), "utf8");
        const n = Number.parseInt(raw.trim(), 10);
        return Number.isFinite(n) && n > 0 ? n : null;
    }
    catch (err) {
        if (err.code === "ENOENT")
            return null;
        throw err;
    }
}
function processExists(pid) {
    try {
        process.kill(pid, 0);
        return true;
    }
    catch (err) {
        if (err.code === "ESRCH")
            return false;
        // On Windows, process.kill(pid, 0) can throw EPERM if the process
        // exists but belongs to another user — treat as "exists".
        if (process.platform === "win32" && err.code === "EPERM")
            return true;
        throw err;
    }
}
function forceKillPid(pid) {
    try {
        if (process.platform === "win32") {
            (0, node_child_process_1.execSync)(`taskkill /F /PID ${pid} /T 2>NUL`, {
                stdio: "ignore",
                timeout: 5000,
                shell: "cmd.exe",
            });
        }
        else {
            process.kill(pid, "SIGKILL");
        }
    }
    catch { /* ignore */ }
}
async function waitForProcessExit(pid, maxMs) {
    const deadline = Date.now() + maxMs;
    while (Date.now() < deadline) {
        if (!processExists(pid))
            return;
        await sleep(50);
    }
}
async function cleanupStaleOrOrphanPid() {
    const pid = await readPidFile();
    if (pid === null)
        return;
    if (!processExists(pid)) {
        try {
            await fs.unlink(getPidFilePath());
        }
        catch (err) {
            if (err.code !== "ENOENT")
                throw err;
        }
        return;
    }
    try {
        process.kill(pid, "SIGTERM");
    }
    catch (err) {
        if (err.code !== "ESRCH")
            throw err;
    }
    await waitForProcessExit(pid, SHUTDOWN_SIGTERM_WAIT_MS);
    if (processExists(pid)) {
        forceKillPid(pid);
    }
    try {
        await fs.unlink(getPidFilePath());
    }
    catch (err) {
        if (err.code !== "ENOENT")
            throw err;
    }
}
/**
 * Poll http://127.0.0.1:<port>/health until it returns `{status: "ok"}` or
 * we hit the startup timeout.
 *
 * If `child` is provided, we additionally short-circuit the moment the
 * child process exits (exitCode !== null || signalCode !== null). Without
 * this fast-fail, a child that crashes ~10ms after spawn (e.g. because
 * load-env.js threw on missing config) still keeps us polling for the full
 * 60-second deadline before the user sees the error dialog.
 */
async function waitForServerHealth(port, child) {
    const deadline = Date.now() + STARTUP_HEALTH_TIMEOUT_MS;
    while (Date.now() < deadline) {
        if (child && (child.exitCode !== null || child.signalCode !== null)) {
            throw new Error(`Server child exited before becoming healthy (code=${child.exitCode ?? "null"}, signal=${child.signalCode ?? "null"})`);
        }
        try {
            const res = await fetch(`http://127.0.0.1:${port}/health`, {
                signal: AbortSignal.timeout(HEALTH_REQUEST_TIMEOUT_MS),
            });
            if (res.ok) {
                const body = (await res.json());
                if (body && body.status === "ok")
                    return;
            }
        }
        catch {
            /* retry until deadline */
        }
        await sleep(HEALTH_POLL_MS);
    }
    throw new Error(`Server health check failed within ${STARTUP_HEALTH_TIMEOUT_MS}ms`);
}
class ServerManager extends node_events_1.EventEmitter {
    dev;
    devRepoRoot;
    appVersion;
    child = null;
    gatewayChild = null;
    port = null;
    stopRequested = false;
    startPromise = null;
    restartAttempts = 0;
    stableTimer = null;
    exitHandlerBound = false;
    /**
     * Set to true while the very first start() is in flight. The exit watchdog
     * checks this and refuses to schedule a restart until the initial start
     * either succeeds or rejects, otherwise an early-crashing child triggers
     * concurrent restart attempts that race against the still-pending health
     * polling loop (and double-emit "error" events).
     */
    initialStartInFlight = false;
    constructor(options = {}) {
        super();
        this.dev = options.dev ?? false;
        this.devRepoRoot = options.devRepoRoot;
        this.appVersion = options.appVersion;
    }
    /**
     * Extract a tarball into `<runtimeBaseDir>/<destDirName>/`, idempotent via
     * marker. The marker stores the source tarball mtime+size so that if the
     * bundled tar is updated (e.g. after an in-place reinstall over the same
     * version) we re-extract automatically.
     *
     * Switched from `execSync('tar xf ...')` to `await execFile('tar', ...)`
     * so the Electron main loop can keep handling IPC (in particular the
     * splash window's status-update channel) while the ~700MB total of
     * bundled tarballs is unpacked. Sync extraction blocked the main thread
     * for tens of seconds on cold APFS caches; the splash text would freeze
     * mid-update and users would assume the app crashed.
     */
    async ensureBundleExtracted(tarballSourceDir, runtimeBaseDir, tarballName, destDirName, progressLabel) {
        const destDir = path.join(runtimeBaseDir, destDirName);
        const tarball = path.join(tarballSourceDir, tarballName);
        const marker = path.join(destDir, ".extracted");
        if (!fsSync.existsSync(tarball)) {
            throw new Error(`Bundle not found: ${tarball}`);
        }
        const tarStat = fsSync.statSync(tarball);
        const expectedMarker = `${tarStat.mtimeMs.toFixed(0)}-${tarStat.size}`;
        if (fsSync.existsSync(marker)) {
            try {
                const recorded = fsSync.readFileSync(marker, "utf8").trim();
                if (recorded === expectedMarker)
                    return destDir;
            }
            catch {
                /* fall through and re-extract */
            }
        }
        // Single user-visible phase covers both the partial-leftover nuke and
        // the actual tar extraction — users don't care which sub-step we're
        // on, and "正在解压…" stays accurate throughout (cleanup is fast,
        // tar dominates wall-clock).
        this.emit("progress", `${progressLabel}…首次安装可能需要 30 秒`);
        if (fsSync.existsSync(destDir)) {
            // Fresh extract: nuke any partial leftover so we don't merge stale
            // + new payloads (could happen if a previous extraction was
            // interrupted).
            await fs.rm(destDir, { recursive: true, force: true });
        }
        await fs.mkdir(destDir, { recursive: true });
        const tarBin = process.platform === "win32" ? "tar" : "/usr/bin/tar";
        if (process.platform === "win32") {
            await this.extractTarWindows(tarball, destDir);
        }
        else {
            await execFile(tarBin, ["xf", tarball, "-C", destDir], {
                timeout: 180_000,
                maxBuffer: 1024 * 1024,
            });
        }
        await fs.writeFile(marker, expectedMarker);
        return destDir;
    }
    async extractTarWindows(tarball, destDir) {
        const fs = await Promise.resolve().then(() => __importStar(require("node:fs")));
        const path = await Promise.resolve().then(() => __importStar(require("node:path")));
        let fileCount = 0;
        let symlinkCount = 0;
        await (await Promise.resolve().then(() => __importStar(require("tar")))).x({
            file: tarball,
            cwd: destDir,
            onentry: (entry) => {
                if (entry.type === "SymbolicLink" || entry.type === "Link") {
                    symlinkCount++;
                }
                else {
                    fileCount++;
                }
            },
            filter: (_path, entry) => {
                if (!entry)
                    return true;
                return entry.type !== "SymbolicLink" && entry.type !== "Link";
            },
        });
        if (fileCount === 0) {
            throw new Error(`tar extraction produced 0 files in ${destDir}`);
        }
        await this.fixPnpmNodeModules(destDir);
        console.log(`[RsAgent] tar extracted ${fileCount} entries, skipped ${symlinkCount} symlinks to ${destDir}`);
    }
    async fixPnpmNodeModules(baseDir) {
        const fs = await Promise.resolve().then(() => __importStar(require("node:fs")));
        const path = await Promise.resolve().then(() => __importStar(require("node:path")));
        const nodeModulesDir = path.join(baseDir, "node_modules");
        const pnpmDir = path.join(nodeModulesDir, ".pnpm");
        if (!fs.existsSync(pnpmDir)) {
            return;
        }
        let createdCount = 0;
        const entries = fs.readdirSync(pnpmDir, { withFileTypes: true });
        for (const entry of entries) {
            if (!entry.isDirectory())
                continue;
            const packageDir = path.join(pnpmDir, entry.name);
            const innerNodeModules = path.join(packageDir, "node_modules");
            if (!fs.existsSync(innerNodeModules))
                continue;
            const innerEntries = fs.readdirSync(innerNodeModules, { withFileTypes: true });
            for (const innerEntry of innerEntries) {
                if (!innerEntry.isDirectory())
                    continue;
                const packageName = innerEntry.name;
                const targetPath = path.join(innerNodeModules, packageName);
                const linkPath = path.join(nodeModulesDir, packageName);
                if (fs.existsSync(linkPath))
                    continue;
                try {
                    fs.symlinkSync(targetPath, linkPath, "junction");
                    createdCount++;
                }
                catch {
                    try {
                        fs.cpSync(targetPath, linkPath, { recursive: true, dereference: true });
                        createdCount++;
                    }
                    catch (err) {
                        console.warn(`[RsAgent] Failed to create ${packageName}:`, err instanceof Error ? err.message : err);
                    }
                }
            }
        }
        if (createdCount > 0) {
            console.log(`[RsAgent] Created ${createdCount} package links in node_modules/`);
        }
    }
    /**
     * Best-effort cleanup of `~/Library/Application Support/RsAgent/runtime/`
     * subdirectories belonging to other versions. Called at startup so that
     * upgrading the app reclaims disk (~1GB per stale version).
     */
    cleanupStaleRuntimeVersions(currentVersion) {
        const runtimeRoot = path.dirname(getRuntimeBaseDir(currentVersion));
        if (!fsSync.existsSync(runtimeRoot))
            return;
        let entries;
        try {
            entries = fsSync.readdirSync(runtimeRoot);
        }
        catch {
            return;
        }
        for (const entry of entries) {
            if (entry === currentVersion)
                continue;
            const stalePath = path.join(runtimeRoot, entry);
            try {
                fsSync.rmSync(stalePath, { recursive: true, force: true });
            }
            catch {
                /* ignore — best-effort GC */
            }
        }
    }
    async resolvePaths() {
        if (this.dev) {
            const root = this.devRepoRoot;
            if (!root)
                throw new Error("ServerManager: devRepoRoot is required when dev=true");
            return {
                nodeBin: bundledBinary(path.join(root, "apps", "desktop", "resources", "node-bin"), "node"),
                bunBin: bundledBinary(path.join(root, "apps", "desktop", "resources", "bun-bin"), "bun"),
                // Repo UI lives at ui/ (bundle tar extracts as rsagentui/ at runtime).
                serverEntry: path.join(root, "ui", "server", "index.js"),
                serverCwd: path.join(root, "ui"),
                pilotDeckMainDir: root,
                runtimeBaseDir: root,
            };
        }
        const resourcesPath = process
            .resourcesPath;
        const resources = typeof resourcesPath === "string" ? resourcesPath : "";
        if (!resources) {
            throw new Error("ServerManager: process.resourcesPath unavailable; pass dev/devRepoRoot or run under Electron");
        }
        if (!this.appVersion) {
            throw new Error("ServerManager: appVersion is required for packaged mode (pass app.getVersion() into the constructor)");
        }
        const runtimeBaseDir = getRuntimeBaseDir(this.appVersion);
        fsSync.mkdirSync(runtimeBaseDir, { recursive: true });
        // Stale-version GC runs silently — it only does work on upgrades and
        // there's nothing useful to tell the user about it. Bundling its
        // wall-clock into the next phase keeps the splash sequence shorter.
        this.cleanupStaleRuntimeVersions(this.appVersion);
        // Order matters only for clarity; resolution at runtime is via ../../../
        // path walks so all three must end up as siblings inside runtimeBaseDir.
        // Each ensureBundleExtracted is awaited *sequentially* (not Promise.all)
        // because: (a) tar is single-threaded I/O bound — parallel extraction
        // saturates the disk and gives no wall-clock win; (b) sequential
        // execution means the splash status label tracks reality (one tarball
        // at a time) instead of showing one phase while three race in the
        // background.
        //
        // Progress labels are intentionally generic ("应用资源 (N/3)") rather
        // than naming the internal bundle (memory-core / rsagentui /
        // rsagent-main) — those names mean nothing to end users and the
        // (N/3) index gives enough sense of "how many steps left".
        await this.ensureBundleExtracted(resources, runtimeBaseDir, "rsagent-memory-core-bundle.tar", "edgeclaw-memory-core", "正在解压应用资源 (1/6)");
        const pilotDeckUiDir = await this.ensureBundleExtracted(resources, runtimeBaseDir, "rsagentui-bundle.tar", "rsagentui", "正在解压应用资源 (2/6)");
        const pilotDeckMainDir = await this.ensureBundleExtracted(resources, runtimeBaseDir, "rsagent-main-bundle.tar", "rsagent-main", "正在解压应用资源 (3/6)");
        await this.ensureBundleExtracted(resources, runtimeBaseDir, "rs-engine-bundle.tar", "rs-engine", "正在解压应用资源 (4/6)");
        await this.ensureBundleExtracted(resources, runtimeBaseDir, "products-bundle.tar", "products", "正在解压应用资源 (5/6)");
        await this.ensureBundleExtracted(resources, runtimeBaseDir, "open-earth-engine-bundle.tar", "open-earth-engine", "正在解压应用资源 (6/6)");
        const rsEngineDir = path.join(runtimeBaseDir, "rs-engine");
        const productsDir = path.join(runtimeBaseDir, "products");
        const openEarthEngineDir = path.join(runtimeBaseDir, "open-earth-engine");
        const rsAgentAppDir = path.join(process.env.APPDATA || path.join(os.homedir(), "AppData", "Roaming"), "RsAgent");
        linkDirectory(path.join(rsAgentAppDir, "rs-engine"), rsEngineDir);
        linkDirectory(path.join(rsAgentAppDir, "products"), productsDir);
        linkDirectory(path.join(rsAgentAppDir, "open-earth-engine"), openEarthEngineDir);
        linkDirectory(path.join(rsAgentAppDir, "data"), path.join(runtimeBaseDir, "data"));
        // ui/server/ files import compiled JS via relative paths like
        // `../../dist/src/pilot/index.js`. From rsagentui/server/ that
        // resolves to <runtimeBaseDir>/dist/src/..., but the actual dist/
        // tree lives inside <runtimeBaseDir>/rsagent-main/dist/. A symlink
        // bridges the gap so all ESM resolve calls succeed at runtime.
        const distLink = path.join(runtimeBaseDir, "dist");
        const distTarget = path.join(pilotDeckMainDir, "dist");
        linkDirectory(distLink, distTarget);
        // edgeclaw-memory-core is a file: dependency in the repo's package.json.
        // The release tar excludes the top-level edgeclaw-memory-core/ (it has
        // its own bundle), which also strips the node_modules/ symlink.
        // Compiled code does `import ... from "edgeclaw-memory-core"` (bare
        // specifier), so Node must find it under rsagent-main/node_modules/.
        const memNodeModLink = path.join(pilotDeckMainDir, "node_modules", "edgeclaw-memory-core");
        const memCoreDir = path.join(runtimeBaseDir, "edgeclaw-memory-core");
        linkDirectory(memNodeModLink, memCoreDir);
        // npm hoists shared deps (ws, express, etc.) into the root node_modules/
        // which ends up inside rsagent-main-bundle.tar, not rsagentui-bundle.tar.
        // ESM resolution walks up the directory tree looking for node_modules/ dirs.
        // A symlink at <runtimeBaseDir>/node_modules → rsagent-main/node_modules
        // lets the resolver find hoisted packages after exhausting rsagentui's own.
        const hoistedLink = path.join(runtimeBaseDir, "node_modules");
        const hoistedTarget = path.join(pilotDeckMainDir, "node_modules");
        linkDirectory(hoistedLink, hoistedTarget);
        // ui/server/ also imports `../../src/web/server/*.js` etc. In dev
        // mode tsx resolves .js → .ts; in packaged mode we need actual .js
        // files. Point src/ → rsagent-main/dist/src/ (compiled output).
        const srcLink = path.join(runtimeBaseDir, "src");
        const srcTarget = path.join(pilotDeckMainDir, "dist", "src");
        linkDirectory(srcLink, srcTarget);
        // rsagentui/server/routes/memory.js imports edgeclaw-memory-core
        // via `../../../src/context/memory/edgeclaw-memory-core/lib/index.js`.
        // The src/ symlink points to rsagent-main/dist/src/ (compiled TS),
        // which contains an empty edgeclaw-memory-core/src/ stub (no lib/).
        // Replace that stub with a symlink to the real extracted bundle.
        const memSrcLink = path.join(runtimeBaseDir, "src", "context", "memory", "edgeclaw-memory-core");
        if (fsSync.existsSync(memSrcLink) && !fsSync.lstatSync(memSrcLink).isSymbolicLink()) {
            fsSync.rmSync(memSrcLink, { recursive: true });
        }
        linkDirectory(memSrcLink, memCoreDir);
        // ── Sync product plugins into the global plugins directory ──────────
        // The gateway's PluginRuntime only scans two directories for MCP server
        // definitions: <pilotHome>/plugins (global) and <projectRoot>/.pilotdeck/
        // plugins (project). The products/ bundle ships plugin.json files with
        // mcpServers entries (rs-agent, etc.) but is never scanned by default.
        // We link each product's plugin sub-directories into ~/.rsagent/plugins/
        // so the gateway discovers them on the next refresh().
        const globalPluginsDir = path.join(getRsAgentDir(), "plugins");
        try {
            fsSync.mkdirSync(globalPluginsDir, { recursive: true });
            console.log(`[RsAgent] Syncing product plugins to ${globalPluginsDir}, productsDir=${productsDir}`);
            if (fsSync.existsSync(productsDir)) {
                const productEntries = fsSync.readdirSync(productsDir, { withFileTypes: true });
                for (const product of productEntries) {
                    if (!product.isDirectory())
                        continue;
                    const productPluginsDir = path.join(productsDir, product.name, "plugins");
                    if (!fsSync.existsSync(productPluginsDir))
                        continue;
                    const pluginDirs = fsSync.readdirSync(productPluginsDir, { withFileTypes: true });
                    for (const pluginDir of pluginDirs) {
                        if (!pluginDir.isDirectory())
                            continue;
                        const linkPath = path.join(globalPluginsDir, pluginDir.name);
                        const targetPath = path.join(productPluginsDir, pluginDir.name);
                        // Remove stale link/dir if exists, then create fresh junction
                        if (fsSync.existsSync(linkPath)) {
                            fsSync.rmSync(linkPath, { recursive: true, force: true });
                        }
                        try {
                            if (process.platform === "win32") {
                                fsSync.symlinkSync(targetPath, linkPath, "junction");
                            }
                            else {
                                fsSync.symlinkSync(targetPath, linkPath);
                            }
                            console.log(`[RsAgent] Linked plugin: ${linkPath} -> ${targetPath}`);
                        }
                        catch (err) {
                            console.warn(`[RsAgent] Failed to link ${linkPath}, copying:`, err instanceof Error ? err.message : err);
                            fsSync.cpSync(targetPath, linkPath, { recursive: true, dereference: true });
                        }
                    }
                }
            }
            else {
                console.warn(`[RsAgent] productsDir does not exist: ${productsDir}`);
            }
        }
        catch (err) {
            console.warn("[RsAgent] Failed to sync product plugins:", err instanceof Error ? err.message : err);
        }
        // ── Sync product skills into the global skills directory ───────────
        // The gateway's PluginRuntime scans <pilotHome>/skills for SKILL.md
        // files. The products/ bundle ships skills under
        // products/<product>/plugins/<plugin>/skills/ but those are never
        // scanned by default. We link each skill sub-directory into
        // ~/.rsagent/skills/ so the gateway discovers them.
        const globalSkillsDir = path.join(getRsAgentDir(), "skills");
        try {
            fsSync.mkdirSync(globalSkillsDir, { recursive: true });
            console.log(`[RsAgent] Syncing product skills to ${globalSkillsDir}`);
            if (fsSync.existsSync(productsDir)) {
                const productEntries = fsSync.readdirSync(productsDir, { withFileTypes: true });
                for (const product of productEntries) {
                    if (!product.isDirectory())
                        continue;
                    const productPluginsDir = path.join(productsDir, product.name, "plugins");
                    if (!fsSync.existsSync(productPluginsDir))
                        continue;
                    const pluginDirs = fsSync.readdirSync(productPluginsDir, { withFileTypes: true });
                    for (const pluginDir of pluginDirs) {
                        if (!pluginDir.isDirectory())
                            continue;
                        const pluginSkillsDir = path.join(productPluginsDir, pluginDir.name, "skills");
                        if (!fsSync.existsSync(pluginSkillsDir))
                            continue;
                        const skillDirs = fsSync.readdirSync(pluginSkillsDir, { withFileTypes: true });
                        for (const skillDir of skillDirs) {
                            if (!skillDir.isDirectory())
                                continue;
                            const linkPath = path.join(globalSkillsDir, skillDir.name);
                            const targetPath = path.join(pluginSkillsDir, skillDir.name);
                            if (fsSync.existsSync(linkPath)) {
                                fsSync.rmSync(linkPath, { recursive: true, force: true });
                            }
                            try {
                                if (process.platform === "win32") {
                                    fsSync.symlinkSync(targetPath, linkPath, "junction");
                                }
                                else {
                                    fsSync.symlinkSync(targetPath, linkPath);
                                }
                                console.log(`[RsAgent] Linked skill: ${linkPath} -> ${targetPath}`);
                            }
                            catch (err) {
                                console.warn(`[RsAgent] Failed to link ${linkPath}, copying:`, err instanceof Error ? err.message : err);
                                fsSync.cpSync(targetPath, linkPath, { recursive: true, dereference: true });
                            }
                        }
                    }
                }
            }
        }
        catch (err) {
            console.warn("[RsAgent] Failed to sync product skills:", err instanceof Error ? err.message : err);
        }
        return {
            nodeBin: bundledBinary(path.join(resources, "node-bin"), "node"),
            bunBin: bundledBinary(path.join(resources, "bun-bin"), "bun"),
            serverEntry: path.join(pilotDeckUiDir, "server", "index.js"),
            serverCwd: pilotDeckUiDir,
            pilotDeckMainDir,
            runtimeBaseDir,
        };
    }
    // ───────────────────────── Orphan-process cleanup ───────────────────────
    //
    // The rsagentui server spawns a Bun "cron daemon" as a *detached* sibling
    // (so multiple UI servers across different windows can share state) AND a
    // Bun "proxy" child that listens on PROXY_PORT. Neither is automatically
    // killed when our top-level Node child dies; both can leak across app
    // restarts.
    //
    // We clean up in two places:
    //   • before each spawn (`cleanupOrphanRuntimeProcesses`) so a fresh start
    //     never silently reuses a stale upstream
    //   • after `stop()` so quitting Electron leaves no background processes
    //
    // Strategy: read the cron-daemon `owner.json` for a recorded processId, and
    // probe PROXY_PORT for whoever is listening. Both go through SIGTERM with a
    // short grace period before SIGKILL.
    async killPidGracefully(pid) {
        if (!processExists(pid))
            return;
        try {
            process.kill(pid, "SIGTERM");
        }
        catch (err) {
            if (err.code === "ESRCH")
                return;
        }
        await waitForProcessExit(pid, ORPHAN_TERM_WAIT_MS);
        if (processExists(pid)) {
            forceKillPid(pid);
        }
    }
    /**
     * Politely shut down the bun cron-daemon via its UNIX socket protocol.
     * Returns true if the daemon acknowledged shutdown (or wasn't running).
     *
     * NOTE: owner.json.processId records the *ui-server* PID (the process that
     * spawned the daemon), NOT the daemon's own PID, so we can't just kill it.
     * The daemon listens on `~/.rsagent/cron-daemon.sock` and accepts a JSON
     * `{ type: "shutdown" }` request which triggers its own clean exit.
     */
    async shutdownCronDaemonViaSocket() {
        const socketPath = getCronDaemonSocketPath();
        if (!fsSync.existsSync(socketPath))
            return true;
        return await new Promise((resolve) => {
            const socket = net.createConnection(socketPath);
            let settled = false;
            let buffer = "";
            const finish = (ok) => {
                if (settled)
                    return;
                settled = true;
                socket.destroy();
                resolve(ok);
            };
            socket.setTimeout(2000, () => finish(false));
            socket.once("connect", () => {
                socket.write(JSON.stringify({ type: "shutdown" }) + "\n");
            });
            socket.once("data", (chunk) => {
                buffer += chunk.toString("utf8");
                const nl = buffer.indexOf("\n");
                if (nl < 0)
                    return;
                try {
                    const reply = JSON.parse(buffer.slice(0, nl));
                    finish(Boolean(reply.ok));
                }
                catch {
                    finish(false);
                }
            });
            socket.once("error", () => finish(false));
        });
    }
    /**
     * pgrep-fallback: if the socket-based shutdown fails (daemon hung, socket
     * stale, etc.), find any bun process whose argv contains the unique
     * "daemonMain(['serve'])" snippet and SIGTERM/SIGKILL it.
     */
    async killOrphanCronDaemonByPgrep() {
        let out = "";
        try {
            if (process.platform === "win32") {
                // wmic is universally available on Windows; filter by command line.
                out = (0, node_child_process_1.execSync)('wmic process where "CommandLine like \'%daemonMain%serve%\'" get ProcessId /format:list 2>NUL', { stdio: ["ignore", "pipe", "ignore"], timeout: 5000, shell: "cmd.exe" }).toString("utf8");
            }
            else {
                out = (0, node_child_process_1.execSync)(`/usr/bin/pgrep -f "daemonMain\\(\\['serve'\\]\\)" || true`, { stdio: ["ignore", "pipe", "ignore"], timeout: 3000 }).toString("utf8");
            }
        }
        catch {
            return;
        }
        const pids = out
            .split("\n")
            .map((s) => Number.parseInt(s.replace(/\D/g, ""), 10))
            .filter((n) => Number.isFinite(n) && n > 0 && n !== process.pid);
        for (const pid of pids) {
            await this.killPidGracefully(pid);
        }
    }
    async killOrphanCronDaemon() {
        const ok = await this.shutdownCronDaemonViaSocket();
        if (!ok) {
            await this.killOrphanCronDaemonByPgrep();
        }
    }
    listenerPidForPort(port) {
        try {
            let out;
            if (process.platform === "win32") {
                // netstat -ano gives lines like:  TCP  0.0.0.0:18790  0.0.0.0:0  LISTENING  1234
                const raw = (0, node_child_process_1.execSync)(`netstat -ano -p TCP`, {
                    stdio: ["ignore", "pipe", "ignore"],
                    timeout: 5000,
                    shell: "cmd.exe",
                }).toString("utf8");
                const line = raw.split("\n").find((l) => l.includes("LISTENING") && l.includes(`:${port} `));
                if (!line)
                    return null;
                const parts = line.trim().split(/\s+/);
                const pid = Number.parseInt(parts[parts.length - 1] ?? "", 10);
                return Number.isFinite(pid) && pid > 0 ? pid : null;
            }
            out = (0, node_child_process_1.execSync)(`/usr/sbin/lsof -nP -t -i :${port} -sTCP:LISTEN`, {
                stdio: ["ignore", "pipe", "ignore"],
                timeout: 3000,
            })
                .toString("utf8")
                .trim();
            if (!out)
                return null;
            const first = Number.parseInt(out.split("\n")[0] ?? "", 10);
            return Number.isFinite(first) && first > 0 ? first : null;
        }
        catch {
            return null;
        }
    }
    async killOrphanProxy() {
        const pid = this.listenerPidForPort(PROXY_PORT);
        if (pid === null)
            return;
        // Avoid suicide: if the listener is the current process tree (shouldn't
        // happen, but be defensive), skip.
        if (pid === process.pid)
            return;
        await this.killPidGracefully(pid);
    }
    async cleanupOrphanRuntimeProcesses() {
        // Order: proxy first (its parent is the cron daemon's child of the
        // previous UI server), then cron daemon, then orphan gateway.
        await this.killOrphanProxy();
        await this.killOrphanCronDaemon();
        await this.killOrphanGateway();
    }
    async killOrphanGateway() {
        const pid = this.listenerPidForPort(GATEWAY_PORT);
        if (pid === null)
            return;
        if (pid === process.pid)
            return;
        await this.killPidGracefully(pid);
    }
    clearStableTimer() {
        if (this.stableTimer !== null) {
            clearTimeout(this.stableTimer);
            this.stableTimer = null;
        }
    }
    scheduleStableReset() {
        this.clearStableTimer();
        this.stableTimer = setTimeout(() => {
            this.stableTimer = null;
            this.restartAttempts = 0;
        }, STABLE_RUN_RESET_MS);
    }
    attachExitWatchdog() {
        if (!this.child || this.exitHandlerBound)
            return;
        this.exitHandlerBound = true;
        this.child.once("exit", (code, signal) => {
            this.exitHandlerBound = false;
            this.child = null;
            this.clearStableTimer();
            if (this.stopRequested)
                return;
            // While the very first start is still pending, let the outer
            // startProcessAndWaitReady -> waitForServerHealth() short-circuit
            // path surface the failure (it already collects the log tail and
            // throws via start() -> caller). Skipping watchdog work here keeps
            // us from emitting a duplicate "error" event before the caller's
            // try/catch attaches its handler, and from spawning concurrent
            // restart attempts that race the still-pending health poll loop.
            if (this.initialStartInFlight)
                return;
            const err = new Error(`Server exited unexpectedly (code=${code ?? "null"}, signal=${signal ?? "null"})`);
            this.emit("error", err);
            if (this.restartAttempts >= MAX_RESTART_ATTEMPTS) {
                this.emit("max-restarts");
                this.port = null;
                return;
            }
            const attempt = this.restartAttempts + 1;
            this.emit("restarting", attempt);
            const delay = RESTART_BACKOFF_MS[Math.min(attempt - 1, RESTART_BACKOFF_MS.length - 1)] ??
                RESTART_BACKOFF_MS[RESTART_BACKOFF_MS.length - 1];
            void (async () => {
                await sleep(delay);
                if (this.stopRequested)
                    return;
                this.restartAttempts = attempt;
                try {
                    const { port } = await this.startProcessAndWaitReady();
                    this.port = port;
                    this.emit("ready", port);
                    this.scheduleStableReset();
                }
                catch (e) {
                    this.emit("error", e instanceof Error ? e : new Error(String(e)));
                    this.port = null;
                }
            })();
        });
    }
    async writePidFile(pid) {
        await ensureRsAgentDir();
        await fs.writeFile(getPidFilePath(), `${pid}\n`, "utf8");
    }
    async removePidFile() {
        try {
            await fs.unlink(getPidFilePath());
        }
        catch (err) {
            if (err.code !== "ENOENT")
                throw err;
        }
    }
    async startProcessAndWaitReady() {
        await cleanupStaleOrOrphanPid();
        // Kill leftover proxy/cron-daemon from a previous (crashed or
        // SIGKILL'd-by-Activity-Monitor) run. ensureRsAgentProxyRunning() in the
        // ui server otherwise short-circuits when port 18080 is occupied and
        // never gets a chance to attach its stdout pipe, so logs from the stale
        // proxy never reach desktop.server.log.
        await this.cleanupOrphanRuntimeProcesses();
        const chosenPort = await pickAvailablePort();
        // NOTE: proxy port is intentionally NOT overridden here. rsagentui
        // spawns proxy.ts as a subprocess (in rsagent-main) which loads its
        // own config from ~/.rsagent/rsagent.yaml. If we set PILOTDECK_PROXY_PORT
        // here, the parent server waits on the new port but the spawned proxy.ts
        // still binds runtime.proxyPort from yaml → mismatch. Leave proxy port
        // to YAML so parent + child agree.
        this.emit("progress", "配置运行环境…");
        const { nodeBin, bunBin, serverEntry, serverCwd, pilotDeckMainDir, runtimeBaseDir } = await this.resolvePaths();
        if (!fsSync.existsSync(nodeBin)) {
            throw new Error(`Bundled Node not found at ${nodeBin}`);
        }
        if (!fsSync.existsSync(serverEntry)) {
            throw new Error(`Server entry not found at ${serverEntry}`);
        }
        const pythonPath = await this.findValidPythonPath();
        const env = {
            ...process.env,
            NO_COLOR: "1",
            FORCE_COLOR: "0",
            PILOTDECK_DESKTOP: "1",
            SERVER_PORT: String(chosenPort),
            PILOT_HOME: getRsAgentDir(),
            PILOTDECK_CONFIG_DIR: getRsAgentDir(),
            HOST: "127.0.0.1",
            BUN_BIN: bunBin,
            PILOTDECK_MAIN_DIR: pilotDeckMainDir,
            PILOTDECK_REPO_ROOT: runtimeBaseDir,
            PILOTDECK_CONDA_PYTHON: pythonPath ? path.join(pythonPath, "python.exe") : undefined,
            PATH: `${path.dirname(nodeBin)}${path.delimiter}${path.dirname(bunBin)}${path.delimiter}${pythonPath ?? ""}${path.delimiter}${process.env.PATH ?? ""}`,
            PILOTDECK_MAX_OUTPUT_TOKENS: process.env.PILOTDECK_MAX_OUTPUT_TOKENS ??
                REASONING_FRIENDLY_MAX_OUTPUT_TOKENS,
        };
        // Mirror server stdout/stderr to ~/.rsagent/desktop.server.log so failures
        // are diagnosable even when the user launches via Finder/Dock (no terminal).
        await ensureRsAgentDir();
        const logPath = getServerLogPath();
        const logStream = fsSync.createWriteStream(logPath, { flags: "a" });
        // --- Start the Gateway process (port 18789) BEFORE the UI server ---
        // The UI server's rsagent-bridge connects to ws://127.0.0.1:18789/ws
        // within 30s. We must have the gateway listening before the UI server
        // attempts its first WebSocket handshake.
        const gatewayEntry = path.join(pilotDeckMainDir, "dist", "src", "cli", "pilotdeck.js");
        if (fsSync.existsSync(gatewayEntry)) {
            this.emit("progress", "启动 RsAgent Gateway…");
            const gwLogStream = fsSync.createWriteStream(logPath, { flags: "a" });
            gwLogStream.write(`\n=== ${new Date().toISOString()} spawn gateway ${gatewayEntry} (port=${GATEWAY_PORT}) ===\n`);
            const gwChild = (0, node_child_process_1.spawn)(nodeBin, [gatewayEntry, "server"], {
                stdio: ["ignore", "pipe", "pipe"],
                cwd: pilotDeckMainDir,
                env: {
                    ...env,
                    PILOTDECK_GATEWAY_PORT: String(GATEWAY_PORT),
                },
                windowsHide: true,
            });
            gwChild.stdout?.pipe(gwLogStream, { end: false });
            gwChild.stderr?.pipe(gwLogStream, { end: false });
            gwChild.once("exit", () => {
                gwLogStream.end();
            });
            this.gatewayChild = gwChild;
            // Wait for gateway to start listening
            const gwDeadline = Date.now() + GATEWAY_STARTUP_TIMEOUT_MS;
            let gwReady = false;
            while (Date.now() < gwDeadline) {
                if (gwChild.exitCode !== null)
                    break;
                const pid = this.listenerPidForPort(GATEWAY_PORT);
                if (pid !== null) {
                    gwReady = true;
                    break;
                }
                await sleep(HEALTH_POLL_MS);
            }
            if (!gwReady) {
                gwChild.kill("SIGTERM");
                this.gatewayChild = null;
                const tail = readTailSafe(logPath, 4000);
                throw new Error(`Gateway failed to start on port ${GATEWAY_PORT} within ${GATEWAY_STARTUP_TIMEOUT_MS}ms\n--- log tail ---\n${tail}`);
            }
        }
        logStream.write(`\n=== ${new Date().toISOString()} spawn ${serverEntry} (port=${chosenPort}) ===\n`);
        const child = (0, node_child_process_1.spawn)(nodeBin, [serverEntry], {
            stdio: ["ignore", "pipe", "pipe"],
            cwd: serverCwd,
            env,
            windowsHide: true,
        });
        if (!child.pid) {
            logStream.end();
            throw new Error("Failed to spawn server process");
        }
        child.stdout?.pipe(logStream, { end: false });
        child.stderr?.pipe(logStream, { end: false });
        child.once("exit", () => {
            logStream.end();
        });
        this.child = child;
        this.exitHandlerBound = false;
        this.attachExitWatchdog();
        await this.writePidFile(child.pid);
        this.emit("progress", "启动本地服务…");
        try {
            await waitForServerHealth(chosenPort, child);
        }
        catch (err) {
            this.stopRequested = true;
            await this.killChildGracefully();
            await this.removePidFile();
            this.child = null;
            this.stopRequested = false;
            const tail = readTailSafe(logPath, 4000);
            throw new Error(`${err instanceof Error ? err.message : String(err)}\n--- server log tail (${logPath}) ---\n${tail}`);
        }
        return { port: chosenPort };
    }
    async killChildGracefully() {
        const proc = this.child;
        if (!proc || !proc.pid)
            return;
        const pid = proc.pid;
        try {
            proc.kill("SIGTERM");
        }
        catch {
            /* ignore */
        }
        const deadline = Date.now() + SHUTDOWN_SIGTERM_WAIT_MS;
        while (Date.now() < deadline) {
            if (!processExists(pid))
                return;
            await sleep(50);
        }
        if (processExists(pid)) {
            forceKillPid(pid);
        }
    }
    async checkPythonVersion(pythonExe) {
        try {
            const versionOutput = (0, node_child_process_1.execSync)(`"${pythonExe}" --version`, { stdio: ['ignore', 'pipe', 'ignore'], timeout: 5000 }).toString('utf8').trim();
            const match = versionOutput.match(/Python (\d+)\.(\d+)/);
            if (match) {
                const major = parseInt(match[1], 10);
                const minor = parseInt(match[2], 10);
                if (major >= 3 && minor >= 10) {
                    console.log(`[RsAgent] Found Python ${major}.${minor} at ${pythonExe}`);
                    return true;
                }
                else {
                    console.warn(`[RsAgent] Python ${major}.${minor} at ${pythonExe} is too old (requires >= 3.10)`);
                }
            }
        }
        catch (err) {
            console.warn(`[RsAgent] Failed to check Python version: ${err instanceof Error ? err.message : err}`);
        }
        return false;
    }
    async checkPythonDependencies(pythonExe) {
        // fastmcp + mcp: MCP server framework
        // numpy: required at startup by rs_engine.earth_agent_tools.utils and
        //        open_earth_engine.knowledge.vector_store
        // aiohttp: required at startup by open_earth_engine.knowledge.knowledge_mcp_server
        const requiredPackages = "fastmcp mcp numpy aiohttp";
        const importCheck = `"${pythonExe}" -c "import fastmcp; import mcp; import numpy; import aiohttp"`;
        try {
            (0, node_child_process_1.execSync)(importCheck, { stdio: ['ignore', 'pipe', 'ignore'], timeout: 10000 });
            console.log(`[RsAgent] Python dependencies (fastmcp, mcp, numpy, aiohttp) are installed`);
            return true;
        }
        catch {
            console.warn(`[RsAgent] Python dependencies missing, attempting auto-install...`);
            try {
                console.log(`[RsAgent] Running: ${pythonExe} -m pip install ${requiredPackages}`);
                const result = (0, node_child_process_1.execSync)(`"${pythonExe}" -m pip install ${requiredPackages}`, {
                    stdio: ['ignore', 'pipe', 'ignore'],
                    timeout: 180000
                }).toString('utf8');
                console.log(`[RsAgent] Pip install completed: ${result.slice(-200)}`);
                (0, node_child_process_1.execSync)(importCheck, { stdio: ['ignore', 'pipe', 'ignore'], timeout: 5000 });
                console.log(`[RsAgent] Python dependencies installed successfully`);
                return true;
            }
            catch (installErr) {
                console.error(`[RsAgent] Failed to install Python dependencies: ${installErr instanceof Error ? installErr.message : installErr}`);
                return false;
            }
        }
    }
    findPythonPath() {
        const pythonPaths = [
            path.join(os.homedir(), 'AppData', 'Local', 'Programs', 'Python', 'Python312'),
            path.join(os.homedir(), 'AppData', 'Local', 'Programs', 'Python', 'Python311'),
            path.join(os.homedir(), 'AppData', 'Local', 'Programs', 'Python', 'Python310'),
            'D:\\miniconda3',
            'D:\\anaconda3',
            'C:\\miniconda3',
            'C:\\anaconda3',
            'C:\\ProgramData\\miniconda3',
            'C:\\ProgramData\\Anaconda3',
            'C:\\Python312',
            'C:\\Python311',
            'C:\\Python310',
            'C:\\Python39',
            'C:\\Program Files\\Python312',
            'C:\\Program Files\\Python311',
            'C:\\Program Files\\Python310',
        ];
        for (const pythonPath of pythonPaths) {
            const exePath = path.join(pythonPath, 'python.exe');
            if (fsSync.existsSync(exePath)) {
                return pythonPath;
            }
        }
        try {
            const result = (0, node_child_process_1.execSync)('where python', { stdio: ['ignore', 'pipe', 'ignore'], timeout: 5000 }).toString('utf8').trim();
            const lines = result.split('\n');
            for (const line of lines) {
                const trimmed = line.trim();
                if (trimmed && !trimmed.includes('Microsoft\\WindowsApps')) {
                    return path.dirname(trimmed);
                }
            }
        }
        catch { /* ignore */ }
        return undefined;
    }
    async findValidPythonPath() {
        this.emit("progress", "检测 Python 环境…");
        const pythonPath = this.findPythonPath();
        if (!pythonPath) {
            console.warn('[RsAgent] No Python installation found');
            return undefined;
        }
        const pythonExe = path.join(pythonPath, 'python.exe');
        if (!fsSync.existsSync(pythonExe)) {
            console.warn(`[RsAgent] Python executable not found: ${pythonExe}`);
            return undefined;
        }
        if (!(await this.checkPythonVersion(pythonExe))) {
            console.warn(`[RsAgent] Python version check failed for ${pythonExe}`);
            return undefined;
        }
        this.emit("progress", "安装依赖包…");
        if (!(await this.checkPythonDependencies(pythonExe))) {
            console.warn(`[RsAgent] Python dependencies could not be installed for ${pythonExe}`);
            return undefined;
        }
        this.emit("progress", "Python 环境检测完成");
        return pythonPath;
    }
    start() {
        if (this.startPromise)
            return this.startPromise;
        this.stopRequested = false;
        this.restartAttempts = 0;
        this.initialStartInFlight = true;
        this.startPromise = (async () => {
            try {
                const { port } = await this.startProcessAndWaitReady();
                this.port = port;
                this.initialStartInFlight = false;
                this.emit("ready", port);
                this.scheduleStableReset();
                return { port };
            }
            catch (e) {
                this.initialStartInFlight = false;
                const err = e instanceof Error ? e : new Error(String(e));
                this.emit("error", err);
                throw err;
            }
            finally {
                this.startPromise = null;
            }
        })();
        return this.startPromise;
    }
    async stop() {
        this.stopRequested = true;
        this.clearStableTimer();
        this.child?.removeAllListeners("exit");
        await this.killChildGracefully();
        this.child = null;
        this.port = null;
        // Stop the gateway process
        await this.killGatewayGracefully();
        this.gatewayChild = null;
        await this.removePidFile();
        // The ui-server's SIGTERM handler stops the proxy and (after our
        // rsagentConfig.js patch) the cron daemon. As a belt-and-suspenders
        // safety net — in case the parent died via SIGKILL, hung past the SIGTERM
        // grace, or the user used `kill -9` from Activity Monitor — sweep any
        // remaining orphans now so quitting RsAgent really leaves zero processes.
        await this.cleanupOrphanRuntimeProcesses();
        this.stopRequested = false;
    }
    async killGatewayGracefully() {
        const proc = this.gatewayChild;
        if (!proc || !proc.pid)
            return;
        const pid = proc.pid;
        try {
            proc.kill("SIGTERM");
        }
        catch {
            /* ignore */
        }
        const deadline = Date.now() + SHUTDOWN_SIGTERM_WAIT_MS;
        while (Date.now() < deadline) {
            if (!processExists(pid))
                return;
            await sleep(50);
        }
        if (processExists(pid)) {
            forceKillPid(pid);
        }
    }
    getPort() {
        return this.port;
    }
    isRunning() {
        const c = this.child;
        return c !== null && c.exitCode === null && c.signalCode === null;
    }
}
exports.ServerManager = ServerManager;
//# sourceMappingURL=server-manager.js.map