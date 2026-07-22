"use client";

import { useState } from "react";

import { BlocksSection } from "./blocks-section";
import { CalendarSection } from "./calendar-section";
import { RulesSection } from "./rules-section";
import { SettingsSection } from "./settings-section";

const TABS = [
  { key: "hours", label: "Weekly hours" },
  { key: "blocks", label: "Time off" },
  { key: "calendar", label: "Calendar" },
  { key: "settings", label: "Settings" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

export function AvailabilityManagerView() {
  const [tab, setTab] = useState<TabKey>("hours");

  return (
    <div>
      <div className="flex flex-wrap gap-2 border-b border-border pb-3">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={`rounded-full px-3 py-1 text-sm font-medium ${
              tab === t.key
                ? "bg-primary text-text-on-primary"
                : "bg-surface-variant text-text-secondary hover:bg-surface-variant/80"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {tab === "hours" ? <RulesSection /> : null}
        {tab === "blocks" ? <BlocksSection /> : null}
        {tab === "calendar" ? <CalendarSection /> : null}
        {tab === "settings" ? <SettingsSection /> : null}
      </div>
    </div>
  );
}
