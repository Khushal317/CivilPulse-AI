import { classNames } from "../../utils/classNames";
import type { ButtonSize, ButtonVariant } from "./Button";

export function buttonClassName(
  variant: ButtonVariant = "primary",
  size: ButtonSize = "medium",
): string {
  return classNames("button", `button-${variant}`, `button-${size}`);
}

