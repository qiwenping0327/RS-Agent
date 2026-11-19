/**
 * Convert the loosely-typed `mcpServers: Record<string, unknown>` blob produced
 * by `PluginRuntime.mcpServers()` (each plugin's manifest) into the strict
 * `PilotDeckMcpServerSpec[]` consumed by `McpRuntime`.
 *
 * Behaviour parity with the legacy upstream plugin manifest schema:
 *   - `command` ⇒ stdio transport (`args`/`env`/`cwd` optional).
 *   - `url` (or `httpUrl`) ⇒ streamable_http transport.
 *   - Anything else is silently dropped — we do **not** throw at startup so
 *     a single misconfigured plugin entry can't take down the gateway.
 */

import { homedir } from "node:os";
import type { PilotDeckMcpServerSpec } from "../protocol/types.js";

function expandHome(s: string): string {
  if (s.startsWith("~/")) return homedir() + s.slice(1);
  if (s.startsWith("~\\")) return homedir() + s.slice(1);
  if (s === "~") return homedir();
  return s;
}

function resolveEnvVars(s: string): string {
  return s.replace(/\$\{([^}]+)\}/g, (_, varName: string) => {
    const val = process.env[varName];
    if (val) return val;
    // Fallback for PILOTDECK_CONDA_PYTHON: use "python" if env var not set
    if (varName === "PILOTDECK_CONDA_PYTHON") return "python";
    return "";
  });
}

function resolvePath(s: string): string {
  return expandHome(resolveEnvVars(s));
}

export type ParsePluginMcpServersResult = {
  servers: PilotDeckMcpServerSpec[];
  diagnostics: { id: string; message: string }[];
};

export function parsePluginMcpServers(
  raw: Record<string, unknown> | undefined,
): ParsePluginMcpServersResult {
  const servers: PilotDeckMcpServerSpec[] = [];
  const diagnostics: { id: string; message: string }[] = [];
  if (!raw || typeof raw !== "object") {
    return { servers, diagnostics };
  }
  for (const [id, value] of Object.entries(raw)) {
    if (!id || !value || typeof value !== "object") {
      diagnostics.push({ id, message: "missing or non-object spec" });
      continue;
    }
    const v = value as Record<string, unknown>;
    if (typeof v.command === "string" && v.command.length > 0) {
      servers.push({
        id,
        transport: "stdio",
        command: resolvePath(v.command),
        args: Array.isArray(v.args)
          ? (v.args.filter((a): a is string => typeof a === "string").map(resolvePath))
          : undefined,
        env: isStringRecord(v.env)
          ? Object.fromEntries(
              Object.entries(v.env as Record<string, string>).map(([k, val]) => [k, resolvePath(val)]),
            )
          : undefined,
        cwd: typeof v.cwd === "string" ? resolvePath(v.cwd) : undefined,
        perSession: v.perSession === true ? true : undefined,
      });
      continue;
    }
    const url = typeof v.url === "string" ? v.url : typeof v.httpUrl === "string" ? v.httpUrl : undefined;
    if (url) {
      servers.push({
        id,
        transport: "streamable_http",
        url,
        headers: isStringRecord(v.headers) ? (v.headers as Record<string, string>) : undefined,
      });
      continue;
    }
    diagnostics.push({ id, message: "no recognized transport (need command or url)" });
  }
  return { servers, diagnostics };
}

function isStringRecord(v: unknown): boolean {
  if (!v || typeof v !== "object") return false;
  for (const value of Object.values(v as Record<string, unknown>)) {
    if (typeof value !== "string") return false;
  }
  return true;
}
