import type { HTMLAttributes, ReactNode } from "react";

import { classNames } from "../../utils/classNames";

export type TrendDirection = "down" | "flat" | "up";

interface TrendPillProps extends HTMLAttributes<HTMLSpanElement> {
  children: ReactNode;
  direction?: TrendDirection;
}

const trendIcons: Record<TrendDirection, string> = {
  down: "↓",
  flat: "→",
  up: "↑",
};

export function TrendPill({
  children,
  className,
  direction = "flat",
  ...props
}: TrendPillProps) {
  return (
    <span
      className={classNames("trend-pill", `trend-pill-${direction}`, className)}
      {...props}
    >
      <span aria-hidden="true">{trendIcons[direction]}</span>
      {children}
    </span>
  );
}
