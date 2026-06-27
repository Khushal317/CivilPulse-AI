import { apiRequest } from "../../api/client";
import type { MissionDetail, MissionListResponse } from "./types";

export function getMissions(signal?: AbortSignal): Promise<MissionListResponse> {
  return apiRequest<MissionListResponse>("/api/v1/missions", { signal });
}

export function getMission(
  missionId: string,
  signal?: AbortSignal,
): Promise<MissionDetail> {
  return apiRequest<MissionDetail>(`/api/v1/missions/${missionId}`, { signal });
}
