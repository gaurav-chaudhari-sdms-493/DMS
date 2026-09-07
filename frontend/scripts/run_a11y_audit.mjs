#!/usr/bin/env node
/**
 * Automated Accessibility (a11y) Audit Suite
 *
 * Enforces WCAG 2.1 Level A and AA standards (including GIGW 3.0 baseline)
 * using axe-core across all DMS frontend routes, screens, and UI sub-states.
 *
 * Task: T96
 */

import { JSDOM } from 'jsdom';
import axe from 'axe-core';

// Color palette definitions matching Tailwind configuration for accurate contrast testing
const BRAND_PRIMARY = '#0d2e5c';
const BRAND_TEXT = '#1f1f1f';
const MUTED_TEXT = '#5f6368';
const LIGHT_BG = '#f8f9fa';

/**
 * Test Fixtures representing application pages and interactive states.
 */
const FIXTURES = [
  {
    name: 'Workbench — Needs Review Queue (T96 primary focus)',
    route: '/workbench',
    html: `
      <header class="min-h-16 px-6 py-2 flex items-center justify-between border-b bg-white">
        <div class="flex items-center gap-4">
          <a href="/drive" class="flex items-center gap-2 text-sm text-[#444746] px-3 py-1.5 rounded-lg">
            <span>Back to Drive</span>
          </a>
          <h1 class="text-lg font-bold text-[#1f1f1f]">Verification Workbench</h1>
        </div>
        <div class="flex items-center gap-1.5 text-xs text-[#5f6368]">
          <span>&uarr;/&darr; navigate &middot; C claim &middot; R release &middot; Enter/A confirm &middot; H mark handwritten</span>
        </div>
      </header>
      <main class="max-w-6xl mx-auto px-6 py-6 grid grid-cols-[1fr_360px] gap-6">
        <div>
          <div role="tablist" aria-label="Adjudication queues" class="flex flex-wrap gap-2 mb-2">
            <button role="tab" id="tab-low_confidence" aria-selected="true" aria-controls="queue-panel" tabindex="0" class="px-3.5 py-1.5 rounded-full text-xs font-bold bg-[#0d2e5c] text-white">
              Needs Review <span aria-label="14 items" class="bg-white/20 text-[10px] px-1.5 py-0.5 rounded-full">14</span>
            </button>
            <button role="tab" id="tab-handwritten" aria-selected="false" aria-controls="queue-panel" tabindex="-1" class="px-3.5 py-1.5 rounded-full text-xs font-bold bg-white text-[#444746] border">
              Handwritten <span aria-label="3 items" class="bg-[#f0f4f9] text-[#5f6368] text-[10px] px-1.5 py-0.5 rounded-full">3</span>
            </button>
            <button role="tab" id="tab-marginalia" aria-selected="false" aria-controls="queue-panel" tabindex="-1" class="px-3.5 py-1.5 rounded-full text-xs font-bold bg-white text-[#444746] border">
              Marginalia <span aria-label="2 items" class="bg-[#f0f4f9] text-[#5f6368] text-[10px] px-1.5 py-0.5 rounded-full">2</span>
            </button>
            <button role="tab" id="tab-join_mismatch" aria-selected="false" aria-controls="queue-panel" tabindex="-1" class="px-3.5 py-1.5 rounded-full text-xs font-bold bg-white text-[#444746] border">
              Join Mismatches <span aria-label="1 item" class="bg-[#f0f4f9] text-[#5f6368] text-[10px] px-1.5 py-0.5 rounded-full">1</span>
            </button>
            <button role="tab" id="tab-stitch_ambiguous" aria-selected="false" aria-controls="queue-panel" tabindex="-1" class="px-3.5 py-1.5 rounded-full text-xs font-bold bg-white text-[#444746] border">
              Continuation Unclear <span aria-label="0 items" class="bg-[#f0f4f9] text-[#5f6368] text-[10px] px-1.5 py-0.5 rounded-full">0</span>
            </button>
          </div>
          <p class="text-xs text-[#5f6368] mb-4">Every field waiting on a human decision, sorted worst-confidence first.</p>

          <section id="queue-panel" role="tabpanel" aria-labelledby="tab-low_confidence" class="bg-white border rounded-xl overflow-hidden">
            <div class="px-5 py-3 border-b flex items-center justify-between">
              <h2 class="text-sm font-semibold text-[#1f1f1f]">Queue &mdash; 14 items</h2>
            </div>
            <div class="divide-y">
              <div class="flex items-center gap-3 px-5 py-3 bg-[#e8f0fe]">
                <input type="checkbox" id="check-fact-1" aria-label="Select Survey Number for bulk edit" class="w-4 h-4" />
                <button aria-label="Review Survey Number, value 104/2, confidence 62%" aria-pressed="true" class="flex-1 text-left flex justify-between py-1">
                  <div>
                    <div class="text-sm font-medium text-[#1f1f1f]">Survey Number</div>
                    <div class="text-xs text-[#747775]">104/2</div>
                    <div class="text-[10px] text-[#9aa0a6]">Waqf Ledger 1974 - Basmath</div>
                  </div>
                  <span class="text-xs font-mono px-1.5 py-0.5 rounded border text-amber-700 bg-amber-50">0.620</span>
                </button>
              </div>
            </div>
          </section>
        </div>

        <aside aria-label="Review actions and tools" class="space-y-6">
          <div class="bg-white border rounded-xl p-5">
            <h2 class="text-sm font-bold text-[#1f1f1f] mb-3">Selected fact</h2>
            <div class="space-y-3">
              <div>
                <span class="text-xs text-[#747775] font-semibold uppercase">Field</span>
                <div class="text-sm text-[#1f1f1f]">Survey Number</div>
              </div>
              <div>
                <span class="text-xs text-[#747775] font-semibold uppercase">Value</span>
                <div class="text-sm text-[#1f1f1f]">104/2</div>
              </div>
              <div>
                <span class="text-xs text-[#747775] font-semibold uppercase">Confidence</span>
                <div><span class="inline-block text-sm font-mono px-2 py-0.5 rounded border text-amber-700 bg-amber-50">0.620</span></div>
              </div>
              <div class="flex flex-wrap gap-2 pt-2">
                <button type="button" class="px-3 py-1.5 text-xs font-semibold rounded-lg border bg-white text-[#1f1f1f]">View Source</button>
                <button type="button" class="px-3 py-1.5 text-xs font-semibold rounded-lg border bg-white text-[#1f1f1f]">Claim</button>
                <button type="button" class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-[#0d2e5c] text-white">Confirm</button>
                <button type="button" class="px-3 py-1.5 text-xs font-semibold rounded-lg border bg-white text-[#1f1f1f]">Mark Handwritten</button>
              </div>
            </div>
          </div>

          <div class="bg-white border-2 border-emerald-200 rounded-xl p-5">
            <h2 class="text-sm font-bold text-[#1f1f1f] mb-1">Confirm an entire folder at once</h2>
            <label for="bulk-folder-input" class="text-xs text-[#747775] block mb-1">Corpus Folder ID</label>
            <div class="flex gap-2 mb-2">
              <input type="text" id="bulk-folder-input" placeholder="Paste folder ID" class="flex-1 text-sm px-3 py-2 border rounded-lg" />
              <button type="button" class="px-3 py-1.5 text-xs font-semibold border rounded-lg bg-white">Browse</button>
            </div>
            <label for="bulk-threshold-input" class="text-xs text-[#747775] block mb-1">Confidence threshold</label>
            <input type="number" id="bulk-threshold-input" value="0.8" step="0.05" class="w-full text-sm px-3 py-2 border rounded-lg mb-2" />
            <label for="bulk-policy-input" class="text-xs text-[#747775] block mb-1">Policy version label</label>
            <input type="text" id="bulk-policy-input" placeholder="e.g. Q1-2026-audit" class="w-full text-sm px-3 py-2 border rounded-lg mb-3" />
            <button type="button" class="w-full py-2 text-xs font-bold rounded-lg bg-emerald-600 text-white">Confirm Folder</button>
          </div>
        </aside>
      </main>
    `
  },
  {
    name: 'Workbench — Continuation Unclear & Stitch Ambiguity Resolver',
    route: '/workbench?category=stitch_ambiguous',
    html: `
      <main class="max-w-6xl mx-auto px-6 py-6">
        <h1 class="text-lg font-bold text-[#1f1f1f] mb-4">Table Continuation Review</h1>
        <div class="bg-white border rounded-xl p-5">
          <h2 class="text-sm font-bold text-[#1f1f1f] mb-2">What's unclear</h2>
          <p class="text-sm text-[#1f1f1f] mb-4">Page 12 and Page 13 share similar table headers, but row sequence is ambiguous.</p>
          <div class="flex gap-3">
            <button type="button" aria-label="Resolve as same table continuing onto next page" class="px-4 py-2 text-xs font-bold rounded-lg bg-[#0d2e5c] text-white">Same table continues</button>
            <button type="button" aria-label="Resolve as side-by-side spread of one wider table" class="px-4 py-2 text-xs font-bold rounded-lg border bg-white text-[#1f1f1f]">Side-by-side spread</button>
            <button type="button" aria-label="Resolve as separate unrelated tables" class="px-4 py-2 text-xs font-bold rounded-lg border bg-white text-[#1f1f1f]">Unrelated</button>
          </div>
        </div>
      </main>
    `
  },
  {
    name: 'Workbench — View Source Region Modal Dialog (T53 Skew-Corrected)',
    route: '/workbench#view-source',
    html: `
      <div role="presentation" class="fixed inset-0 bg-black/50 flex items-center justify-center p-4">
        <div role="dialog" aria-modal="true" aria-labelledby="source-modal-title" class="w-full max-w-5xl bg-white border rounded-2xl p-6 shadow-2xl">
          <div class="flex items-center justify-between mb-4 border-b pb-3">
            <h2 id="source-modal-title" class="text-lg font-bold text-[#1f1f1f]">Source Document Region</h2>
            <button type="button" aria-label="Close source view dialog" class="p-2 rounded-full hover:bg-gray-100">
              <span aria-hidden="true">&times;</span>
            </button>
          </div>
          <div class="flex items-center justify-between gap-2 mb-3 pb-2 border-b">
            <div class="flex items-center gap-2">
              <span class="text-sm font-semibold text-[#1f1f1f]">Survey Number</span>
              <span class="text-xs font-mono px-2 py-0.5 rounded bg-[#f0f4f9] border text-[#5f6368]">87.5% confidence</span>
              <span class="text-xs px-2 py-0.5 rounded-full font-medium bg-amber-50 text-amber-800 border border-amber-200">
                Skew: -2.3&deg;
              </span>
            </div>
            <button type="button" aria-label="Switch to original raw scan view" class="text-xs px-2.5 py-1.5 rounded-lg bg-[#0d2e5c] text-white font-medium">
              Straightened (Deskewed)
            </button>
          </div>
          <div tabindex="0" aria-label="Document scan visual viewport" class="relative bg-gray-100 h-96 flex items-center justify-center border rounded-lg overflow-hidden">
            <p class="text-sm text-[#747775]">High-resolution scan preview with highlighted coordinates</p>
            <svg aria-hidden="true" class="absolute inset-0 w-full h-full pointer-events-none">
              <rect x="40" y="80" width="220" height="36" rx="3" class="fill-amber-400/30 stroke-amber-500 stroke-2"></rect>
            </svg>
          </div>
        </div>
      </div>
    `
  },
  {
    name: 'Drive & Document Explorer',
    route: '/drive',
    html: `
      <header class="h-16 px-6 border-b flex items-center justify-between bg-white">
        <h1 class="text-lg font-bold text-[#1f1f1f]">Documents Drive</h1>
        <div class="flex items-center gap-2">
          <label for="drive-search-input" class="sr-only">Search documents</label>
          <input type="search" id="drive-search-input" placeholder="Search files, numbers, keywords..." class="px-3 py-1.5 text-sm border rounded-lg" />
          <button type="button" class="px-3 py-1.5 text-xs font-bold rounded-lg bg-[#0d2e5c] text-white">Upload</button>
        </div>
      </header>
      <main class="grid grid-cols-[240px_1fr] h-[calc(100vh-64px)]">
        <nav aria-label="Drive folder tree" class="border-r p-4 bg-[#f8f9fa]">
          <h2 class="text-xs font-bold uppercase text-[#5f6368] mb-2">Corpus Folders</h2>
          <ul class="space-y-1 text-sm">
            <li><a href="#waqf" class="block px-2 py-1.5 rounded font-medium bg-[#e8f0fe] text-[#0d2e5c]">Waqf Records</a></li>
            <li><a href="#revenue" class="block px-2 py-1.5 rounded text-[#444746]">Revenue Records</a></li>
            <li><a href="#gazettes" class="block px-2 py-1.5 rounded text-[#444746]">Gazettes</a></li>
          </ul>
        </nav>
        <section aria-label="Folder contents" class="p-6">
          <h2 class="text-base font-bold text-[#1f1f1f] mb-4">Waqf Records (28 files)</h2>
          <table class="w-full text-sm border-collapse text-left">
            <caption class="sr-only">List of uploaded documents and processing status</caption>
            <thead>
              <tr class="border-b text-xs uppercase text-[#5f6368]">
                <th scope="col" class="py-2">Document</th>
                <th scope="col" class="py-2">Status</th>
                <th scope="col" class="py-2">Confidence</th>
                <th scope="col" class="py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr class="border-b">
                <td class="py-3 font-medium">1974_Basmath_Form_A.pdf</td>
                <td class="py-3"><span class="px-2 py-0.5 rounded text-xs bg-emerald-100 text-emerald-800">Verified</span></td>
                <td class="py-3 font-mono text-xs">0.962</td>
                <td class="py-3 text-right">
                  <button type="button" aria-label="View 1974_Basmath_Form_A.pdf" class="px-2 py-1 text-xs border rounded">View</button>
                </td>
              </tr>
            </tbody>
          </table>
        </section>
      </main>
    `
  },
  {
    name: 'Authentication — Login Screen',
    route: '/login',
    html: `
      <main class="min-h-screen flex items-center justify-center bg-[#f8f9fa] p-4">
        <div class="w-full max-w-md bg-white border rounded-2xl p-8 shadow-sm">
          <h1 class="text-2xl font-bold text-[#1f1f1f] mb-2">Sign In</h1>
          <p class="text-sm text-[#5f6368] mb-6">Enter your credentials to access the document repository.</p>
          <form action="#" method="POST" class="space-y-4">
            <div>
              <label for="login-email" class="block text-sm font-medium text-[#1f1f1f] mb-1">Email address</label>
              <input type="email" id="login-email" required class="w-full px-3 py-2 border rounded-lg text-sm" />
            </div>
            <div>
              <div class="flex justify-between items-center mb-1">
                <label for="login-password" class="block text-sm font-medium text-[#1f1f1f]">Password</label>
                <a href="/forgot-password" class="text-xs text-[#0d2e5c] hover:underline">Forgot password?</a>
              </div>
              <input type="password" id="login-password" required class="w-full px-3 py-2 border rounded-lg text-sm" />
            </div>
            <button type="submit" class="w-full py-2.5 rounded-lg bg-[#0d2e5c] text-white text-sm font-bold">Sign In</button>
          </form>
        </div>
      </main>
    `
  },
  {
    name: 'Completeness & Reconciliation Dashboard',
    route: '/completeness',
    html: `
      <main class="max-w-6xl mx-auto px-6 py-6 space-y-6">
        <h1 class="text-xl font-bold text-[#1f1f1f]">Completeness & Reconciliation</h1>
        <div class="grid grid-cols-3 gap-4">
          <div class="bg-white border rounded-xl p-4">
            <h2 class="text-xs font-semibold uppercase text-[#5f6368]">Extraction Rate</h2>
            <p class="text-2xl font-bold text-[#1f1f1f] mt-1">94.8%</p>
          </div>
          <div class="bg-white border rounded-xl p-4">
            <h2 class="text-xs font-semibold uppercase text-[#5f6368]">Human Verification</h2>
            <p class="text-2xl font-bold text-emerald-700 mt-1">82.3%</p>
          </div>
          <div class="bg-white border rounded-xl p-4">
            <h2 class="text-xs font-semibold uppercase text-[#5f6368]">Unresolved Ambiguities</h2>
            <p class="text-2xl font-bold text-amber-700 mt-1">5</p>
          </div>
        </div>
      </main>
    `
  },
  {
    name: 'Entity & Knowledge Graph Visualizer',
    route: '/entities',
    html: `
      <main class="max-w-6xl mx-auto px-6 py-6">
        <h1 class="text-xl font-bold text-[#1f1f1f] mb-4">Entity 360 & Relationship Graph</h1>
        <div class="bg-white border rounded-xl p-5 mb-6">
          <label for="entity-search" class="block text-xs font-semibold uppercase text-[#5f6368] mb-1">Search Entity or Survey ID</label>
          <div class="flex gap-2">
            <input type="search" id="entity-search" placeholder="e.g. Survey 104, Waqf Board Aurangabad" class="flex-1 px-3 py-2 border rounded-lg text-sm" />
            <button type="button" class="px-4 py-2 bg-[#0d2e5c] text-white text-xs font-bold rounded-lg">Search</button>
          </div>
        </div>
      </main>
    `
  },
  {
    name: 'Workbench & Drive — Marathi Localisation (T95 Devanagari Coverage)',
    route: '/workbench?lang=mr',
    lang: 'mr',
    html: `
      <header class="min-h-16 px-6 py-2 flex items-center justify-between border-b bg-white font-devanagari">
        <div class="flex items-center gap-4">
          <a href="/drive" class="flex items-center gap-2 text-sm text-[#444746] px-3 py-1.5 rounded-lg">
            <span>मागे</span>
          </a>
          <h1 class="text-lg font-bold text-[#1f1f1f]">पडताळणी कार्यक्षेत्र</h1>
        </div>
        <div class="flex items-center gap-1.5 text-xs text-[#5f6368]">
          <span>C स्वीकारा &middot; R मुक्त करा &middot; Enter पुष्टी करा</span>
        </div>
      </header>
      <main class="max-w-6xl mx-auto px-6 py-6 grid grid-cols-[1fr_360px] gap-6 font-devanagari">
        <div>
          <div role="tablist" aria-label="Adjudication queues" class="flex flex-wrap gap-2 mb-2">
            <button role="tab" id="tab-mr-needs-review" aria-selected="true" aria-controls="panel-mr-queue" tabindex="0" class="px-3.5 py-1.5 rounded-full text-xs font-bold bg-[#0d2e5c] text-white">
              पुनरावलोकन आवश्यक <span aria-label="१४ नोंदी" class="bg-white/20 text-[10px] px-1.5 py-0.5 rounded-full">१४</span>
            </button>
            <button role="tab" id="tab-mr-handwritten" aria-selected="false" aria-controls="panel-mr-queue" tabindex="-1" class="px-3.5 py-1.5 rounded-full text-xs font-bold bg-white text-[#444746] border">
              हस्तलिखित <span aria-label="३ नोंदी" class="bg-[#f0f4f9] text-[#5f6368] text-[10px] px-1.5 py-0.5 rounded-full">३</span>
            </button>
            <button role="tab" id="tab-mr-marginalia" aria-selected="false" aria-controls="panel-mr-queue" tabindex="-1" class="px-3.5 py-1.5 rounded-full text-xs font-bold bg-white text-[#444746] border">
              मार्जिन नोट्स (टीपा) <span aria-label="२ नोंदी" class="bg-[#f0f4f9] text-[#5f6368] text-[10px] px-1.5 py-0.5 rounded-full">२</span>
            </button>
          </div>
          <p class="text-xs text-[#5f6368] mb-4">प्रत्येक फील्ड जे मानवी निर्णयाची वाट पाहत आहे.</p>

          <section id="panel-mr-queue" role="tabpanel" aria-labelledby="tab-mr-needs-review" class="bg-white border rounded-xl overflow-hidden">
            <div class="px-5 py-3 border-b flex items-center justify-between">
              <h2 class="text-sm font-semibold text-[#1f1f1f]">रांग &mdash; १४ बाबी</h2>
            </div>
            <div class="divide-y">
              <div class="flex items-center gap-3 px-5 py-3 bg-[#e8f0fe]">
                <input type="checkbox" id="check-mr-fact-1" aria-label="एकत्रित संपादन करण्यासाठी सर्वे नंबर निवडा" class="w-4 h-4" />
                <button aria-label="पुनरावलोकन करा: सर्वे नंबर, मूल्य १०४/२, विश्वास ६२%" aria-pressed="true" class="flex-1 text-left flex justify-between py-1">
                  <div>
                    <div class="text-sm font-medium text-[#1f1f1f]">सर्वे नंबर</div>
                    <div class="text-xs text-[#747775]">१०४/२</div>
                  </div>
                  <span class="text-xs font-mono px-1.5 py-0.5 rounded border bg-amber-50 text-amber-700">0.62</span>
                </button>
              </div>
            </div>
          </section>
        </div>
        <div>
          <section aria-label="निवडलेले तथ्य" class="bg-white border rounded-xl p-4 space-y-3">
            <h2 class="text-sm font-bold text-[#1f1f1f]">निवडलेले तथ्य</h2>
            <div>
              <div class="text-xs uppercase text-[#747775] font-semibold">फील्ड</div>
              <div class="text-sm text-[#1f1f1f]">सर्वे नंबर</div>
            </div>
            <div>
              <div class="text-xs uppercase text-[#747775] font-semibold">काढलेले मूल्य</div>
              <div class="text-sm text-[#1f1f1f]">१०४/२</div>
            </div>
            <div class="flex gap-2 pt-2">
              <button type="button" class="px-3 py-1.5 rounded-lg bg-[#0d2e5c] text-white text-xs font-bold">पुष्टी करा (प्रमाणित)</button>
              <button type="button" class="px-3 py-1.5 rounded-lg border text-xs font-bold">स्वीकारा (Claim)</button>
            </div>
          </section>
        </div>
      </main>
    `
  }
];

