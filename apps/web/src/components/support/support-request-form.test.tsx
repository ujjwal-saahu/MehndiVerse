// @vitest-environment jsdom
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { axe } from "jest-axe";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SupportRequestForm } from "./support-request-form";

describe("SupportRequestForm", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("submits and shows a confirmation", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ id: "1", status: "open" }), { status: 201 }),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<SupportRequestForm defaultCategory="bug_report" prefillEmail="me@example.com" />);

    fireEvent.change(screen.getByLabelText("Subject"), {
      target: { value: "Upload fails" },
    });
    fireEvent.change(screen.getByLabelText("Message"), {
      target: { value: "The upload button does nothing." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() =>
      expect(
        screen.getByText("Thanks — we've received your message and will follow up by email."),
      ).toBeInTheDocument(),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/support/requests",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("shows a server error without crashing", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ message: "Too many requests." }), { status: 429 }),
        ),
    );

    render(<SupportRequestForm defaultCategory="other" prefillEmail="me@example.com" />);
    fireEvent.change(screen.getByLabelText("Subject"), { target: { value: "x" } });
    fireEvent.change(screen.getByLabelText("Message"), { target: { value: "y" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Too many requests.");
  });

  it("has no detectable accessibility violations", async () => {
    const { container } = render(<SupportRequestForm defaultCategory="other" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
