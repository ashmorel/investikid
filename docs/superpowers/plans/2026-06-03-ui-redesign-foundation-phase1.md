# UI Redesign — Foundation + Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the InvestiKid Figma redesign into the app — a shared in-code design system (incl. a robot-Eddie SVG mascot) plus the restyled Home and lesson flow — reusing all existing logic/data.

**Architecture:** Add presentational primitives under `src/components/child/ui/`, then re-skin the Home page and the lesson renderers to compose them. Restyle only — every existing hook, route, API call, and behaviour is preserved; the existing test suite must stay green (assertions updated only where copy/markup changed). All styling uses existing Tailwind tokens (brand amber→orange gradient, cream background).

**Tech Stack:** React 18 + TypeScript + Tailwind + shadcn/ui + framer-motion + react-router; Vitest + @testing-library/react + vitest-axe.

**Spec:** `docs/superpowers/specs/2026-06-03-ui-redesign-foundation-phase1-design.md`

**Conventions (run from `invest-ed/frontend`):** `npx tsc -b`, `npm run lint` (one pre-existing `button.tsx` fast-refresh warning is acceptable), `npx vitest run <path>`, `npm test`, `npm run build`. Commit to `main` from `/Users/leeashmore/Local Repo`; trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. New UI needs a `vitest-axe` check. Backend is untouched in Phase 1. After all tasks: `npx cap sync ios` + push on green CI.

## File Structure
- Create `src/components/child/ui/RobotEddie.tsx`, `GradientButton.tsx`, `OptionCard.tsx`, `ModuleTile.tsx`, `StatChip.tsx`, `HeroCard.tsx`, `FeedbackPanel.tsx` (+ `__tests__/`).
- Modify `src/components/child/EddieFAB.tsx` (use RobotEddie), `src/components/child/BottomTabBar.tsx` (restyle), `src/components/child/HomeHero.tsx` + `src/pages/child/Home.tsx`, and lesson renderers `src/components/child/lesson/{QuizLesson,ScenarioLesson,CardLesson,CompletionPanel}.tsx`.

---

### Task 1: `RobotEddie` mascot + use in `EddieFAB`

**Files:** Create `src/components/child/ui/RobotEddie.tsx`, `src/components/child/ui/__tests__/RobotEddie.test.tsx`; Modify `src/components/child/EddieFAB.tsx`.

- [ ] **Step 1: Write the failing test** — `src/components/child/ui/__tests__/RobotEddie.test.tsx`:
```tsx
import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { axe } from 'vitest-axe';
import { RobotEddie } from '../RobotEddie';

describe('RobotEddie', () => {
  it('renders an svg sized by the size prop, decorative by default', () => {
    const { container } = render(<RobotEddie size={64} />);
    const svg = container.querySelector('svg')!;
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveAttribute('width', '64');
    expect(svg).toHaveAttribute('aria-hidden', 'true');
  });
  it('has no accessibility violations', async () => {
    const { container } = render(<div>Eddie <RobotEddie size={40} /></div>);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```
