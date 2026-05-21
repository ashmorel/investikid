import { execFileSync } from 'node:child_process';
import type { Page } from '@playwright/test';

const BACKEND = 'http://localhost:8000';

export async function registerMinor(opts: {
  email: string; username: string; parentEmail: string;
}) {
  const res = await fetch(`${BACKEND}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: opts.email,
      username: opts.username,
      password: 'SecurePass123!',
      dob: '2015-01-01',
      country_code: 'GB',
      currency_code: 'GBP',
      parent_email: opts.parentEmail,
    }),
  });
  if (!res.ok) throw new Error(`register failed: ${res.status}`);
  return (await res.json()) as { user_id: string };
}

/**
 * Reads the body of the latest sent email matching template+to.
 * Uses execFileSync with psql via stdin — no shell spawning, values passed via
 * \set + :'var' quoting (standard psql interpolation, no string injection into
 * the SQL command line argument).
 *
 * Note: psql :'var' quoting requires passing the \set commands via stdin;
 * the -v flag on the command line does not support the :'var' syntax in all
 * Homebrew psql builds, so we use stdin + \set instead.
 */
export function readLatestEmailToken(toEmail: string, template: string): string {
  // Escape any single quotes in the values (SQL-style doubling).
  const emEsc = toEmail.replace(/'/g, "''");
  const tplEsc = template.replace(/'/g, "''");
  const input =
    `\\set em '${emEsc}'\n` +
    `\\set tpl '${tplEsc}'\n` +
    "SELECT body FROM sent_emails " +
    "WHERE to_email = :'em' AND template = :'tpl' " +
    "ORDER BY sent_at DESC LIMIT 1;\n";
  const out = execFileSync(
    'psql',
    ['-d', 'investedb', '-At'],
    { encoding: 'utf-8', input },
  );
  const match = out.match(/token=([^\s)]+)/);
  if (!match) throw new Error(`no token in latest ${template} email to ${toEmail}`);
  return match[1];
}

export function uniq(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
}

export async function loginChild(page: Page, email: string, password = 'SecurePass123!') {
  await page.goto('/login');
  await page.getByLabel(/email/i).fill(email);
  await page.getByLabel(/password/i).fill(password);
  await page.getByRole('button', { name: /log in/i }).click();
  await page.waitForURL('/home');
}

export async function registerOverThresholdUS(page: Page, username: string) {
  await page.goto('/signup');
  await page.getByLabel('Date of birth').fill('2010-01-01');
  await page.getByLabel('Country').selectOption('US');
  await page.getByRole('button', { name: 'Next' }).click();
  await page.getByLabel(/^Email$/).fill(`${username}@example.com`);
  await page.getByLabel('Username').fill(username);
  await page.getByLabel(/Password/).fill('SecurePass123!');
  await page.getByRole('button', { name: 'Create account' }).click();
  await page.waitForURL(/\/home$/);
}

export async function approveConsent(page: Page, parentEmail: string) {
  const token = readLatestEmailToken(parentEmail, 'consent_request');
  await page.goto(`/consent/verify?token=${encodeURIComponent(token)}`);
  await page.getByRole('button', { name: /approve/i }).click();
  await page.waitForURL(/\/consent\/verify/);
}

export async function loginParentViaMagicLink(page: Page, parentEmail: string) {
  await page.goto('/parent/login');
  await page.getByLabel('Email').fill(parentEmail);
  await page.getByRole('button', { name: /Send sign-in link/i }).click();
  const magicToken = readLatestEmailToken(parentEmail, 'parent_magic_link');
  await page.goto(`/parent/auth/callback?token=${encodeURIComponent(magicToken)}`);
  await page.waitForURL(/\/parent$/);
}

export async function grantPremiumViaApi(page: Page, childUserId: string, premium = true) {
  const cookies = await page.context().cookies();
  const cookieHeader = cookies.map((c) => `${c.name}=${c.value}`).join('; ');
  const csrfCookie = cookies.find((c) => c.name === 'csrf_token');
  if (!csrfCookie) throw new Error('No csrf_token cookie found — is the parent logged in?');

  const res = await fetch(`${BACKEND}/parent/children/${childUserId}/premium`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Cookie': cookieHeader,
      'X-CSRF-Token': csrfCookie.value,
    },
    body: JSON.stringify({ premium }),
  });
  if (!res.ok) throw new Error(`grantPremiumViaApi failed: ${res.status}`);
}
