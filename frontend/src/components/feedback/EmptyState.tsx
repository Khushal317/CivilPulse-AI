import type { ReactNode } from "react";

import { Card } from "../ui/Card";

interface EmptyStateProps {
  action?: ReactNode;
  description: string;
  title: string;
}

export function EmptyState({ action, description, title }: EmptyStateProps) {
  return (
    <Card className="state-card" padding="large">
      <span className="state-icon" aria-hidden="true">
        ○
      </span>
      <h2>{title}</h2>
      <p>{description}</p>
      {action && <div className="state-action">{action}</div>}
    </Card>
  );
}

