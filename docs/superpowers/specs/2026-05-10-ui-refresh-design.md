# Plan 9: UI Refresh — Gamified & Kid-Friendly

## Goal

Transform the plain, enterprise-looking UI into a warm, gamified, kid-friendly experience. Add colour, illustrations, progress bars, and "quest" framing to make learning about money feel like playing a game.

## Scope

- Restyle the entire child-facing UI (not parent dashboard or auth pages)
- Update colour palette to warm sunset theme (amber/orange gradients, cream backgrounds)
- Add emoji icons to module cards on the lessons grid
- Add inline SVG illustrations to lesson content (cards, quizzes, scenarios)
- Add illustrated banner to module header pages
- Add trophy celebration to completion screen
- Rename "lessons" to "quests" in UI copy (not in API/data layer)
- Add XP level progress bar to home page

## Design Decisions

### Colour System

**Primary brand:** Amber-to-orange gradient (`#f59e0b` → `#ea580c`)

**Backgrounds:** Warm cream gradient (`#fffbeb` → `#fff7ed`) instead of plain white

**Cards:** White (`#fff`) with amber border (`2px solid #fde68a`) and rounded corners (`border-radius: 16px`)

**Accent chips/badges:**
- XP/Level: Amber gradient on white text
- Streak: Warm yellow background (`#fef3c7`) with brown text (`#92400e`)
- Progress bars: Amber-to-orange gradient fill on cream track (`#fef3c7`)

**Correct/incorrect feedback:** Keep existing green (`#10b981`) and red (`#ef4444`) — these are universal and recognisable.

**CSS variables to update in `index.css`:**
```
--background: 48 100% 96%        /* warm cream instead of white */
--foreground: 220 9% 12%         /* keep dark text */
--card: 0 0% 100%                /* cards stay white */
--card-foreground: 220 9% 12%
--primary: 38 92% 50%            /* amber */
--primary-foreground: 0 0% 100%
--muted: 48 100% 93%             /* warm muted */
--muted-foreground: 220 9% 46%
--accent: 48 100% 93%
--accent-foreground: 220 9% 12%
--border: 48 97% 77%             /* amber-tinted borders */
```

### Module Card Emoji Icons

Each module gets a topic-based emoji displayed large (36px+) on its card. Stored as a new `icon` field in the seed data and returned via the API.

| Module | Topic | Emoji |
|--------|-------|-------|
| What is a Stock? | stocks | 📈 |
| Compound Interest | savings | 🏦 |
| What is a REIT? | real_estate | 🏠 |
| Budgeting Basics | budgeting | 💰 |
| Needs vs Wants | budgeting | 🛒 |
| Risk & Diversification | risk | 🎲 |
| What is Crypto? | crypto | ₿ |
| How Taxes Work | taxes | 🧾 |
| Debt & Credit | debt | 💳 |
| Starting a Side Hustle | entrepreneurship | 🚀 |
| Revenue, Costs & Profit | entrepreneurship | 📊 |
| Your First Paycheque | taxes | 💷 |

### Lesson Illustrations

Each lesson type gets an illustration area above the content:

**Card lessons:** A themed SVG illustration in a coloured banner div. The illustration visually represents the concept being taught (e.g. a pie chart for 50/30/20 rule, a credit card + coins for debt).

**Quiz lessons:** A smaller illustration/visual above the question. Helps contextualise what's being asked (e.g. baskets with eggs for diversification, a volatile chart for crypto).

**Scenario lessons:** An illustration that sets the scene for the "what would you do?" prompt.

**Implementation approach:** Create a mapping of lesson titles to illustration component names. Each illustration is a small React component that renders inline SVG. Store in `src/components/child/lesson/illustrations/`. For lessons without a custom illustration, show a topic-based fallback (large emoji on gradient background).

### Quest Terminology

Replace "lesson" with "quest" in all user-facing copy:
- "3 lessons" → "3 quests"
- "Lesson 2 of 6" → "Quest 2 of 6"
- "Next lesson →" → "Next Quest →"
- "lessons complete" → "quests complete"
- "Great work!" → "Quest Complete!"

Do NOT rename in:
- API endpoints or response fields
- Database models or columns
- File names or component names (internal naming stays as "lesson")
- Backend code

### Home Page Enhancements

