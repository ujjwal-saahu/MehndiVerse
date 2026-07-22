/** Shapes returned by the backend's artist availability/scheduling
 * endpoints (see app/schemas/scheduling.py) — see docs/artist-scheduling.md.
 */

export interface ArtistScheduleSettingsData {
  timezone: string;
  default_buffer_minutes: number;
  default_travel_buffer_minutes: number;
}

export interface AvailabilityRuleData {
  id: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  is_active: boolean;
}

export type BlockType = "holiday" | "personal_leave" | "vacation" | "other";

export interface BlockedDateData {
  id: string;
  start_date: string;
  end_date: string;
  block_type: BlockType;
  start_time: string | null;
  end_time: string | null;
  reason: string | null;
}

export interface CalendarWindowData {
  start_time: string;
  end_time: string;
}

export interface CalendarDayData {
  date: string;
  day_of_week: number;
  windows: CalendarWindowData[];
  blocks: BlockedDateData[];
  is_available: boolean;
}

export interface CalendarViewData {
  timezone: string;
  days: CalendarDayData[];
}

export interface AvailableSlotData {
  start: string;
  end: string;
}

export interface AvailableSlotsData {
  artist_profile_id: string;
  service_id: string;
  artist_timezone: string;
  slots: AvailableSlotData[];
}

export const DAY_NAMES = [
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
] as const;

export const BLOCK_TYPE_LABELS: Record<BlockType, string> = {
  holiday: "Holiday",
  personal_leave: "Personal leave",
  vacation: "Vacation",
  other: "Other",
};
