interface SkeletonProps {
  className?: string;
  "aria-label"?: string;
}

/** A shimmering placeholder box shown while real content is loading. Never
 * used to fake real content — see docs/design-system.md. */
export function Skeleton({ className = "", ...rest }: SkeletonProps) {
  return (
    <div
      role="status"
      aria-label={rest["aria-label"] ?? "Loading"}
      className={`animate-pulse rounded-md bg-surface-variant ${className}`}
    />
  );
}
