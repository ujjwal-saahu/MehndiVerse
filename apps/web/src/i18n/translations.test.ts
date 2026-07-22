import { describe, expect, it } from "vitest";

import { SUPPORTED_LOCALES } from "./config";
import { translate, translations } from "./translations";

function flattenKeys(node: unknown, prefix = ""): string[] {
  if (node === null || typeof node !== "object") {
    return [prefix];
  }
  return Object.entries(node as Record<string, unknown>).flatMap(([key, value]) =>
    flattenKeys(value, prefix ? `${prefix}.${key}` : key),
  );
}

describe("translation catalogs", () => {
  const baseKeys = new Set(flattenKeys(translations.en));

  it.each(SUPPORTED_LOCALES)(
    "%s has exactly the same keys as the English base catalog",
    (locale) => {
      const keys = new Set(flattenKeys(translations[locale]));
      const missing = [...baseKeys].filter((key) => !keys.has(key));
      const extra = [...keys].filter((key) => !baseKeys.has(key));
      expect({ missing, extra }).toEqual({ missing: [], extra: [] });
    },
  );

  it.each(SUPPORTED_LOCALES)("%s has a non-empty string for every key", (locale) => {
    for (const key of baseKeys) {
      const value = key.split(".").reduce<unknown>((node, part) => {
        return node && typeof node === "object"
          ? (node as Record<string, unknown>)[part]
          : undefined;
      }, translations[locale]);
      expect(typeof value, `${locale}.${key}`).toBe("string");
      expect((value as string).length, `${locale}.${key}`).toBeGreaterThan(0);
    }
  });
});

describe("translate()", () => {
  it("resolves a nested dot-path key", () => {
    expect(translate("en", "auth.login.title")).toBe("Log in");
  });

  it("interpolates {{params}}", () => {
    expect(translate("en", "footer.rights", { year: 2026 })).toContain("2026");
  });

  it("falls back to the English catalog for an unresolvable key", () => {
    expect(translate("hi", "does.not.exist")).toBe("does.not.exist");
  });
});
