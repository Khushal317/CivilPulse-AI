import { useEffect, useId, useState, type ChangeEvent } from "react";
import type { UseFormRegisterReturn } from "react-hook-form";

import { classNames } from "../../utils/classNames";

interface ImageUploadFieldProps {
  error?: string;
  registration: UseFormRegisterReturn;
}

export function ImageUploadField({ error, registration }: ImageUploadFieldProps) {
  const id = useId();
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  useEffect(
    () => () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    },
    [previewUrl],
  );

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    const file = event.target.files?.item(0);
    setPreviewUrl(file ? URL.createObjectURL(file) : null);
    setFileName(file?.name ?? null);
    void registration.onChange(event);
  };

  return (
    <div className={classNames("field", error && "field-invalid")}>
      <div className="field-label-row">
        <label htmlFor={id}>Issue photo</label>
        <span>Required</span>
      </div>
      <label className="image-upload" htmlFor={id}>
        {previewUrl ? (
          <img alt="Selected issue preview" src={previewUrl} />
        ) : (
          <span className="image-upload-placeholder" aria-hidden="true">
            +
          </span>
        )}
        <span>
          <strong>{fileName ?? "Choose an issue photo"}</strong>
          <small>JPEG, PNG, or WebP · maximum 10 MB</small>
        </span>
      </label>
      <input
        {...registration}
        accept="image/jpeg,image/png,image/webp"
        aria-describedby={error ? `${id}-error` : undefined}
        aria-invalid={Boolean(error)}
        className="visually-hidden"
        id={id}
        onChange={handleChange}
        type="file"
      />
      {error && (
        <p className="field-message field-error" id={`${id}-error`}>
          {error}
        </p>
      )}
    </div>
  );
}

