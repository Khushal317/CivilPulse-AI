import { env } from "../config/env";

export interface HealthResponse {
  status: "alive" | "ready";
  service: string;
  version: string;
}

export async function getApiReadiness(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(`${env.apiBaseUrl}/health/ready`, {
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    throw new Error(`API readiness check failed with status ${response.status}`);
  }

  return (await response.json()) as HealthResponse;
}

