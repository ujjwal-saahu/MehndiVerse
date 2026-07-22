// @vitest-environment jsdom
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { LikeSaveButtons } from "./like-save-buttons";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("LikeSaveButtons", () => {
  it("optimistically likes, then confirms with the server response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        expect(url).toBe("/api/designs/d1/like");
        expect(init?.method).toBe("POST");
        return Promise.resolve(jsonResponse({ liked: true, like_count: 6 }));
      }),
    );

    render(
      <LikeSaveButtons
        designId="d1"
        initialIsLiked={false}
        initialLikeCount={5}
        initialIsSaved={false}
        initialSaveCount={0}
      />,
    );

    const likeButton = screen.getByRole("button", { name: /Like/ });
    fireEvent.click(likeButton);

    // Optimistic update is visible immediately, before the fetch resolves.
    expect(screen.getByRole("button", { name: /Liked/ })).toHaveAttribute("aria-pressed", "true");

    await waitFor(() => {
      expect(screen.getByText("6")).toBeInTheDocument();
    });

    vi.unstubAllGlobals();
  });

  it("rolls back the optimistic like when the server call fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse({ message: "Server unavailable." }, 500))),
    );

    render(
      <LikeSaveButtons
        designId="d1"
        initialIsLiked={false}
        initialLikeCount={5}
        initialIsSaved={false}
        initialSaveCount={0}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Like/ }));
    expect(screen.getByRole("button", { name: /Liked/ })).toBeInTheDocument();

    await screen.findByText("Server unavailable.");

    expect(screen.getByRole("button", { name: /^Like/ })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByText("5")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("optimistically unsaves and rolls back on failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse({ message: "Server unavailable." }, 500))),
    );

    render(
      <LikeSaveButtons
        designId="d1"
        initialIsLiked={false}
        initialLikeCount={0}
        initialIsSaved={true}
        initialSaveCount={3}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Saved/ }));
    await screen.findByText("Server unavailable.");

    // Rolled back to the pre-click (saved) state, not left as "unsaved".
    expect(screen.getByRole("button", { name: /^Saved/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("3")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });
});
