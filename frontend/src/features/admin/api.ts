import { apiRequest } from "../../api/client";
import type {
  AdminDashboard,
  AdminIssueDetail,
  AdminIssueFilters,
  AdminIssueListResponse,
  AdminSession,
  AdminStatusUpdate,
  OperationsReport,
} from "./types";

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
