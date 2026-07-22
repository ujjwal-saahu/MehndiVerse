// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";

const cookieStore = { get: vi.fn(() => undefined) };
vi.mock("next/headers", () => ({
  cookies: async () => cookieStore,
}));

import { Footer } from "./footer";

describe("Footer", () => {
  it("renders the current year and navigation links", async () => {
    render(await Footer());

    expect(screen.getByText(new RegExp(String(new Date().getFullYear())))).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Log in" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign up" })).toBeInTheDocument();
  });

  it("has no detectable accessibility violations", async () => {
    const { container } = render(await Footer());
    expect(await axe(container)).toHaveNoViolations();
  });
});
