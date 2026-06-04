# Auth-Screen Polish + Friendly Copy + Coach Panel (SP-D2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the auth screens a branded card look + friendlier copy via the shared `AuthPage`, and make the global Coach Penny button open an in-context slide-over panel instead of navigating away.

**Architecture:** Enhance the single `AuthPage` wrapper (Penny + "InvestiKid" wordmark + white card + `title`/`subtitle`) and adopt it across all 8 auth screens with warmer copy. Extract `Coach.tsx`'s chat into a reusable `CoachChat`; render it in a `Sheet`-based `CoachPanel` opened by `PennyFAB` from `Shell`; keep the `/coach` route as a thin page. Frontend only.

**Tech Stack:** React 18 + TS + Tailwind v4 + shadcn (`sheet.tsx` = Radix Dialog) + TanStack Query.

**Spec:** `docs/superpowers/specs/2026-06-04-auth-screen-polish-design.md`

**Conventions:** From `invest-ed/frontend`: `npx tsc -b`, `npm run lint` (one pre-existing `button.tsx` warning), `npm test`, `npm run build`. Backend untouched. Git from repo root; commit to `main`; trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Railway deploys backend only on green CI (5 jobs). **Layout/UX only — never change field `id`/`htmlFor`/names, validation, error semantics, routes, or the Coach chat endpoints. READ each file before editing.**

**Verified:** `src/components/AuthPage.tsx` (bare centered `max-w-md` safe-area wrapper, props `{children,className}`); `child/Login.tsx` + `child/Signup.tsx` already use `AuthPage`; the other 6 roll their own containers. `Penny` at `src/components/child/ui/Penny.tsx` `{size,mood,className}`. `src/components/ui/sheet.tsx` exports `Sheet, SheetContent (side="right" default), SheetHeader, SheetTitle, SheetDescription`. `Coach.tsx` (182 lines) = back-button + Penny header + remaining counter + messages (greeting/chips/bubbles/action-links/thinking/error) + input; uses `useCoachGreeting`, `aiApi.sendCoachMessage`, `CoachAction`/`CoachChatResponse`. `PennyFAB` (`{dueCount}`, `navigate('/coach')`). `Shell.tsx` renders `<PennyFAB dueCount={recsData?.review_summary?.due_count ?? 0} />` (~line 80). `/coach` route in `App.tsx`.

