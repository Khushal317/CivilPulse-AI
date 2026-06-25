import type { IssueCategory, IssueSeverity } from "../../types/domain";
import type { UrgencyLevel } from "./types";

export const categoryOptions: Array<{ label: string; value: IssueCategory }> = [
  { label: "Road damage", value: "road_damage" },
  { label: "Garbage / Waste", value: "garbage_waste" },
  { label: "Streetlight", value: "streetlight" },
  { label: "Water leakage", value: "water_leakage" },
  { label: "Drainage / Sewage", value: "drainage_sewage" },
  { label: "Public safety", value: "public_safety" },
  { label: "Other", value: "other" },
];

export const severityOptions: Array<{ label: string; value: IssueSeverity }> = [
  { label: "Low", value: "low" },
  { label: "Medium", value: "medium" },
  { label: "High", value: "high" },
  { label: "Critical", value: "critical" },
];

export const urgencyOptions: Array<{ label: string; value: UrgencyLevel }> = [
  { label: "Routine", value: "routine" },
  { label: "Soon", value: "soon" },
  { label: "Urgent", value: "urgent" },
  { label: "Immediate", value: "immediate" },
];

