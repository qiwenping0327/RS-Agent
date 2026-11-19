import { McpRuntime } from "../../mcp/runtime/McpRuntime.js";
import { McpClient, McpClientError } from "../../mcp/client/McpClient.js";
import { buildMcpToolWireName } from "../../mcp/runtime/wireName.js";
import type {
  BridgeExecutionResult,
  ParamMappingConfig,
  RetryPolicy,
} from "./openEarthTypes.js";
import type { PilotDeckMcpToolSpec } from "../../mcp/protocol/types.js";

const DEFAULT_RETRY_POLICY: RetryPolicy = {
  maxRetries: 3,
  initialDelayMs: 1000,
  maxDelayMs: 10000,
  backoffMultiplier: 2,
  retryableErrorCodes: [
    "mcp_session_expired",
    "mcp_call_timeout",
    "mcp_handshake_failed",
  ],
};

const TOOL_PARAM_MAPPINGS: Record<string, ParamMappingConfig> = {
  "rs-agent.rs_download": {
    paramRules: {
      sensor: {
        aliases: ["satellite", "sensor_type"],
        default: "sentinel2",
      },
      aoi: { aliases: ["region", "area", "polygon"] },
      start_date: { aliases: ["start", "from", "date_start"] },
      end_date: { aliases: ["end", "to", "date_end"] },
      max_cloud_cover: { aliases: ["cloud", "cloud_cover"], default: 20 },
      output_dir: { aliases: ["output", "out_dir"] },
    },
    required: ["sensor", "aoi", "start_date", "end_date"],
  },
  "rs-agent.rs_preprocess": {
    paramRules: {
      input_path: { aliases: ["input", "image", "src", "source"] },
      operations: { aliases: ["steps", "ops", "preprocess_steps"] },
      params: { aliases: ["options", "config", "kwargs"], default: {} },
      output_dir: { aliases: ["output"] },
    },
    required: ["input_path", "operations"],
  },
  "rs-agent.rs_analyze": {
    paramRules: {
      input_path: { aliases: ["input", "image"] },
      analysis_type: { aliases: ["analysis", "type", "index_type"] },
      index: { aliases: ["index_name", "specific_index"] },
      params: { aliases: ["options"], default: {} },
    },
    required: ["input_path", "analysis_type"],
  },
  "rs-index.ndvi_calc": {
    paramRules: {
      input_nir_path: { aliases: ["nir_path", "nir_band", "band_nir"] },
      input_red_path: { aliases: ["red_path", "red_band", "band_red"] },
      output_path: { aliases: ["output", "result_path"] },
    },
    required: ["input_nir_path", "input_red_path", "output_path"],
  },
};

export class OpenEarthToolBridge {
  private toolSpecs: Map<string, PilotDeckMcpToolSpec> = new Map();
  private retryPolicy: RetryPolicy;
  private circuitBreakers: Map<string, { failures: number; lastFailureAt: number }> = new Map();

  constructor(
    public readonly runtime: McpRuntime,
    retryPolicy?: Partial<RetryPolicy>,
  ) {
    this.retryPolicy = { ...DEFAULT_RETRY_POLICY, ...retryPolicy };
  }

  async initialize(): Promise<void> {
    const tools = await this.runtime.listAllTools();
    for (const tool of tools) {
      const key = `${tool.serverId}.${tool.toolName}`;
      this.toolSpecs.set(key, tool);
    }
  }

  async executeMcpTool(
    toolId: string,
    args: Record<string, unknown>,
    options: {
      abortSignal?: AbortSignal;
      timeoutMs?: number;
      workspaceId?: string;
    } = {},
  ): Promise<BridgeExecutionResult> {
    const [serverId, toolName] = this.parseToolId(toolId);
    const toolSpec = this.toolSpecs.get(toolId);

    if (!toolSpec) {
      return { success: false, error: `Tool not found: ${toolId}`, errorCode: "TOOL_NOT_FOUND" };
    }

    const mappedArgs = this.mapParameters(toolId, args);
    const validation = this.validateParams(toolId, mappedArgs);

    if (!validation.valid) {
      return {
        success: false,
        error: `Parameter validation failed: ${validation.missing.join(", ")}`,
        errorCode: "PARAM_VALIDATION_FAILED",
        missingParams: validation.missing,
      };
    }

    return this.executeWithRetry(toolId, serverId, toolName, mappedArgs, options, 0);
  }

