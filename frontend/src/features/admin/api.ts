import { apiRequest } from "../../api/client";
import type {
  AdminDashboard,
  AdminIssueDetail,
  AdminIssueFilters,
  AdminIssueListResponse,
  AdminMissionListResponse,
  AdminSession,
  AdminStatusUpdate,
  DuplicateIssueResolutionRequest,
  DuplicateIssueResolutionResponse,
  ManualMissionCreate,
  ManualMissionDraft,
  MissionGenerationResponse,
  OperationsReport,
} from "./types";
import type { MissionDetail } from "../missions/types";

export function loginAdmin(username: string, password: string): Promise<AdminSession> {
  return apiRequest<AdminSession>("/api/v1/admin/auth/login", {
    method: "POST",
    body: { username, password },
  });
}

export function getAdminSession(signal?: AbortSignal): Promise<AdminSession> {
  return apiRequest<AdminSession>("/api/v1/admin/auth/session", { signal });
}

export function logoutAdmin(csrfToken: string): Promise<void> {
  return apiRequest<void>("/api/v1/admin/auth/logout", {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
  });
}

export function getAdminDashboard(signal?: AbortSignal): Promise<AdminDashboard> {
  return apiRequest<AdminDashboard>("/api/v1/admin/dashboard", { signal });
}

export function getAdminIssues(
  filters: AdminIssueFilters,
  signal?: AbortSignal,
): Promise<AdminIssueListResponse> {
  const params = new URLSearchParams({
    page: String(filters.page),
    page_size: "20",
  });
  if (filters.search) params.set("search", filters.search);
  if (filters.category) params.set("category", filters.category);
  if (filters.severity) params.set("severity", filters.severity);
  if (filters.status) params.set("status", filters.status);
  return apiRequest<AdminIssueListResponse>(`/api/v1/admin/issues?${params}`, { signal });
}

export function getAdminIssue(
  issueId: string,
  signal?: AbortSignal,
): Promise<AdminIssueDetail> {
  return apiRequest<AdminIssueDetail>(`/api/v1/admin/issues/${issueId}`, { signal });
}

export function updateAdminIssueStatus(
  issueId: string,
  update: AdminStatusUpdate,
  csrfToken: string,
): Promise<AdminIssueDetail> {
  return apiRequest<AdminIssueDetail>(`/api/v1/admin/issues/${issueId}/status`, {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
    body: { ...update },
  });
}

export function resolveDuplicateIssues(
  request: DuplicateIssueResolutionRequest,
  csrfToken: string,
): Promise<DuplicateIssueResolutionResponse> {
  return apiRequest<DuplicateIssueResolutionResponse>("/api/v1/admin/issues/duplicates", {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
    body: { ...request },
  });
}

export function getLatestOperationsReport(
  signal?: AbortSignal,
): Promise<OperationsReport | null> {
  return apiRequest<OperationsReport | null>("/api/v1/admin/operations/latest", {
    signal,
  });
}

export function analyzeOperationsReport(csrfToken: string): Promise<OperationsReport> {
  return apiRequest<OperationsReport>("/api/v1/admin/operations/analyze", {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
  });
}

export function generateMissionDrafts(
  csrfToken: string,
): Promise<MissionGenerationResponse> {
  return apiRequest<MissionGenerationResponse>("/api/v1/admin/missions/generate", {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
  });
}

export function getAdminMissions(signal?: AbortSignal): Promise<AdminMissionListResponse> {
  return apiRequest<AdminMissionListResponse>("/api/v1/admin/missions", { signal });
}

export function publishMission(missionId: string, csrfToken: string): Promise<MissionDetail> {
  return apiRequest<MissionDetail>(`/api/v1/admin/missions/${missionId}/publish`, {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
  });
}

export function deleteMission(missionId: string, csrfToken: string): Promise<void> {
  return apiRequest<void>(`/api/v1/admin/missions/${missionId}`, {
    method: "DELETE",
    headers: { "X-CSRF-Token": csrfToken },
  });
}

export function refineManualMission(
  draft: ManualMissionDraft,
  csrfToken: string,
): Promise<ManualMissionDraft> {
  return apiRequest<ManualMissionDraft>("/api/v1/admin/missions/manual/refine", {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
    body: { ...draft },
  });
}

export function createManualMission(
  mission: ManualMissionCreate,
  csrfToken: string,
): Promise<MissionDetail> {
  return apiRequest<MissionDetail>("/api/v1/admin/missions/manual", {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
    body: { ...mission },
  });
}

export function expireMission(missionId: string, csrfToken: string): Promise<MissionDetail> {
  return apiRequest<MissionDetail>(`/api/v1/admin/missions/${missionId}/expire`, {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
  });
}

export function completeMission(missionId: string, csrfToken: string): Promise<MissionDetail> {
  return apiRequest<MissionDetail>(`/api/v1/admin/missions/${missionId}/complete`, {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
  });
}
