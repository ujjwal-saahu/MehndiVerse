// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

import type { ArtistProfileData } from "@/lib/artist-types";

import { OnboardingWizard } from "./onboarding-wizard";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const draftProfile: ArtistProfileData = {
  id: "p1",
  user_id: "u1",
  professional_name: null,
  business_name: null,
  headline: null,
  bio: null,
  years_experience: null,
  country: null,
  city: null,
  service_areas: [],
  languages: [],
  contact_email: null,
  contact_phone: null,
  social_links: {},
  profile_image_url: null,
  cover_image_url: null,
  verification_status: "draft",
  submitted_at: null,
  reviewed_at: null,
  rejection_reason: null,
  more_info_request: null,
  is_editable: true,
  missing_requirements: ["professional_name", "bio", "identity_document"],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("OnboardingWizard", () => {
  it("shows a read-only message instead of the form when the application isn't editable", () => {
    render(
      <OnboardingWizard
        initialProfile={{ ...draftProfile, verification_status: "submitted", is_editable: false }}
        initialDocuments={[]}
      />,
    );

    expect(screen.getByText(/can't be edited right now/)).toBeInTheDocument();
    expect(screen.queryByText("Professional name")).not.toBeInTheDocument();
  });

  it("saves the current step and advances to the next one", async () => {
    const fetchSpy = vi.fn<(url: string, init?: RequestInit) => Promise<Response>>(() =>
      Promise.resolve(jsonResponse({ ...draftProfile, professional_name: "Priya" })),
    );
    vi.stubGlobal("fetch", fetchSpy);

    render(<OnboardingWizard initialProfile={draftProfile} initialDocuments={[]} />);

    fireEvent.change(screen.getByLabelText("Professional name"), {
      target: { value: "Priya" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));

    await screen.findByText("Country (e.g. IN)");
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(init.body as string)).toMatchObject({ professional_name: "Priya" });

    vi.unstubAllGlobals();
  });

  it("disables submission while requirements are missing on the review step", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(jsonResponse({ ...draftProfile, missing_requirements: ["bio"] })),
      ),
    );

    render(<OnboardingWizard initialProfile={draftProfile} initialDocuments={[]} />);

    fireEvent.click(screen.getByRole("button", { name: "Continue" })); // step 0 -> 1
    await screen.findByText("Country (e.g. IN)");
    fireEvent.click(screen.getByRole("button", { name: "Continue" })); // step 1 -> 2
    await screen.findByText("Contact email (optional)");
    fireEvent.click(screen.getByRole("button", { name: "Continue" })); // step 2 -> 3
    await screen.findByText("Profile photo (optional)");
    fireEvent.click(screen.getByRole("button", { name: "Continue" })); // step 3 -> 4
    await screen.findByText("Identity document (required)");
    fireEvent.click(screen.getByRole("button", { name: "Continue" })); // step 4 -> 5

    const submitButton = await screen.findByRole("button", { name: "Submit for review" });
    expect(submitButton).toBeDisabled();
    expect(screen.getByText("Biography")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });
});
