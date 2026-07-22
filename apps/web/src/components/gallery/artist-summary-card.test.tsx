// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it } from "vitest";

import { ArtistSummaryCard } from "./artist-summary-card";

describe("ArtistSummaryCard", () => {
  it("shows the artist's rating when they have reviews", () => {
    render(
      <ArtistSummaryCard
        artist={{
          id: "a1",
          display_name: "Henna by Asha",
          avatar_url: null,
          headline: "Bridal specialist",
          rating_average: 4.75,
          rating_count: 12,
          is_accepting_bookings: true,
        }}
      />,
    );

    expect(screen.getByText("Henna by Asha")).toBeInTheDocument();
    expect(screen.getByText("Bridal specialist")).toBeInTheDocument();
    expect(screen.getByText("★ 4.8 (12)")).toBeInTheDocument();
  });

  it("shows a no-reviews message when the artist has none yet", () => {
    render(
      <ArtistSummaryCard
        artist={{
          id: "a1",
          display_name: "New Artist",
          avatar_url: null,
          headline: null,
          rating_average: 0,
          rating_count: 0,
          is_accepting_bookings: true,
        }}
      />,
    );

    expect(screen.getByText("No reviews yet")).toBeInTheDocument();
  });

  it("has no detectable accessibility violations", async () => {
    const { container } = render(
      <ArtistSummaryCard
        artist={{
          id: "a1",
          display_name: "Henna by Asha",
          avatar_url: null,
          headline: null,
          rating_average: 0,
          rating_count: 0,
          is_accepting_bookings: true,
        }}
      />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
