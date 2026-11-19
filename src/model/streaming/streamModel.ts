import { normalizeModelError } from "../errors/normalizeModelError.js";
import { buildModelRequest } from "../request/buildModelRequest.js";
import { validateModelRequest } from "../request/validateModelRequest.js";
import type {
  CanonicalImageBlock,
  CanonicalModelEvent,
  CanonicalModelRequest,
  ModelConfig,
  ModelProtocol,
  ProviderConfig,
} from "../protocol/canonical.js";
import { ModelProviderError } from "../protocol/errors.js";
import { parseModelResponse } from "../response/parseModelResponse.js";
import { createStreamNormalizerState, normalizeStreamEvent } from "./normalizeStreamEvent.js";
import { StreamingCheckpointManager } from "./StreamingCheckpoint.js";

export type ModelTransport = typeof fetch;

export type ModelRuntimeOptions = {
  fetch?: ModelTransport;
  signal?: AbortSignal;
};

export async function complete(
  request: CanonicalModelRequest,
  config: ModelConfig,
  options: ModelRuntimeOptions = {},
) {
  const nonStreamingRequest = { ...request, stream: false };
  const { provider } = validateModelRequest(nonStreamingRequest, config);
  const body = buildModelRequest(nonStreamingRequest, config);
  const response = await sendProviderRequest(provider, body, false, options.fetch ?? fetch, options.signal);

  if (!response.ok) {
    const raw = await safeReadJson(response);
    throw new ModelProviderError(
      normalizeModelError(provider.id, provider.protocol, raw, response.status),
    );
  }

  const raw = await response.json();
  return parseModelResponse(provider.protocol, raw, provider.id);
}

const MAX_STREAM_RETRIES = 2;

export async function* streamModel(
  request: CanonicalModelRequest,
  config: ModelConfig,
  options: ModelRuntimeOptions = {},
): AsyncIterable<CanonicalModelEvent> {
  // Image-generation models (e.g. gpt-image-2) do not support streaming or
  // the Chat Completions endpoint. Route them through the dedicated
  // /images/generations or /images/edits path and synthesize an event
  // stream manually so downstream consumers stay unchanged.
  const stripped = stripUnsupportedFeatures(request, config);
  if (isImageGenerationModel(stripped, config)) {
    yield* completeImageGeneration(stripped, config, options);
    return;
  }

  const streamingRequest = { ...request, stream: true };
  const { provider } = validateModelRequest(streamingRequest, config);

  yield {
    type: "request_started",
    provider: provider.id,
    model: streamingRequest.model,
    metadata: streamingRequest.metadata,
  };

  let currentRequest = streamingRequest;
  const checkpoint = new StreamingCheckpointManager();

  for (let attempt = 0; attempt <= MAX_STREAM_RETRIES; attempt++) {
    throwIfAborted(options.signal);
    const body = buildModelRequest(currentRequest, config);
    if (process.env.PILOTDECK_DUMP_REQUEST === "1") {
      const fs = await import("node:fs");
      const dumpPath = `/tmp/pilotdeck_request_${Date.now()}.json`;
      fs.writeFileSync(dumpPath, JSON.stringify(body, null, 2));
      console.log(`[model-debug] Request dumped to ${dumpPath} (model=${currentRequest.model})`);
    }
    let response: Response;
    try {
      response = await sendProviderRequest(provider, body, true, options.fetch ?? fetch, options.signal);
    } catch (error) {
      if (attempt < MAX_STREAM_RETRIES && isRetryableStreamError(error)) {
        await delay(1000 * (attempt + 1));
        continue;
      }
      throw error;
    }

    if (!response.ok) {
      const raw = await safeReadJson(response);
      yield {
        type: "error",
        error: normalizeModelError(provider.id, provider.protocol, raw, response.status),
      };
      return;
    }

    if (!response.body) {
      yield {
        type: "error",
        error: normalizeModelError(provider.id, provider.protocol, new Error("Missing response body.")),
      };
      return;
    }

    const state = createStreamNormalizerState(streamingRequest.tools);
    let streamCompleted = false;

    try {
      for await (const rawEvent of readServerSentEvents(response.body, options.signal)) {
        for (const event of normalizeStreamEvent(provider.protocol, rawEvent, state)) {
          checkpoint.onEvent(event);
          yield event;
        }
      }
      streamCompleted = true;
    } catch (error) {
      if (
        attempt < MAX_STREAM_RETRIES &&
        isRetryableStreamError(error) &&
        checkpoint.hasSubstantialContent()
      ) {
        currentRequest = buildContinuationRequest(currentRequest, checkpoint.get().partialText);
        checkpoint.reset();
        await delay(1000 * (attempt + 1), options.signal);
        continue;
      }

      if (isRetryableStreamError(error) && attempt < MAX_STREAM_RETRIES) {
        await delay(1000 * (attempt + 1), options.signal);
        continue;
      }

      throw error;
    }

    if (streamCompleted) {
      return;
    }
  }
}

