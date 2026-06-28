import type {
  CommunityActionType,
  IssueCategory,
  IssueSeverity,
  IssueSort,
  IssueStatus,
} from "../../types/domain";

export type UrgencyLevel = "routine" | "soon" | "urgent" | "immediate";

export interface CommunityCounts {
  saw_this_too: number;
  still_unresolved: number;
  fixed: number;
  incorrect: number;
}

export interface PublicIssueUpdate {
  id: string;
  from_status: IssueStatus | null;
  to_status: IssueStatus;
  note: string | null;
  actor_type: "system" | "admin";
  created_at: string;
}

export interface PublicIssueListItem {
  id: string;
  public_reference: string;
  title: string;
  category: IssueCategory;
  severity: IssueSeverity;
  location: string;
  landmark: string | null;
  image_url: string;
  status: IssueStatus;
  created_at: string;
  updated_at: string;
  verification_count: number;
}

export interface PublicIssueListResponse {
  items: PublicIssueListItem[];
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

export interface PublicIssueDuplicateReference {
  id: string;
  public_reference: string;
  title: string;
  status: IssueStatus;
}

export interface IssueTrackerFilters {
  page: number;
  pageSize: number;
  category?: IssueCategory;
  severity?: IssueSeverity;
  status?: IssueStatus;
  location?: string;
  sort: IssueSort;
}

export interface PublicIssueDetail extends PublicIssueListItem {
  original_description: string;
  ai_summary: string;
  urgency_level: UrgencyLevel;
  urgency_reason: string;
  suggested_department: string;
  safety_risk: string;
  citizen_explanation: string;
  suggested_next_action: string;
  community_counts: CommunityCounts;
  updates: PublicIssueUpdate[];
  viewer_actions: CommunityActionType[];
  duplicate_of?: PublicIssueDuplicateReference | null;
  duplicate_marked_at?: string | null;
}

export interface CommunityActionResponse {
  action_type: CommunityActionType;
  accepted: boolean;
  issue_status: IssueStatus;
  community_counts: CommunityCounts;
  viewer_actions: CommunityActionType[];
}
