import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  test: {
    // Route handler / middleware tests (.test.ts) run fine under plain node;
    // component tests (.test.tsx) need a DOM — add a
    // `// @vitest-environment jsdom` docblock at the top of those files
    // rather than switching the default globally (keeps node tests fast).
    environment: "node",
    setupFiles: ["./vitest.setup.ts"],
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
