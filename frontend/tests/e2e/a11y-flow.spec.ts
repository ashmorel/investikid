import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

type PageSpec = {
  path: string;
  name: string;
  // Optional reason to skip; logged via test.skip with conformance-register reference.
  // Tracked in Task 12 conformance register.
  skipReason?: string;
};

const PAGES: PageSpec[] = [
  // OPEN-1 RESOLVED 2026-06-08: --color-primary retuned to brand-600 (#2563eb,
  // white ≈ 5.17:1, passes WCAG 1.4.3) — /login + /forgot-password no longer skipped.
  { path: '/login', name: 'login' },
  { path: '/signup', name: 'signup' },
  { path: '/privacy', name: 'privacy' },
  { path: '/forgot-password', name: 'forgot-password' },
];

for (const { path, name, skipReason } of PAGES) {
  test(`a11y: ${name} has no serious/critical axe violations`, async ({ page }) => {
    test.skip(Boolean(skipReason), skipReason ?? '');
    await page.goto(path);
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag22aa'])
      .analyze();
    const blocking = results.violations.filter(
      (v) => v.impact === 'serious' || v.impact === 'critical',
    );
    expect(blocking, JSON.stringify(blocking, null, 2)).toEqual([]);
  });
}
