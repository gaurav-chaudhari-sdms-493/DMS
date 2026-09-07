import { defineConfig } from "@playwright/test";

// T96 — accessibility scan config. Separate from any future functional
// E2E suite: testDir is scoped to tests/a11y only, and the whole run
// deliberately stays single-worker (fullyParallel: false) — the setup
// project signs up one real user against a real backend and every scan
// test reuses that same session; running scans concurrently would just
// add CI contention for no benefit, since each page load is already fast.
export default defineConfig({
  testDir: "./tests/a11y",
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  // list for readable CI logs, html for the artifact CI uploads on
  // failure (open:never — CI has no browser to auto-open a report in).
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000",
    // Runs against the system-installed Chrome instead of downloading
    // Playwright's own Chromium — this environment (and CI, once set up
    // the same way) already has google-chrome available, and `playwright
    // install` needs network access this sandbox doesn't always have.
    channel: "chrome",
  },
  projects: [
    {
      name: "setup",
      testMatch: /global\.setup\.ts/,
    },
    {
      name: "a11y",
      testMatch: /.*\.spec\.ts/,
      dependencies: ["setup"],
      use: {
        storageState: "tests/a11y/.auth/user.json",
      },
    },
  ],
});
