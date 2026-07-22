// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";

import { ReasonDialog } from "./reason-dialog";

describe("ReasonDialog", () => {
  it("renders nothing when closed", () => {
    const { container } = render(
      <ReasonDialog isOpen={false} title="Suspend user" onConfirm={vi.fn()} onCancel={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("keeps the confirm button disabled until a reason is entered", () => {
    render(<ReasonDialog isOpen title="Suspend user" onConfirm={vi.fn()} onCancel={vi.fn()} />);

    const confirmButton = screen.getByRole("button", { name: "Submit" });
    expect(confirmButton).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Reason"), {
      target: { value: "Repeated harassment reports" },
    });
    expect(confirmButton).toBeEnabled();
  });

  it("disables the confirm button again for whitespace-only input", () => {
    render(<ReasonDialog isOpen title="Suspend user" onConfirm={vi.fn()} onCancel={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Reason"), { target: { value: "   " } });
    expect(screen.getByRole("button", { name: "Submit" })).toBeDisabled();
  });

  it("calls onConfirm with the trimmed reason", () => {
    const onConfirm = vi.fn();
    render(<ReasonDialog isOpen title="Suspend user" onConfirm={onConfirm} onCancel={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Reason"), {
      target: { value: "  Repeated harassment reports  " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit" }));

    expect(onConfirm).toHaveBeenCalledWith("Repeated harassment reports");
  });

  it("shows a server error message when provided", () => {
    render(
      <ReasonDialog
        isOpen
        title="Suspend user"
        error="Something went wrong."
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("Something went wrong.");
  });

  it("has no detectable accessibility violations", async () => {
    const { container } = render(
      <ReasonDialog isOpen title="Suspend user" onConfirm={vi.fn()} onCancel={vi.fn()} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
