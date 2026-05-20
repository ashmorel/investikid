# Invest-Ed Accessibility Authoring Guide

Short reference for building new UI without regressing the WCAG 2.2 AA
conformance documented in `conformance-2026-05.md`.

## Primitives (`frontend/src/components/a11y/`)

### `SkipLink`
A visually-hidden-until-focused "Skip to main content" anchor pointing at
`#main`. Already rendered as the first child of `Shell` in the child app.
Use only at app shell level — do not nest.

```tsx
import { SkipLink } from '@/components/a11y/SkipLink';
// inside the layout's outermost div:
<SkipLink />
```

### `useRouteFocus`
Hook that, on every Router location change, focuses `<main id="main">` and
announces `document.title` via the polite `LiveRegion`. Already called in
`Shell`. New shells (e.g. parent layout) must:

```tsx
import { useRouteFocus } from '@/components/a11y/useRouteFocus';
useRouteFocus();
// ...and render a focusable <main id="main" tabIndex={-1}> somewhere downtree.
```

### `LiveRegion` + `useAnnounce`
App-level polite live region + the hook to push messages into it. Already
wraps `<Routes>` in `App.tsx`. Use `useAnnounce` for async state changes
not covered by an existing `role="alert"` error:

```tsx
import { useAnnounce } from '@/components/a11y/useAnnounce';
const announce = useAnnounce();
announce('Trade placed');
```

### `VisuallyHidden`
Canonical `sr-only` span. Prefer this over hand-rolled `className="sr-only"`
elsewhere.

```tsx
<VisuallyHidden>Loading portfolio…</VisuallyHidden>
```

### `Disclosure`
Accessible button + region pair with `aria-expanded`/`aria-controls`. Used
for the video-lesson transcript.

```tsx
<Disclosure label="Show transcript">{lesson.transcript}</Disclosure>
```

### `Field`
Wrapper that standardises `<label htmlFor>` + control + error
(`aria-invalid`, `aria-describedby`, `role="alert"`). Use for any new form
field, especially when wrapping a bare `<input>` or native `<select>`.

```tsx
<Field id="country" label="Country" error={errors.country}>
  <select>{...}</select>
</Field>
```

### `ChartDescription`
SR summary + hidden data table for chart components. Pair with a `role="img"`
+ `aria-label` wrapper on the chart container.

```tsx
<div role="img" aria-label={summary}>
  <ResponsiveContainer>{/* recharts here */}</ResponsiveContainer>
  <ChartDescription summary={summary} columns={['Date', 'Value']} rows={rows} />
</div>
```

## Content policy: video lessons

- **Only captioned YouTube sources** may be used as `youtube_id` in a
  `video`-type lesson.
- **Every video lesson MUST ship** a non-empty `transcript: string` in its
  `content_json`, plus `captions_available: true`.
- `backend/tests/test_video_lesson_transcripts.py` enforces this on every
  seeded video lesson; the assertion runs in CI.
- The frontend `VideoLesson` component renders the transcript inside a
  `Disclosure` and shows a "Captions available" / "No captions" indicator
  driven by the `captions_available` flag.

## DO-NOT-DISABLE rule

- Never silence `eslint-plugin-jsx-a11y` or `axe-core` via blanket disables
  (`eslint-disable jsx-a11y/...`, `axe.configure(...)` global rule off, etc.).
- Fix at the source using the allowed patterns (see Task 10 of the plan):
  - `<div onClick>` → `<button type="button">` or `role="button" tabIndex={0}` + `onKeyDown` Enter/Space
  - missing `htmlFor` → add it, or wrap with `<Field>`
  - icon-only button → `aria-label` (and `aria-hidden` on the inner icon)
  - decorative SVG → `aria-hidden="true"`; meaningful SVG → `role="img"` + `aria-label`
  - contrast — adjust the Tailwind utility class (`text-gray-400` → `text-gray-600`).
    Brand-token contrast issues belong in the **conformance register** as an
    `OPEN-*` row, not in source code.
- If a finding genuinely can't be fixed without a brand/scope change, file
  it as an `OPEN-*` row in `conformance-2026-05.md` and `test.skip(...)` /
  `it.skip(...)` the affected assertion citing that row by ID.

## Where to look next

- Conformance register: `frontend/docs/accessibility/conformance-2026-05.md`
- Tests: `frontend/tests/a11y/` (one file per surface group + primitives)
- Playwright e2e a11y scan: `frontend/tests/e2e/a11y-flow.spec.ts`
- CI gate: `.github/workflows/ci.yml` → `a11y` job
