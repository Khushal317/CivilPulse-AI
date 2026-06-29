import type { CSSProperties } from "react";

interface AreaScoreBadgeProps {
  score: number;
}

export function AreaScoreBadge({ score }: AreaScoreBadgeProps) {
  const safeScore = Math.min(Math.max(Math.round(score), 0), 100);
  return (
    <div
      aria-label={`Civic Health ${safeScore} out of 100`}
      className="area-score-ring"
      style={{ "--area-score": `${safeScore}%` } as CSSProperties}
    >
      <strong>{safeScore}</strong>
      <span>/100</span>
    </div>
  );
}
