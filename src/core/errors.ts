export class ProviderError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly retryable: boolean,
    public readonly requiresSplit: boolean,
    public readonly statusCode?: number
  ) {
    super(message);
    this.name = "ProviderError";
  }
}

export function classifyProviderFailure(status: number, body: string): ProviderError {
  const normalized = body.toLowerCase();
  const contextMarkers = [
    "context length",
    "context window",
    "too many tokens",
    "prompt is too long",
    "kv cache",
    "out of memory",
    "image too large",
    "payload too large"
  ];
  const requiresSplit = status === 413 || contextMarkers.some((marker) => normalized.includes(marker));
  const retryable = status === 408 || status === 409 || status === 429 || status >= 500;
  return new ProviderError(
    `Fournisseur OCR: HTTP ${status} — ${body.slice(0, 800)}`,
    requiresSplit ? "CONTEXT_OR_PAYLOAD_OVERFLOW" : `HTTP_${status}`,
    retryable,
    requiresSplit,
    status
  );
}
