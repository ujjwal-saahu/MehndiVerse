// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";

import { ComingSoon } from "./coming-soon";
import { EmptyState } from "./empty-state";
import { ErrorState } from "./error-state";
import { Skeleton } from "./skeleton";

describe("EmptyState", () => {
  it("renders title and message", () => {
    render(<EmptyState title="No users yet" message="Nothing to show." />);

    expect(screen.getByRole("heading", { name: "No users yet" })).toBeInTheDocument();
    expect(screen.getByText("Nothing to show.")).toBeInTheDocument();
  });

  it("has no detectable accessibility violations", async () => {
    const { container } = render(<EmptyState title="No users yet" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe("ErrorState", () => {
  it("renders the message and calls onRetry when clicked", () => {
    const onRetry = vi.fn();
    render(<ErrorState message="Could not load." onRetry={onRetry} />);

    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});

describe("Skeleton", () => {
  it("exposes a status role with a loading label", () => {
    render(<Skeleton aria-label="Loading row" />);
    expect(screen.getByRole("status", { name: "Loading row" })).toBeInTheDocument();
  });
});

describe("ComingSoon", () => {
  it("renders the section title and message", () => {
    render(<ComingSoon title="Users" message="User management is coming soon." />);

    expect(screen.getByRole("heading", { name: "Users", level: 1 })).toBeInTheDocument();
    expect(screen.getByText("User management is coming soon.")).toBeInTheDocument();
  });
});
