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

test('stats: new user sees XP summary, badges, challenges, leaderboard', async ({ page }) => {
  const id = uniq('stats');
  const childEmail = `${id}@test.example`;
  const parentEmail = `parent-${id}@test.example`;

  // Register + approve
  await registerMinor({ email: childEmail, username: id, parentEmail });
  await approveConsent(page, parentEmail);

  // Log in as child
  await loginAsChild(page, childEmail);

  // Navigate to Stats
  await page.getByRole('link', { name: /stats/i }).click();
  await page.waitForURL('/stats');

  // XP summary — new user: Level 1, 0 XP
  await expect(page.getByText(/Level 1/)).toBeVisible();
  await expect(page.getByText('0')).toBeVisible();

  // Badges section — all 5 should be visible (all locked for new user)
  await expect(page.getByRole('heading', { name: /badges/i })).toBeVisible();
  await expect(page.getByText('First Step')).toBeVisible();
  await expect(page.getByText('Quiz Ace')).toBeVisible();
  await expect(page.getByText('Streak Master')).toBeVisible();
  await expect(page.getByText('First Trade')).toBeVisible();
  await expect(page.getByText('Century Club')).toBeVisible();

  // Challenges section visible
  await expect(page.getByRole('heading', { name: /weekly challenges/i })).toBeVisible();

  // Leaderboard section visible
  await expect(page.getByRole('heading', { name: /weekly leaderboard/i })).toBeVisible();
});
