export interface AreaScoreBreakdown {
  overall: number;
  infrastructure: number;
  cleanliness: number;
  safety: number;
  participation: number;
  responsiveness: number;
  environment: number;
}

export interface AreaSummary {
  id: string;
  name: string;
  slug: string;
  city: string;
  rank: number | null;
  status_label: string;
  scores: AreaScoreBreakdown;
  open_issues: number;
  resolved_this_week: number;
  active_missions: number;
  created_at: string;
  updated_at: string;
}

export interface AreaListResponse {
  items: AreaSummary[];
}

export interface AreaScoreEvent {
  id: string;
  event_type: string;
  related_issue_id: string | null;
  related_mission_id: string | null;
  score_key: keyof AreaScoreBreakdown;
  score_change: number;
  previous_score: number;
  new_score: number;
  reason: string;
  created_at: string;
}

export interface AreaDetail extends AreaSummary {
  total_issues: number;
  recent_score_events: AreaScoreEvent[];
}
