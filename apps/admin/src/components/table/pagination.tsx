interface PaginationProps {
  page: number;
  totalPages: number;
  total: number;
  onPageChange: (page: number) => void;
  isLoading?: boolean;
}

/** Page-number pagination for admin data tables — see
 * docs/admin-dashboard.md#pagination-and-sorting. Deliberately page-number
 * based (not "load more"/infinite scroll) since admin lists are bounded
 * and jumping to a specific page is a real workflow (e.g. "page 3 of the
 * refund queue"). */
export function Pagination({
  page,
  totalPages,
  total,
  onPageChange,
  isLoading = false,
}: PaginationProps) {
  if (totalPages <= 1) return null;

  return (
    <nav
      aria-label="Pagination"
      className="mt-4 flex items-center justify-between text-sm text-text-secondary"
    >
      <p>
        Page {page} of {totalPages} · {total} total
      </p>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => onPageChange(page - 1)}
          disabled={isLoading || page <= 1}
          className="rounded-md border border-border px-3 py-1.5 font-medium text-text-primary hover:bg-surface-variant disabled:cursor-not-allowed disabled:opacity-50"
        >
          Previous
        </button>
        <button
          type="button"
          onClick={() => onPageChange(page + 1)}
          disabled={isLoading || page >= totalPages}
          className="rounded-md border border-border px-3 py-1.5 font-medium text-text-primary hover:bg-surface-variant disabled:cursor-not-allowed disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </nav>
  );
}
