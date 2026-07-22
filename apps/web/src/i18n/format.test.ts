import { describe, expect, it } from "vitest";

import { formatCurrency, formatDate, formatNumber, formatShortDate } from "./format";

describe("formatDate", () => {
  it("formats a date in English", () => {
    expect(formatDate("2026-03-15", "en")).toContain("2026");
  });

  it("formats a date in Hindi without throwing", () => {
    expect(() => formatDate("2026-03-15", "hi")).not.toThrow();
  });

  it("formats a short date", () => {
    expect(formatShortDate("2026-03-15", "en")).toContain("2026");
  });
});

describe("formatNumber", () => {
  it("uses locale-appropriate grouping for large numbers", () => {
    expect(formatNumber(1234567, "en")).toBe("12,34,567");
  });

  it("formats a number in Arabic without throwing", () => {
    expect(() => formatNumber(1234567, "ar")).not.toThrow();
  });
});

describe("formatCurrency", () => {
  it("formats INR in English", () => {
    const result = formatCurrency(1999, "INR", "en");
    expect(result).toContain("1,999");
  });

  it("formats a currency in Urdu without throwing", () => {
    expect(() => formatCurrency(1999, "INR", "ur")).not.toThrow();
  });
});
