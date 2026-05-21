import { test, expect } from '@playwright/test';
import {
  uniq, readLatestEmailToken, registerOverThresholdUS,
} from './helpers';

test('wrong password shows error', async ({ page }) => {
  const username = uniq('auth');
  await registerOverThresholdUS(page, username);

  // Log out by clearing cookies, then try wrong password
  await page.context().clearCookies();
  await page.goto('/login');
  await page.getByLabel(/email/i).fill(`${username}@example.com`);
  await page.getByLabel(/password/i).fill('WrongPassword999!');
  await page.getByRole('button', { name: /log in/i }).click();

  await expect(page.getByText(/Email or password incorrect/i)).toBeVisible();
});

test('nonexistent user shows error', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel(/email/i).fill('nobody-ever@example.com');
  await page.getByLabel(/password/i).fill('SomePassword123!');
  await page.getByRole('button', { name: /log in/i }).click();

  await expect(page.getByText(/Email or password incorrect/i)).toBeVisible();
});

test('forgot password → reset → login with new password', async ({ page }) => {
  const username = uniq('auth');
  const email = `${username}@example.com`;
  await registerOverThresholdUS(page, username);
  await page.context().clearCookies();

  // Forgot password
  await page.goto('/forgot-password');
  await page.getByLabel(/email or username/i).fill(email);
  await page.getByRole('button', { name: /send/i }).click();
  await expect(page.getByText(/Check your email/i)).toBeVisible();

  // Read reset token from DB
  const resetToken = readLatestEmailToken(email, 'password_reset');

  // Reset password
  await page.goto(`/reset-password?token=${encodeURIComponent(resetToken)}`);
  await expect(page.getByText(/Reset your password/i)).toBeVisible();

  const newPassword = 'BrandNewPass456!';
  await page.getByLabel('New password').fill(newPassword);
  await page.getByLabel('Confirm new password').fill(newPassword);
  await page.getByRole('button', { name: /reset password/i }).click();

  await expect(page.getByText(/Password updated/i)).toBeVisible();

  // Login with new password
  await page.getByRole('link', { name: /Sign in/i }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel(/email/i).fill(email);
  await page.getByLabel(/password/i).fill(newPassword);
  await page.getByRole('button', { name: /log in/i }).click();
  await expect(page).toHaveURL(/\/home$/);
});

test('verify email: valid token confirms email', async ({ page }) => {
  const username = uniq('auth');
  const email = `${username}@example.com`;
  await registerOverThresholdUS(page, username);

  // Registration triggers a verify_email sent_email row
  const verifyToken = readLatestEmailToken(email, 'verify_email');

  await page.goto(`/verify-email?token=${encodeURIComponent(verifyToken)}`);
  await expect(page.getByText(/Email confirmed/i)).toBeVisible();
});