function isRetryableStreamError(error: unknown): boolean {
  if (isAbortError(error)) {
    return false;
  }
  if (error instanceof ModelProviderError) {
    return false;
  }
  if (error instanceof Error) {
    const msg = error.message.toLowerCase();
    return (
      msg.includes("network") ||
      msg.includes("econnreset") ||
      msg.includes("socket hang up") ||
      msg.includes("fetch failed") ||
      msg.includes("aborted") ||
      msg.includes("timeout") ||
      msg.includes("epipe") ||
      msg.includes("econnrefused")
    );
  }
  return false;
}

function buildContinuationRequest(
  original: CanonicalModelRequest & { stream: boolean },
  partialText: string,
): CanonicalModelRequest & { stream: boolean } {
  return {
    ...original,
    messages: [
      ...original.messages,
      {
        role: "assistant" as const,
        content: [{ type: "text" as const, text: partialText }],
      },
      {
        role: "user" as const,
        content: [{ type: "text" as const, text: "Continue from where you left off." }],
      },
    ],
  };
}

function delay(ms: number, signal?: AbortSignal): Promise<void> {
  if (!signal) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
  throwIfAborted(signal);
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      signal.removeEventListener("abort", onAbort);
      resolve();
    }, ms);
    const onAbort = () => {
      clearTimeout(timer);
      reject(createAbortError(signal.reason));
    };
    signal.addEventListener("abort", onAbort, { once: true });
  });
}

async function sendProviderRequest(
  provider: ProviderConfig,
  body: unknown,
  stream: boolean,
  transport: ModelTransport,
  signal?: AbortSignal,
): Promise<Response> {
  const controller = new AbortController();
  const detachAbort = signal ? forwardAbort(signal, controller) : undefined;
  const timeout = provider.timeoutMs
    ? setTimeout(() => controller.abort(), provider.timeoutMs)
    : undefined;

  const finalBody = provider.extraBody
    ? { ...(body as Record<string, unknown>), ...provider.extraBody }
    : body;

  try {
    return await transport(buildEndpoint(provider, stream), {
      method: "POST",
      headers: buildHeaders(provider),
      body: JSON.stringify(finalBody),
      signal: controller.signal,
    });
  } catch (error) {
    if (signal?.aborted) {
      throw createAbortError(signal.reason);
    }
    throw new ModelProviderError(normalizeModelError(provider.id, provider.protocol, error));
  } finally {
    if (timeout) {
      clearTimeout(timeout);
    }
    detachAbort?.();
  }
}

function forwardAbort(source: AbortSignal, target: AbortController): () => void {
  if (source.aborted) {
    target.abort(source.reason);
    return () => {};
  }

  const onAbort = () => target.abort(source.reason);
  source.addEventListener("abort", onAbort, { once: true });
  return () => source.removeEventListener("abort", onAbort);
}

function buildEndpoint(provider: ProviderConfig, _stream: boolean): string {
  if (provider.protocol === "anthropic") {
    return joinUrl(provider.url, "v1/messages");
  }

  return joinUrl(provider.url, "chat/completions");
}

function buildHeaders(provider: ProviderConfig): HeadersInit {
  const headers: Record<string, string> = {
    "content-type": "application/json",
    ...provider.headers,
  };

  // Defensive trim: parseModelConfig already strips whitespace from
  // apiKey, but a programmatic caller could hand a ProviderConfig in
  // here that bypassed the parser. A stray space in the header value
  // (`Bearer  sk-...`) is silently rejected by most providers as
  // `invalid_token`, so guard at the wire boundary too.
  const apiKey = provider.apiKey.trim();
  if (provider.protocol === "anthropic") {
    headers["x-api-key"] = apiKey;
    headers["anthropic-version"] = headers["anthropic-version"] ?? "2023-06-01";
  } else {
    headers.authorization = headers.authorization ?? `Bearer ${apiKey}`;
  }

  return headers;
}

