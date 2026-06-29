import type { ReactNode } from "react";

import { Card } from "../ui/Card";

interface EmptyStateProps {
  action?: ReactNode;
  description: string;
  icon?: ReactNode;
  title: string;
}

export function EmptyState({ action, description, icon = "○", title }: EmptyStateProps) {
  return (
    <Card className="state-card" padding="large">
      <span className="state-icon" aria-hidden="true">
        {icon}
      </span>
      <div className="state-copy">
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      {action && <div className="state-action">{action}</div>}
    </Card>
  );
}
