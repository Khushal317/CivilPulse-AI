import { useEffect, useId, useRef, type ReactNode } from "react";

import { Button } from "./Button";

interface DialogProps {
  cancelLabel?: string;
  children: ReactNode;
  confirmLabel?: string;
  isOpen: boolean;
  onClose: () => void;
  onConfirm?: () => void;
  title: string;
  variant?: "default" | "danger";
}

export function Dialog({
  cancelLabel = "Cancel",
  children,
  confirmLabel = "Confirm",
  isOpen,
  onClose,
  onConfirm,
  title,
  variant = "default",
}: DialogProps) {
  const titleId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    previousFocusRef.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    panelRef.current?.querySelector<HTMLButtonElement>("button")?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key !== "Tab" || panelRef.current === null) return;

      const focusable = Array.from(
        panelRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      );
      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previousFocusRef.current?.focus();
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="dialog-backdrop" onMouseDown={onClose}>
      <div
        aria-labelledby={titleId}
        aria-modal="true"
        className="dialog-panel"
        onMouseDown={(event) => event.stopPropagation()}
        ref={panelRef}
        role="dialog"
      >
        <div>
          <p className="eyebrow">Please confirm</p>
          <h2 id={titleId}>{title}</h2>
        </div>
        <div className="dialog-content">{children}</div>
        <div className="dialog-actions">
          <Button onClick={onClose} variant="secondary">
            {cancelLabel}
          </Button>
          {onConfirm && (
            <Button onClick={onConfirm} variant={variant === "danger" ? "danger" : "primary"}>
              {confirmLabel}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
