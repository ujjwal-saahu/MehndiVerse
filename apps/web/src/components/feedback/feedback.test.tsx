// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";

import { EmptyState } from "./empty-state";
import { ErrorState } from "./error-state";
import { Skeleton } from "./skeleton";

describe("EmptyState", () => {
  it("renders title, message, and an optional action", () => {
    render(
      <EmptyState
        title="No bookings yet"
        message="Nothing to show."
        action={<button type="button">Browse artists</button>}
      />,
    );

    expect(screen.getByRole("heading", { name: "No bookings yet" })).toBeInTheDocument();
    expect(screen.getByText("Nothing to show.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Browse artists" })).toBeInTheDocument();
  });

  it("has no detectable accessibility violations", async () => {
    const { container } = render(<EmptyState title="No bookings yet" />);
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

  it("uses an alert role so assistive tech announces it", () => {
    render(<ErrorState message="Could not load." />);
    expect(screen.getByRole("alert")).toHaveTextContent("Could not load.");
  });
});

describe("Skeleton", () => {
  it("exposes a status role with a loading label", () => {
    render(<Skeleton aria-label="Loading design" />);
    expect(screen.getByRole("status", { name: "Loading design" })).toBeInTheDocument();
  });
});
