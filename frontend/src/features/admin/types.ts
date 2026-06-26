import type {
  IssueCategory,
  IssueSeverity,
  IssueStatus,
} from "../../types/domain";
import type {
  CommunityCounts,
  PublicIssueUpdate,
  UrgencyLevel,
} from "../issues/types";

export interface AdminSession {
  username: string;
  expires_at: string;
  csrf_token: string;
}

export interface AdminIssueSummary {
  id: string;
  public_reference: string;
  title: string;
  category: IssueCategory;
  severity: IssueSeverity;
  status: IssueStatus;
  location: string;
  landmark: string | null;
  created_at: string;
  updated_at: string;
  verification_count: number;
}

export interface AdminDashboard {
  metrics: {
    total_reports: number;
    high_severity: number;
    verified: number;
    pending: number;
    resolved: number;
  };
  category_breakdown: Array<{ category: IssueCategory; count: number }>;
  latest_reports: AdminIssueSummary[];
  priority_issues: AdminIssueSummary[];
}

export interface AdminIssueListResponse {
  items: AdminIssueSummary[];
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

export interface AdminIssueDetail extends AdminIssueSummary {
  original_description: string;
  ai_summary: string;
  urgency_level: UrgencyLevel;
  urgency_reason: string;
  suggested_department: string;
  safety_risk: string;
  citizen_explanation: string;
  suggested_next_action: string;
  image_url: string;
  image_mime: string;
  citizen_name: string | null;
  citizen_contact: string | null;
  ai_model: string;
  prompt_version: string;
  community_counts: CommunityCounts;
  updates: PublicIssueUpdate[];
}

export interface AdminIssueFilters {
  page: number;
  search?: string;
  category?: IssueCategory;
  severity?: IssueSeverity;
  status?: IssueStatus;
}

export interface AdminStatusUpdate {
  to_status: IssueStatus;
  note?: string;
  rejection_reason?: string;
}
