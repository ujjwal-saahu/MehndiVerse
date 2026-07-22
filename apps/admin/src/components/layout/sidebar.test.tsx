// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}));

import { Sidebar } from "./sidebar";

describe("Sidebar", () => {
  it("shows only the moderator-visible items for a moderator", () => {
    render(<Sidebar role="moderator" />);

    expect(screen.getByRole("link", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Design Moderation" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Reports" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Disputes" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Audit Log" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Settings" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Role Management" })).not.toBeInTheDocument();
  });

  it("shows the admin-visible items (including Audit Log, but not Settings or Role Management)", () => {
    render(<Sidebar role="admin" />);

    expect(screen.getByRole("link", { name: "Users" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Artist Verification" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Audit Log" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Settings" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Role Management" })).not.toBeInTheDocument();
  });

  it("shows every item, including Settings and Role Management, for a super_admin", () => {
    render(<Sidebar role="super_admin" />);

    expect(screen.getByRole("link", { name: "Settings" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Role Management" })).toBeInTheDocument();
  });

  it("marks the current route with aria-current", () => {
    render(<Sidebar role="super_admin" />);

    expect(screen.getByRole("link", { name: "Dashboard" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Users" })).not.toHaveAttribute("aria-current");
  });

  it("has no detectable accessibility violations", async () => {
    const { container } = render(<Sidebar role="super_admin" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