- [ ] **Step 2: Run to verify it fails** — `npx vitest run src/components/child/ui/__tests__/RobotEddie.test.tsx` → FAIL (module not found).
- [ ] **Step 3: Implement** — `src/components/child/ui/RobotEddie.tsx`:
```tsx
export function RobotEddie({ size = 48, className }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 50" fill="none" aria-hidden="true" className={className}>
      <rect x="22.5" y="1" width="3" height="9" rx="1.5" fill="#8b93a3" />
      <circle cx="24" cy="3" r="4" fill="url(#eddie-antenna)" />
      <rect x="2" y="9" width="44" height="40" rx="13" fill="#6b95eb" />
      <rect x="7" y="17" width="34" height="24" rx="9" fill="#1d2647" />
      <circle cx="17.5" cy="29" r="3.5" fill="#66e0ff" />
      <circle cx="30.5" cy="29" r="3.5" fill="#66e0ff" />
      <defs>
        <linearGradient id="eddie-antenna" x1="20" y1="-1" x2="28" y2="7" gradientUnits="userSpaceOnUse">
          <stop stopColor="#fbbf24" />
          <stop offset="1" stopColor="#f97316" />
        </linearGradient>
      </defs>
    </svg>
  );
}
```
- [ ] **Step 4: Use it in `EddieFAB`** — in `src/components/child/EddieFAB.tsx`, add `import { RobotEddie } from '@/components/child/ui/RobotEddie';` and replace `<span className="text-2xl" aria-hidden="true">💡</span>` with `<RobotEddie size={30} />`.
- [ ] **Step 5: Verify** — `npx vitest run src/components/child/ui/__tests__/RobotEddie.test.tsx` → pass; `npx tsc -b` clean; run the EddieFAB test if one exists (`npx vitest run src/components/child/__tests__/EddieFAB.test.tsx`) — if it asserted the 💡 emoji, update it to assert the svg/`aria-label="Open Coach Eddie"` instead.
- [ ] **Step 6: Commit**
```bash
git add invest-ed/frontend/src/components/child/ui/RobotEddie.tsx invest-ed/frontend/src/components/child/ui/__tests__/RobotEddie.test.tsx invest-ed/frontend/src/components/child/EddieFAB.tsx
# plus EddieFAB test if changed
git commit -m "feat(ui): robot Eddie mascot component; use in EddieFAB

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `GradientButton`

**Files:** Create `src/components/child/ui/GradientButton.tsx`, `__tests__/GradientButton.test.tsx`.

- [ ] **Step 1: Failing test**
```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import { GradientButton } from '../GradientButton';

