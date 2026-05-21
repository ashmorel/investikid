# CI Security Gate — invest-ed

## Overview

The `security` job in `.github/workflows/ci.yml` runs three static/dependency scanners on every push and pull-request targeting `main`. It is a peer job of `frontend` and `backend` (all three run in parallel).

---

## What the gate runs

### 1. Bandit — backend SAST

- **Command:** `bandit -r app -lll -iii`
- **Working directory:** `invest-ed/backend`
- **Scope:** the entire `app/` package (recursive)
- **Flags:**
  - `-lll` — report only **High** severity issues (three `l` flags = severity level HIGH)
  - `-iii` — report only **High** confidence issues (three `i` flags = confidence level HIGH)
- **Effect:** the step exits non-zero (failing the build) only when at least one High-severity / High-confidence finding exists. Low and Medium findings (which require fewer flags) are **not** reported by this invocation — they are visible in the manual audit register (`audit-2026-05.md`) and do not block CI.

### 2. pip-audit — backend dependency CVEs

- **Command:** `pip-audit -r requirements.txt`
- **Working directory:** `invest-ed/backend`
- **Scope:** all packages listed in `invest-ed/backend/requirements.txt` (including dev/test section)
- **Effect:** exits non-zero and fails the build if any package has a known published CVE or GHSA advisory. There is no severity floor — any known vulnerability blocks the build.

### 3. npm audit — frontend dependency CVEs

- **Command:** `npm audit --audit-level=high`
- **Working directory:** `invest-ed/frontend`
- **Scope:** the full `node_modules` dependency tree resolved from `package-lock.json`
- **Effect:** exits non-zero and fails the build if any dependency has a **High** or **Critical** severity advisory. Moderate/Low advisories appear in the audit report in the job log but do not cause a non-zero exit.

---

## Fail policy

| Tool | Build fails on | Non-blocking (logged only) |
|------|---------------|---------------------------|
| bandit | High severity AND High confidence | Low/Medium severity; lower confidence |
| pip-audit | Any known CVE/GHSA (all severities) | — |
| npm audit | High or Critical | Moderate, Low |

The gate is intentionally strict on High/Critical and permissive on Medium/Low for the following reason: High/Critical findings represent directly exploitable paths that must be fixed before merge. Medium/Low findings are recorded in the audit register and addressed on a prioritised schedule without blocking all PRs immediately.

---

## Triaging a gate failure

1. **Read the tool output** in the failing CI step log. Each tool prints the specific finding, affected package/file, and (for bandit) the CWE and rule ID.

2. **For a bandit failure:**
   - Locate the file and line number printed by bandit.
   - Determine whether the finding is a true positive or a false positive.
   - **True positive:** fix the code before merging.
   - **False positive:** add an inline suppression — see "Justified allowlist entries" below.

3. **For a pip-audit failure:**
   - Note the package name, installed version, and advisory ID (GHSA-… or CVE-…).
   - Check whether a non-vulnerable version is available: `pip index versions <package>` or the advisory page.
   - **Upgrade available:** update `requirements.txt` to the fixed version and re-run `pip-audit -r requirements.txt` locally to confirm clean.
   - **No upgrade available:** see "Justified allowlist entries" below.

4. **For an npm audit failure:**
   - Run `npm audit` locally (no `--audit-level` flag) to see full details.
   - Check `npm audit fix --dry-run` to see what an automatic fix would change.
   - If safe, apply `npm audit fix` (or manually update `package.json`/`package-lock.json`).
   - If the vulnerable package is a transitive dependency with no available fix, see "Justified allowlist entries" below.

---

## Adding a justified allowlist entry

Allowlist entries are a last resort. They require a written rationale and a review date, and the entry itself is subject to normal code review. Never add a blanket disable.

### Bandit — inline `# nosec`

Suppress a specific rule on a specific line only. Do **not** use a bare `# nosec` (which disables all rules on that line).

```python
# Example: B105 fires on a test fixture that deliberately uses a weak password string
TEST_PASSWORD = "hunter2"  # nosec B105  # test fixture only — not a real credential, 2026-05-17
```

Format: `# nosec <BXXX>  # <rationale> + review date`

A bare `# nosec` with no rule ID, or a `# nosec` on production auth/crypto code, will be rejected in code review.

### pip-audit — `.pip-audit-ignore`

If a CVE/GHSA has no available fix (e.g. a vulnerability in a transitive dependency with no upstream release), create or update `invest-ed/backend/.pip-audit-ignore`. Each advisory occupies two lines: a comment with rationale and review date, followed by the advisory ID.

```
# GHSA-xxxx-xxxx-xxxx: <package> <version> — <why this is acceptable / when to revisit> — reviewed 2026-05-17
GHSA-xxxx-xxxx-xxxx
```

Then update the CI step in `.github/workflows/ci.yml` to add an explicit `--ignore-vuln` flag for each accepted ID:

```yaml
- name: pip-audit (fail on any known vuln)
  working-directory: invest-ed/backend
  run: pip-audit -r requirements.txt --ignore-vuln GHSA-xxxx-xxxx-xxxx
```

Both the `.pip-audit-ignore` file and the CI change must be in the same PR and reviewed together. Set a calendar reminder to re-evaluate when the upstream fix ships.

### npm audit — no blanket `--force`

Do not use `npm audit fix --force` in CI or add `--force` to the audit command; force-fixing can introduce breaking semver changes silently. Instead:

1. Review the specific advisory in the job log.
2. If there is no fix available and the vulnerability is in a dev-only dependency (e.g. a build tool) that does not affect the production bundle, document the decision in a PR comment with the advisory ID, the rationale (dev-only / not reachable at runtime), and a review date.
3. If the vuln is in a production dependency, treat it as blocking until a fix is available or a mitigating control is in place.

There is no automated ignore mechanism for npm audit; the justification lives in the PR review thread for the relevant `package-lock.json` commit. Create a follow-up ticket to revisit when a fix is published.

---

## Requirements for any allowlist entry

- **Written rationale:** why the finding is acceptable (false positive, dev-only, no upstream fix, mitigating control in place).
- **Review date:** the date the entry was added.
- **Code review:** the allowlist change must go through a normal PR review — it cannot be merged without a reviewer approving it.
- **Expiry check:** entries should be re-evaluated when a new version of the affected package is released. For bandit suppressions, revisit if the surrounding code changes.

---

## Gate verification (one-time, Task 11)

Task 11 will perform the one-time gate-block verification procedure: introduce a deliberate High-severity finding (e.g. a known-bad dependency version pinned in a test branch) and confirm the `security` job exits non-zero, then revert and confirm it returns to green. This procedure validates that the gate actually blocks rather than merely running.

---

## Gate-block verification — 2026-05-18

**Procedure:** A throwaway file `invest-ed/backend/app/_gate_probe_tmp.py` was created containing a single `subprocess.Popen(sys.argv[1], shell=True)` call — bandit rule **B602** (subprocess call with shell=True, non-constant argument). This is rated **High severity / High confidence** by bandit.

**Result:** Running `bandit -r app -lll -iii` with the probe file present produced exit code **1** (non-zero), confirming the gate blocks on a High/High finding. The finding was correctly identified as B602 / CWE-78 at `app/_gate_probe_tmp.py:2`.

**Revert:** The probe file was deleted (`rm`). It was never staged or committed (`git status --short invest-ed/backend` returned empty). Re-running `bandit -r app -lll -iii` after revert returned exit code **0**, confirming the gate is back to clean.

**Conclusion:** The CI bandit gate demonstrably blocks High/High findings and is not a no-op. Gate-block sanity confirmed.
