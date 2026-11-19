/**
 * `McpRuntime` — top-level orchestrator for many `McpClient`s. Implements
 * M4 (bounded connect concurrency) and exposes the data shape consumed by
 * the `PluginToToolBridge` (`listAllTools`) and the prompt assembler
 * (`getInstructions`).
 *
 * The runtime is process-local (one per agent session). Cross-process
 * sharing is not in scope for this PR.
 */

import { execSync } from "node:child_process";
import { existsSync } from "node:fs";
import { McpClient, McpClientError, type McpClientOptions } from "../client/McpClient.js";
import type {
  PilotDeckMcpClientStatusEntry,
  PilotDeckMcpServerInstructions,
  PilotDeckMcpServerSpec,
  PilotDeckMcpToolSpec,
} from "../protocol/types.js";

/**
 * Heuristic: detect whether a stdio MCP server is launched via a Python
 * interpreter and, if so, try to ensure the required pip packages are
 * available so the subprocess doesn't immediately die with
 * ModuleNotFoundError.
 *
 * This is an on-sight best-effort check.  Errors are intentionally
 * swallowed — the McpClient.connect() handshake later will surface a
 * clearer diagnostic (and we won't slow down non-python servers at all).
 */
type StdioSpec = PilotDeckMcpServerSpec & { transport: "stdio" };

function ensurePythonMcpHappy(servers: PilotDeckMcpServerSpec[]): void {
  const pythonServers = servers.filter((s): s is StdioSpec => {
    if (s.transport !== "stdio") return false;
    const cmd = ("command" in s ? s.command ?? "" : "").toLowerCase();
    return cmd.includes("python");
  });
  if (pythonServers.length === 0) return;

  // Pick one python.exe as the "installation target".  All Python MCP
  // servers shipped by PilotDeck share the same interpreter, so this is
  // safe to batch.  Prefer an absolute path over bare "python".
  let pythonExe: string | undefined;
  for (const s of pythonServers) {
    const cand = s.command ?? "";
    if (existsSync(cand)) {
      pythonExe = cand;
      break;
    }
  }
  if (!pythonExe) {
    // Fall back to the first command verbatim (let `pip` resolve via PATH).
    pythonExe = pythonServers[0].command ?? undefined;
  }
  if (!pythonExe) return;

  // Knowledge-base server lives in open-earth-engine and needs numpy.
  // The rest live in rs-engine and need fastmcp + mcp.
  const needFastmcp = pythonServers.some((s) =>
    (s.args ?? []).some((a: string) => a.includes("rs_engine")),
  );
  const needNumpy = pythonServers.some((s) =>
    (s.args ?? []).some((a: string) => a.includes("open_earth_engine")),
  );
  if (!needFastmcp && !needNumpy) return;

  const required: string[] = [];
  if (needFastmcp) required.push("fastmcp", "mcp");
  if (needNumpy) required.push("numpy");
  if (required.length === 0) return;

  const imports = required.join("; import ");
  const checkCmd = `"${pythonExe}" -c "import ${imports}"`;
  try {
    execSync(checkCmd, { stdio: ["ignore", "ignore", "ignore"], timeout: 15000 });
    console.log(`[pilotdeck] Python MCP deps ready: ${required.join(", ")}`);
    return;
  } catch {
    console.log(
      `[pilotdeck] Installing missing Python MCP deps: ${required.join(", ")} ...`,
    );
  }

  try {
    const installCmd = `"${pythonExe}" -m pip install ${required.join(" ")} --quiet`;
    execSync(installCmd, { stdio: ["ignore", "pipe", "pipe"], timeout: 300000 });
    console.log(`[pilotdeck] Python MCP deps install completed`);
  } catch (e) {
    const stderr =
      e && typeof (e as { stderr?: unknown }).stderr === "object"
        ? String((e as { stderr: Buffer }).stderr).slice(-500)
        : String((e as Error).message ?? "").slice(-300);
    console.warn(`[pilotdeck] Python MCP deps install failed: ${stderr || e}`);
    console.warn(`[pilotdeck] -> you can manually run: ${pythonExe} -m pip install ${required.join(" ")}`);
  }
}

