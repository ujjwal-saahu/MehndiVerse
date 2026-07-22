// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it } from "vitest";

import { FormField } from "./form-field";
import { SubmitButton } from "./submit-button";

describe("FormField", () => {
  it("associates the label and error message with the input for screen readers", () => {
    render(<FormField label="Email" name="email" error="Enter a valid email address." />);

    const input = screen.getByLabelText("Email");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("alert")).toHaveTextContent("Enter a valid email address.");
  });

  it("omits aria-invalid when there is no error", () => {
    render(<FormField label="Email" name="email" />);
    expect(screen.getByLabelText("Email")).toHaveAttribute("aria-invalid", "false");
  });

  it("has no detectable accessibility violations", async () => {
    const { container } = render(<FormField label="Email" name="email" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe("SubmitButton", () => {
  it("shows the loading label and disables itself while submitting", () => {
    render(
      <SubmitButton isSubmitting loadingLabel="Saving…">
        Save
      </SubmitButton>,
    );

    expect(screen.getByRole("button", { name: "Saving…" })).toBeDisabled();
  });

  it("renders its children and is enabled by default", () => {
    render(<SubmitButton>Save</SubmitButton>);
    expect(screen.getByRole("button", { name: "Save" })).toBeEnabled();
  });
});
