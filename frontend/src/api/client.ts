import { env } from "../config/env";

interface ErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
    details?: Array<Record<string, unknown>>;
    request_id?: string | null;
  };
}

export class ApiError extends Error {
  readonly code: string;
  readonly details: Array<Record<string, unknown>>;
  readonly requestId: string | null;
  readonly status: number;

  constructor({
    code,
    details = [],
    message,
    requestId = null,
    status,
  }: {
    code: string;
    details?: Array<Record<string, unknown>>;
    message: string;
    requestId?: string | null;
    status: number;
  }) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.details = details;
    this.requestId = requestId;
    this.status = status;
  }
}

type ApiRequestOptions = Omit<RequestInit, "body"> & {
  body?: BodyInit | Record<string, unknown>;
};

function isRecordBody(body: ApiRequestOptions["body"]): body is Record<string, unknown> {
  return (
    body !== undefined &&
    body !== null &&
    typeof body === "object" &&
    !(body instanceof FormData) &&
    !(body instanceof Blob) &&
    !(body instanceof URLSearchParams) &&
    !(body instanceof ArrayBuffer)
  );
}

async function parseErrorResponse(response: Response): Promise<ApiError> {
  let payload: ErrorEnvelope = {};

  try {
    payload = (await response.json()) as ErrorEnvelope;
  } catch {
    // Non-JSON upstream errors still receive a stable client-side shape.
  }

  return new ApiError({
    code: payload.error?.code ?? "request_failed",
    details: payload.error?.details,
    message: payload.error?.message ?? "The request could not be completed.",
    requestId: payload.error?.request_id ?? response.headers.get("X-Request-ID"),
    status: response.status,
  });
}

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");

  let body = options.body;
  if (isRecordBody(body)) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(body);
  }

  const response = await fetch(`${env.apiBaseUrl}${path}`, {
    ...options,
    body,
    credentials: "include",
    headers,
  });

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

