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
import type { MissionDetail } from "../missions/types";

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

export interface DuplicateIssueResolutionRequest {
  canonical_issue_id: string;
  duplicate_issue_ids: string[];
  reason: string;
}

export interface DuplicateIssueResolutionResponse {
  canonical_issue: AdminIssueSummary;
  duplicates_marked: AdminIssueSummary[];
}

export type OperationsRiskLevel = "low" | "medium" | "high" | "critical";

export interface OperationsUrgentIssue {
  issue_id: string;
  public_reference: string;
  title: string;
  location: string;
  department: string;
  severity: IssueSeverity;
  priority_reason: string;
  recommended_action: string;
  suggested_time_window: string;
}

export interface OperationsDuplicateIssue {
  issue_id: string;
  public_reference: string;
  title: string;
}

export interface OperationsDuplicateCluster {
  cluster_title: string;
  issues: OperationsDuplicateIssue[];
  reason: string;
  recommended_action: string;
}

export interface OperationsAreaHotspot {
  area: string;
  issue_count: number;
  main_categories: IssueCategory[];
  risk_level: OperationsRiskLevel;
  insight: string;
}

export interface OperationsDepartmentPriority {
  department: string;
  open_issues: number;
  high_priority_count: number;
  recommended_focus: string;
}

export interface OperationsEscalationMessage {
  department: string;
  issue_id: string;
  public_reference: string;
  issue_title: string;
  message: string;
}

export interface OperationsPredictedRisk {
  issue_id: string;
  public_reference: string;
  issue_title: string;
  risk: string;
  risk_level: OperationsRiskLevel;
  preventive_action: string;
}

export interface OperationsReport {
  id: string;
  generated_at: string;
  created_at: string;
  total_issues_analyzed: number;
  model_used: string;
  executive_summary: string;
  urgent_issues: OperationsUrgentIssue[];
  duplicate_clusters: OperationsDuplicateCluster[];
  area_hotspots: OperationsAreaHotspot[];
  department_priorities: OperationsDepartmentPriority[];
  escalation_messages: OperationsEscalationMessage[];
  predicted_risks: OperationsPredictedRisk[];
  raw_response: Record<string, unknown>;
}

export interface MissionGenerationResponse {
  model_used: string;
  created_drafts: MissionDetail[];
}

export interface ManualMissionDraft {
  title: string;
  area_id: string;
  mission_type: MissionDetail["mission_type"];
  goal_description: string;
  target_count: number;
  category: string | null;
  reward_points: number;
  reward_score_key: string;
  ai_reason: string;
  linked_issue_ids: string[];
  expires_in_days: number;
}

export interface ManualMissionCreate extends ManualMissionDraft {
  publish: boolean;
}

export interface AdminMissionListResponse {
  drafts: MissionDetail[];
  active: MissionDetail[];
  completed: MissionDetail[];
  expired: MissionDetail[];
}
