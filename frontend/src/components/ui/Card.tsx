import type { HTMLAttributes, ReactNode } from "react";

import { classNames } from "../../utils/classNames";

interface CardProps extends HTMLAttributes<HTMLElement> {
  children: ReactNode;
  as?: "article" | "aside" | "section" | "div";
  padding?: "none" | "small" | "medium" | "large";
}

export function Card({
  as: Element = "div",
  children,
  className,
  padding = "medium",
  ...props
}: CardProps) {
  return (
    <Element className={classNames("card", `card-padding-${padding}`, className)} {...props}>
      {children}
    </Element>
  );
}
