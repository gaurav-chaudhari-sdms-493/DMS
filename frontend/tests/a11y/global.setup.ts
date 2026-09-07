import { test as setup, expect } from "@playwright/test";

// T96 — one real signup against a real backend, shared by every scan test
// via storageState. `it_admin` is the role sign-up grants the first user
// on a brand-new tenant (see backend/app/services/auth_service.py), which
// is exactly what's needed to reach every authenticated route this suite
// scans, including the /admin/* ones — no separate admin fixture needed.
const API_URL = process.env.PLAYWRIGHT_API_URL || "http://localhost:8000";
const AUTH_FILE = "tests/a11y/.auth/user.json";

setup("create a real test user and save an authenticated session", async ({ page, request }) => {
  const email = `a11y-scan-${Date.now()}@example.com`;
  const password = "A11yScan!2026x";

  const signupResp = await request.post(`${API_URL}/api/v1/auth/sign-up`, {
    data: { full_name: "A11y Scan User", email, password },
  });
  expect(signupResp.ok(), `signup failed: ${await signupResp.text()}`).toBeTruthy();
  const body = await signupResp.json();

  // A same-origin navigation is required before localStorage can be set —
  // there's no document context to write into before the first goto().
  await page.goto("/login");
  await page.evaluate(
    ([accessToken, refreshToken, profile]) => {
      localStorage.setItem("access_token", accessToken);
      localStorage.setItem("refresh_token", refreshToken);
      localStorage.setItem("user_profile", JSON.stringify(profile));
    },
    [
      body.access_token,
      body.refresh_token,
      {
        id: body.user_id,
        tenant_id: body.tenant_id,
        email: body.email,
        role: "it_admin",
        full_name: body.full_name,
      },
    ] as const,
  );

  await page.context().storageState({ path: AUTH_FILE });
});
