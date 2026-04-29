import { test, expect } from '@playwright/test';
import { registerMinor, readLatestEmailToken, uniq } from './helpers';

test('happy path: consent → magic link → freeze → erase → logout', async ({ page }) => {
  const childUser = uniq('kid');
  const childEmail = `${childUser}@example.com`;
  const parentEmail = `${uniq('parent')}@example.com`;

  await registerMinor({ email: childEmail, username: childUser, parentEmail });

  // 1. Consent verify + approve
  const consentToken = readLatestEmailToken(parentEmail, 'consent_request');
  await page.goto(`/consent/verify?token=${encodeURIComponent(consentToken)}`);
  await expect(page.getByText(childUser)).toBeVisible();
  await page.getByRole('button', { name: 'Approve' }).click();
  await expect(page.getByText(/Account approved/i)).toBeVisible();

  // 2. Parent login → magic
  await page.goto('/parent/login');
  await page.getByLabel('Email').fill(parentEmail);
  await page.getByRole('button', { name: /Send sign-in link/i }).click();
  await expect(page.getByText(/Check your inbox/i)).toBeVisible();

  // 3. Magic callback → dashboard
  const magicToken = readLatestEmailToken(parentEmail, 'parent_magic_link');
  await page.goto(`/parent/auth/callback?token=${encodeURIComponent(magicToken)}`);
  await expect(page).toHaveURL(/\/parent$/);
  await expect(page.getByRole('heading', { name: /Parent dashboard/i })).toBeVisible();

  // 4. Freeze
  await expect(page.getByText(childUser)).toBeVisible();
  const freezeSwitch = page.getByLabel(/Freeze account/i);
  await freezeSwitch.click();
  await expect(page.getByText('Frozen')).toBeVisible();

  // 5. Erase
  await page.getByRole('button', { name: /Delete account…/i }).click();
  await page.getByLabel(/Type child username/i).fill(childUser);
  await page.getByRole('button', { name: /^Delete account$/i }).click();
  await expect(page.getByText('Deleted')).toBeVisible();

  // 6. Logout
  await page.getByRole('button', { name: /Log out/i }).click();
  await expect(page).toHaveURL(/\/parent\/login$/);
});

test('replay attack on consent token shows 410', async ({ page }) => {
  const childUser = uniq('kid');
  const childEmail = `${childUser}@example.com`;
  const parentEmail = `${uniq('parent')}@example.com`;
  await registerMinor({ email: childEmail, username: childUser, parentEmail });
  const consentToken = readLatestEmailToken(parentEmail, 'consent_request');

  await page.goto(`/consent/verify?token=${encodeURIComponent(consentToken)}`);
  await page.getByRole('button', { name: 'Approve' }).click();
  await expect(page.getByText(/Account approved/i)).toBeVisible();

  // Visit verify with same token again — should 410.
  await page.goto(`/consent/verify?token=${encodeURIComponent(consentToken)}`);
  await expect(page.getByText(/Link unavailable/i)).toBeVisible();
});

test('invalid magic token shows error and link to relogin', async ({ page }) => {
  await page.goto('/parent/auth/callback?token=not-a-jwt');
  await expect(page.getByText(/Sign-in link expired/i)).toBeVisible();
  await page.getByRole('link', { name: /Request a new link/i }).click();
  await expect(page).toHaveURL(/\/parent\/login$/);
});
