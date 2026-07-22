// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

import type { ArtistProfileData } from "@/lib/artist-types";

import { ArtistReviewView } from "./artist-review-view";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const underReviewProfile: ArtistProfileData = {
  id: "p1",
  user_id: "artist-1",
  professional_name: "Priya Sharma",
  business_name: null,
  headline: null,
  bio: "Ten years of bridal henna.",
  years_experience: 10,
  country: "IN",
  city: "Jaipur",
  service_areas: [],
  languages: [],
  contact_email: null,
  contact_phone: null,
  social_links: {},
  profile_image_url: null,
  cover_image_url: null,
  verification_status: "under_review",
  submitted_at: "2026-01-01T00:00:00Z",
  reviewed_at: null,
  rejection_reason: null,
  more_info_request: null,
  is_editable: false,
  missing_requirements: [],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const emptyAuditLog = { items: [], page_info: { next_cursor: null, has_more: false } };

describe("ArtistReviewView", () => {
  it("hides review actions and shows a self-review warning when isSelf is true", () => {
    render(
      <ArtistReviewView
        artistId="p1"
        initialProfile={underReviewProfile}
        initialDocuments={[]}
        initialAuditLog={emptyAuditLog}
        canAct={false}
        isSelf={true}
      />,
    );

    expect(screen.getByText(/you cannot review it/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
  });

  it("hides review actions for a viewer without edit rights (moderator)", () => {
    render(
      <ArtistReviewView
        artistId="p1"
        initialProfile={underReviewProfile}
        initialDocuments={[]}
        initialAuditLog={emptyAuditLog}
        canAct={false}
        isSelf={false}
      />,
    );

    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
    expect(screen.queryByText(/you cannot review it/)).not.toBeInTheDocument();
  });

  it("approves the application when an authorized reviewer clicks Approve", async () => {
    const fetchSpy = vi.fn<(url: string, init?: RequestInit) => Promise<Response>>((url) =>
      Promise.resolve(
        url.includes("/audit-log")
          ? jsonResponse(emptyAuditLog)
          : jsonResponse({ ...underReviewProfile, verification_status: "approved" }),
      ),
    );
    vi.stubGlobal("fetch", fetchSpy);

    render(
      <ArtistReviewView
        artistId="p1"
        initialProfile={underReviewProfile}
        initialDocuments={[]}
        initialAuditLog={emptyAuditLog}
        canAct={true}
        isSelf={false}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Approve" }));

    await screen.findByText("Approved");
    const [url] = fetchSpy.mock.calls[0] as [string];
    expect(url).toContain("/api/admin/artists/p1/approve");

    vi.unstubAllGlobals();
  });

  it("requires a non-empty reason before confirming a rejection", async () => {
    const fetchSpy = vi.fn<(url: string, init?: RequestInit) => Promise<Response>>((url) =>
      Promise.resolve(
        url.includes("/audit-log")
          ? jsonResponse(emptyAuditLog)
          : jsonResponse({ ...underReviewProfile, verification_status: "rejected" }),
      ),
    );
    vi.stubGlobal("fetch", fetchSpy);

    render(
      <ArtistReviewView
        artistId="p1"
        initialProfile={underReviewProfile}
        initialDocuments={[]}
        initialAuditLog={emptyAuditLog}
        canAct={true}
        isSelf={false}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Reject" }));
    const confirmButton = await screen.findByRole("button", { name: "Reject application" });
    expect(confirmButton).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Reason for rejection"), {
      target: { value: "Documents are unclear." },
    });
    expect(confirmButton).not.toBeDisabled();

    fireEvent.click(confirmButton);
    await screen.findByText("Rejected");
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(init.body as string)).toEqual({ reason: "Documents are unclear." });

    vi.unstubAllGlobals();
  });
});
