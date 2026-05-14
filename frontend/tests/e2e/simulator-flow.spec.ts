import { test, expect, type Page } from '@playwright/test';
import { registerMinor, readLatestEmailToken, uniq } from './helpers';

async function loginAsChild(page: Page, email: string) {
  await page.goto('/login');
  await page.getByLabel(/email/i).fill(email);
  await page.getByLabel(/password/i).fill('SecurePass123!');
  await page.getByRole('button', { name: /log in/i }).click();
  await page.waitForURL('/home');
}

async function approveConsent(page: Page, parentEmail: string) {
  const token = readLatestEmailToken(parentEmail, 'consent_request');
  await page.goto(`/consent/verify?token=${token}`);
  await page.getByRole('button', { name: /approve/i }).click();
  await page.waitForURL(/\/consent\/verify/);
}

test('simulator: browse market, buy stock, verify portfolio', async ({ page }) => {
  const id = uniq('sim');
  const childEmail = `${id}@test.example`;
  const parentEmail = `parent-${id}@test.example`;

  // Register + approve
  await registerMinor({ email: childEmail, username: id, parentEmail });
  await approveConsent(page, parentEmail);

  // Log in as child
  await loginAsChild(page, childEmail);

  // Navigate to simulator
  await page.getByRole('link', { name: /simulator/i }).click();
  await page.waitForURL('/simulator');
  await expect(page.getByText(/practice mode/i)).toBeVisible();
  await expect(page.getByText(/\$10,000\.00 USD/)).toBeVisible();
  await expect(page.getByText(/haven't bought any stocks/i)).toBeVisible();

  // Browse stocks
  await page.getByRole('link', { name: /browse stocks/i }).click();
  await page.waitForURL('/simulator/market');
  await expect(page.getByText('Apple Inc.')).toBeVisible();

  // Click AAPL
  await page.getByText('Apple Inc.').click();
  await page.waitForURL('/simulator/stock/NASDAQ/AAPL');
  await expect(page.getByText(/\$185\.42 USD/)).toBeVisible();

  // Buy 2 shares — step 1
  await page.getByLabel(/number of shares/i).fill('2');
  await expect(page.getByText(/2 shares × \$185\.42 USD/)).toBeVisible();
  await page.getByRole('button', { name: /review trade/i }).click();

  // Step 2 — confirm
  await expect(page.getByText(/Buy 2 shares of AAPL/)).toBeVisible();
  await page.getByRole('button', { name: /confirm/i }).click();

  // Should redirect to portfolio with updated holdings
  await page.waitForURL('/simulator');
  await expect(page.getByText('AAPL')).toBeVisible();
  // Cash should be reduced: 10000 - (2 * 185.42) = 9629.16
  await expect(page.getByText(/\$9,629\.16 USD/)).toBeVisible();
});
