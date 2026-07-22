import type { ReactNode } from "react";

import { EmptyState } from "@/components/feedback/empty-state";
import { Skeleton } from "@/components/feedback/skeleton";

export type SortDirection = "asc" | "desc";

export interface DataTableColumn<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  /** When set, the header becomes a clickable sort control — see
   * docs/admin-dashboard.md#pagination-and-sorting. The value sent to
   * `onSortChange` (and compared against `sortBy`) is this key, which the
   * caller maps to whatever `sort_by` value the backend expects. */
  sortKey?: string;
}

interface DataTableProps<T> {
  columns: readonly DataTableColumn<T>[];
  rows: readonly T[];
  getRowKey: (row: T) => string;
  isLoading?: boolean;
  emptyTitle?: string;
  emptyMessage?: string;
  skeletonRowCount?: number;
  sortBy?: string;
  sortDir?: SortDirection;
  onSortChange?: (sortKey: string) => void;
}

/** Generic, reusable table foundation — every admin list (users, reports,
 * verification queue, ...) renders through this rather than a bespoke
 * `<table>` per page. Accepts real rows via props; never seeded with fake
 * data itself (see docs/design-system.md). */
export function DataTable<T>({
  columns,
  rows,
  getRowKey,
  isLoading = false,
  emptyTitle = "No records yet",
  emptyMessage,
  skeletonRowCount = 5,
  sortBy,
  sortDir = "asc",
  onSortChange,
}: DataTableProps<T>) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-surface">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-border bg-surface-variant">
          <tr>
            {columns.map((column) => {
              if (!column.sortKey || !onSortChange) {
                return (
                  <th
                    key={column.key}
                    scope="col"
                    className="px-4 py-3 font-medium text-text-primary"
                  >
                    {column.header}
                  </th>
                );
              }
              const isActive = sortBy === column.sortKey;
              const ariaSort = isActive ? (sortDir === "asc" ? "ascending" : "descending") : "none";
              return (
                <th
                  key={column.key}
                  scope="col"
                  aria-sort={ariaSort}
                  className="px-4 py-3 font-medium text-text-primary"
                >
                  <button
                    type="button"
                    onClick={() => onSortChange(column.sortKey!)}
                    className="flex items-center gap-1 hover:underline"
                  >
                    {column.header}
                    {isActive ? (
                      <span aria-hidden="true">{sortDir === "asc" ? "▲" : "▼"}</span>
                    ) : null}
                  </button>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {isLoading
            ? Array.from({ length: skeletonRowCount }).map((_, rowIndex) => (
                <tr key={rowIndex} className="border-b border-border last:border-0">
                  {columns.map((column) => (
                    <td key={column.key} className="px-4 py-3">
                      <Skeleton className="h-4 w-full" aria-label="Loading row" />
                    </td>
                  ))}
                </tr>
              ))
            : rows.map((row) => (
                <tr key={getRowKey(row)} className="border-b border-border last:border-0">
                  {columns.map((column) => (
                    <td key={column.key} className="px-4 py-3 text-text-primary">
                      {column.render(row)}
                    </td>
                  ))}
                </tr>
              ))}
        </tbody>
      </table>
      {!isLoading && rows.length === 0 ? (
        <EmptyState title={emptyTitle} message={emptyMessage} />
      ) : null}
    </div>
  );
}
