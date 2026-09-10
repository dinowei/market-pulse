import { defineConfig, devices } from "@playwright/test";

// Local-only runner: no deploy, saved sessions, traces or provider calls.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  reporter: "list",
  use: {
    ...devices["Desktop Chrome"],
    baseURL: "http://localhost:3000",
    serviceWorkers: "block",
    trace: "off",
    video: "off",
    screenshot: "off",
  },
});