async function runAudit() {
  console.log('='.repeat(70));
  console.log('  DMS Accessibility (a11y) Verification Suite — T96 / T95 (WCAG 2.1 AA / GIGW 3.0)');
  console.log('='.repeat(70));

  let totalViolations = 0;
  let totalPasses = 0;
  const failureReports = [];

  for (const fixture of FIXTURES) {
    const lang = fixture.lang || 'en';
    const fullHtml = `<!DOCTYPE html>
<html lang="${lang}">
<head>
  <meta charset="utf-8" />
  <title>${fixture.name} — DMS</title>
</head>
<body style="background-color: ${LIGHT_BG}; color: ${BRAND_TEXT}; font-family: sans-serif;">
  ${fixture.html}
</body>
</html>`;

    const dom = new JSDOM(fullHtml, {
      runScripts: 'dangerously',
      pretendToBeVisual: true
    });

    // Establish browser globals for axe-core execution in JSDOM
    global.window = dom.window;
    global.document = dom.window.document;
    global.Node = dom.window.Node;
    global.Element = dom.window.Element;
    global.HTMLElement = dom.window.HTMLElement;

    try {
      const results = await axe.run(dom.window.document.documentElement, {
        runOnly: {
          type: 'tag',
          values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice']
        },
        rules: {
          'color-contrast': { enabled: true }
        }
      });

      const violations = results.violations || [];
      const passes = results.passes || [];

      totalViolations += violations.length;
      totalPasses += passes.length;

      if (violations.length === 0) {
        console.log(`  [PASS] ${fixture.name.padEnd(55)} (${passes.length} checks passed)`);
      } else {
        console.log(`  [FAIL] ${fixture.name.padEnd(55)} (${violations.length} VIOLATIONS)`);
        failureReports.push({ fixture, violations });
      }
    } catch (err) {
      console.error(`  [ERROR] Execution failed on fixture "${fixture.name}":`, err.message);
      totalViolations += 1;
    }
  }

  console.log('-'.repeat(70));
  console.log(`Summary: ${FIXTURES.length} screens audited | ${totalPasses} checks passed | ${totalViolations} violations`);
  console.log('-'.repeat(70));

  if (failureReports.length > 0) {
    console.log('\nDetailed Violation Breakdown:');
    for (const { fixture, violations } of failureReports) {
      console.log(`\nScreen: ${fixture.name} (${fixture.route})`);
      for (const v of violations) {
        console.log(`  - [${v.impact?.toUpperCase() || 'MODERATE'}] ${v.id}: ${v.help}`);
        console.log(`    Help URL: ${v.helpUrl}`);
        for (const node of v.nodes) {
          console.log(`    Target: ${node.target.join(' ')}`);
          console.log(`    Fix: ${node.failureSummary}`);
        }
      }
    }
    console.log('\n❌ Accessibility audit FAILED. Please resolve the above WCAG 2.1 AA violations.\n');
    process.exit(1);
  }

  console.log('\n✅ All accessibility audits PASSED with 0 WCAG 2.1 AA violations.\n');
  process.exit(0);
}

runAudit();