- Friendly greeting with emoji: "Hey {username}! 👋"
- Subtitle: "Ready to level up your money skills?"
- XP level progress bar showing current XP / next level threshold
- "Your Next Quest" card with module emoji icon, quest name, XP reward, and gradient "Start →" button
- Stats chips with gradient styling (Level, XP, streak)

### Module Page Enhancements

- Illustrated banner at top (topic-themed SVG illustration on gradient background)
- Module title and quest count in the banner
- Lesson rows with play/done/locked icons styled with amber accent

### Completion Panel Enhancements

- Trophy SVG illustration with sparkles
- "Quest Complete!" heading
- Large gradient "+{xp} XP" text
- Level progress bar showing progress to next level
- Stats summary (total XP, level, streak)
- "Next Quest →" button with gradient styling

### TopNav Restyling

- Warm white background with amber bottom border instead of grey
- Active nav link highlighted with amber underline
- "Invest-Ed" logo text with small gradient circle icon

### StatsBar Restyling

- Gradient amber chips instead of plain bordered chips
- Larger, bolder text

## Architecture

### Data layer changes

Add `icon` field to Module model:
- `backend/app/models/content.py`: Add `icon: Mapped[str] = mapped_column(String(10), default="📚")`
- `backend/app/seed/content.py`: Add `icon` to each module dict
- Migration: Add column with default value
- API schema: Include `icon` in `ModuleOut` response

### Frontend structure

New/modified files:
```
src/
  index.css                          — Update CSS variables for warm palette
  components/child/
    TopNav.tsx                       — Restyle with warm colours
    StatsBar.tsx                     — Gradient chips
    ModuleCard.tsx                   — Add emoji icon, warm card styling
    LessonRow.tsx                    — Amber accent styling
    Shell.tsx                        — Add warm background
    lesson/
      CardLesson.tsx                 — Add illustration slot above content
      QuizLesson.tsx                 — Add illustration slot above question
      ScenarioLesson.tsx             — Add illustration slot above prompt
      CompletionPanel.tsx            — Trophy illustration, gradient XP text
      LessonIllustration.tsx         — NEW: illustration resolver component
      illustrations/                 — NEW: directory of SVG illustration components
        BudgetPieChart.tsx
        EggsInBaskets.tsx
        CryptoChart.tsx
        CreditCard.tsx
        Trophy.tsx
        FallbackIllustration.tsx     — Topic emoji on gradient background
  pages/child/
    Home.tsx                         — Friendly greeting, XP bar, quest card
    Lessons.tsx                      — Update heading copy
    Module.tsx                       — Add banner illustration
    Lesson.tsx                       — Update copy to "quest"
```

### Illustration component pattern

```tsx
// LessonIllustration.tsx
type Props = { lessonTitle: string; topic: string };

const ILLUSTRATION_MAP: Record<string, React.ComponentType> = {
  "The 50/30/20 rule": BudgetPieChart,
  "Which portfolio is more diversified?": EggsInBaskets,
  // ... more mappings
};

export function LessonIllustration({ lessonTitle, topic }: Props) {
  const Illustration = ILLUSTRATION_MAP[lessonTitle];
  if (Illustration) return <Illustration />;
  return <FallbackIllustration topic={topic} />;
}
```

The fallback shows the topic's emoji large on a gradient background — so every lesson has *something* visual even without a custom illustration. Custom illustrations can be added incrementally.

## What does NOT change

- Backend API endpoints, routes, or response shapes (except adding `icon` to Module)
- Database schema (except `icon` column on modules)
- Auth pages (Login, Signup, PendingConsent)
- Parent dashboard
- Simulator pages (separate visual refresh later)
- Test infrastructure

## Testing Strategy

- Visual: Run `npm run dev`, navigate through all pages, verify styling
- Build: `npm run build` — no TypeScript or build errors
- Backend: `python -m pytest -v` — all tests still pass after migration
- Seed: Re-run seed to populate `icon` field on existing modules
- Responsive: Check mobile breakpoint (hamburger menu) still works

## Future Work (not in scope)

- Dark mode toggle
- Animated SVG illustrations (Lottie/GSAP)
- Simulator page restyling
- Parent dashboard restyling
- Custom illustrations for all 49 lessons (start with ~10-15, rest use fallback)
