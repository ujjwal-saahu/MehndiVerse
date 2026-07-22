import type { InputHTMLAttributes } from "react";

interface FormFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

/** Standard labeled text input with inline validation error — used by every
 * auth form so label/error styling never drifts between pages. */
export function FormField({ label, error, id, ...inputProps }: FormFieldProps) {
  const fieldId = id ?? inputProps.name;
  const errorId = error ? `${fieldId}-error` : undefined;

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={fieldId} className="text-sm font-medium text-text-primary">
        {label}
      </label>
      <input
        id={fieldId}
        aria-invalid={Boolean(error)}
        aria-describedby={errorId}
        className="rounded-md border border-border bg-background px-3 py-2 text-text-primary focus:border-focus-ring focus:outline-none focus:ring-2 focus:ring-focus-ring"
        {...inputProps}
      />
      {error ? (
        <p id={errorId} className="text-sm text-danger" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
