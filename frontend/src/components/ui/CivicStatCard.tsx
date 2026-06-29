import type { ReactNode } from "react";

import { classNames } from "../../utils/classNames";
import { Card } from "./Card";

type CivicStatTone = "ai" | "brand" | "danger" | "neutral" | "success" | "warning";

interface CivicStatCardProps {
  className?: string;
  description?: ReactNode;
  eyebrow?: ReactNode;
  icon?: ReactNode;
  tone?: CivicStatTone;
  value: ReactNode;
}

export function CivicStatCard({
  className,
  description,
  eyebrow,
  icon,
  tone = "brand",
  value,
}: CivicStatCardProps) {
  return (
    <Card
      as="article"
      className={classNames("civic-stat-card", `civic-stat-card-${tone}`, className)}
      padding="medium"
    >
      <div className="civic-stat-card-heading">
        {eyebrow && <span>{eyebrow}</span>}
        {icon && <i aria-hidden="true">{icon}</i>}
      </div>
      <strong>{value}</strong>
      {description && <p>{description}</p>}
    </Card>
  );
}
