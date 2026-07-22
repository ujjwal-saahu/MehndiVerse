// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";

import { Pagination } from "./pagination";

describe("Pagination", () => {
  it("renders nothing when there is only one page", () => {
    const { container } = render(
      <Pagination page={1} totalPages={1} total={3} onPageChange={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("disables Previous on the first page and Next on the last page", () => {
    render(<Pagination page={1} totalPages={3} total={30} onPageChange={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next" })).toBeEnabled();
  });

  it("calls onPageChange with the next/previous page", () => {
    const onPageChange = vi.fn();
    render(<Pagination page={2} totalPages={3} total={30} onPageChange={onPageChange} />);

    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(onPageChange).toHaveBeenCalledWith(3);

    fireEvent.click(screen.getByRole("button", { name: "Previous" }));
    expect(onPageChange).toHaveBeenCalledWith(1);
  });

  it("has no detectable accessibility violations", async () => {
    const { container } = render(
      <Pagination page={2} totalPages={3} total={30} onPageChange={vi.fn()} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
