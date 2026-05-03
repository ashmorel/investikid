import { test, expect, type Page } from '@playwright/test';
import { uniq } from './helpers';

async function registerOverThresholdUS(page: Page, username: string) {
  await page.goto('/signup');
  await page.getByLabel('Date of birth').fill('2010-01-01');
  await page.getByLabel('Country').selectOption('US');
  await page.getByRole('button', { name: 'Next' }).click();
  await page.getByLabel(/^Email$/).fill(`${username}@example.com`);
  await page.getByLabel('Username').fill(username);
  await page.getByLabel(/Password/).fill('SecurePass123!');
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page).toHaveURL(/\/home$/);
}

test('happy: complete a card lesson end-to-end', async ({ page }) => {
  await registerOverThresholdUS(page, uniq('kid'));

  // From Home, click Resume / Start learning
  await page.getByRole('link', { name: /Resume|Start learning/ }).click();

  // Should land on a lesson page
  await expect(page).toHaveURL(/\/lessons\/[^/]+\/[^/]+/);

  // Card lessons have a "Got it" button. If first seeded lesson is card-type, click it.
  // Seed file ships "What is a Stock?" (card) as the first module's first lesson.
  await page.getByRole('button', { name: /Got it/ }).click();

  // CompletionPanel
  await expect(page.getByText(/Great work/)).toBeVisible();
  await expect(page.getByText(/\+10 XP/)).toBeVisible();

  // Next lesson link should advance
  await page.getByRole('link', { name: /Next lesson/ }).click();
  await expect(page).toHaveURL(/\/lessons\/[^/]+\/[^/]+/);
});

test('quiz wrong then revisit shows already-completed panel', async ({ page }) => {
  await registerOverThresholdUS(page, uniq('kid'));
  // Navigate to /lessons via the Home link (page.goto('/lessons') is proxied to backend)
  await page.getByRole('link', { name: /Browse all modules/ }).click();
  await expect(page).toHaveURL(/\/lessons$/);

  // Find the Stocks module (seed: "What is a Stock?")
  await page.getByRole('link', { name: /What is a Stock\?/i }).click();

  // The 3rd lesson in that seeded module is a quiz: "If you own one stock…"
  // Use the lesson row that has the Quiz badge.
  const quizRow = page.getByRole('link', { name: /Quiz/i }).first();
  await quizRow.click();

  // Pick a wrong answer (the seeded quiz: choices[0] = "1/100", correct is index 1)
  await page.getByRole('radio', { name: '1/100' }).click();
  await page.getByRole('button', { name: /Submit/ }).click();
  await expect(page.getByText(/Not quite/i)).toBeVisible();
  await page.getByRole('button', { name: /Continue/ }).click();
  // CompletionPanel — XP awarded even on wrong answer (backend awards xp_reward regardless)
  await expect(page.getByText(/Great work/)).toBeVisible();

  // Revisit the same quiz lesson
  await page.goBack(); // back to module page
  await quizRow.click();
  // Now the lesson is already completed; user can re-open and re-submit, but the
  // POST returns already_completed: true and 0 XP. Submit a (correct) answer this time.
  await page.getByRole('radio', { name: '1/1,000,000' }).click();
  await page.getByRole('button', { name: /Submit/ }).click();
  await page.getByRole('button', { name: /Continue/ }).click();
  await expect(page.getByText(/already done this one/i)).toBeVisible();
});

test('locked premium module: card click shows toast, URL unchanged', async ({ page }) => {
  // Use a pre-seeded GB user (e2e-gb-kid@example.com / SecurePass123!) to avoid
  // consuming the 5/minute rate limit on /auth/register during sequential suite runs.
  await page.goto('/login');
  await page.getByLabel('Email').fill('e2e-gb-kid@example.com');
  await page.getByLabel('Password').fill('SecurePass123!');
  await page.getByRole('button', { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/home$/);

  // Navigate to /lessons via the Home link (page.goto('/lessons') is proxied to backend)
  await page.getByRole('link', { name: /Browse all modules/ }).click();
  await expect(page).toHaveURL(/\/lessons$/);
  const lockedCard = page.getByRole('button', { name: /E2E Premium Module \(locked\)/i });
  await expect(lockedCard).toBeVisible();
  await lockedCard.click();
  await expect(page.getByText(/Premium required/i)).toBeVisible();
  await expect(page).toHaveURL(/\/lessons$/);
});
