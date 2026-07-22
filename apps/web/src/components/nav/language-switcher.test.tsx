// @vitest-environment jsdom
import { fireEvent, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";

const refresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh }),
}));

import { renderWithLocale } from "@/i18n/test-utils";

import { LanguageSwitcher } from "./language-switcher";

describe("LanguageSwitcher", () => {
  it("shows the four supported locales", () => {
    renderWithLocale(<LanguageSwitcher />);

    const select = screen.getByRole("combobox", { name: "Language" });
    const options = Array.from(select.querySelectorAll("option")).map((o) => o.textContent);
    expect(options).toEqual(["English", "Hindi (हिन्दी)", "Urdu (اردو)", "Arabic (العربية)"]);
  });

  it("persists the choice to a cookie and refreshes the router on change", () => {
    renderWithLocale(<LanguageSwitcher />);

    fireEvent.change(screen.getByRole("combobox", { name: "Language" }), {
      target: { value: "hi" },
    });

    expect(document.cookie).toContain("mv_locale=hi");
    expect(refresh).toHaveBeenCalled();
  });

  it("has no detectable accessibility violations", async () => {
    const { container } = renderWithLocale(<LanguageSwitcher />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
