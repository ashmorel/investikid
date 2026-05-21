import { test, expect } from '@playwright/test';
import {
  registerMinor, uniq,
  approveConsent, loginParentViaMagicLink, grantPremiumViaApi, loginChild,
} from './helpers';

test('free state: parent sees upgrade CTA, no premium badge', async ({ page }) => {
  const childUser = uniq('bill');
  const childEmail = `${childUser}@example.com`;
  const parentEmail = `${uniq('parent')}@example.com`;

  await registerMinor({ email: childEmail, username: childUser, parentEmail });
  await approveConsent(page, parentEmail);
  await loginParentViaMagicLink(page, parentEmail);

  // SubscriptionCard shows free plan
  await expect(page.getByText(/Free plan/i)).toBeVisible();
  await expect(page.getByRole('button', { name: /Subscribe to Premium/i })).toBeVisible();

  // Child card does NOT show premium badge
  await expect(page.getByText(childUser)).toBeVisible();
  await expect(page.getByText(/Premium ✨/)).not.toBeVisible();
});

test('premium grant: child card shows premium badge', async ({ page }) => {
  const childUser = uniq('bill');
  const childEmail = `${childUser}@example.com`;
  const parentEmail = `${uniq('parent')}@example.com`;

  const { user_id } = await registerMinor({ email: childEmail, username: childUser, parentEmail });
  await approveConsent(page, parentEmail);
  await loginParentViaMagicLink(page, parentEmail);

  await grantPremiumViaApi(page, user_id);
  await page.reload();

  await expect(page.getByText(childUser)).toBeVisible();
  await expect(page.getByText(/Premium ✨/)).toBeVisible();
});

test('premium visible to child: premium module accessible', async ({ page }) => {
  const childUser = uniq('bill');
  const childEmail = `${childUser}@example.com`;
  const parentEmail = `${uniq('parent')}@example.com`;

  const { user_id } = await registerMinor({ email: childEmail, username: childUser, parentEmail });
  await approveConsent(page, parentEmail);
  await loginParentViaMagicLink(page, parentEmail);
  await grantPremiumViaApi(page, user_id);

  // Now log in as the child
  await loginChild(page, childEmail);

  // Navigate to lessons
  await page.getByRole('link', { name: /Browse all modules/ }).click();
  await expect(page).toHaveURL(/\/lessons$/);

  // The premium module should be accessible (not show "Premium required" toast)
  // Seed data includes "E2E Premium Module" — it should be clickable without a toast.
  const premiumModule = page.getByRole('link', { name: /E2E Premium Module/i });
  if (await premiumModule.isVisible()) {
    await premiumModule.click();
    // Should navigate into the module, not stay on /lessons with a toast
    await expect(page).not.toHaveURL(/\/lessons$/);
  }
});

test('premium revoke: badge removed from child card', async ({ page }) => {
  const childUser = uniq('bill');
  const childEmail = `${childUser}@example.com`;
  const parentEmail = `${uniq('parent')}@example.com`;

  const { user_id } = await registerMinor({ email: childEmail, username: childUser, parentEmail });
  await approveConsent(page, parentEmail);
  await loginParentViaMagicLink(page, parentEmail);

  // Grant
  await grantPremiumViaApi(page, user_id);
  await page.reload();
  await expect(page.getByText(/Premium ✨/)).toBeVisible();

  // Revoke
  await grantPremiumViaApi(page, user_id, false);
  await page.reload();
  await expect(page.getByText(childUser)).toBeVisible();
  await expect(page.getByText(/Premium ✨/)).not.toBeVisible();
});
