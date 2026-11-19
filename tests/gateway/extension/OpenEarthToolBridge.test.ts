import { describe, it, expect, beforeEach, vi } from "vitest";
import { McpRuntime } from "../../../src/mcp/runtime/McpRuntime.js";
import { OpenEarthToolBridge } from "../../../src/gateway/extension/OpenEarthToolBridge.js";
import type { PilotDeckMcpServerSpec, PilotDeckMcpToolSpec } from "../../../src/mcp/protocol/types.js";

describe("OpenEarthToolBridge", () => {
  let mockRuntime: McpRuntime;
  let bridge: OpenEarthToolBridge;

  beforeEach(() => {
    const mockServers: PilotDeckMcpServerSpec[] = [
      { id: "rs-agent", transport: "stdio", command: "python", args: ["-m", "rs_engine.mcp_server"], cwd: "/tmp" },
    ];

    mockRuntime = new McpRuntime(mockServers);

    vi.spyOn(mockRuntime, "listAllTools").mockResolvedValue([
      {
        serverId: "rs-agent",
        toolName: "rs_download",
        wireName: "mcp__rs-agent__rs_download",
        description: "Download satellite images",
        inputSchema: { type: "object", properties: {}, required: [] },
      } as PilotDeckMcpToolSpec,
    ]);

    vi.spyOn(mockRuntime, "getClient").mockReturnValue({
      callTool: vi.fn().mockResolvedValue({ content: [{ type: "text", text: "Success" }], isError: false }),
      getStatus: vi.fn().mockReturnValue("ready"),
    } as unknown as ReturnType<typeof mockRuntime.getClient>);

    vi.spyOn(mockRuntime, "statuses").mockReturnValue([{ serverId: "rs-agent", status: "ready" }]);

    bridge = new OpenEarthToolBridge(mockRuntime);
  });

  it("should initialize and list tools", async () => {
    await bridge.initialize();
    const tools = bridge.listTools();
    expect(tools.length).toBeGreaterThan(0);
    expect(tools[0].toolId).toBe("rs-agent.rs_download");
  });

  it("should map parameters correctly for rs_download", async () => {
    await bridge.initialize();
    const args = {
      satellite: "sentinel2",
      region: "Beijing",
      start: "2024-01-01",
      end: "2024-12-31",
    };

    const result = await bridge.executeMcpTool("rs-agent.rs_download", args);

    expect(result.success).toBe(true);
  });

  it("should validate required parameters", async () => {
    await bridge.initialize();
    const args = { sensor: "sentinel2" };

    const result = await bridge.executeMcpTool("rs-agent.rs_download", args);

    expect(result.success).toBe(false);
    expect(result.errorCode).toBe("PARAM_VALIDATION_FAILED");
  });

  it("should get health status", async () => {
    await bridge.initialize();
    const health = bridge.getHealthStatus();
    expect(health["rs-agent"]).toBeDefined();
    expect(health["rs-agent"].status).toBe("ready");
  });
});