## Screenshot harness
Reuse the SP-A/B/C mocked-API capturer at `invest-ed/frontend/tmp-shot.mjs` (untracked; create if absent; removed in the final task). Auth screens need no auth mock (they're public); for the Coach panel, mock `/users/me`, `/users/me/progress`, `/recommendations`, `/home-greeting`, `/modules`. Run: `(npm run dev -- --port 5188 --strictPort >/tmp/dev.log 2>&1 &) ; for i in $(seq 1 40); do curl -sf -o /dev/null http://localhost:5188/ && break; sleep 1; done ; OUTDIR=/tmp/spd2/<tag> node tmp-shot.mjs ; pkill -f "port 5188"`.

---

### Task 1: Enhance `AuthPage` (branded card + title/subtitle) + test

**Files:** Modify `src/components/AuthPage.tsx`; Create `src/components/__tests__/AuthPage.test.tsx`.

- [ ] **Step 1: READ** `src/components/AuthPage.tsx` (keep its `<main>` centering + the inline safe-area padding styles + `max-w-md`/overflow guards). 

- [ ] **Step 2: Write the failing test** `src/components/__tests__/AuthPage.test.tsx`:
```tsx
import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { describe, it, expect } from 'vitest';
import { AuthPage } from '../AuthPage';

describe('AuthPage', () => {
  it('renders the wordmark, a single h1 title, subtitle, and children', () => {
    render(<AuthPage title="Welcome back!" subtitle="Let's keep learning."><button>child</button></AuthPage>);
    expect(screen.getByText('InvestiKid')).toBeInTheDocument();
    const h1s = screen.getAllByRole('heading', { level: 1 });
    expect(h1s).toHaveLength(1);
    expect(h1s[0]).toHaveTextContent('Welcome back!');
    expect(screen.getByText("Let's keep learning.")).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'child' })).toBeInTheDocument();
  });

  it('renders without a title (no h1) when title omitted', () => {
    render(<AuthPage><p>hi</p></AuthPage>);
    expect(screen.queryByRole('heading', { level: 1 })).toBeNull();
  });

  it('has no axe violations', async () => {
    const { container } = render(<AuthPage title="Hi"><label htmlFor="x">Email</label><input id="x" /></AuthPage>);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```
- [ ] **Step 3: Run, verify FAIL** (`InvestiKid`/title not rendered): `npm test -- src/components/__tests__/AuthPage.test.tsx`.

- [ ] **Step 4: Implement.** Rewrite `src/components/AuthPage.tsx`:
```tsx
import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { Penny } from '@/components/child/ui/Penny';

type Props = {
  children: ReactNode;
  title?: string;
  subtitle?: string;
  className?: string;
};

export function AuthPage({ children, title, subtitle, className }: Props) {
  return (
    <main
      className="box-border flex min-h-[100svh] w-full max-w-full items-center justify-center overflow-x-hidden px-4 py-8 sm:px-6"
      style={{
        paddingTop: 'max(2rem, calc(env(safe-area-inset-top, 0px) + 1.5rem))',
        paddingBottom: 'max(2rem, calc(env(safe-area-inset-bottom, 0px) + 1.5rem))',
        paddingLeft: 'max(1rem, env(safe-area-inset-left, 0px))',
        paddingRight: 'max(1rem, env(safe-area-inset-right, 0px))',
      }}
    >
      <div className={cn('w-full max-w-md min-w-0 break-words', className)}>
        <div className="mb-5 flex flex-col items-center text-center">
          <div className="flex items-center gap-2">
            <span className="flex h-11 w-11 items-center justify-center rounded-full bg-brand-100" aria-hidden="true">
              <Penny size={36} mood="happy" />
            </span>
            <span className="text-xl font-extrabold tracking-tight text-ink">InvestiKid</span>
          </div>
          {title && <h1 className="mt-4 text-2xl font-extrabold text-ink">{title}</h1>}
          {subtitle && <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>}
        </div>
        <div className="rounded-2xl border border-brand-100 bg-card p-6 shadow-sm">
          {children}
        </div>
      </div>
    </main>
  );
}
```
- [ ] **Step 5: Run, verify 3 PASS.** Then `npx tsc -b && npm run lint`.
- [ ] **Step 6: Commit**
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/AuthPage.tsx invest-ed/frontend/src/components/__tests__/AuthPage.test.tsx
git commit -m "feat(auth-ui): branded AuthPage (Penny + wordmark + card + title/subtitle)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Child Login / Signup / PendingConsent — adopt title + friendly copy

**Files:** Modify `src/pages/child/Login.tsx`, `src/pages/child/Signup.tsx`, `src/pages/child/PendingConsent.tsx`; update their tests.

- [ ] **Step 1: READ** all three + their tests (grep `tests/ src -l` for each name).

- [ ] **Step 2: Login.** It already wraps content in `<AuthPage>`. Remove the inner `<h1 className="text-2xl font-semibold">Sign in to InvestiKid</h1>` and instead pass props: `<AuthPage title="Welcome back!" subtitle="Let's keep learning.">`. Soften the helper links if desired (keep targets): "New to InvestiKid? Create an account" can stay. Keep the form, fields, `error` `role="alert"`, mutation, redirects EXACTLY.

- [ ] **Step 3: Signup.** It already uses `AuthPage` (two steps each render `<AuthPage>` with an inner `<h1>Create your account</h1>`). Move the heading to the prop: `<AuthPage title="Let's get you set up">` (both steps) and remove the inner `<h1>`s. Optionally add a `subtitle` per step (e.g. step 1 `subtitle="First, your date of birth."`). Keep ALL validation, the DOB group, the policy dialog, and step logic.

- [ ] **Step 4: PendingConsent.** READ it; wrap its content in `<AuthPage title="Almost there!" subtitle="We've emailed your grown-up to approve your account.">` (adjust subtitle to the screen's real meaning), removing any bespoke outer container + inner heading. Keep the resend/poll logic.

- [ ] **Step 5: Verify + tests.** `npx tsc -b && npm run lint && npm test && npm run build`. Update tests that asserted the old headings (e.g. `getByText('Sign in to InvestiKid')` → `getByRole('heading',{name:'Welcome back!'})`). Keep behavioural assertions. Expected green.

- [ ] **Step 6: Capture** `/tmp/spd2/login` (goto `/login`). VIEW: Penny+wordmark header, "Welcome back!" title, the form in a white card. Commit:
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/pages/child/Login.tsx invest-ed/frontend/src/pages/child/Signup.tsx invest-ed/frontend/src/pages/child/PendingConsent.tsx invest-ed/frontend/src/pages/child/__tests__ invest-ed/frontend/tests
git commit -m "feat(auth-ui): branded + friendlier child Login/Signup/PendingConsent

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: ParentLogin (+ social) / ForgotPassword / ResetPassword — adopt + copy

**Files:** Modify `src/pages/ParentLogin.tsx`, `src/pages/ForgotPassword.tsx`, `src/pages/ResetPassword.tsx`; tests.

- [ ] **Step 1: READ** all three + tests. `ParentLogin` has the D1 "Continue with Apple/Google" buttons + the magic-link form + `socialError` + a "Check your inbox" success state — KEEP ALL of it.

- [ ] **Step 2: ParentLogin.** Wrap the form state in `<AuthPage title="Parents' sign-in" subtitle="Manage your child's account.">` and the success state in `<AuthPage title="Check your inbox">`. Remove the bespoke outer container + the inner `<h1>`s. The social buttons + divider + magic-link form move inside the card unchanged. Keep `import` of `AuthPage` (add it).

- [ ] **Step 3: ForgotPassword.** Wrap in `<AuthPage title="Forgot your password?" subtitle="We'll email you a reset link.">`; keep the email form + submit + success message.

- [ ] **Step 4: ResetPassword.** Wrap in `<AuthPage title="Choose a new password">`; keep the token handling, the new-password fields, validation, and submit.

- [ ] **Step 5: Verify + tests + capture.** `npx tsc -b && npm run lint && npm test && npm run build` (update moved-heading assertions). Capture `/tmp/spd2/parentlogin` (goto `/parent/login`) — VIEW: branded card with social buttons + "or" + magic-link, "Parents' sign-in" title. Commit:
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/pages/ParentLogin.tsx invest-ed/frontend/src/pages/ForgotPassword.tsx invest-ed/frontend/src/pages/ResetPassword.tsx invest-ed/frontend/src/pages/__tests__ invest-ed/frontend/tests
git commit -m "feat(auth-ui): branded + friendlier ParentLogin/Forgot/Reset

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: VerifyEmail / ConsentVerify — adopt + copy

**Files:** Modify `src/pages/VerifyEmail.tsx`, `src/pages/ConsentVerify.tsx`; tests.

- [ ] **Step 1: READ** both + tests. These are status screens (verifying token → success/error states).
- [ ] **Step 2: VerifyEmail.** Wrap each state in `<AuthPage title="…">` with reassuring copy (e.g. verifying → `title="Verifying your email…"`; success → `title="Email verified! 🎉"`; error → `title="That link didn't work"` `subtitle="It may have expired — request a new one."`). Keep the token logic + any links/buttons.
- [ ] **Step 3: ConsentVerify.** Wrap in `<AuthPage title="…">` with parent-friendly wording (e.g. `title="Approve your child's account"` / success `title="All set — thank you!"`). Keep the approve action + token handling.
- [ ] **Step 4: Verify + tests.** `npx tsc -b && npm run lint && npm test && npm run build`. Update moved-heading assertions. Commit:
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/pages/VerifyEmail.tsx invest-ed/frontend/src/pages/ConsentVerify.tsx invest-ed/frontend/src/pages/__tests__ invest-ed/frontend/tests
git commit -m "feat(auth-ui): branded + friendlier VerifyEmail/ConsentVerify

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Extract `CoachChat` + thin `/coach` page

**Files:** Create `src/components/child/CoachChat.tsx`; Modify `src/pages/child/Coach.tsx`; move/update Coach tests.

- [ ] **Step 1: READ** `src/pages/child/Coach.tsx` fully. It is one component: an outer `<div className="mx-auto flex max-w-2xl flex-col px-4 py-4">` containing (a) a header row [back `<button>` `navigate(-1)`, Penny avatar + "Coach Penny", `remaining` counter], (b) a `flex-1` messages area [greeting bubble, suggestion chips, message bubbles + action `<Link>`s, "Thinking…", error, scroll anchor], (c) the input row [`<input>` + Send `<Button>`]. State/logic: `useCoachGreeting`, `messages`, `input`, `conversationId`, `remaining`, `chipsSent`, `messagesEndRef` + scroll effect, `sendMessage` mutation, `handleSend`, `actionToPath`.

- [ ] **Step 2: Create `src/components/child/CoachChat.tsx`** — move the WHOLE component body in, with two changes: (1) add a prop `{ onNavigate?: () => void }`; the action `<Link>` `onClick` calls `onNavigate?.()` (so a host panel can close); (2) DROP the outer page padding wrapper and the back `<button>` (the host provides chrome) — the component renders a `flex h-full flex-col` with the Penny+"Coach Penny"+remaining header, the messages area, and the input row. Keep every hook, state, the `aiApi.sendCoachMessage` mutation, `SUGGESTION_CHIPS`, `actionToPath`, error/thinking/remaining UI, and the scroll effect EXACTLY. Export `function CoachChat({ onNavigate }: { onNavigate?: () => void })`. Keep the `Penny` header import.

- [ ] **Step 3: Rewrite `Coach.tsx`** as a thin full-screen page that reuses `CoachChat`:
```tsx
import { Link } from 'react-router-dom';
import { CoachChat } from '@/components/child/CoachChat';

export default function Coach() {
  return (
    <div className="mx-auto flex h-[calc(100svh-8rem)] max-w-2xl flex-col px-4 py-4">
      <Link to="/home" className="mb-2 inline-block text-sm text-brand-700 hover:underline" aria-label="Back to home">← Back</Link>
      <div className="min-h-0 flex-1"><CoachChat /></div>
    </div>
  );
}
```
(Adjust the height/wrapper to match how other child pages size within the Shell — READ a sibling page; the point is CoachChat fills the area.)

- [ ] **Step 4: Tests.** The existing Coach page test likely asserts greeting/chips/send behaviour — move those assertions to a new `CoachChat` test (`src/components/child/__tests__/CoachChat.test.tsx`) rendering `<CoachChat />` in a `MemoryRouter` + `QueryClientProvider` (READ the old Coach test for the mock setup of `useCoachGreeting`/`aiApi`). Keep a minimal Coach page test (renders + contains CoachChat). Run `npx tsc -b && npm run lint && npm test`.

- [ ] **Step 5: Commit**
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/child/CoachChat.tsx invest-ed/frontend/src/pages/child/Coach.tsx invest-ed/frontend/src/components/child/__tests__ invest-ed/frontend/src/pages/child/__tests__ invest-ed/frontend/tests
git commit -m "refactor(coach): extract reusable CoachChat; /coach renders it

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: `CoachPanel` sheet + wire `PennyFAB` / `Shell`

**Files:** Create `src/components/child/CoachPanel.tsx`; Modify `src/components/child/PennyFAB.tsx`, `src/components/child/Shell.tsx`; tests.

- [ ] **Step 1: Create `src/components/child/CoachPanel.tsx`:**
```tsx
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Penny } from '@/components/child/ui/Penny';
import { CoachChat } from '@/components/child/CoachChat';

export function CoachPanel({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="flex w-full max-w-md flex-col gap-0 p-0 sm:max-w-md">
        <SheetHeader className="flex-row items-center gap-2 border-b border-brand-100 px-4 py-3 text-left">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100" aria-hidden="true">
            <Penny size={28} mood="happy" />
          </span>
          <SheetTitle>Coach Penny</SheetTitle>
        </SheetHeader>
        <div className="min-h-0 flex-1 overflow-hidden px-4 py-3">
          <CoachChat onNavigate={() => onOpenChange(false)} />
        </div>
      </SheetContent>
    </Sheet>
  );
}
```
(READ `sheet.tsx` to confirm `SheetContent`/`SheetHeader`/`SheetTitle` props + that `side="right"` exists; the Radix Dialog gives focus-trap, ESC, overlay-close, `aria-modal`, and focus-return automatically. If `CoachChat`'s header now duplicates the "Coach Penny" title shown in `SheetHeader`, drop CoachChat's own Penny/name header when it's inside the panel — simplest: keep CoachChat's header minimal and let the SheetHeader own the title; if duplication looks bad in the screenshot, remove CoachChat's header row and rely on the SheetHeader. Decide from the screenshot.)

- [ ] **Step 2: `PennyFAB`** — change from internal navigation to an `onOpen` callback:
```tsx
import { Penny } from '@/components/child/ui/Penny';

type Props = { dueCount: number; onOpen: () => void };

export function PennyFAB({ dueCount, onOpen }: Props) {
  return (
    <button
      onClick={onOpen}
      aria-label="Open Coach Penny"
      className="fixed bottom-20 right-4 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-brand-gradient shadow-lg transition-transform hover:scale-105 active:scale-95"
    >
      <Penny size={34} mood="happy" />
      {dueCount > 0 && (
        <span data-testid="penny-badge" className="absolute -right-0.5 -top-0.5 h-3.5 w-3.5 rounded-full border-2 border-white bg-danger-500" />
      )}
    </button>
  );
}
```

- [ ] **Step 3: `Shell.tsx`** — READ it; add `const [coachOpen, setCoachOpen] = useState(false);` (import `useState` if needed), change the FAB usage to `<PennyFAB dueCount={recsData?.review_summary?.due_count ?? 0} onOpen={() => setCoachOpen(true)} />`, and render `<CoachPanel open={coachOpen} onOpenChange={setCoachOpen} />` alongside it (import `CoachPanel`). Keep everything else.

- [ ] **Step 4: Tests.** Update `PennyFAB` test: it now needs an `onOpen` prop; assert clicking the FAB calls `onOpen` (and the badge shows when `dueCount>0`). Add/adjust a Shell test or a `CoachPanel` test: rendering `CoachPanel open` shows "Coach Penny" + the chat; `onOpenChange(false)` (ESC/overlay) closes. (Mock `useCoachGreeting`/`aiApi` as the CoachChat test does.) Run `npx tsc -b && npm run lint && npm test && npm run build`.

- [ ] **Step 5: Screenshot.** Capture a child screen with the panel open: in `tmp-shot.mjs`, after loading `/home`, click the FAB (`await page.getByRole('button',{name:/Open Coach Penny/i}).click()`) then screenshot. VIEW `/tmp/spd2/coach-panel`: the right-side sheet overlays Home, header "Coach Penny" + Penny, greeting + chips + input; the page behind is dimmed. Confirm no duplicate header. Fix + re-capture if needed.

- [ ] **Step 6: Commit**
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/child/CoachPanel.tsx invest-ed/frontend/src/components/child/PennyFAB.tsx invest-ed/frontend/src/components/child/Shell.tsx invest-ed/frontend/src/components/child/__tests__ invest-ed/frontend/tests
git commit -m "feat(coach): Coach Penny opens an in-context slide-over panel

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: A11y + full regression + push

- [ ] **Step 1: A11y sweep.** `grep -rnE "text-(brand|info)-(300|400)" src/components/AuthPage.tsx src/pages` — bump any text-on-white to `-600/700`. Confirm: each auth screen renders exactly one `<h1>` (the AuthPage `title`) — `grep -rn "<h1" src/pages/ParentLogin.tsx src/pages/ForgotPassword.tsx src/pages/ResetPassword.tsx src/pages/VerifyEmail.tsx src/pages/ConsentVerify.tsx src/pages/child/Login.tsx src/pages/child/Signup.tsx src/pages/child/PendingConsent.tsx` should return nothing (headings now come from AuthPage). The Coach panel (Radix Dialog) traps focus + closes on ESC + returns focus to the FAB; chat input ≥16px; decorative Penny/glyphs `aria-hidden`; errors keep `role="alert"`.
- [ ] **Step 2: Full regression.** `npx tsc -b && npm run lint && npm test && npm run build`. Expected: tsc clean; lint = only `button.tsx` warning; vitest green (incl. AuthPage/CoachChat/CoachPanel/PennyFAB tests); build OK.
- [ ] **Step 3: Cleanup + push.** `rm -f invest-ed/frontend/tmp-shot.mjs`; if it was added to `eslint.config.js` ignores during this work, remove that stale line; re-run `npm run lint`. Then from repo root: `git status --porcelain` (only intended files), `git add -A invest-ed/frontend/src invest-ed/frontend/eslint.config.js`, commit `a11y(auth-ui): contrast + single-h1 pass`, `git push origin main`.
- [ ] **Step 4: Confirm green CI** — all 5 jobs (a11y job validates the dialog/headings). Fix any failure.
- [ ] **Step 5: Report SP-D2 complete** — branded + friendlier auth screens; Coach Penny in-context panel; CI green. Note the iOS Xcode rebuild is still deferred to programme end. Next: SP-E (parent/admin).

---

## Self-Review

**1. Spec coverage:** Enhance AuthPage → T1; adopt across 8 screens + friendly copy → T2 (Login/Signup/PendingConsent), T3 (ParentLogin+social/Forgot/Reset), T4 (VerifyEmail/ConsentVerify); extract CoachChat + thin /coach → T5; CoachPanel sheet + FAB/Shell wiring → T6; a11y/regression → T7. All spec sections covered (the `/coach` route is kept in T5; social buttons preserved in T3). ✓

**2. Placeholder scan:** AuthPage, CoachChat extraction, CoachPanel, PennyFAB carry full code; screen-adoption tasks give exact files, the `title`/`subtitle` strings, READ-first steps, the "copy-only, no field/validation change" guardrail, and screenshot+test gates. No "TBD"/"handle appropriately".

**3. Type consistency:** `AuthPage {children,title?,subtitle?,className}` used the same in T1–T4. `CoachChat {onNavigate?}` defined T5, consumed by `CoachPanel` (T6) + `Coach.tsx` page (T5, no prop). `CoachPanel {open,onOpenChange}` defined T6, rendered by Shell (T6). `PennyFAB {dueCount,onOpen}` changed in T6 + Shell updated in the same task (no stale single-arg caller left). `/coach` route untouched. Sheet exports (`Sheet/SheetContent/SheetHeader/SheetTitle`) match `sheet.tsx`. ✓
