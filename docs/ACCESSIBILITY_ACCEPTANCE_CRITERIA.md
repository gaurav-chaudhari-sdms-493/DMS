# Accessibility Acceptance Criteria & Specification Template

**Baseline Standard:** WCAG 2.1 Level AA & Guidelines for Indian Government Websites (GIGW 3.0)  
**Applicability:** All frontend routes, components, modal dialogues, and interactive review panels in VeritasDocs DMS.  
**Enforcement:** Automated CI regression gate via `axe-core` + ESLint `eslint-plugin-jsx-a11y` (`npm run test:a11y`).

---

## 1. Core Acceptance Criteria (WCAG 2.1 AA / GIGW 3.0)

Every user interface feature must satisfy the following verifiable criteria:

### A. Perceivable (Structure, Semantics & Contrast)
1. **Semantic Landmarks:** Every page must define a single `<main>` landmark. Headers, navigation menus, and auxiliary sidebars must use appropriate semantic tags (`<header>`, `<nav>`, `<aside>`) or ARIA landmark roles with distinct accessible names (`aria-label`).
2. **Color Contrast Ratios:**
   - Standard body text & interactive text: Minimum **4.5:1** contrast ratio against its background.
   - Large text ($\ge 18\text{pt}$ or bold $\ge 14\text{pt}$) & UI component boundaries/icons: Minimum **3.0:1** contrast ratio.
3. **Information & Relationships:**
   - Visual headings must follow a logical hierarchy (`<h1>` $\to$ `<h2>` $\to$ `<h3>`) without skipping levels.
   - Tabbed interfaces must implement the ARIA Tablist pattern: container has `role="tablist"`, individual tabs have `role="tab"`, `aria-selected="true|false"`, `aria-controls="[panel-id]"`, and panels have `role="tabpanel"` and `aria-labelledby="[tab-id]"`.
   - Data tables must include explicit `<th>` headers with `scope="col"` or `scope="row"`, and a `<caption>` or `aria-label`.

### B. Operable (Keyboard Navigation & Modals)
1. **Complete Keyboard Operability:** All interactive elements (buttons, links, inputs, queue rows, tab switches) must be reachable and operable using standard keyboard controls (`Tab`, `Shift+Tab`, `Enter`, `Space`, and Arrow keys).
2. **Visible Focus Indicators:** Interactive elements must display a distinct visual outline or focus ring when focused via keyboard navigation.
3. **Dialog & Modal Focus Trapping:**
   - Modal dialogs must specify `role="dialog"`, `aria-modal="true"`, and `aria-labelledby="[dialog-title-id]"`.
   - Modals must be dismissible via the `Escape` key.
   - Close buttons must provide an explicit accessible name (`aria-label="Close dialog"`).

### C. Understandable (Forms, Labels & Language)
1. **Form Input Labeling:** Every form control (`<input>`, `<select>`, `<textarea>`) must have an associated programmatic label via `<label for="...">`, `aria-label`, or `aria-labelledby`. Placeholders must never be used as the sole label.
2. **Status Messages & Live Regions:** Dynamic system updates, errors, notices, and queue counters must announce changes to assistive technologies using `role="alert"` / `aria-live="assertive"` for critical failures and `role="status"` / `aria-live="polite"` for non-critical notices.
3. **Language Tagging:** Document root must declare the primary language (e.g. `<html lang="en">` or `<html lang="mr">`). Multi-script words (e.g. Marathi / Devanagari terms) must be rendered in UTF-8 Unicode.

### D. Robust (Compatibility & State Synchronization)
1. **Valid ARIA Attributes:** All ARIA roles, states, and properties must conform to WAI-ARIA 1.2 specifications without invalid attributes or conflicting roles.
2. **Icon Buttons:** Any button containing only an icon (e.g. Lucide icons `Eye`, `X`, `Lock`, `SlidersHorizontal`) must specify an `aria-label` or visually-hidden screen reader text (`<span className="sr-only">...</span>`).

---

## 2. Developer Feature Spec Checklist (Template)

When writing or reviewing frontend specification documents, include this checklist block:

```markdown
### Accessibility & WCAG 2.1 AA Checklist
- [ ] **Landmarks & Semantics:** Structured with valid `<main>`, `<nav>`, and `<header>` containers.
- [ ] **Tab Navigation:** Uses `role="tablist"`, `role="tab"`, `aria-selected`, `aria-controls`, and `role="tabpanel"`.
- [ ] **Interactive Elements:** All buttons/links have visible text or `aria-label`. No bare icon buttons.
- [ ] **Form Fields:** Every input/select has an associated `<label>` or `aria-label`.
- [ ] **Dialogs & Overlays:** Includes `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, and `Escape` dismiss handler.
- [ ] **Status & Alerts:** Uses `aria-live="polite"` for notices and `role="alert"` for errors.
- [ ] **Contrast Verification:** Text meets 4.5:1 (normal) / 3.0:1 (large/icons) contrast.
- [ ] **Automated CI Test:** Scanned and passing under `npm run test:a11y`.
```

---

## 3. Automated CI Enforcement Protocol

1. **Pre-commit / CI Verification:**
   - Running `npm run test:a11y` executes the axe-core test engine over all screen fixtures in `frontend/scripts/run_a11y_audit.mjs`.
   - Running `npx next lint` executes `eslint-plugin-jsx-a11y` across all TSX components.
2. **Zero-Tolerance Regression Policy:**
   - Any commit or Pull Request introducing a WCAG 2.1 AA violation (critical, serious, or moderate impact) will immediately fail the `frontend-checks` job in `.github/workflows/ci.yml`.
