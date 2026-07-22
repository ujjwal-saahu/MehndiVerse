// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PreviewStudio } from "./preview-studio";

describe("PreviewStudio", () => {
  it("explains storage behavior and prompts for a photo before anything is saved", () => {
    render(<PreviewStudio />);

    expect(screen.getByText(/Your photo stays on this device while you edit/i)).toBeInTheDocument();
    expect(screen.getByText("Choose a hand or foot photo")).toBeInTheDocument();

    // Save/export/share/send are all disabled until a photo is chosen.
    expect(screen.getByRole("button", { name: "Save preview" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Export image" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Share" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Send to artist" })).toBeDisabled();
  });
});
