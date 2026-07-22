import "@testing-library/jest-dom/vitest";
import { afterEach, expect, vi } from "vitest";
import { cleanup } from "@testing-library/react";
import { toHaveNoViolations } from "jest-axe";
import React from "react";

expect.extend(toHaveNoViolations);

// @testing-library/react normally auto-registers this via a global
// `afterEach`, but vitest doesn't expose test-framework globals unless
// `test.globals: true` is set — register it explicitly instead so each
// component test starts from an empty DOM.
afterEach(() => {
  cleanup();
});

// next/image relies on Next's dev/build-time image optimization pipeline,
// which isn't present under plain jsdom — render a plain <img> instead.
vi.mock("next/image", () => ({
  __esModule: true,
  default: (props: Record<string, unknown>) => {
    const { fill, sizes, priority, ...rest } = props;
    void fill;
    void sizes;
    void priority;
    return React.createElement("img", rest);
  },
}));
