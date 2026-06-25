import {
  forwardRef,
  useId,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";

import { classNames } from "../../utils/classNames";

interface FieldFrameProps {
  children: ReactNode;
  error?: string;
  hint?: string;
  id: string;
  label: string;
  optional?: boolean;
}

function FieldFrame({
  children,
  error,
  hint,
  id,
  label,
  optional = false,
}: FieldFrameProps) {
  const messageId = `${id}-message`;

  return (
    <div className={classNames("field", error && "field-invalid")}>
      <div className="field-label-row">
        <label htmlFor={id}>{label}</label>
        {optional && <span>Optional</span>}
      </div>
      {children}
      {(error || hint) && (
        <p className={classNames("field-message", error && "field-error")} id={messageId}>
          {error ?? hint}
        </p>
      )}
    </div>
  );
}

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: string;
  hint?: string;
  label: string;
  optional?: boolean;
}

export const TextField = forwardRef<HTMLInputElement, TextFieldProps>(function TextField(
  { className, error, hint, id: providedId, label, optional, ...props },
  ref,
) {
  const generatedId = useId();
  const id = providedId ?? generatedId;
  const messageId = error || hint ? `${id}-message` : undefined;

  return (
    <FieldFrame error={error} hint={hint} id={id} label={label} optional={optional}>
      <input
        aria-describedby={messageId}
        aria-invalid={Boolean(error)}
        className={classNames("field-control", className)}
        id={id}
        ref={ref}
        {...props}
      />
    </FieldFrame>
  );
});

interface TextAreaFieldProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: string;
  hint?: string;
  label: string;
  optional?: boolean;
}

export const TextAreaField = forwardRef<HTMLTextAreaElement, TextAreaFieldProps>(
  function TextAreaField(
    { className, error, hint, id: providedId, label, optional, ...props },
    ref,
  ) {
    const generatedId = useId();
    const id = providedId ?? generatedId;
    const messageId = error || hint ? `${id}-message` : undefined;

    return (
      <FieldFrame error={error} hint={hint} id={id} label={label} optional={optional}>
        <textarea
          aria-describedby={messageId}
          aria-invalid={Boolean(error)}
          className={classNames("field-control field-textarea", className)}
          id={id}
          ref={ref}
          {...props}
        />
      </FieldFrame>
    );
  },
);

interface SelectFieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  error?: string;
  hint?: string;
  label: string;
  optional?: boolean;
}

export const SelectField = forwardRef<HTMLSelectElement, SelectFieldProps>(
  function SelectField(
    { children, className, error, hint, id: providedId, label, optional, ...props },
    ref,
  ) {
    const generatedId = useId();
    const id = providedId ?? generatedId;
    const messageId = error || hint ? `${id}-message` : undefined;

    return (
      <FieldFrame error={error} hint={hint} id={id} label={label} optional={optional}>
        <select
          aria-describedby={messageId}
          aria-invalid={Boolean(error)}
          className={classNames("field-control field-select", className)}
          id={id}
          ref={ref}
          {...props}
        >
          {children}
        </select>
      </FieldFrame>
    );
  },
);

