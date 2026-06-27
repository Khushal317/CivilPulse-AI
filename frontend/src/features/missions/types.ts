export type MissionStatus = "draft" | "active" | "completed" | "expired";

export type MissionType =
  | "verification"
  | "fix_confirmation"
  | "hotspot"
  | "category"
  | "volunteer";

export type MissionActionType =
  | "joined"
  | "verified_issue"
  | "confirmed_unresolved"
  | "confirmed_fixed"
  | "volunteered";

export interface MissionAreaSummary {
  id: string;
  name: string;
  slug: string;
  city: string;
}

export interface MissionSummary {
  id: string;
  title: string;
  mission_type: MissionType;
  status: MissionStatus;
  area: MissionAreaSummary;
  goal_description: string;
  target_count: number;
  progress_count: number;
  category: string | null;
  reward: Record<string, unknown>;
  ai_reason: string;
  joined_count: number;
  expires_at: string | null;
  published_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface MissionDetail extends MissionSummary {
  linked_issue_ids: string[];
  viewer_actions: MissionActionType[];
}

export interface MissionListResponse {
  items: MissionSummary[];
}

export interface MissionActionResponse {
  action_type: MissionActionType;
  accepted: boolean;
  mission_status: MissionStatus;
  progress_count: number;
  target_count: number;
  joined_count: number;
  viewer_actions: MissionActionType[];
}
