import { test, expect } from '@playwright/test';

test('unauthenticated child route redirects to login', async ({ page }) => {
  await page.goto('/home');
  await expect(page).toHaveURL(/\/login$/);
});

test('unauthenticated parent route redirects to parent login', async ({ page }) => {
  await page.goto('/parent');
  await expect(page).toHaveURL(/\/parent\/login$/);
});

test('404: unknown route shows not found', async ({ page }) => {
  await page.goto('/this-page-does-not-exist');
  await expect(page.getByText(/Not found/i)).toBeVisible();
});
