// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";

import { CategoryChips } from "./category-chips";

const categories = [
  {
    id: "c1",
    name: "Bridal",
    slug: "bridal",
    category_type: "occasion",
    description: null,
    parent_category_id: null,
    sort_order: 0,
    is_active: true,
  },
  {
    id: "c2",
    name: "Arabic",
    slug: "arabic",
    category_type: "style",
    description: null,
    parent_category_id: null,
    sort_order: 1,
    is_active: true,
  },
];

describe("CategoryChips", () => {
  it("marks the active chip as pressed", () => {
    render(<CategoryChips categories={categories} activeKey="c1" onSelect={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Bridal" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Arabic" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "Home" })).toHaveAttribute("aria-pressed", "false");
  });

  it("calls onSelect with the chosen category id", () => {
    const onSelect = vi.fn();
    render(<CategoryChips categories={categories} activeKey="home" onSelect={onSelect} />);

    fireEvent.click(screen.getByRole("button", { name: "Arabic" }));

    expect(onSelect).toHaveBeenCalledWith("c2");
  });

  it("has no detectable accessibility violations", async () => {
    const { container } = render(
      <CategoryChips categories={categories} activeKey="home" onSelect={vi.fn()} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
