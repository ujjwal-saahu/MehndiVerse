// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it } from "vitest";

import { DesignCard } from "./design-card";

describe("DesignCard", () => {
  it("renders an accessible image with the design and artist in the alt text", () => {
    render(
      <DesignCard
        design={{ id: "1", title: "Bridal floral", imageUrl: "/test.jpg", artistName: "Asha" }}
      />,
    );

    expect(screen.getByAltText("Bridal floral mehndi design by Asha")).toBeInTheDocument();
  });

  it("falls back to a title-only alt text when there is no artist", () => {
    render(<DesignCard design={{ id: "1", title: "Minimalist wrist", imageUrl: "/test.jpg" }} />);

    expect(screen.getByAltText("Minimalist wrist mehndi design")).toBeInTheDocument();
  });

  it("shows an accessible placeholder instead of a broken image when imageUrl is null", () => {
    render(<DesignCard design={{ id: "1", title: "Processing design", imageUrl: null }} />);

    expect(screen.queryByRole("img", { name: /processing design/i })).toBeInTheDocument();
    expect(screen.queryByAltText(/mehndi design$/i)).not.toBeInTheDocument();
  });

  it("has no detectable accessibility violations", async () => {
    const { container } = render(
      <DesignCard design={{ id: "1", title: "Bridal floral", imageUrl: "/test.jpg" }} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
