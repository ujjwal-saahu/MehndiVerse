// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ReportButton } from "@/components/feedback/report-button";

describe("ReportButton", () => {
  it("does nothing when the reason prompt is dismissed", () => {
    vi.spyOn(window, "prompt").mockReturnValue(null);
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    render(<ReportButton endpoint="/api/designs/d1/report" label="Report design" />);
    fireEvent.click(screen.getByRole("button", { name: "Report design" }));

    expect(fetchMock).not.toHaveBeenCalled();

    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("submits the reason and shows a confirmation", async () => {
    vi.spyOn(window, "prompt").mockReturnValue("Stolen artwork");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ status: "pending" }), {
          status: 201,
          headers: { "content-type": "application/json" },
        }),
      ),
    );

    render(<ReportButton endpoint="/api/designs/d1/report" label="Report design" />);
    fireEvent.click(screen.getByRole("button", { name: "Report design" }));

    expect(await screen.findByText(/Thanks/)).toBeInTheDocument();

    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("shows the backend's error message on failure", async () => {
    vi.spyOn(window, "prompt").mockReturnValue("Spam");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ message: "You already have an open report for this." }), {
          status: 409,
          headers: { "content-type": "application/json" },
        }),
      ),
    );

    render(<ReportButton endpoint="/api/comments/c1/report" label="Report" />);
    fireEvent.click(screen.getByRole("button", { name: "Report" }));

    expect(
      await screen.findByText("You already have an open report for this."),
    ).toBeInTheDocument();

    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });
});
