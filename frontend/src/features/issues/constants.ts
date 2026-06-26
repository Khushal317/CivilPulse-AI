import type {
  IssueCategory,
  IssueSeverity,
  IssueSort,
  IssueStatus,
} from "../../types/domain";

export const categoryFilterOptions: Array<{ label: string; value: IssueCategory }> = [
  { label: "Road damage", value: "road_damage" },
  { label: "Garbage / Waste", value: "garbage_waste" },
  { label: "Streetlight", value: "streetlight" },
  { label: "Water leakage", value: "water_leakage" },
  { label: "Drainage / Sewage", value: "drainage_sewage" },
  { label: "Public safety", value: "public_safety" },
  { label: "Other", value: "other" },
];

export const severityFilterOptions: Array<{ label: string; value: IssueSeverity }> = [
  { label: "Low", value: "low" },
  { label: "Medium", value: "medium" },
  { label: "High", value: "high" },
  { label: "Critical", value: "critical" },
];

export const statusFilterOptions: Array<{ label: string; value: IssueStatus }> = [
  { label: "Reported", value: "reported" },
  { label: "Community verified", value: "community_verified" },
  { label: "Escalated", value: "escalated" },
  { label: "In progress", value: "in_progress" },
  { label: "Resolved", value: "resolved" },
  { label: "Rejected", value: "rejected" },
];

export const sortOptions: Array<{ label: string; value: IssueSort }> = [
  { label: "Newest first", value: "newest" },
  { label: "Oldest first", value: "oldest" },
  { label: "Most verified", value: "most_verified" },
  { label: "Highest severity", value: "severity" },
];
