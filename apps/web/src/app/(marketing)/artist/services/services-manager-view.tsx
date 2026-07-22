"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { Skeleton } from "@/components/feedback/skeleton";
import type { ArtistServiceData } from "@/lib/artist-directory-types";
import { fetchJson, mutateJson } from "@/lib/gallery-client";

import { ServiceForm } from "./service-form";

type SectionState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: ArtistServiceData[] };

function formatPrice(service: ArtistServiceData): string {
  if (service.pricing_type === "fixed") {
    return service.price_amount !== null ? `${service.currency} ${service.price_amount}` : "—";
  }
  if (service.pricing_type === "range") {
    return `${service.currency} ${service.price_min ?? "?"} – ${service.price_max ?? "?"}`;
  }
  return "Custom quote";
}

function ServiceRow({
  service,
  onUpdated,
}: {
  service: ArtistServiceData;
  onUpdated: (service: ArtistServiceData) => void;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [isToggling, setIsToggling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleActive = async () => {
    setIsToggling(true);
    setError(null);
    try {
      const updated = await mutateJson<ArtistServiceData>(
        `/api/artist/services/${service.id}`,
        "PATCH",
        { is_active: !service.is_active },
      );
      onUpdated(updated);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsToggling(false);
    }
  };

  if (isEditing) {
    return (
      <ServiceForm
        initial={service}
        onSaved={(updated) => {
          onUpdated(updated);
          setIsEditing(false);
        }}
        onCancel={() => setIsEditing(false)}
      />
    );
  }

  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-medium text-text-primary">{service.name}</p>
          <p className="text-sm text-text-secondary">{formatPrice(service)}</p>
          {!service.is_active ? <p className="mt-1 text-xs text-text-secondary">Inactive</p> : null}
        </div>
        <div className="flex shrink-0 gap-2">
          <button
            type="button"
            onClick={() => setIsEditing(true)}
            className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-text-primary hover:bg-surface-variant"
          >
            Edit
          </button>
          <button
            type="button"
            disabled={isToggling}
            onClick={() => void toggleActive()}
            className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:cursor-not-allowed disabled:opacity-60"
          >
            {service.is_active ? "Deactivate" : "Activate"}
          </button>
        </div>
      </div>
      {error ? <p className="mt-2 text-sm text-danger">{error}</p> : null}
    </div>
  );
}

export function ServicesManagerView() {
  const [state, setState] = useState<SectionState>({ status: "loading" });
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    fetchJson<ArtistServiceData[]>("/api/artist/services")
      .then((data) => setState({ status: "ready", data }))
      .catch((error: Error) => setState({ status: "error", message: error.message }));
  }, []);

  const updateOne = (updated: ArtistServiceData) => {
    setState((current) =>
      current.status === "ready"
        ? {
            status: "ready",
            data: current.data.map((s) => (s.id === updated.id ? updated : s)),
          }
        : current,
    );
  };

  const addOne = (created: ArtistServiceData) => {
    setState((current) =>
      current.status === "ready" ? { status: "ready", data: [...current.data, created] } : current,
    );
    setIsCreating(false);
  };

  if (state.status === "error") {
    return <ErrorState message={state.message} />;
  }

  return (
    <div className="flex flex-col gap-4">
      {!isCreating ? (
        <button
          type="button"
          onClick={() => setIsCreating(true)}
          className="self-start rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary hover:bg-primary-hover"
        >
          New service
        </button>
      ) : (
        <ServiceForm onSaved={addOne} onCancel={() => setIsCreating(false)} />
      )}

      {state.status === "loading" ? (
        <div role="status" aria-label="Loading services" className="flex flex-col gap-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <Skeleton key={index} className="h-20" aria-label="Loading service" />
          ))}
        </div>
      ) : state.data.length === 0 && !isCreating ? (
        <EmptyState
          title="No services yet"
          message="Add a service so customers know what you offer."
        />
      ) : (
        <div className="flex flex-col gap-3">
          {state.data.map((service) => (
            <ServiceRow key={service.id} service={service} onUpdated={updateOne} />
          ))}
        </div>
      )}
    </div>
  );
}
