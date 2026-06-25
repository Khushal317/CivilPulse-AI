import type { ButtonHTMLAttributes, ReactNode } from "react";

import { classNames } from "../../utils/classNames";
import { buttonClassName } from "./buttonStyles";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "small" | "medium";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
}

export function Button({
  children,
  className,
  disabled,
  isLoading = false,
  size = "medium",
  type = "button",
  variant = "primary",
  ...props
}: ButtonProps) {
  return (
    <button
      className={classNames(buttonClassName(variant, size), className)}
      disabled={disabled || isLoading}
      type={type}
      {...props}
    >
      {isLoading ? (
        <>
          <span className="spinner spinner-small" aria-hidden="true" />
          <span>Working…</span>
        </>
      ) : (
        children
      )}
    </button>
  );
}
