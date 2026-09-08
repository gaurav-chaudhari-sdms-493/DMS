// Shared between the server component app/layout.tsx and the client-only
// I18nProvider in lib/i18n.tsx. Must NOT have "use client" — importing a
// constant from a "use client" module into a Server Component turns it into
// a client-reference proxy on the server (Next.js App Router), and calling
// e.g. `.includes()` on it there throws at request time.
export const SUPPORTED_LOCALES = ["en", "mr"] as const;
export type Locale = (typeof SUPPORTED_LOCALES)[number];

// Mirrors the "dms_locale" localStorage key i18n.tsx already used, so the
// server can read the same preference from a cookie before hydration.
export const LOCALE_COOKIE_KEY = "dms_locale";
