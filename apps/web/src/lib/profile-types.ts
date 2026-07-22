/** Shapes returned by the backend's /users/me/* endpoints (see
 * app/schemas/profile.py) — shared across the profile/settings pages so they
 * don't each redeclare the same fields. */

export interface ProfileData {
  user_id: string;
  display_name: string;
  avatar_url: string | null;
  bio: string | null;
  city: string | null;
  country: string | null;
  locale: string | null;
  timezone: string | null;
}

export interface PreferencesData {
  email_notifications: boolean;
  push_notifications: boolean;
  sms_notifications: boolean;
  marketing_opt_in: boolean;
  analytics_consent: boolean;
  profile_visibility: "public" | "private";
  show_location: boolean;
  allow_messages_from_strangers: boolean;
}

export interface BlockedUserData {
  user_id: string;
  display_name: string | null;
  blocked_at: string;
}
