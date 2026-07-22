// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { FollowButton } from "./follow-button";

describe("FollowButton", () => {
  it("optimistically follows and increments the count", async () => {
    const fetchSpy = vi.fn<(url: string, init?: RequestInit) => Promise<Response>>(() =>
      Promise.resolve(new Response(null, { status: 204 })),
    );
    vi.stubGlobal("fetch", fetchSpy);

    render(<FollowButton artistId="a1" initialIsFollowed={false} initialFollowerCount={3} />);

    fireEvent.click(screen.getByRole("button", { name: /Follow · 3/ }));

    expect(await screen.findByRole("button", { name: /Following · 4/ })).toBeInTheDocument();
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/artists/a1/follow");
    expect(init.method).toBe("POST");

    vi.unstubAllGlobals();
  });

  it("optimistically unfollows and decrements the count", async () => {
    const fetchSpy = vi.fn<(url: string, init?: RequestInit) => Promise<Response>>(() =>
      Promise.resolve(new Response(null, { status: 204 })),
    );
    vi.stubGlobal("fetch", fetchSpy);

    render(<FollowButton artistId="a1" initialIsFollowed={true} initialFollowerCount={3} />);

    fireEvent.click(screen.getByRole("button", { name: /Following · 3/ }));

    expect(await screen.findByRole("button", { name: /Follow · 2/ })).toBeInTheDocument();
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("DELETE");

    vi.unstubAllGlobals();
  });

  it("rolls back to the previous state when the request fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          new Response(JSON.stringify({ message: "Server unavailable." }), { status: 500 }),
        ),
      ),
    );

    render(<FollowButton artistId="a1" initialIsFollowed={false} initialFollowerCount={3} />);

    fireEvent.click(screen.getByRole("button", { name: /Follow · 3/ }));

    expect(await screen.findByText("Server unavailable.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Follow · 3/ })).toBeInTheDocument();

    vi.unstubAllGlobals();
  });
});
