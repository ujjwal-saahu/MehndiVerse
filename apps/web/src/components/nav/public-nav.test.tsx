// @vitest-environment jsdom
import { screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";

const cookieStore = {
  has: vi.fn(),
  get: vi.fn((): { value: string } | undefined => undefined),
};
vi.mock("next/headers", () => ({
  cookies: async () => cookieStore,
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

import { renderWithLocale } from "@/i18n/test-utils";

import { PublicNav } from "./public-nav";

describe("PublicNav", () => {
  it("shows login/sign up links when there is no session", async () => {
    cookieStore.has.mockReturnValue(false);
    renderWithLocale(await PublicNav());

    expect(screen.getByRole("link", { name: "Log in" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign up" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Account" })).not.toBeInTheDocument();
  });

  it("shows an Account link when a session cookie is present", async () => {
    cookieStore.has.mockReturnValue(true);
    renderWithLocale(await PublicNav());

    expect(screen.getByRole("link", { name: "Account" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Log in" })).not.toBeInTheDocument();
  });

  it("includes a language switcher", async () => {
    cookieStore.has.mockReturnValue(false);
    renderWithLocale(await PublicNav());

    expect(screen.getByRole("combobox", { name: "Language" })).toBeInTheDocument();
  });

  it("has no detectable accessibility violations", async () => {
    cookieStore.has.mockReturnValue(false);
    const { container } = renderWithLocale(await PublicNav());

    expect(await axe(container)).toHaveNoViolations();
  });
});

describe("PublicNav locale rendering", () => {
  it("renders nav labels in the resolved locale without a LocaleProvider mismatch", async () => {
    cookieStore.has.mockReturnValue(false);
    cookieStore.get.mockReturnValue({ value: "hi" });

    renderWithLocale(await PublicNav(), { locale: "hi" });

    expect(screen.getByText("लॉग इन करें")).toBeInTheDocument();
  });
});
