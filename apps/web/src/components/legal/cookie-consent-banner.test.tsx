// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CookieConsentBanner } from "./cookie-consent-banner";

describe("CookieConsentBanner", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows the banner on first visit", async () => {
    render(<CookieConsentBanner />);
    expect(await screen.findByRole("region", { name: "Cookie consent" })).toBeInTheDocument();
  });

  it("does not show the banner once a choice was already stored", async () => {
    window.localStorage.setItem("mv_cookie_consent", "accepted");
    render(<CookieConsentBanner />);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(screen.queryByRole("region", { name: "Cookie consent" })).not.toBeInTheDocument();
  });

  it("accepting analytics stores the choice and posts to /api/preferences", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    render(<CookieConsentBanner />);
    fireEvent.click(await screen.findByRole("button", { name: "Accept analytics" }));

    expect(window.localStorage.getItem("mv_cookie_consent")).toBe("accepted");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/preferences",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ analytics_consent: true }),
      }),
    );
    expect(screen.queryByRole("region", { name: "Cookie consent" })).not.toBeInTheDocument();
  });

  it("declining does not throw even when the visitor is signed out (401)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 401 })));

    render(<CookieConsentBanner />);
    fireEvent.click(await screen.findByRole("button", { name: "Necessary only" }));

    expect(window.localStorage.getItem("mv_cookie_consent")).toBe("necessary-only");
  });

  it("has no detectable accessibility violations", async () => {
    const { container } = render(<CookieConsentBanner />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
