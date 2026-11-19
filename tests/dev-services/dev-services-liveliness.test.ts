import test from "node:test";
import assert from "node:assert/strict";
import * as http from "node:http";

/**
 * Dev services smoke test.
 *
 * Covers the user-reported regressions where http://localhost:5173/ becomes
 * unreachable because one or more of the four background services have
 * exited.  It validates:
 *   1. All four TCP ports are LISTEN (18789 gateway, 3001 ui server, 5173
 *      vite client, 8765 open-earth python).
 *   2. 5173 returns HTTP 200 + text/html (Vite index document).
 *   3. /api/projects proxied via 5173 returns HTTP 200 and a JSON array
 *      (Vite -> Express 3001 -> Gateway 18789 bridge).
 *   4. /api/open-earth/knowledge/stats proxied via 5173 returns HTTP 200
 *      and a body containing total_entries (Vite -> 3001 -> OEA 8765).
 *
 * Failures reproduce the exact symptoms of the historical "5173打不开"
 * reports and prevent silent regressions of service liveliness.
 */

const PORTS: Array<{ name: string; port: number }> = [
  { name: "Gateway (18789)", port: 18789 },
  { name: "Server (3001)", port: 3001 },
  { name: "Vite client (5173)", port: 5173 },
  { name: "OpenEarthEngine OEA (8765)", port: 8765 },
];

const REQUEST_TIMEOUT_MS = 4000;

function httpGetString(urlStr: string): Promise<{ status: number; body: string; headers: http.IncomingHttpHeaders }> {
  return new Promise((resolve, reject) => {
    const url = new URL(urlStr);
    const req = http.request(
      {
        host: url.hostname,
        port: url.port,
        path: url.pathname + url.search,
        method: "GET",
        timeout: REQUEST_TIMEOUT_MS,
        headers: {
          // The ui server returns 401 for unauthenticated requests to the
          // /api/open-earth routes, so reuse the server-token the same way
          // the browser does after login.
          ...(process.env.PILOTDECK_SERVER_TOKEN
            ? { Authorization: `Bearer ${process.env.PILOTDECK_SERVER_TOKEN}` }
            : {}),
        },
      },
      (res) => {
        const chunks: Array<Buffer> = [];
        res.on("data", (c: Buffer) => chunks.push(c));
        res.on("end", () =>
          resolve({
            status: res.statusCode ?? 0,
            headers: res.headers,
            body: Buffer.concat(chunks).toString("utf8"),
          }),
        );
      },
    );
    req.on("timeout", () => {
      req.destroy(new Error(`Request to ${urlStr} timed out after ${REQUEST_TIMEOUT_MS}ms`));
    });
    req.on("error", (err) => reject(err));
    req.end();
  });
}

async function readServerToken(): Promise<string | undefined> {
  // Mirror ui/server/routes/auth.js location.
  const { readFile } = await import("node:fs/promises");
  const { join } = await import("node:path");
  const base = process.env.PILOT_HOME ?? process.env.PILOTDECK_CONFIG_DIR ?? join(process.env.HOME ?? "/root", ".pilotdeck");
  try {
    return (await readFile(join(base, "server-token"), "utf8")).trim();
  } catch {
    return undefined;
  }
}

test("four dev service ports are listening on localhost", async (t) => {
  const net = await import("node:net");
  for (const spec of PORTS) {
    await t.test(`${spec.name} on :${spec.port} is reachable`, () =>
      new Promise<void>((resolve, reject) => {
        const s = new net.Socket();
        const timer = setTimeout(() => {
          s.destroy();
          reject(new Error(`Connection to 127.0.0.1:${spec.port} timed out`));
        }, 1500);
        s.setTimeout(1500);
        s.once("connect", () => {
          clearTimeout(timer);
          s.end();
          resolve();
        });
        s.once("error", (e) => {
          clearTimeout(timer);
          reject(e);
        });
        s.connect(spec.port, "127.0.0.1");
      }),
    );
  }
});

test("5173 root page returns Vite HTML document (HTTP 200, text/html)", async () => {
  const res = await httpGetString("http://127.0.0.1:5173/");
  assert.equal(res.status, 200, `Expected 5173 HTTP 200, got ${res.status}. Body head: ${res.body.slice(0, 120)}`);
  const ct = res.headers["content-type"] ?? "";
  assert.ok(
    ct.includes("text/html"),
    `Expected 5173 root content-type text/html, got "${ct}". Body head: ${res.body.slice(0, 120)}`,
  );
  assert.ok(
    res.body.trim().toLowerCase().startsWith("<!doctype html>") ||
      res.body.toLowerCase().includes("<html"),
    `5173 root body does not look like HTML: ${res.body.slice(0, 120)}`,
  );
});

test("5173 /api/projects returns JSON array (Vite -> 3001 -> 18789 bridge)", async () => {
  const token = await readServerToken();
  assert.ok(token, "server-token missing; cannot authenticate /api/projects call");
  process.env.PILOTDECK_SERVER_TOKEN = token;

  const res = await httpGetString("http://127.0.0.1:5173/api/projects");
  // The proxy through 3001 should succeed.  It is acceptable for the first
  // call to race and return 401 only if the header was stripped; otherwise
  // we expect 2xx with a JSON array of projects.
  assert.equal(res.status, 200, `Expected 5173 /api/projects HTTP 200, got ${res.status}. Body: ${res.body.slice(0, 240)}`);
  let parsed: unknown;
  try {
    parsed = JSON.parse(res.body);
  } catch (e) {
    assert.fail(`/api/projects did not return valid JSON: ${(e as Error).message}. Body: ${res.body.slice(0, 240)}`);
  }
  assert.ok(Array.isArray(parsed), `/api/projects expected JSON array, got ${typeof parsed}: ${res.body.slice(0, 240)}`);
});

test("5173 /api/open-earth/knowledge/stats returns total_entries (Vite -> 3001 -> 8765 OEA)", async () => {
  const token = process.env.PILOTDECK_SERVER_TOKEN ?? (await readServerToken());
  assert.ok(token, "server-token missing for /api/open-earth/knowledge/stats call");
  process.env.PILOTDECK_SERVER_TOKEN = token;

  const res = await httpGetString("http://127.0.0.1:5173/api/open-earth/knowledge/stats");
  assert.equal(res.status, 200, `Expected /knowledge/stats HTTP 200, got ${res.status}. Body: ${res.body.slice(0, 240)}`);
  let parsed: unknown;
  try {
    parsed = JSON.parse(res.body);
  } catch (e) {
    assert.fail(`/knowledge/stats did not return valid JSON: ${(e as Error).message}. Body: ${res.body.slice(0, 240)}`);
  }
  const obj = parsed as { total_entries?: unknown };
  assert.equal(
    typeof obj.total_entries,
    "number",
    `/knowledge/stats missing number total_entries. Body: ${res.body.slice(0, 240)}`,
  );
});
