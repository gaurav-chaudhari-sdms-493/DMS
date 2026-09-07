# Feature Spec: {{Feature Name}}

*Copy this file, fill it in, delete this line and any bracketed instructions as you go. Sections marked (optional) can be deleted if genuinely not applicable — don't leave them as empty headers.*

## Problem

What's broken, missing, or costly today, in one or two sentences. Name who feels this and how — a vague "would be nice" isn't a problem statement.

## Scope

What this feature actually does. Be concrete: which screens, which API routes, which data.

## Non-goals (optional)

What this explicitly does *not* cover — worth stating whenever the natural reading of the scope above could be misread as broader than intended.

## Design / approach

The actual mechanism: data model changes, new endpoints, UI changes, sequencing. Link to code where it already exists (a partial implementation, a related pattern to follow).

## Accessibility acceptance criteria

*Required for any feature that adds or changes a screen, component, or user-facing flow — not optional boilerplate. See `frontend/tests/a11y/` for how this project actually enforces this (a real `@axe-core/playwright` scan, CI-gated via the `accessibility-scan` job in `.github/workflows/ci.yml`, not just the static `eslint-plugin-jsx-a11y` lint).*

- [ ] **Zero WCAG 2.1 AA violations.** New/changed pages are added to `frontend/tests/a11y/public-pages.spec.ts` or `authenticated-pages.spec.ts` (whichever fits) and the CI scan passes clean — not just "no *new* violations," genuinely zero on that route.
- [ ] **Keyboard operable.** Every interactive control (buttons, links, custom dropdowns, drag targets) is reachable and operable via Tab/Shift+Tab/Enter/Space/Escape alone, with a visible focus indicator at every stop. A clickable `<div>` needs both a keyboard handler and a role — see `frontend/lib/a11y.ts`'s `onKeyActivate` helper, already used elsewhere in this codebase for exactly this.
- [ ] **Color is never the only signal.** Status, error, and selection states pair color with text, an icon, or a pattern — check this specifically for anything red/green (status chips, diff highlighting, form validation).
- [ ] **Color contrast, including at small text sizes.** 4.5:1 for normal text, 3:1 for large text (18pt+/14pt+bold) and UI component boundaries. `#9aa0a6` on white was found failing this (2.64:1) across three real pages during T96's first live scan — verify any new muted/secondary text color against a contrast calculator before using it, not just visually.
- [ ] **Real accessible names.** Every input has a associated `<label>` (or `aria-label`/`aria-labelledby`); every icon-only button has an accessible name (`aria-label`, not just a `title` tooltip); every image that conveys information has real `alt` text (decorative images get `alt=""`, not a missing attribute).
- [ ] **Modals and dialogs trap focus correctly.** Opening a modal moves focus into it; closing it (Escape, backdrop click, close button) returns focus to what triggered it; focus can't tab out to the page behind it while open.
- [ ] **Live regions for async updates.** A toast, inline validation error, or "saved" confirmation that appears without a page navigation is announced to a screen reader (`aria-live`), not silently visual-only.

## Testing plan

Unit/integration tests to add, plus the specific live-verification steps you'll actually run before calling this done (real API calls, a real browser session — see this project's established live-verification discipline, not code-review-only).

## Rollout / migration notes (optional)

Anything that needs a migration, a backfill for existing data, a feature flag, or a specific deploy-order dependency.
