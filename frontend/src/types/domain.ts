export type IssueCategory =
  | "road_damage"
  | "garbage_waste"
  | "streetlight"
  | "water_leakage"
  | "drainage_sewage"
  | "public_safety"
  | "other";

export type IssueSeverity = "low" | "medium" | "high" | "critical";

export type IssueStatus =
  | "reported"
  | "community_verified"
  | "escalated"
  | "in_progress"
  | "resolved"
  | "rejected"
  | "duplicate";

export type IssueSort = "newest" | "oldest" | "most_verified" | "severity";

export type CommunityActionType =
  | "saw_this_too"
  | "still_unresolved"
  | "fixed"
  | "incorrect";
