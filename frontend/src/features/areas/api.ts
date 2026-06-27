import { apiRequest } from "../../api/client";
import type { AreaDetail, AreaListResponse } from "./types";

export function getAreas(signal?: AbortSignal): Promise<AreaListResponse> {
  return apiRequest<AreaListResponse>("/api/v1/areas", { signal });
}

export function getArea(slug: string, signal?: AbortSignal): Promise<AreaDetail> {
  return apiRequest<AreaDetail>(`/api/v1/areas/${slug}`, { signal });
}