async function safeReadJson(response: Response): Promise<unknown> {
  const text = await response.text();
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

async function* readServerSentEvents(
  body: ReadableStream<Uint8Array>,
  signal?: AbortSignal,
): AsyncIterable<unknown> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const cancelReader = () => {
    reader.cancel(signal?.reason).catch(() => undefined);
  };

  if (signal?.aborted) {
    cancelReader();
    throw createAbortError(signal.reason);
  }
  signal?.addEventListener("abort", cancelReader, { once: true });

  try {
    while (true) {
      throwIfAborted(signal);
      const { value, done } = await reader.read();
      throwIfAborted(signal);
      if (done) {
        buffer += decoder.decode();
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split(/\n\n/);
      buffer = chunks.pop() ?? "";

      for (const chunk of chunks) {
        const dataLines = chunk
          .split(/\n/)
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice("data:".length).trim());

        for (const data of dataLines) {
          if (!data || data === "[DONE]") {
            continue;
          }
          yield JSON.parse(data);
        }
      }
    }
  } finally {
    signal?.removeEventListener("abort", cancelReader);
  }
}

function throwIfAborted(signal?: AbortSignal): void {
  if (signal?.aborted) {
    throw createAbortError(signal.reason);
  }
}

function createAbortError(reason?: unknown): Error {
  if (reason instanceof Error) return reason;
  const message = typeof reason === "string" && reason ? reason : "Operation aborted.";
  return new DOMException(message, "AbortError");
}

function isAbortError(error: unknown): boolean {
  return error instanceof Error && (error.name === "AbortError" || error.message.toLowerCase().includes("aborted"));
}

function joinUrl(base: string, path: string): string {
  return `${base.replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`;
}

// ─── Image generation (gpt-image-2 and compatible models) ──────────────────

// Upstream image APIs are slow but finite; without a client-side ceiling a
// stalled request would keep the turn (and the UI spinner) alive forever.
// Five minutes comfortably covers real generation times (1-3 min observed).
const DEFAULT_IMAGE_TIMEOUT_MS = 5 * 60 * 1000;
//
// These models don't speak the Chat Completions protocol. They expose two
// REST endpoints instead:
//   • POST /images/generations  — text-to-image
//   • POST /images/edits        — image+text-to-image (multipart/form-data)
//
// `streamModel` detects `modelType === "image_generation"` and routes here
// instead of trying to stream SSE from an endpoint that doesn't support it.

function stripUnsupportedFeatures(
  request: CanonicalModelRequest,
  config: ModelConfig,
): CanonicalModelRequest {
  if (!isImageGenerationModel(request, config)) return request;
  // Image models reject `tools`, `tool_choice`, and related fields.
  return {
    ...request,
    tools: undefined,
    toolChoice: undefined,
  };
}

function isImageGenerationModel(
  request: CanonicalModelRequest,
  config: ModelConfig,
): boolean {
  const { provider, modelId } = resolveProviderAndModel(request, config);
  const modelDef = provider?.models?.[modelId];
  return modelDef?.modelType === "image_generation";
}

function resolveProviderAndModel(
  request: CanonicalModelRequest,
  config: ModelConfig,
): { provider: ProviderConfig | undefined; modelId: string } {
  const modelRef = request.model;
  if (!modelRef) return { provider: undefined, modelId: "" };
  // Format: "provider/model" or just "model" (use default provider)
  const slashIndex = modelRef.indexOf("/");
  if (slashIndex > 0) {
    const providerId = modelRef.slice(0, slashIndex);
    const modelId = modelRef.slice(slashIndex + 1);
    const provider = config.providers?.[providerId];
    return { provider, modelId };
  }
  // Fall back: search all providers for this model id
  for (const provider of Object.values(config.providers ?? {})) {
    if (provider.models?.[modelRef]) {
      return { provider, modelId: modelRef };
    }
  }
  return { provider: undefined, modelId: modelRef };
}

