import type { ButtonHTMLAttributes } from "react";

interface SubmitButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  isSubmitting?: boolean;
  loadingLabel?: string;
}

export function SubmitButton({
  children,
  isSubmitting = false,
  loadingLabel,
  disabled,
  ...rest
}: SubmitButtonProps) {
  return (
    <button
      type="submit"
      disabled={disabled || isSubmitting}
      className="w-full rounded-md bg-primary px-4 py-2 font-medium text-text-on-primary transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
      {...rest}
    >
      {isSubmitting ? (loadingLabel ?? "Please wait…") : children}
    </button>
  );
}