export type McpRuntimeOptions = {
  /** Max parallel `connect()` calls during `start()`. M4. Default 5. */
  connectConcurrency?: number;
  /** Per-client options passed through to `McpClient`. */
  clientOptions?: McpClientOptions;
};

export class McpRuntime {
  private readonly clients = new Map<string, McpClient>();
  private readonly options: Required<Pick<McpRuntimeOptions, "connectConcurrency">> &
    Pick<McpRuntimeOptions, "clientOptions">;

  constructor(
    public readonly servers: PilotDeckMcpServerSpec[],
    options: McpRuntimeOptions = {},
  ) {
    this.options = {
      connectConcurrency: options.connectConcurrency ?? 5,
      clientOptions: options.clientOptions,
    };
    for (const spec of servers) {
      this.clients.set(spec.id, new McpClient(spec, this.options.clientOptions));
    }
  }

  /** Start each client. Errors are captured per server (do not abort the rest). */
  async start(): Promise<PilotDeckMcpClientStatusEntry[]> {
    // Best-effort: ensure Python MCP pip packages are available *before*
    // we try to handshake — otherwise the subprocess dies immediately and
    // users get a cryptic "Connection closed" error with no hint that
    // `pip install fastmcp mcp` was missing.  Runs synchronously here so
    // the install output interleaves with per-server start logs.
    try {
      ensurePythonMcpHappy(this.servers);
    } catch {
      /* swallow — connect will surface real errors */
    }

    const queue = [...this.clients.values()];
    const concurrency = Math.max(1, Math.min(this.options.connectConcurrency, queue.length));
    const results: PilotDeckMcpClientStatusEntry[] = [];

    const workers: Promise<void>[] = [];
    for (let i = 0; i < concurrency; i++) {
      workers.push(
        (async () => {
          while (queue.length > 0) {
            const client = queue.shift();
            if (!client) break;
            try {
              await client.start();
              results.push({ serverId: client.spec.id, status: client.getStatus() });
            } catch (err) {
              results.push({
                serverId: client.spec.id,
                status: "error",
                error: err instanceof McpClientError ? err.message : (err as Error).message,
              });
            }
          }
        })(),
      );
    }
    await Promise.all(workers);
    return results;
  }

  getClient(serverId: string): McpClient | undefined {
    return this.clients.get(serverId);
  }

  async stop(): Promise<void> {
    await Promise.all([...this.clients.values()].map((c) => c.close()));
  }

  /** Aggregate every advertised tool across every client. */
  async listAllTools(): Promise<PilotDeckMcpToolSpec[]> {
    const out: PilotDeckMcpToolSpec[] = [];
    for (const client of this.clients.values()) {
      if (client.getStatus() !== "ready") continue;
      try {
        const tools = await client.listTools();
        out.push(...tools);
      } catch {
        // skip — `start()` already recorded the error
      }
    }
    return out;
  }

  /** Runtime-fetched server instructions (B3 upgrade path). */
  getInstructions(): PilotDeckMcpServerInstructions[] {
    const out: PilotDeckMcpServerInstructions[] = [];
    for (const client of this.clients.values()) {
      if (client.getStatus() !== "ready") continue;
      const instructions = client.getInstructions();
      if (instructions.trim().length === 0) continue;
      out.push({ serverId: client.spec.id, instructions });
    }
    out.sort((a, b) => a.serverId.localeCompare(b.serverId));
    return out;
  }

  statuses(): PilotDeckMcpClientStatusEntry[] {
    return [...this.clients.values()].map((c) => ({
      serverId: c.spec.id,
      status: c.getStatus(),
    }));
  }
}
