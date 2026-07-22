// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";

import { DesignGrid } from "./design-grid";
import type { DesignCardData } from "./design-card";

const sampleDesigns: DesignCardData[] = [
  { id: "1", title: "Bridal floral", imageUrl: "/test-image-1.jpg", artistName: "Asha" },
  { id: "2", title: "Minimalist wrist", imageUrl: "/test-image-2.jpg" },
];

describe("DesignGrid", () => {
  it("renders a skeleton grid while loading", () => {
    render(<DesignGrid designs={[]} isLoading skeletonCount={4} />);

    expect(screen.getByRole("status", { name: "Loading designs" })).toBeInTheDocument();
  });

  it("renders an empty state when there are no designs and it is not loading", () => {
    render(
      <DesignGrid designs={[]} emptyTitle="Nothing here yet" emptyMessage="Check back soon." />,
    );

    expect(screen.getByText("Nothing here yet")).toBeInTheDocument();
    expect(screen.getByText("Check back soon.")).toBeInTheDocument();
  });

  it("renders a card per design when designs are present", () => {
    render(<DesignGrid designs={sampleDesigns} />);

    expect(screen.getByText("Bridal floral")).toBeInTheDocument();
    expect(screen.getByText("by Asha")).toBeInTheDocument();
    expect(screen.getByText("Minimalist wrist")).toBeInTheDocument();
  });

  it("renders a retry-capable error state and takes priority over loading/empty", () => {
    const onRetry = vi.fn();
    render(<DesignGrid designs={[]} isLoading error="Could not load designs." onRetry={onRetry} />);

    expect(screen.getByRole("alert")).toHaveTextContent("Could not load designs.");
    screen.getByRole("button", { name: "Try again" }).click();
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("has no detectable accessibility violations in any state", async () => {
    const { container: loadingContainer } = render(<DesignGrid designs={[]} isLoading />);
    expect(await axe(loadingContainer)).toHaveNoViolations();

    const { container: emptyContainer } = render(<DesignGrid designs={[]} />);
    expect(await axe(emptyContainer)).toHaveNoViolations();

    const { container: populatedContainer } = render(<DesignGrid designs={sampleDesigns} />);
    expect(await axe(populatedContainer)).toHaveNoViolations();
  });
});
