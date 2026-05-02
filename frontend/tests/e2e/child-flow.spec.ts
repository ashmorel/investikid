import { test, expect } from '@playwright/test';
import { readLatestEmailToken, uniq } from './helpers';

test('happy: over-threshold US 14 → /home', async ({ page }) => {
  const username = uniq('kid');
  const email = `${username}@example.com`;

  await page.goto('/signup');

  // Step 1
  await page.getByLabel('Date of birth').fill('2012-01-01');
  await page.getByLabel('Country').selectOption('US');
  await expect(page.getByText(/you can set up your own account/i)).toBeVisible();
  await page.getByRole('button', { name: 'Next' }).click();

  // Step 2
  await page.getByLabel(/^Email$/).fill(email);
  await page.getByLabel('Username').fill(username);
  await page.getByLabel(/Password/).fill('SecurePass123!');
  await page.getByRole('button', { name: 'Create account' }).click();

  await expect(page).toHaveURL(/\/home$/);
  await expect(
    page.getByRole('heading', { name: new RegExp(`Welcome, ${username}`, 'i') }),
  ).toBeVisible();
});

test('happy: under-threshold GB 11 → pending → approve → /home', async ({ page }) => {
  const username = uniq('kid');
  const email = `${username}@example.com`;
  const parentEmail = `${uniq('parent')}@example.com`;

  await page.goto('/signup');

  await page.getByLabel('Date of birth').fill('2015-01-01');
  await page.getByLabel('Country').selectOption('GB');
  await expect(page.getByText(/parent's email will be required/i)).toBeVisible();
  await page.getByRole('button', { name: 'Next' }).click();

  await page.getByLabel(/^Email$/).fill(email);
  await page.getByLabel('Username').fill(username);
  await page.getByLabel(/Password/).fill('SecurePass123!');
  await page.getByLabel(/Parent email/).fill(parentEmail);
  await page.getByRole('button', { name: 'Create account' }).click();

  await expect(page).toHaveURL(/\/pending-consent/);

  // First recheck: still pending
  await page.getByRole('button', { name: /I've been approved/i }).click();
  await page.getByLabel(/Enter your password/).fill('SecurePass123!');
  await page.getByRole('button', { name: /^Sign in$/ }).click();
  await expect(page.getByText(/not approved yet/i)).toBeVisible();

  // Parent approves via consent verify
  const consentToken = readLatestEmailToken(parentEmail, 'consent_request');
  await page.goto(`/consent/verify?token=${encodeURIComponent(consentToken)}`);
  await page.getByRole('button', { name: 'Approve' }).click();
  await expect(page.getByText(/Account approved/i)).toBeVisible();

  // Back to pending-consent, recheck again
  await page.goto(`/pending-consent?email=${encodeURIComponent(email)}`);
  await page.getByRole('button', { name: /I've been approved/i }).click();
  await page.getByLabel(/Enter your password/).fill('SecurePass123!');
  await page.getByRole('button', { name: /^Sign in$/ }).click();
  await expect(page).toHaveURL(/\/home$/);
});

test('unhappy: invalid login shows generic error', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill('nobody@example.com');
  await page.getByLabel('Password').fill('wrongpassword');
  await page.getByRole('button', { name: /sign in/i }).click();
  await expect(page.getByText(/Email or password incorrect/i)).toBeVisible();
});