async function* completeImageGeneration(
  request: CanonicalModelRequest,
  config: ModelConfig,
  options: ModelRuntimeOptions,
): AsyncIterable<CanonicalModelEvent> {
  const { provider, modelId } = resolveProviderAndModel(request, config);
  if (!provider) {
    yield {
      type: "error",
      error: {
        provider: request.model?.split("/")[0] ?? "unknown",
        protocol: "openai",
        code: "provider_not_found",
        message: `No provider configured for model "${request.model}".`,
        retryable: false,
      },
    };
    return;
  }

  yield {
    type: "request_started",
    provider: provider.id,
    model: request.model,
    metadata: request.metadata,
  };
  yield { type: "message_start", role: "assistant" };

  try {
    const { prompt, images } = extractPromptAndImages(request);
    const size = resolveImageSize(prompt);
    // [TEMP-DEBUG] reference-image diagnosis
    console.error(
      `[img-ref-debug] model=${request.model} images=${images.length} mimes=${JSON.stringify(images.map((i) => i.mimeType))} bytes=${JSON.stringify(images.map((i) => Math.round((i.data?.length ?? 0) * 0.75)))} endpoint=${images.length > 0 ? "edits" : "generations"} prompt=${JSON.stringify(prompt.slice(0, 200))}`,
    );

    let raw: unknown;
    if (images.length > 0) {
      raw = await sendImageEditRequest(provider, modelId, prompt, images, size, options);
    } else {
      raw = await sendImageGenerationRequest(provider, modelId, prompt, size, options);
    }

    const parsed = raw as { data?: Array<{ b64_json?: string; url?: string; revised_prompt?: string }> };
    const items = Array.isArray(parsed?.data) ? parsed.data : [];
    if (items.length === 0) {
      yield {
        type: "error",
        error: {
          provider: provider.id,
          protocol: provider.protocol,
          code: "provider_error",
          message: "Image generation returned no data.",
          retryable: true,
        },
      };
      return;
    }

    for (const item of items) {
      const data = item.b64_json ?? item.url ?? "";
      if (!data) continue;
      const isUrl = !item.b64_json;
      const image: CanonicalImageBlock = {
        type: "image",
        source: isUrl ? "url" : "base64",
        data,
        mimeType: "image/png",
      };
      yield { type: "image_block", image, raw: item };
    }

    yield { type: "message_end", finishReason: "stop" };
    yield {
      type: "usage",
      usage: { inputTokens: 0, outputTokens: 0 },
    };
  } catch (error) {
    // A user stop (or the default timeout) must unwind the turn as aborted.
    // Swallowing it here would surface a generic provider error instead and
    // leave the consumer waiting for a message_end that never comes.
    if (isAbortError(error)) {
      throw error;
    }
    yield {
      type: "error",
      error: normalizeModelError(provider.id, provider.protocol, error),
    };
  }
}

function extractPromptAndImages(
  request: CanonicalModelRequest,
): { prompt: string; images: CanonicalImageBlock[] } {
  const promptParts: string[] = [];
  const images: CanonicalImageBlock[] = [];
  for (const message of request.messages) {
    if (message.role !== "user") continue;
    const content = Array.isArray(message.content) ? message.content : [];
    for (const block of content) {
      if (block.type === "text") {
        promptParts.push(block.text);
      } else if (block.type === "image") {
        images.push(block as CanonicalImageBlock);
      }
    }
  }
  return { prompt: promptParts.join("\n").trim(), images };
}

/**
 * Resolve the requested image size from the user's prompt. The upstream
 * image API only supports three sizes (landscape / square / portrait), so
 * any requested dimension or ratio is snapped to the closest one.
 *
 * Chat history is joined into `prompt`, so size hints from earlier turns
 * coexist with the current request. The LAST user message is checked first
 * and matches are taken from the end of the text, so the most recent intent
 * always wins (e.g. a follow-up "改成竖版" must override an earlier "16:9").
 */
function resolveImageSize(prompt: string): string {
  const lines = prompt.split("\n").filter((line) => line.trim().length > 0);
  const lastLine = lines[lines.length - 1] ?? "";
  return (
    resolveImageSizeFromText(lastLine) ??
    resolveImageSizeFromText(prompt) ??
    "1024x1024"
  );
}

function resolveImageSizeFromText(text: string): string | undefined {
  if (!text) return undefined;
  const lower = text.toLowerCase();

  // Explicit pixel size, e.g. "1920x1080" — last mention wins.
  const pixelMatches = [...lower.matchAll(/(\d{3,5})\s*[x×]\s*(\d{3,5})/g)];
  if (pixelMatches.length > 0) {
    const match = pixelMatches[pixelMatches.length - 1];
    const w = parseInt(match[1], 10);
    const h = parseInt(match[2], 10);
    if (w > 0 && h > 0) return snapToSupportedSize(w / h);
  }

  // Ratio, e.g. "16:9" / "9:16" / "9比16" — last mention wins.
  const ratioMatches = [
    ...lower.matchAll(/(\d{1,2})\s*[:：比]\s*(\d{1,2})/g),
  ];
  if (ratioMatches.length > 0) {
    const match = ratioMatches[ratioMatches.length - 1];
    const w = parseInt(match[1], 10);
    const h = parseInt(match[2], 10);
    if (w > 0 && h > 0) return snapToSupportedSize(w / h);
  }

  // Chinese keywords
  if (/横版|横向|宽屏|横屏|横图|横构图/.test(lower)) return "1536x1024";
  if (/竖版|纵向|竖屏|竖图|竖构图/.test(lower)) return "1024x1536";

  // English keywords
  if (/\blandscape\b/.test(lower)) return "1536x1024";
  if (/\bportrait\b/.test(lower)) return "1024x1536";

  return undefined;
}

