// @vitest-environment jsdom
import { screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

import { renderWithLocale } from "@/i18n/test-utils";

import { SettingsForm } from "./settings-form";

const profile = {
  user_id: "u1",
  display_name: "Demo User",
  avatar_url: null,
  bio: null,
  city: null,
  country: null,
  locale: "en",
  timezone: null,
};

const preferences = {
  email_notifications: true,
  push_notifications: true,
  sms_notifications: false,
  marketing_opt_in: false,
  analytics_consent: false,
  profile_visibility: "public" as const,
  show_location: true,
  allow_messages_from_strangers: true,
};

describe("SettingsForm", () => {
  it("renders the language selector and notification toggles", () => {
    renderWithLocale(<SettingsForm profile={profile} preferences={preferences} />);

    expect(screen.getByLabelText("Language")).toBeInTheDocument();
    expect(screen.getByText("Email notifications")).toBeInTheDocument();
    expect(screen.getByText("Push notifications")).toBeInTheDocument();
    expect(screen.getByText("SMS notifications")).toBeInTheDocument();
    expect(screen.getByText("Marketing emails")).toBeInTheDocument();
    expect(
      screen.getByText("Personalization and analytics (see our Cookie Policy)"),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Privacy settings" })).toBeInTheDocument();
  });

  it("offers exactly the four supported locales", () => {
    renderWithLocale(<SettingsForm profile={profile} preferences={preferences} />);

    const select = screen.getByLabelText("Language") as HTMLSelectElement;
    const values = Array.from(select.options).map((o) => o.value);
    expect(values).toEqual(["en", "hi", "ur", "ar"]);
  });

  it("has no detectable accessibility violations", async () => {
    const { container } = renderWithLocale(
      <SettingsForm profile={profile} preferences={preferences} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
