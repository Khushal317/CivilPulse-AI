import { apiRequest } from "../../api/client";
import type {
  MissionActionResponse,
  MissionActionType,
  MissionDetail,
  MissionListResponse,
} from "./types";

export function getMissions(signal?: AbortSignal): Promise<MissionListResponse> {
  return apiRequest<MissionListResponse>("/api/v1/missions", { signal });
}

export function getMission(
  missionId: string,
  signal?: AbortSignal,
): Promise<MissionDetail> {
  return apiRequest<MissionDetail>(`/api/v1/missions/${missionId}`, { signal });
}

export function submitMissionAction(
  missionId: string,
  actionType: MissionActionType,
  issueId?: string,
): Promise<MissionActionResponse> {
  return apiRequest<MissionActionResponse>(`/api/v1/missions/${missionId}/actions`, {
    method: "POST",
    body: {
      action_type: actionType,
      issue_id: issueId ?? null,
    },
  });
}
