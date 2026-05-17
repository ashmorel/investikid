# Invest-Ed Operations Runbook: Account Purge

This document describes the operational procedure for running the account purge job, which permanently overwrites personal data for accounts that have been soft-deleted for longer than the configured retention period.

---

## Purpose

When a user requests account deletion (or an account is administratively closed), Invest-Ed performs a soft-delete: the account is made inactive immediately, but personal data remains in the database for up to `data_retention_days` days (default: 30 days). This window allows for accidental-deletion recovery and gives time for any in-flight legal holds to be applied before data is destroyed.

After the retention window has elapsed, the account is eligible for hard purge. The purge operation overwrites all personally identifiable fields with anonymised values. It does not delete the database row — the row is retained for referential integrity and audit purposes, but it contains no information that can identify the former account holder.

Fields overwritten on purge: `email`, `username`, `password_hash`, `parent_email`, `topic_path`, `currency_code`, `email_verified_at`.

Fields retained after purge (non-identifying): `id` (opaque UUID), `dob`, `country_code`, `purged_at`, `deleted_at`, `deletion_requested_at`, `policy_version_accepted`, `policy_accepted_at`, `parent_consent_given_at`.

---

## Purge Command

```bash
cd invest-ed/backend && python -m app.cli purge-accounts
```

Run this command from the `invest-ed/backend` directory. The application must be able to connect to the production database and read from the environment configuration (`.env` or environment variables).

---

## Scheduling

The purge command should be run daily via cron. The recommended schedule is 03:15 local server time (off-peak):

```
15 3 * * * cd /path/to/invest-ed/backend && python -m app.cli purge-accounts >> /var/log/invest-ed/purge.log 2>&1
```

Replace `/path/to/invest-ed/backend` with the absolute path to the backend directory on your server. Redirect output to a persistent log file so that each run is auditable.

---

## Behaviour

- The command identifies all accounts where `deleted_at IS NOT NULL` and `purged_at IS NULL` and `deleted_at < midnight(today) - data_retention_days`.
- For each eligible account, it overwrites the PII fields listed above and sets `purged_at` to the current UTC timestamp.
- The operation is **idempotent**: running the command multiple times against the same dataset produces the same result. Accounts already marked `purged_at IS NOT NULL` are skipped entirely. It is safe to re-run after a partial failure.
- The command does not delete rows. After a successful run, `SELECT * FROM users WHERE purged_at IS NOT NULL` will show overwritten rows with opaque values in the PII columns.

---

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success — all eligible accounts processed without error |
| `2` | Bad arguments — invalid command-line options passed to the CLI |

Any other non-zero exit code indicates an unexpected error (e.g. database connection failure). Check the log output and re-run after resolving the underlying issue.

---

## Verification

After a successful purge run, the following SQL query should return zero rows. Any non-zero result indicates accounts that are overdue for purging but were not processed, which requires investigation.

```sql
SELECT count(*)
FROM users
WHERE deleted_at IS NOT NULL
  AND purged_at IS NULL
  AND deleted_at < now() - interval '30 days';
```

Note: replace `30 days` with the value of `data_retention_days` from your environment configuration if it has been changed from the default.

If this query returns a non-zero count after a purge run that exited with code 0, check for:

1. Database connection issues during the run — look for errors in the purge log.
2. Clock skew between the application server and the database server — the cutoff calculation uses the application clock.
3. Rows where `deleted_at` is set to a future date — this would indicate a data integrity issue in the deletion flow.

---

## Prerequisites

- The command must be run in an environment where the application's Python virtual environment is active (or where the `app` package is importable from the Python path).
- The environment must provide valid database credentials via the configured `.env` file or environment variables (`DATABASE_URL`, `SECRET_KEY`, etc. as defined in `app/core/config.py`).
- The database user must have `UPDATE` permission on the `users` table.
- No special file-system permissions are required beyond the ability to read the `.env` file and write to the log output target.

---

## Frequency and Audit

This command must be run at least once per day to satisfy the commitment that personal data is purged within `data_retention_days + 1` days of the soft-delete event. Each run should be logged with its timestamp and exit code. Logs should be retained for at least 12 months for audit purposes.

If the cron job fails to run for any reason (server downtime, misconfiguration), the accounts that became eligible during the outage will be processed on the next successful run, because the command processes all eligible accounts regardless of when they became eligible. No data is permanently missed as long as the job is eventually restored.
