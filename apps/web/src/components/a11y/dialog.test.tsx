// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";

import { Dialog } from "./dialog";

function Fixture({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <div>
      <button type="button">Open trigger</button>
      <Dialog open={open} onClose={onClose} title="Delete design">
        <p>Are you sure?</p>
        <button type="button">Confirm</button>
      </Dialog>
    </div>
  );
}

describe("Dialog", () => {
  it("renders nothing when closed", () => {
    render(<Fixture open={false} onClose={vi.fn()} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders with the title as its accessible name when open", () => {
    render(<Fixture open={true} onClose={vi.fn()} />);
    expect(screen.getByRole("dialog", { name: "Delete design" })).toBeInTheDocument();
  });

  it("moves focus into the dialog when it opens", () => {
    render(<Fixture open={true} onClose={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Close" })).toHaveFocus();
  });

  it("calls onClose on Escape", () => {
    const onClose = vi.fn();
    render(<Fixture open={true} onClose={onClose} />);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose on close-button click", () => {
    const onClose = vi.fn();
    render(<Fixture open={true} onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(onClose).toHaveBeenCalled();
  });

  it("traps Tab focus within the dialog", () => {
    render(<Fixture open={true} onClose={vi.fn()} />);
    const closeButton = screen.getByRole("button", { name: "Close" });
    const confirmButton = screen.getByRole("button", { name: "Confirm" });

    confirmButton.focus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(closeButton).toHaveFocus();

    fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
    expect(confirmButton).toHaveFocus();
  });

  it("restores focus to the trigger on close", () => {
    const { rerender } = render(<Fixture open={false} onClose={vi.fn()} />);
    const trigger = screen.getByRole("button", { name: "Open trigger" });
    trigger.focus();

    rerender(<Fixture open={true} onClose={vi.fn()} />);
    rerender(<Fixture open={false} onClose={vi.fn()} />);

    expect(trigger).toHaveFocus();
  });

  it("has no detectable accessibility violations", async () => {
    const { baseElement } = render(<Fixture open={true} onClose={vi.fn()} />);
    expect(await axe(baseElement)).toHaveNoViolations();
  });
});
