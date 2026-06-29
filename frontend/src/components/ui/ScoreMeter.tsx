import type { HTMLAttributes, ReactNode } from "react";

import { classNames } from "../../utils/classNames";

type ScoreTone =
  | "civic-health"
  | "cleanliness"
  | "community-power"
  | "environment"
  | "infrastructure"
  | "responsiveness"
  | "safety";

interface ScoreMeterProps extends HTMLAttributes<HTMLDivElement> {
  helper?: ReactNode;
  label: ReactNode;
  max?: number;
  tone?: ScoreTone;
  value: number;
}

const clampScore = (value: number, max: number) => Math.min(Math.max(value, 0), max);

export function ScoreMeter({
  className,
  helper,
  label,
  max = 100,
  tone = "civic-health",
  value,
  ...props
}: ScoreMeterProps) {
  const safeMax = max > 0 ? max : 100;
  const safeValue = clampScore(value, safeMax);
  const percent = Math.round((safeValue / safeMax) * 100);

  return (
    <div className={classNames("score-meter", `score-meter-${tone}`, className)} {...props}>
      <div className="score-meter-heading">
        <span>{label}</span>
        <strong>
          {Math.round(safeValue)}
          <span>/{safeMax}</span>
        </strong>
      </div>
      <div
        aria-label={typeof label === "string" ? label : undefined}
        aria-valuemax={safeMax}
        aria-valuemin={0}
        aria-valuenow={Math.round(safeValue)}
        className="score-meter-track"
        role="progressbar"
      >
        <span style={{ inlineSize: `${percent}%` }} />
      </div>
      {helper && <p>{helper}</p>}
    </div>
  );
}
