export interface BridgeExecutionResult {
  success: boolean;
  result?: unknown;
  error?: string;
  errorCode?: string;
  missingParams?: string[];
  wireName?: string;
  toolId?: string;
  rawResult?: unknown;
  attempt?: number;
}

export interface ParamMappingRule {
  aliases?: string[];
  default?: unknown;
  enum?: string[];
  format?: string;
  transform?: (value: unknown) => unknown;
}

export interface ParamMappingConfig {
  paramRules: Record<string, ParamMappingRule>;
  required: string[];
}

export interface RetryPolicy {
  maxRetries: number;
  initialDelayMs: number;
  maxDelayMs: number;
  backoffMultiplier: number;
  retryableErrorCodes: string[];
}
