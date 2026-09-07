import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// Unauthenticated on purpose: the shared storageState from global.setup.ts
// would otherwise carry a logged-in session onto these routes, which
// redirects straight past /login and /signup to /drive — defeating the
// point of scanning the pages a signed-out visitor actually lands on.
test.use({ storageState: { cookies: [], origins: [] } });

const PUBLIC_PAGES = ["/", "/login", "/signup", "/forgot-password"];

for (const path of PUBLIC_PAGES) {
  test(`${path} has no WCAG 2.1 AA violations`, async ({ page }) => {
    await page.goto(path);
    await page.waitForLoadState("networkidle");

    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();

    expect(
      results.violations,
      formatViolations(path, results.violations),
    ).toEqual([]);
  });
}

function formatViolations(path: string, violations: any[]): string {
  if (violations.length === 0) return "";
  return [
    `${path}: ${violations.length} WCAG 2.1 AA violation(s)`,
    ...violations.map(
      (v) =>
        `  [${v.impact}] ${v.id} — ${v.help} (${v.nodes.length} element(s))\n` +
        v.nodes.map((n: any) => `    ${n.target.join(" ")}`).join("\n"),
    ),
  ].join("\n");
}
