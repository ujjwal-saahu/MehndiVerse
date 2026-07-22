// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PrivacySettingsForm } from "./privacy-settings-form";

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

describe("PrivacySettingsForm", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows an empty state when there are no blocked users", () => {
    render(<PrivacySettingsForm preferences={preferences} initialBlockedUsers={[]} />);

    expect(screen.getByText("You haven't blocked anyone.")).toBeInTheDocument();
  });

  it("lists blocked users and removes one on unblock", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));

    render(
      <PrivacySettingsForm
        preferences={preferences}
        initialBlockedUsers={[
          { user_id: "u2", display_name: "Annoying Person", blocked_at: "2026-01-01T00:00:00Z" },
        ]}
      />,
    );

    expect(screen.getByText("Annoying Person")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Unblock" }));

    expect(await screen.findByText("You haven't blocked anyone.")).toBeInTheDocument();
  });

  it("has no detectable accessibility violations", async () => {
    const { container } = render(
      <PrivacySettingsForm preferences={preferences} initialBlockedUsers={[]} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
