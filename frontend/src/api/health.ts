import { apiRequest } from "./client";

export interface HealthResponse {
  status: "alive" | "ready";
  service: string;
  version: string;
}

export async function getApiHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return apiRequest<HealthResponse>("/health/live", {
    signal,
  });
}
