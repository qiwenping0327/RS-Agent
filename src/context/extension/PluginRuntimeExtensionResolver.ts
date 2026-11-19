import type { PilotDeckLoadedPlugin } from "../../extension/index.js";
import type {
  ContributedCommand,
  ContributedSkill,
  ExtensionResolver,
  McpServerInstruction,
} from "./ExtensionResolver.js";

/**
 * Minimal runtime contract; extension owner has agreed to expose
 * `getAllCommands()` / `getAllSkills()` aggregators (review 2026-05). Until
 * those exist, we accept just `snapshot()` and flatMap manually with a TODO
 * marker.
 *
 * `ExtensionSnapshot` (turn-stable contribution view) is the long-term API;
 * this resolver will be migrated to read it once the extension owner ships it.
 */
export type PluginRuntimeLike = {
  snapshot(): PilotDeckLoadedPlugin[];
  /** Optional aggregator preferred when available. */
  getAllCommands?(): ContributedCommand[];
  getAllSkills?(): ContributedSkill[];
  /** Optional aggregator for MCP instructions. Phase 6 leaves this empty. */
  getAllMcpInstructions?(): McpServerInstruction[];
};

/**
 * Contract for the MCP runtime to supply dynamic instructions fetched from
 * connected MCP servers via the initialize handshake.
 */
export type McpRuntimeLike = {
  /** Returns instructions from all connected MCP servers. */
  getInstructions(): { serverId: string; instructions: string }[];
};

/**
 * Wraps a `PluginRuntime` (or compatible) so context can read plugin-derived
 * info without reaching into `PilotDeckLoadedPlugin` directly.
 *
 * Decision §3.2 — read-only resolver, no separate registry. When extension
 * owner ships the `ExtensionSnapshot` API this implementation should switch
 * to consume it (deferred `context-extension-snapshot`).
 */
export class PluginRuntimeExtensionResolver implements ExtensionResolver {
  private mcpRuntimes: McpRuntimeLike[] = [];

  constructor(private readonly runtime: PluginRuntimeLike) {}

  /**
   * Inject an MCP runtime so dynamic instructions from connected servers
   * can be merged into the system prompt. Called after MCP startup completes.
   * Multiple runtimes can be registered (e.g. shared + per-session).
   */
  addMcpRuntime(mcpRuntime: McpRuntimeLike): void {
    this.mcpRuntimes.push(mcpRuntime);
  }

  listCommands(): ContributedCommand[] {
    if (this.runtime.getAllCommands) {
      return this.runtime.getAllCommands();
    }
    return this.runtime.snapshot().flatMap((plugin) =>
      (plugin.commands ?? []).map(
        (command): ContributedCommand => ({
          name: command.name,
          description: typeof command.frontmatter?.description === "string" ? command.frontmatter.description : undefined,
          argumentHint:
            typeof command.frontmatter?.["argument-hint"] === "string"
              ? (command.frontmatter["argument-hint"] as string)
              : undefined,
          namespace: plugin.name,
        }),
      ),
    );
  }

  listSkills(): ContributedSkill[] {
    if (this.runtime.getAllSkills) {
      return this.runtime.getAllSkills();
    }
    return this.runtime.snapshot().flatMap((plugin) =>
      (plugin.skills ?? []).map(
        (skill): ContributedSkill => ({
          name: skill.name,
          description: typeof skill.frontmatter?.description === "string" ? skill.frontmatter.description : undefined,
          namespace: plugin.name,
        }),
      ),
    );
  }

  listMcpInstructions(): McpServerInstruction[] {
    // 1. Start with static instructions from plugin manifests
    const staticInstructions = this.runtime.getAllMcpInstructions
      ? this.runtime.getAllMcpInstructions()
      : [];

    // 2. Merge dynamic instructions from all connected MCP runtimes
    const dynamicInstructions: McpServerInstruction[] = [];
    for (const mcpRuntime of this.mcpRuntimes) {
      for (const entry of mcpRuntime.getInstructions()) {
        if (entry.instructions.trim().length > 0) {
          dynamicInstructions.push({
            serverName: entry.serverId,
            instructions: entry.instructions,
          });
        }
      }
    }

    // 3. Merge: dynamic instructions override static ones for the same server
    const merged = new Map<string, McpServerInstruction>();
    for (const entry of staticInstructions) {
      if (entry.instructions && entry.instructions.trim().length > 0) {
        merged.set(entry.serverName, entry);
      }
    }
    for (const entry of dynamicInstructions) {
      if (entry.instructions && entry.instructions.trim().length > 0) {
        merged.set(entry.serverName, entry);
      }
    }

    return [...merged.values()].sort((a, b) => a.serverName.localeCompare(b.serverName));
  }
}
