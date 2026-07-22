// @vitest-environment jsdom
import { fireEvent, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

import { renderWithLocale } from "@/i18n/test-utils";

import { EditProfileForm } from "./edit-profile-form";

const profile = {
  user_id: "u1",
  display_name: "Original Name",
  avatar_url: null,
  bio: null,
  city: null,
  country: null,
  locale: "en",
  timezone: null,
};

describe("EditProfileForm", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("pre-fills the display name field", () => {
    renderWithLocale(<EditProfileForm profile={profile} />);

    expect(screen.getByLabelText("Display name")).toHaveValue("Original Name");
  });

  it("rejects a blank display name", async () => {
    renderWithLocale(<EditProfileForm profile={profile} />);

    fireEvent.change(screen.getByLabelText("Display name"), { target: { value: "   " } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

    expect(await screen.findByText("Display name is required.")).toBeInTheDocument();
  });

  it("rejects an invalid country code", async () => {
    renderWithLocale(<EditProfileForm profile={profile} />);

    fireEvent.change(screen.getByLabelText("Country (e.g. IN)"), {
      target: { value: "India" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

    expect(await screen.findByText("Use a 2-letter country code (e.g. IN).")).toBeInTheDocument();
  });

  it("has no detectable accessibility violations", async () => {
    const { container } = renderWithLocale(<EditProfileForm profile={profile} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
