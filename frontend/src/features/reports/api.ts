import { apiRequest } from "../../api/client";
import { env } from "../../config/env";
import type {
  PublishedReport,
  ReportDraft,
  ReportDraftUpdate,
  ReportFormValues,
} from "./types";

export function reportImageUrl(path: string): string {
  return path.startsWith("http") ? path : `${env.apiBaseUrl}${path}`;
}

export function analyzeReport(values: ReportFormValues): Promise<ReportDraft> {
  const image = values.image.item(0);
  if (!image) {
    return Promise.reject(new Error("An issue image is required."));
  }

  const form = new FormData();
  form.append("image", image);
  form.append("original_description", values.originalDescription);
  form.append("location", values.location);
  if (typeof values.latitude === "number" && typeof values.longitude === "number") {
    form.append("latitude", String(values.latitude));
    form.append("longitude", String(values.longitude));
  }

  const optionalValues = {
    landmark: values.landmark,
    preferred_category: values.preferredCategory,
    urgency_note: values.urgencyNote,
    citizen_name: values.citizenName,
    citizen_contact: values.citizenContact,
  };
  for (const [key, value] of Object.entries(optionalValues)) {
    if (value) form.append(key, value);
  }

  return apiRequest<ReportDraft>("/api/v1/reports/analyze", {
    body: form,
    method: "POST",
  });
}

export function getReportDraft(draftId: string, signal?: AbortSignal): Promise<ReportDraft> {
  return apiRequest<ReportDraft>(`/api/v1/reports/${draftId}`, { signal });
}

export function updateReportDraft(
  draftId: string,
  changes: ReportDraftUpdate,
): Promise<ReportDraft> {
  return apiRequest<ReportDraft>(`/api/v1/reports/${draftId}`, {
    body: { ...changes },
    method: "PATCH",
  });
}

export function publishReport(draftId: string): Promise<PublishedReport> {
  return apiRequest<PublishedReport>(`/api/v1/reports/${draftId}/publish`, {
    method: "POST",
  });
}

export function cancelReport(draftId: string): Promise<void> {
  return apiRequest<void>(`/api/v1/reports/${draftId}`, {
    method: "DELETE",
  });
}
