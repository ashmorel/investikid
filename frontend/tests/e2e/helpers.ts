import { execFileSync } from 'node:child_process';

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
