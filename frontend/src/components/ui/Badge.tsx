import type { ReactNode } from "react";

import type { IssueCategory, IssueSeverity, IssueStatus } from "../../types/domain";
import { classNames } from "../../utils/classNames";

const categoryLabels: Record<IssueCategory, string> = {
  road_damage: "Road damage",
  garbage_waste: "Garbage / Waste",
  streetlight: "Streetlight",
  water_leakage: "Water leakage",
  drainage_sewage: "Drainage / Sewage",
  public_safety: "Public safety",
  other: "Other",
};

const statusLabels: Record<IssueStatus, string> = {
  reported: "Reported",
  community_verified: "Community verified",
  escalated: "Escalated",
  in_progress: "In progress",
  resolved: "Resolved",
  rejected: "Rejected",
  duplicate: "Duplicate",
};

interface BadgeProps {
  children: ReactNode;
  tone?: "neutral" | "info" | "success" | "warning" | "danger";
}

export function Badge({ children, tone = "neutral" }: BadgeProps) {
  return <span className={classNames("badge", `badge-${tone}`)}>{children}</span>;
}

export function CategoryBadge({ category }: { category: IssueCategory }) {
  return <Badge tone="info">{categoryLabels[category]}</Badge>;
}

export function SeverityBadge({ severity }: { severity: IssueSeverity }) {
  const tone = {
    low: "neutral",
    medium: "warning",
    high: "danger",
    critical: "danger",
  } as const;

  return <Badge tone={tone[severity]}>{severity[0].toUpperCase() + severity.slice(1)}</Badge>;
}

export function StatusBadge({ status }: { status: IssueStatus }) {
  const tone = {
    reported: "neutral",
    community_verified: "info",
    escalated: "warning",
    in_progress: "warning",
    resolved: "success",
    rejected: "danger",
    duplicate: "warning",
  } as const;

  return <Badge tone={tone[status]}>{statusLabels[status]}</Badge>;
}
