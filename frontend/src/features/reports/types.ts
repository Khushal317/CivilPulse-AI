import type { IssueCategory, IssueSeverity, IssueStatus } from "../../types/domain";

export type UrgencyLevel = "routine" | "soon" | "urgent" | "immediate";

export interface ReportDraft {
  id: string;
  title: string;
  original_description: string;
  ai_summary: string;
  category: IssueCategory;
  severity: IssueSeverity;
  urgency_level: UrgencyLevel;
  urgency_reason: string;
  suggested_department: string;
  safety_risk: string;
  citizen_explanation: string;
  suggested_next_action: string;
  location: string;
  landmark: string | null;
  urgency_note: string | null;
  image_url: string;
  expires_at: string;
  created_at: string;
}

export interface ReportDraftUpdate {
  title?: string;
  original_description?: string;
  ai_summary?: string;
  category?: IssueCategory;
  severity?: IssueSeverity;
  urgency_level?: UrgencyLevel;
  urgency_reason?: string;
  suggested_department?: string;
  safety_risk?: string;
  citizen_explanation?: string;
  suggested_next_action?: string;
  location?: string;
  landmark?: string | null;
}

export interface PublishedReport {
  issue_id: string;
  public_reference: string;
  status: IssueStatus;
  published_at: string;
}

export interface ReportFormValues {
  image: FileList;
  originalDescription: string;
  location: string;
  landmark: string;
  preferredCategory: IssueCategory | "";
  urgencyNote: string;
  citizenName: string;
  citizenContact: string;
}