describe('GradientButton', () => {
  it('renders a button and fires onClick', async () => {
    const onClick = vi.fn();
    render(<GradientButton onClick={onClick}>Start</GradientButton>);
    screen.getByRole('button', { name: 'Start' }).click();
    expect(onClick).toHaveBeenCalled();
  });
  it('renders a link when `to` is set', () => {
    render(<MemoryRouter><GradientButton to="/x">Go</GradientButton></MemoryRouter>);
    expect(screen.getByRole('link', { name: 'Go' })).toHaveAttribute('href', '/x');
  });
  it('no a11y violations', async () => {
    const { container } = render(<GradientButton>Check</GradientButton>);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```
- [ ] **Step 2: Run → fails.**
- [ ] **Step 3: Implement** — `src/components/child/ui/GradientButton.tsx`:
```tsx
import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & { to?: string; full?: boolean };

const BASE =
  'inline-flex items-center justify-center gap-1 rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 px-5 py-3.5 text-sm font-extrabold text-white shadow-lg shadow-orange-500/30 transition-transform hover:from-amber-500 hover:to-orange-600 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-600 focus-visible:ring-offset-2 disabled:opacity-50 disabled:active:scale-100';

export function GradientButton({ to, full, className, children, ...rest }: Props) {
  const cls = cn(BASE, full && 'w-full', className);
  if (to) return <Link to={to} className={cls}>{children}</Link>;
  return <button className={cls} {...rest}>{children}</button>;
}
```
- [ ] **Step 4: Run → pass; `npx tsc -b` clean.**
- [ ] **Step 5: Commit** (`feat(ui): GradientButton primitive`).

---

### Task 3: `OptionCard` (quiz/scenario answer)

**Files:** Create `src/components/child/ui/OptionCard.tsx`, `__tests__/OptionCard.test.tsx`.

- [ ] **Step 1: Failing test**
```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { OptionCard } from '../OptionCard';

describe('OptionCard', () => {
  it('is a radio that reports checked when selected/correct and fires onSelect', () => {
    const onSelect = vi.fn();
    render(<OptionCard letter="A" state="selected" onSelect={onSelect}>£10</OptionCard>);
    const r = screen.getByRole('radio', { name: /£10/ });
    expect(r).toHaveAttribute('aria-checked', 'true');
    r.click();
    expect(onSelect).toHaveBeenCalled();
  });
  it('no a11y violations inside a radiogroup', async () => {
    const { container } = render(
      <div role="radiogroup" aria-label="answers">
        <OptionCard letter="A" state="default" onSelect={() => {}}>One</OptionCard>
        <OptionCard letter="B" state="correct" onSelect={() => {}}>Two</OptionCard>
      </div>,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
```
- [ ] **Step 2: Run → fails.**
- [ ] **Step 3: Implement** — `src/components/child/ui/OptionCard.tsx`:
```tsx
import { cn } from '@/lib/utils';

export type OptionState = 'default' | 'selected' | 'correct' | 'incorrect';

type Props = {
  letter: string;
  state?: OptionState;
  disabled?: boolean;
  onSelect?: () => void;
  children: React.ReactNode;
};

export function OptionCard({ letter, state = 'default', disabled, onSelect, children }: Props) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={state === 'selected' || state === 'correct'}
      disabled={disabled}
      onClick={onSelect}
      className={cn(
        'flex w-full items-center gap-3 rounded-2xl border-2 p-3.5 text-left transition-all active:scale-[0.99] disabled:active:scale-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500',
        state === 'default' && 'border-gray-200 bg-white',
        state === 'selected' && 'border-amber-400 bg-amber-50 shadow-md shadow-orange-500/15',
        state === 'correct' && 'border-green-500 bg-green-50',
        state === 'incorrect' && 'border-red-500 bg-red-50',
      )}
    >
      <span
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-xl text-sm font-extrabold',
          state === 'selected' && 'bg-gradient-to-br from-amber-400 to-orange-500 text-white',
          state === 'correct' && 'bg-green-500 text-white',
          state === 'incorrect' && 'bg-red-500 text-white',
          state === 'default' && 'bg-gray-100 text-gray-500',
        )}
        aria-hidden="true"
      >
        {letter}
      </span>
      <span className="flex-1 text-sm font-bold leading-snug text-gray-900">{children}</span>
    </button>
  );
}
```
- [ ] **Step 4: Run → pass; tsc clean.**
- [ ] **Step 5: Commit** (`feat(ui): OptionCard answer primitive`).

---

### Task 4: `StatChip`, `HeroCard`, `ModuleTile`, `FeedbackPanel`

**Files:** Create `src/components/child/ui/StatChip.tsx`, `HeroCard.tsx`, `ModuleTile.tsx`, `FeedbackPanel.tsx` + a combined `__tests__/ui-primitives.test.tsx`.

- [ ] **Step 1: Failing test** — `src/components/child/ui/__tests__/ui-primitives.test.tsx`:
```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import { StatChip } from '../StatChip';
import { HeroCard } from '../HeroCard';
import { ModuleTile } from '../ModuleTile';
import { FeedbackPanel } from '../FeedbackPanel';

describe('ui primitives', () => {
  it('StatChip shows value + label', () => {
    render(<StatChip emoji="🔥" value="6" label="Streak" />);
    expect(screen.getByText('6')).toBeInTheDocument();
    expect(screen.getByText('Streak')).toBeInTheDocument();
  });
  it('HeroCard renders title + CTA link', () => {
    render(<MemoryRouter><HeroCard eyebrow="Up next" icon="📈" title="What is a Stock?" cta="Start" to="/x" /></MemoryRouter>);
    expect(screen.getByText('What is a Stock?')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /start/i })).toHaveAttribute('href', '/x');
  });
  it('ModuleTile shows title + subtitle and links when unlocked', () => {
    render(<MemoryRouter><ModuleTile emoji="📈" title="Stocks" subtitle="3 / 8" accent="#fbbf24" tint="#fff4d6" to="/m" /></MemoryRouter>);
    expect(screen.getByRole('link', { name: /stocks/i })).toBeInTheDocument();
  });
  it('FeedbackPanel correct + incorrect render', () => {
    const { rerender } = render(<FeedbackPanel correct explanation="because" />);
    expect(screen.getByText(/correct/i)).toBeInTheDocument();
    rerender(<FeedbackPanel correct={false} explanation="because" correctAnswer="£10" />);
    expect(screen.getByText(/not quite/i)).toBeInTheDocument();
  });
  it('no a11y violations', async () => {
    const { container } = render(<MemoryRouter>
      <StatChip emoji="⭐" value="120" label="XP" />
      <FeedbackPanel correct explanation="x" />
    </MemoryRouter>);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```
- [ ] **Step 2: Run → fails.**
- [ ] **Step 3: Implement the four files.**

`StatChip.tsx`:
```tsx
export function StatChip({ emoji, value, label }: { emoji: string; value: string; label: string }) {
  return (
    <div className="flex flex-1 flex-col items-center rounded-2xl border border-amber-200 bg-white px-2 py-2.5 shadow-sm">
      <span className="text-lg" aria-hidden="true">{emoji}</span>
      <span className="text-base font-extrabold text-gray-900">{value}</span>
      <span className="text-[11px] font-medium text-gray-500">{label}</span>
    </div>
  );
}
```
`HeroCard.tsx`:
```tsx
import { motion } from 'framer-motion';
import { GradientButton } from './GradientButton';

type Props = { eyebrow: string; icon?: string; title: string; subtitle?: string; cta: string; to: string };

export function HeroCard({ eyebrow, icon, title, subtitle, cta, to }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.35 }}
      className="overflow-hidden rounded-3xl bg-gradient-to-br from-amber-400 to-orange-500 p-5 text-white shadow-lg shadow-orange-500/30"
    >
      <p className="text-xs font-extrabold uppercase tracking-wider opacity-95">▶ {eyebrow}</p>
      <div className="mt-2 flex items-center gap-3">
        {icon && <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white text-2xl" aria-hidden="true">{icon}</span>}
        <p className="text-lg font-extrabold leading-tight">{title}</p>
      </div>
      {subtitle && <p className="mt-1 text-sm font-medium opacity-90">{subtitle}</p>}
      <GradientButton to={to} full className="mt-4 bg-white !bg-none from-white to-white text-amber-700 shadow-none hover:!bg-amber-50">{cta} →</GradientButton>
    </motion.div>
  );
}
```
(The CTA is a white pill on the gradient — `!bg-none` removes the gradient so the white shows; keep the GradientButton focus ring.)

`ModuleTile.tsx`:
```tsx
import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';

type Props = { emoji: string; title: string; subtitle: string; accent: string; tint: string; to?: string; locked?: boolean; recommended?: boolean };

export function ModuleTile({ emoji, title, subtitle, accent, tint, to, locked, recommended }: Props) {
  const inner = (
    <>
      {recommended && <span className="absolute right-3 top-3 rounded-full bg-white/80 px-2 py-0.5 text-[10px] font-extrabold text-amber-700">★ Next</span>}
      <span className="flex h-10 w-10 items-center justify-center rounded-xl text-xl" style={{ backgroundColor: accent }} aria-hidden="true">{emoji}</span>
      <span className="mt-2 block text-[15px] font-extrabold text-gray-900">{title}</span>
      <span className="text-[11px] font-bold text-gray-500">{subtitle}</span>
    </>
  );
  const cls = cn('relative block rounded-2xl p-3.5', locked && 'opacity-60');
  if (to && !locked) return <Link to={to} className={cn(cls, 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500')} style={{ backgroundColor: tint }}>{inner}</Link>;
  return <div className={cls} style={{ backgroundColor: tint }} aria-disabled={locked}>{inner}</div>;
}
```
`FeedbackPanel.tsx`:
```tsx
import { cn } from '@/lib/utils';

type Props = { correct: boolean; explanation: string; correctAnswer?: string };

export function FeedbackPanel({ correct, explanation, correctAnswer }: Props) {
  return (
    <div className={cn('rounded-2xl p-4', correct ? 'bg-green-50' : 'bg-red-50')}>
      <div className="flex items-center gap-2">
        <span className={cn('flex h-7 w-7 items-center justify-center rounded-full text-base font-extrabold text-white', correct ? 'bg-green-600' : 'bg-red-500')} aria-hidden="true">{correct ? '✓' : '✕'}</span>
        <p className={cn('text-lg font-extrabold', correct ? 'text-green-700' : 'text-red-700')}>{correct ? 'Correct!' : 'Not quite!'}</p>
      </div>
      {!correct && correctAnswer && <p className="mt-2 text-sm font-bold text-red-700">Correct answer: {correctAnswer}</p>}
      <p className="mt-2 text-sm leading-relaxed text-gray-700">{explanation}</p>
    </div>
  );
}
```
- [ ] **Step 4: Run → pass; tsc clean; lint clean.**
- [ ] **Step 5: Commit** (`feat(ui): StatChip, HeroCard, ModuleTile, FeedbackPanel primitives`).

---

### Task 5: Restyle `QuizLesson` with the primitives

**Files:** Modify `src/components/child/lesson/QuizLesson.tsx`; check `src/components/child/lesson/__tests__/QuizLesson.test.tsx` if present.

Preserve the exact `Props` (`contentJson`, `onComplete`, `illustration?`, `onShowEddie?`, `completing?`) and behaviour (select → Submit → inline feedback → Continue calls `onComplete(isCorrect ? 1.0 : 0.0)`; radiogroup semantics).

- [ ] **Step 1: Replace the component body** with the restyled version using `OptionCard`, `GradientButton`, `FeedbackPanel`:
```tsx
import { useState } from 'react';
import { OptionCard, type OptionState } from '@/components/child/ui/OptionCard';
import { GradientButton } from '@/components/child/ui/GradientButton';
import { FeedbackPanel } from '@/components/child/ui/FeedbackPanel';

type QuizContent = { question: string; choices: string[]; answer_index: number; explanation: string };
type Props = { contentJson: QuizContent; onComplete: (score: number | null) => void; illustration?: React.ReactNode; onShowEddie?: () => void; completing?: boolean };
const LETTERS = ['A', 'B', 'C', 'D', 'E', 'F'];

export function QuizLesson({ contentJson, onComplete, illustration, onShowEddie, completing = false }: Props) {
  const [selected, setSelected] = useState<number | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const isCorrect = selected === contentJson.answer_index;

  function optionState(i: number): OptionState {
    if (!submitted) return selected === i ? 'selected' : 'default';
    if (i === contentJson.answer_index) return 'correct';
    if (i === selected) return 'incorrect';
    return 'default';
  }

  return (
    <div className="space-y-5 rounded-3xl bg-white p-6 shadow-lg shadow-orange-500/10">
      {illustration && <div>{illustration}</div>}
      <p className="text-lg font-extrabold leading-snug text-gray-900">{contentJson.question}</p>
      <div className="space-y-3" role="radiogroup" aria-label="Answer choices">
        {contentJson.choices.map((choice, i) => (
          <OptionCard key={i} letter={LETTERS[i] ?? '?'} state={optionState(i)} disabled={submitted} onSelect={() => setSelected(i)}>
            {choice}
          </OptionCard>
        ))}
      </div>
      {submitted ? (
        <>
          <FeedbackPanel correct={isCorrect} explanation={contentJson.explanation} correctAnswer={!isCorrect ? contentJson.choices[contentJson.answer_index] : undefined} />
          <GradientButton full onClick={() => onComplete(isCorrect ? 1.0 : 0.0)} disabled={completing}>
            {completing ? 'Saving…' : 'Continue →'}
          </GradientButton>
        </>
      ) : (
        <div className="flex items-center justify-between gap-4">
          {onShowEddie ? (
            <button type="button" onClick={onShowEddie} className="text-sm font-bold text-amber-600 underline hover:text-amber-700">Ask Coach Eddie</button>
          ) : <span />}
          <GradientButton disabled={selected === null} onClick={() => setSubmitted(true)}>Check answer</GradientButton>
        </div>
      )}
    </div>
  );
}
```
- [ ] **Step 2: Verify** — `npx tsc -b` clean. Run the QuizLesson test if present (`npx vitest run -t Quiz` or the file). If it asserted old copy ("Submit", "✅ Correct!", `border-amber-200`), update assertions to the new copy/roles ("Check answer", `FeedbackPanel` "Correct!"/"Not quite!", options via `getByRole('radio')`). Keep the behavioural assertions (select→check→continue calls `onComplete`). If no test exists, add a short one covering: pick correct → Check → shows "Correct!" → Continue calls `onComplete(1)`.
- [ ] **Step 3: a11y** — `npx vitest run` the QuizLesson test with an `axe` assertion (radiogroup intact).
- [ ] **Step 4: Commit** (`feat(ui): restyle QuizLesson with new primitives`).

---

### Task 6: Restyle `ScenarioLesson`

**Files:** Modify `src/components/child/lesson/ScenarioLesson.tsx`; its test if present.

Mirror Task 5 exactly, but ScenarioLesson's content is `{ prompt: string; choices: {label; outcome}[]; correct_index: number }` and it shows the chosen choice's `outcome` as the explanation. Preserve its `Props` and `onComplete(isCorrect ? 1.0 : 0.0)` behaviour.

- [ ] **Step 1: Replace the body** — same structure as the restyled QuizLesson, with these differences: a small purple "🧠 Real-life scenario" eyebrow label above the prompt; `contentJson.prompt` as the question text; options are `contentJson.choices[i].label`; on submit, `FeedbackPanel` `explanation={contentJson.choices[selected!].outcome}` and `correctAnswer={!isCorrect ? contentJson.choices[contentJson.correct_index].label : undefined}`; `isCorrect = selected === contentJson.correct_index`. Use `OptionCard`/`GradientButton`/`FeedbackPanel` and the same `optionState` helper (comparing against `correct_index`). Keep `role="radiogroup"`.
```tsx
// eyebrow
<span className="inline-block rounded-full bg-violet-100 px-3 py-1.5 text-[11px] font-extrabold text-violet-700">🧠 Real-life scenario</span>
<p className="text-lg font-extrabold leading-snug text-gray-900">{contentJson.prompt}</p>
```
- [ ] **Step 2: Verify tsc + update/add the ScenarioLesson test** (same approach as Task 5 — new copy, radio roles, `onComplete` behaviour, axe).
- [ ] **Step 3: Commit** (`feat(ui): restyle ScenarioLesson with new primitives`).

---

### Task 7: Restyle `CardLesson`

**Files:** Modify `src/components/child/lesson/CardLesson.tsx`; its test if present.

Props: `{ contentJson: { title?; body? }; onComplete: (score: null) => void; illustration?; completing? }`. Preserve `onComplete(null)` on the button.

- [ ] **Step 1: Replace the body**:
```tsx
import { GradientButton } from '@/components/child/ui/GradientButton';

type Props = { contentJson: { title?: string; body?: string }; onComplete: (score: number | null) => void; illustration?: React.ReactNode; completing?: boolean };

export function CardLesson({ contentJson, onComplete, illustration, completing = false }: Props) {
  return (
    <div className="space-y-5 rounded-3xl bg-white p-7 text-center shadow-lg shadow-orange-500/10">
      {illustration && <div className="flex justify-center">{illustration}</div>}
      <h2 className="text-2xl font-extrabold leading-tight text-gray-900">{contentJson.title ?? ''}</h2>
      <p className="text-[15px] leading-relaxed text-gray-600">{contentJson.body ?? ''}</p>
      <GradientButton full onClick={() => onComplete(null)} disabled={completing}>{completing ? 'Saving…' : 'Got it →'}</GradientButton>
    </div>
  );
}
```
- [ ] **Step 2: Verify tsc; update/add CardLesson test** (renders title/body; button calls `onComplete(null)`; axe).
- [ ] **Step 3: Commit** (`feat(ui): restyle CardLesson`).

---

### Task 8: Restyle `CompletionPanel` (lesson-complete celebration)

**Files:** Modify `src/components/child/lesson/CompletionPanel.tsx`; its test if present.

Preserve Props `{ result: LessonCompletionResult; onContinue: () => void }`, the `confetti(...)` + `animate(xpCount, ...)` effect (only when `!result.already_completed`), and that `onContinue` fires from the button. Restyle to the Figma celebration: gradient medal with ⭐, "Lesson complete!" (or the already-done heading), 3 stars, stat chips (XP / level / streak), `GradientButton` "Continue".

- [ ] **Step 1: Restyle** — keep the existing imports/effect (confetti, framer `animate`, `useMotionValue`), keep `useReducedMotion()` gating if present (add it: skip confetti when reduced motion). Replace the visual markup with: a centered column — gradient circle (`bg-gradient-to-br from-amber-400 to-orange-500`) ~96px containing a `text-4xl ⭐`; `<h2>` heading; a `⭐ ⭐ ⭐` row; a row of three `StatChip` (`+{result.xp_awarded}`/XP, `result.level`/Level, `result.streak_count`/Streak); a `GradientButton full onClick={onContinue}`. Keep the `xpInLevel`/"to Level N+1" caption. Import `StatChip` and `GradientButton`.
- [ ] **Step 2: Verify tsc; update CompletionPanel test** — keep behavioural assertions (renders the XP/level/streak values from `result`, Continue calls `onContinue`); update any copy assertions ("Quest Complete!" → keep or change to "Lesson complete!" — match what you render). axe check.
- [ ] **Step 3: Commit** (`feat(ui): restyle lesson-complete celebration`).

---

### Task 9: Restyle `BottomTabBar`

**Files:** Modify `src/components/child/BottomTabBar.tsx`; its test if present.

Keep the exact `TABS` array (routes/labels/icons) and `NavLink` behaviour. Restyle: white bar with top border + subtle shadow, active tab in amber with bolder weight, larger touch targets retained (`min-h-[44px]`).

- [ ] **Step 1: Restyle markup** — keep imports + TABS; update the `<nav>`/`NavLink` classes: active `text-amber-600 font-extrabold`, inactive `text-gray-400 font-medium`; add `shadow-[0_-4px_12px_rgba(0,0,0,0.05)]` to the nav; keep `min-h-[44px] min-w-[44px]` and `env(safe-area-inset-bottom)` padding. Do not change routes/labels/icons.
- [ ] **Step 2: Verify tsc + lint; run the BottomTabBar test if present** (it should still pass — routes/labels unchanged; update only if it asserted specific old classes, which is unlikely).
- [ ] **Step 3: Commit** (`feat(ui): restyle bottom tab bar`).

---

### Task 10: Restyle Home — hero + stat chips + "Your quests" grid

**Files:** Modify `src/components/child/HomeHero.tsx` and `src/pages/child/Home.tsx`; update `tests/unit/child-Home.test.tsx` + `tests/a11y/child-core.a11y.test.tsx` mocks/assertions as needed.

Reuse all existing data hooks. `HomeHero` already uses `useNextLesson` + the greeting; swap its inline hero card for the `HeroCard` primitive and its Eddie 💡 circle for `RobotEddie`. `Home.tsx` adds a "Your quests" `ModuleTile` grid below the hero+stats and drops the verbose `CategorySection` lists (same data: modules + recommendations).

- [ ] **Step 1: Update `HomeHero.tsx`** — keep all hooks/logic and the templated/premium-AI greeting swap. Replace the Eddie avatar `<div>…💡…</div>` with `<RobotEddie size={44} />` (in a coloured rounded container is fine), and replace the hand-built hero `<motion.div>` action card with:
```tsx
<HeroCard eyebrow={next.mode === 'continue' ? 'Continue' : 'Start here'} icon={next.moduleIcon ?? '📈'} title={next.lessonLabel ?? ''} subtitle={next.moduleTitle ?? undefined} cta={next.mode === 'continue' ? 'Continue' : 'Start lesson'} to={next.to!} />
```
…guarded by the existing `next.isLoading` skeleton and `caught_up`/`!next.to` branches (keep those — for caught_up render the existing celebratory block or a simple `GradientButton to="/lessons"`). Import `HeroCard`, `RobotEddie`, `GradientButton`.
- [ ] **Step 2: Add a `ModuleTiles` section to `Home.tsx`** — using the already-fetched `modules` (from `contentApi.listModules()` — `ModuleOut{id,title,icon,locked,topic,order_index}`) render a 2-col grid of `ModuleTile`, sorted by `order_index`; map each topic to an accent+tint via a local `TOPIC_STYLE: Record<string,{accent:string;tint:string}>` (amber/sky/green/violet/etc., default amber); `to={`/lessons/${m.id}`}`, `locked={m.locked}`, `subtitle={m.locked ? 'Locked' : 'Open'}`, and mark `recommended` on the module id matching `recs?.continue_learning?.[0]?.module_id ?? recs?.something_new?.[0]?.module_id`. Place it under the hero + StatsBar/XP. Remove the empty-state + `CategorySection` rendering (keep `ReviewBanner` and the `<h1 className="sr-only">` + "Browse all modules" button). Keep imports tidy (remove now-unused `CategorySection`/`RecommendationCard` if no longer referenced).
- [ ] **Step 3: Verify** — `npx tsc -b`, `npm run lint`. Update `tests/unit/child-Home.test.tsx` and `tests/a11y/child-core.a11y.test.tsx`: they already mock `useNextLesson`/`useHomeGreeting`; ensure `useRecommendations` mock provides `continue_learning`/`something_new` arrays and `contentApi.listModules` is mocked to return a couple of modules so the grid renders; assert a module tile appears; drop assertions about the removed empty-state/CategorySection. Run them → green.
- [ ] **Step 4: Run full `npm test`** → all green (fix any other test that rendered Home/HomeHero).
- [ ] **Step 5: Commit** (`feat(ui): restyle Home with hero + quests grid + robot Eddie`).

---

### Task 11: Lesson progress header / chrome

**Files:** Modify `src/pages/child/Lesson.tsx`.

Add the shared lesson chrome around whichever renderer is shown: a top row with a back control, a progress bar, and the question/step count; and an Eddie speech-bubble line above the renderer (use `RobotEddie` + the lesson's existing context). Use the lesson position data already available in `Lesson.tsx` (`lessonsQ`/`levelsQ` — the current lesson's index within the level gives "X of N"; if not readily available, show the level's `lessons_completed`/`lessons_total` or omit the count rather than invent data).

- [ ] **Step 1: Add a `LessonChrome`** (inline in `Lesson.tsx` or a small local component): back chevron (`navigate(-1)` or to the level), a progress track (filled by `completedInLevel / totalInLevel` from the existing level data), and `RobotEddie size={40}` + a white speech bubble with a short encouraging line. Render it above the active renderer; don't alter the renderer props or completion flow.
- [ ] **Step 2: Verify** `npx tsc -b`, lint; run the Lesson page test if present (update only if copy/structure assertions break). Keep the existing view-ping + auto-return effects intact.
- [ ] **Step 3: Commit** (`feat(ui): lesson progress header + Eddie chrome`).

---

### Task 12: Full regression + ship

**Files:** none (verification).

- [ ] **Step 1:** `cd invest-ed/frontend && npx tsc -b && npm run lint && npm test && npm run build` → tsc clean; lint only the pre-existing `button.tsx` warning; all vitest green; build OK.
- [ ] **Step 2:** `npx cap sync ios` (the redesign ships in the web bundle; the iOS app needs an Xcode rebuild to show it).
- [ ] **Step 3:** `git push origin main`; confirm all 5 CI jobs pass.
- [ ] **Step 4:** Final code review across the feature; address any blocking findings.

## Notes for the implementer
- **Restyle only** — never change a renderer's `Props`, the `onComplete`/`onContinue` contracts, routes, data hooks, or the lesson completion/auto-return logic. If a change would alter behaviour, stop and flag it.
- Keep the quiz/scenario **radiogroup** semantics (don't regress the prior a11y fix) — `OptionCard` is `role="radio"` inside `role="radiogroup"`.
- Don't introduce `100vw`, `maximum-scale`, or remove safe-area handling. Use Tailwind tokens, not hard-coded hex (except the per-topic tile accents and the RobotEddie SVG, which are intentional).
- Backend is untouched in Phase 1.
- Phase 2 (Quests/all-modules, module "path", Stats, Progress, Coach) and Phase 3 (Login/Sign-up) are separate specs — don't build them here.
