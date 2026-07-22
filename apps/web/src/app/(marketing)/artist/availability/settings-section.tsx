"use client";

import { useEffect, useState } from "react";

import { SubmitButton } from "@/components/forms/submit-button";
import type { ArtistScheduleSettingsData } from "@/lib/scheduling-types";
import { fetchJson, mutateJson } from "@/lib/gallery-client";

export function SettingsSection() {
  const [settings, setSettings] = useState<ArtistScheduleSettingsData | null>(null);
  const [timezone, setTimezone] = useState("");
  const [bufferMinutes, setBufferMinutes] = useState("0");
  const [travelBufferMinutes, setTravelBufferMinutes] = useState("0");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    fetchJson<ArtistScheduleSettingsData>("/api/artist/availability/settings")
      .then((data) => {
        setSettings(data);
        setTimezone(data.timezone);
        setBufferMinutes(String(data.default_buffer_minutes));
        setTravelBufferMinutes(String(data.default_travel_buffer_minutes));
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsSaving(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await mutateJson<ArtistScheduleSettingsData>(
        "/api/artist/availability/settings",
        "PATCH",
        {
          timezone: timezone.trim(),
          default_buffer_minutes: Number(bufferMinutes),
          default_travel_buffer_minutes: Number(travelBufferMinutes),
        },
      );
      setSettings(updated);
      setMessage("Settings saved.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsSaving(false);
    }
  };

  if (!settings && !error) {
    return <p className="text-sm text-text-secondary">Loading…</p>;
  }

  return (
    <form onSubmit={onSubmit} className="flex max-w-md flex-col gap-4">
      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}
      {message ? (
        <p role="status" className="text-sm text-text-secondary">
          {message}
        </p>
      ) : null}

      <label className="flex flex-col gap-1">
        <span className="text-sm font-medium text-text-primary">
          Timezone (IANA name, e.g. Asia/Kolkata)
        </span>
        <input
          type="text"
          value={timezone}
          onChange={(event) => setTimezone(event.target.value)}
          className="rounded-md border border-border bg-background px-3 py-2 text-text-primary"
        />
      </label>

      <label className="flex flex-col gap-1">
        <span className="text-sm font-medium text-text-primary">
          Default buffer between appointments (minutes)
        </span>
        <input
          type="number"
          min={0}
          value={bufferMinutes}
          onChange={(event) => setBufferMinutes(event.target.value)}
          className="rounded-md border border-border bg-background px-3 py-2 text-text-primary"
        />
      </label>

      <label className="flex flex-col gap-1">
        <span className="text-sm font-medium text-text-primary">
          Default travel buffer (minutes)
        </span>
        <input
          type="number"
          min={0}
          value={travelBufferMinutes}
          onChange={(event) => setTravelBufferMinutes(event.target.value)}
          className="rounded-md border border-border bg-background px-3 py-2 text-text-primary"
        />
      </label>

      <SubmitButton isSubmitting={isSaving} loadingLabel="Saving…">
        Save settings
      </SubmitButton>
    </form>
  );
}
