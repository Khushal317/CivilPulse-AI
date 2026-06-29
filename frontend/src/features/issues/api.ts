import { apiRequest } from "../../api/client";
import { env } from "../../config/env";
import type { CommunityActionType } from "../../types/domain";
import type {
  CommunityActionResponse,
  IssueTrackerFilters,
  PublicIssueMapResponse,
  PublicIssueDetail,
  PublicIssueListResponse,
} from "./types";

export function getPublicIssues(
  filters: IssueTrackerFilters,
  signal?: AbortSignal,
): Promise<PublicIssueListResponse> {
  const params = new URLSearchParams({
    page: String(filters.page),
    page_size: String(filters.pageSize),
    sort: filters.sort,
  });
  if (filters.category) params.set("category", filters.category);
  if (filters.severity) params.set("severity", filters.severity);
  if (filters.status) params.set("status", filters.status);
  if (filters.location) params.set("location", filters.location);

  return apiRequest<PublicIssueListResponse>(`/api/v1/issues?${params}`, { signal });
}

export function getPublicIssueMap(
  filters: IssueTrackerFilters,
  signal?: AbortSignal,
): Promise<PublicIssueMapResponse> {
  const params = new URLSearchParams();
  if (filters.category) params.set("category", filters.category);
  if (filters.severity) params.set("severity", filters.severity);
  if (filters.status) params.set("status", filters.status);
  if (filters.location) params.set("location", filters.location);

  const suffix = params.size > 0 ? `?${params}` : "";
  return apiRequest<PublicIssueMapResponse>(`/api/v1/issues/map${suffix}`, { signal });
}

export function publicIssueImageUrl(path: string): string {
  return path.startsWith("http") ? path : `${env.apiBaseUrl}${path}`;
}

export function getPublicIssue(
  issueId: string,
  signal?: AbortSignal,
): Promise<PublicIssueDetail> {
  return apiRequest<PublicIssueDetail>(`/api/v1/issues/${issueId}`, { signal });
}

export function submitCommunityAction(
  issueId: string,
  actionType: CommunityActionType,
): Promise<CommunityActionResponse> {
  return apiRequest<CommunityActionResponse>(
    `/api/v1/issues/${issueId}/community-actions`,
    {
      method: "POST",
      body: { action_type: actionType },
    },
  );
}
