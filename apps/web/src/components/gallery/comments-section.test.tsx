// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CommentsSection } from "@/components/gallery/comments-section";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const sampleComment = {
  id: "c1",
  design_id: "d1",
  user_id: "u2",
  user_display_name: "Priya",
  parent_comment_id: null,
  body: "Beautiful work!",
  replies: [],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const me = { id: "u1", email: "me@example.com", role: "customer" };

describe("CommentsSection", () => {
  it("shows comments once loaded", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.includes("/api/auth/me")) return Promise.resolve(jsonResponse(me));
        return Promise.resolve(jsonResponse({ items: [sampleComment] }));
      }),
    );

    render(<CommentsSection designId="d1" />);

    expect(await screen.findByText("Beautiful work!")).toBeInTheDocument();
    expect(screen.getByText("Priya")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("shows edit/delete only on your own comment, and Report on others'", async () => {
    const myComment = { ...sampleComment, id: "c2", user_id: "u1", body: "My own comment" };
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.includes("/api/auth/me")) return Promise.resolve(jsonResponse(me));
        return Promise.resolve(jsonResponse({ items: [sampleComment, myComment] }));
      }),
    );

    render(<CommentsSection designId="d1" />);
    await screen.findByText("Beautiful work!");
    await screen.findByText("My own comment");

    expect(screen.getAllByRole("button", { name: "Edit" })).toHaveLength(1);
    expect(screen.getAllByRole("button", { name: "Delete" })).toHaveLength(1);
    expect(screen.getAllByRole("button", { name: "Report" })).toHaveLength(1);

    vi.unstubAllGlobals();
  });

  it("posts a new top-level comment", async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (url.includes("/api/auth/me")) return Promise.resolve(jsonResponse(me));
      if (init?.method === "POST") return Promise.resolve(jsonResponse({ id: "c3" }, 201));
      return Promise.resolve(jsonResponse({ items: [] }));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<CommentsSection designId="d1" />);
    await screen.findByText("No comments yet. Be the first to say something.");

    fireEvent.change(screen.getByPlaceholderText("Add a comment…"), {
      target: { value: "Lovely design" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Post" }));

    await vi.waitFor(() =>
      expect(
        fetchMock.mock.calls.some(
          ([, init]) =>
            (init as RequestInit | undefined)?.method === "POST" &&
            JSON.parse((init as RequestInit).body as string).body === "Lovely design",
        ),
      ).toBe(true),
    );

    vi.unstubAllGlobals();
  });
});