  private parseToolId(toolId: string): [string, string] {
    const parts = toolId.split(".");
    if (parts.length < 2) {
      throw new Error(`Invalid tool ID format: ${toolId}`);
    }
    return [parts[0], parts.slice(1).join(".")];
  }

  private mapParameters(
    toolId: string,
    rawArgs: Record<string, unknown>,
  ): Record<string, unknown> {
    const mapping = TOOL_PARAM_MAPPINGS[toolId];
    if (!mapping) return rawArgs;

    const mapped: Record<string, unknown> = {};

    for (const [targetParam, rule] of Object.entries(mapping.paramRules)) {
      if (rawArgs[targetParam] !== undefined) {
        mapped[targetParam] = rawArgs[targetParam];
        continue;
      }

      let found = false;
      for (const alias of rule.aliases || []) {
        if (rawArgs[alias] !== undefined) {
          mapped[targetParam] = rawArgs[alias];
          found = true;
          break;
        }
      }

      if (!found && rule.default !== undefined) {
        mapped[targetParam] = rule.default;
      }
    }

    return mapped;
  }

  private validateParams(
    toolId: string,
    args: Record<string, unknown>,
  ): { valid: boolean; missing: string[] } {
    const mapping = TOOL_PARAM_MAPPINGS[toolId];
    if (!mapping) return { valid: true, missing: [] };

    const missing: string[] = [];
    for (const required of mapping.required) {
      if (args[required] === undefined) missing.push(required);
    }

    return { valid: missing.length === 0, missing };
  }

  private async executeWithRetry(
    toolId: string,
    serverId: string,
    toolName: string,
    args: Record<string, unknown>,
    options: { abortSignal?: AbortSignal; timeoutMs?: number },
    attempt: number,
  ): Promise<BridgeExecutionResult> {
    const client = this.runtime.getClient(serverId);
    if (!client) {
      return { success: false, error: `MCP server not connected: ${serverId}`, errorCode: "SERVER_NOT_CONNECTED" };
    }

    try {
      const wireName = buildMcpToolWireName(serverId, toolName);
      const result = await client.callTool(toolName, args, {
        signal: options.abortSignal,
        timeoutMs: options.timeoutMs,
      });

      this.circuitBreakers.delete(serverId);

      if (result.isError === true) {
        return { success: false, error: `Tool execution error`, errorCode: "TOOL_EXECUTION_ERROR", rawResult: result.content };
      }

      return { success: true, result: result.content, wireName, toolId };
    } catch (err) {
      const mcpError = err as McpClientError;
      const isRetryable =
        this.retryPolicy.retryableErrorCodes.includes(mcpError.code as string) &&
        attempt < this.retryPolicy.maxRetries;

      if (isRetryable) {
        const delay = Math.min(
          this.retryPolicy.initialDelayMs * Math.pow(this.retryPolicy.backoffMultiplier, attempt),
          this.retryPolicy.maxDelayMs,
        );
        await this.sleep(delay);
        return this.executeWithRetry(toolId, serverId, toolName, args, options, attempt + 1);
      }

      return { success: false, error: mcpError.message, errorCode: mcpError.code, attempt };
    }
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  getToolSpec(toolId: string): PilotDeckMcpToolSpec | undefined {
    return this.toolSpecs.get(toolId);
  }

  listTools(): Array<{ toolId: string; serverId: string; toolName: string }> {
    return Array.from(this.toolSpecs.keys()).map((toolId) => {
      const [serverId, toolName] = this.parseToolId(toolId);
      return { toolId, serverId, toolName };
    });
  }

  getHealthStatus(): Record<string, { status: string; failures: number }> {
    const status: Record<string, { status: string; failures: number }> = {};
    for (const client of this.runtime.statuses()) {
      const breaker = this.circuitBreakers.get(client.serverId);
      status[client.serverId] = { status: client.status, failures: breaker?.failures || 0 };
    }
    return status;
  }
}
