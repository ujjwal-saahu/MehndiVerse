"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { Skeleton } from "@/components/feedback/skeleton";
import type { DesignListData, DesignSummaryData } from "@/lib/gallery-types";
import { fetchJson, mutateJson } from "@/lib/gallery-client";

type SectionState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: DesignListData };

const STATUS_FILTERS = [
  { label: "All", value: null },
  { label: "Draft", value: "draft" },
  { label: "Published", value: "published" },
  { label: "Archived", value: "archived" },
] as const;

function DesignRow({
  design,
  onArchived,
}: {
  design: DesignSummaryData;
  onArchived: (id: string) => void;
}) {
  const [isArchiving, setIsArchiving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const canArchive = design.status === "draft" || design.status === "published";

  const archive = async () => {
    setIsArchiving(true);
    setError(null);
    try {
      await mutateJson(`/api/designs/${design.id}/archive`, "POST");
      onArchived(design.id);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsArchiving(false);
    }
  };

  return (
    <div className="flex items-center gap-3 rounded-xl border border-border bg-surface p-3">
      <div className="relative h-16 w-16 shrink-0 overflow-hidden rounded-md bg-surface-variant">
        {design.thumbnail_url ? (
          <Image src={design.thumbnail_url} alt="" fill sizes="64px" className="object-cover" />
        ) : null}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium text-text-primary">{design.title}</p>
        <p className="text-xs text-text-secondary">
          {design.status}
          {design.is_premium ? " · premium" : ""}
        </p>
        {error ? <p className="text-xs text-danger">{error}</p> : null}
      </div>
      <Link
        href={`/artist/portfolio/${design.id}/edit`}
        className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-text-primary hover:bg-surface-variant"
      >
        Edit
      </Link>
      {canArchive ? (
        <button
          type="button"
          disabled={isArchiving}
          onClick={() => void archive()}
          className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isArchiving ? "Archiving…" : "Archive"}
        </button>
      ) : null}
    </div>
  );
}

function DesignList({ statusFilter }: { statusFilter: string | null }) {
  const [state, setState] = useState<SectionState>({ status: "loading" });
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  const fetchPage = useCallback(
    (cursor?: string) => {
      const params = new URLSearchParams({ limit: "20" });
      if (statusFilter) params.set("status_filter", statusFilter);
      if (cursor) params.set("cursor", cursor);

      fetchJson<DesignListData>(`/api/designs/mine?${params.toString()}`)
        .then((data) => {
          setState((current) => {
            if (cursor && current.status === "ready") {
              return {
                status: "ready",
                data: { items: [...current.data.items, ...data.items], page_info: data.page_info },
              };
            }
            return { status: "ready", data };
          });
        })
        .catch((error: Error) => setState({ status: "error", message: error.message }))
        .finally(() => setIsLoadingMore(false));
    },
    [statusFilter],
  );

  useEffect(() => {
    fetchPage();
  }, [fetchPage]);

  const removeFromList = (id: string) => {
    setState((current) =>
      current.status === "ready"
        ? {
            status: "ready",
            data: { ...current.data, items: current.data.items.filter((d) => d.id !== id) },
          }
        : current,
    );
  };

  if (state.status === "error") {
    return <ErrorState message={state.message} onRetry={() => fetchPage()} />;
  }
  if (state.status === "loading") {
    return (
      <div role="status" aria-label="Loading your designs" className="flex flex-col gap-3">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-20" aria-label="Loading design" />
        ))}
      </div>
    );
  }
  if (state.data.items.length === 0) {
    return (
      <EmptyState
        title="No designs yet"
        message="Create your first design to start building your portfolio."
      />
    );
  }

  return (
    <>
      <div className="flex flex-col gap-3">
        {state.data.items.map((design) => (
          <DesignRow
            key={design.id}
            design={design}
            onArchived={(id) => {
              if (statusFilter === "published" || statusFilter === "draft") {
                removeFromList(id);
              } else {
                fetchPage();
              }
            }}
          />
        ))}
      </div>
      {state.data.page_info.has_more ? (
        <div className="mt-6 flex justify-center">
          <button
            type="button"
            disabled={isLoadingMore}
            onClick={() => {
              setIsLoadingMore(true);
              fetchPage(state.data.page_info.next_cursor ?? undefined);
            }}
            className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isLoadingMore ? "Loading…" : "Load more"}
          </button>
        </div>
      ) : null}
    </>
  );
}

export function PortfolioManagerView() {
  const [statusFilter, setStatusFilter] = useState<string | null>(null);

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {STATUS_FILTERS.map((filter) => (
          <button
            key={filter.label}
            type="button"
            onClick={() => setStatusFilter(filter.value)}
            className={`rounded-full px-3 py-1 text-sm font-medium ${
              filter.value === statusFilter
                ? "bg-primary text-text-on-primary"
                : "bg-surface-variant text-text-secondary hover:bg-surface-variant/80"
            }`}
          >
            {filter.label}
          </button>
        ))}
      </div>
      <div className="mt-6">
        <DesignList key={statusFilter} statusFilter={statusFilter} />
      </div>
    </div>
  );
}