/**
 * Snap an arbitrary width/height ratio to the closest supported size.
 * gpt-image-* models only accept 1536x1024 (3:2), 1024x1536 (2:3), and
 * 1024x1024 (1:1).
 */
function snapToSupportedSize(ratio: number): string {
  if (ratio >= 1.15) return "1536x1024";
  if (ratio <= 0.87) return "1024x1536";
  return "1024x1024";
}

function buildImageGenerationBody(
  modelId: string,
  prompt: string,
  size: string,
  extraBody?: Record<string, unknown>,
): Record<string, unknown> {
  const body: Record<string, unknown> = {
    model: modelId,
    prompt,
    n: 1,
    size,
    response_format: "b64_json",
  };
  if (extraBody && typeof extraBody === "object") {
    Object.assign(body, extraBody);
  }
  return body;
}

async function sendImageGenerationRequest(
  provider: ProviderConfig,
  modelId: string,
  prompt: string,
  size: string,
  options: ModelRuntimeOptions,
): Promise<unknown> {
  const endpoint = joinUrl(provider.url, "images/generations");
  const body = buildImageGenerationBody(modelId, prompt, size, provider.extraBody);
  const transport = options.fetch ?? fetch;

  const controller = new AbortController();
  const detachAbort = options.signal ? forwardAbort(options.signal, controller) : undefined;
  // Image generation is slow (1-3 min is normal) but must not hang forever:
  // apply the provider timeout when configured, else a generous default.
  const timeoutMs = provider.timeoutMs ?? DEFAULT_IMAGE_TIMEOUT_MS;
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await transport(endpoint, {
      method: "POST",
      headers: buildHeaders(provider),
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    if (!response.ok) {
      const raw = await safeReadJson(response);
      throw new ModelProviderError(normalizeModelError(provider.id, provider.protocol, raw, response.status));
    }
    return await response.json();
  } finally {
    if (timeout) clearTimeout(timeout);
    detachAbort?.();
  }
}

async function sendImageEditRequest(
  provider: ProviderConfig,
  modelId: string,
  prompt: string,
  images: CanonicalImageBlock[],
  size: string,
  options: ModelRuntimeOptions,
): Promise<unknown> {
  const endpoint = joinUrl(provider.url, "images/edits");
  const transport = options.fetch ?? fetch;
  const formData = new FormData();
  formData.append("model", modelId);
  formData.append("prompt", prompt);
  formData.append("n", "1");
  formData.append("size", size);
  formData.append("response_format", "b64_json");

  // Attach the first reference image (OpenAI /images/edits accepts one
  // image per call for gpt-image-* models). Decoded from base64 to a Blob
  // so fetch can set the multipart boundary automatically.
  const refImage = images[0];
  if (refImage) {
    const base64Data = refImage.source === "base64" ? refImage.data : "";
    if (base64Data) {
      const byteString = atob(base64Data);
      const bytes = new Uint8Array(byteString.length);
      for (let i = 0; i < byteString.length; i++) {
        bytes[i] = byteString.charCodeAt(i);
      }
      const blob = new Blob([bytes], { type: refImage.mimeType || "image/png" });
      formData.append("image", blob, "reference.png");
    }
  }

  const controller = new AbortController();
  const detachAbort = options.signal ? forwardAbort(options.signal, controller) : undefined;
  // Same default-timeout guard as sendImageGenerationRequest: never hang
  // forever when the upstream edits endpoint stalls.
  const timeoutMs = provider.timeoutMs ?? DEFAULT_IMAGE_TIMEOUT_MS;
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    // Don't set Content-Type: fetch infers multipart/form-data + boundary.
    const headers: Record<string, string> = { ...provider.headers };
    const apiKey = provider.apiKey.trim();
    if (provider.protocol === "anthropic") {
      headers["x-api-key"] = apiKey;
      headers["anthropic-version"] = headers["anthropic-version"] ?? "2023-06-01";
    } else {
      headers.authorization = headers.authorization ?? `Bearer ${apiKey}`;
    }

    const response = await transport(endpoint, {
      method: "POST",
      headers,
      body: formData,
      signal: controller.signal,
    });
    if (!response.ok) {
      const raw = await safeReadJson(response);
      throw new ModelProviderError(normalizeModelError(provider.id, provider.protocol, raw, response.status));
    }
    return await response.json();
  } finally {
    if (timeout) clearTimeout(timeout);
    detachAbort?.();
  }
}
