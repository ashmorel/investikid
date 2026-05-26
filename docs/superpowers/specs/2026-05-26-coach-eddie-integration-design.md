# Coach Eddie + Recommendations Integration Design

## Goal

Integrate Coach Eddie with the Phase 2 recommendation engine so Eddie can reference the child's weak concepts, strengths, due reviews, and categorised recommendations. Add a standalone Coach Eddie page accessible via a floating action button, plus enrich the existing lesson-scoped Eddie with topic-specific context.

## Architecture

Two integration surfaces on top of the existing tutor infrastructure:

1. **Standalone Coach Eddie** — a new `POST /tutor/coach` endpoint (no lesson binding) that assembles the child's full learning state into Eddie's system prompt. Frontend: FAB on every child page, full-screen coach panel at `/coach` with template greeting + suggestion chips + action buttons.
2. **Enriched Lesson Eddie** — the existing `POST /tutor/chat` endpoint gets weak-concept context injected into its system prompt for the current topic.

Both reuse all Phase 2 services as read-only data sources: `get_recommendations()`, `get_strengths_and_gaps()`, `get_due_count()`, `get_due_items()`.

## Backend

### Standalone Coach Endpoint

**Route:** `POST /tutor/coach`

**Request schema:**
```python
class CoachChatRequest(BaseModel):
    message: str = Field(max_length=200)
    conversation_id: uuid.UUID | None = None
```

**Response schema:**
```python
class CoachAction(BaseModel):
    type: str          # "lesson" | "module" | "review"
    module_id: str
    lesson_id: str | None = None
    label: str         # display text, e.g. "Go to Stocks 101"

class CoachChatResponse(BaseModel):
    response: str
    conversation_id: uuid.UUID
    messages_remaining: int
    actions: list[CoachAction]
```

### Context Assembly

A new pure function `build_coach_context()` in `tutor_service.py` (or a new `coach_service.py` if the file gets too large). It takes:

- `CategorisedRecommendations` (from `get_recommendations()`)
- `StrengthsAndGaps` (from `get_strengths_and_gaps()`)
- Due SR count and items

And returns a formatted string block injected into the system prompt. Example output:

```
Your student's learning state:
- Strengths: stocks (85% mastery), savings (72%)
- Needs practice: budgeting (45% mastery, 2 weak concepts: "50/30/20 rule", "compound interest")
- Due for review: 3 concepts
- Currently working on: Stocks 101 (60% complete)
- Suggested next: Budgeting Basics (something new)
```

### System Prompt (Standalone)

```
You are Coach Eddie, a friendly money tutor for kids. You help them navigate
their learning journey — what to learn next, what to review, and how they're doing.

Rules:
1. Reference the student's actual learning state (provided below).
2. When suggesting a lesson or module, include an action marker: [ACTION:lesson:<module_id>:<lesson_id>] or [ACTION:module:<module_id>]
3. When suggesting a review session, use: [ACTION:review:<module_id>]
4. Never give real financial advice or suggest spending real money.
5. Keep responses under 120 words.
6. Use simple, encouraging language.
7. {skill_level_instruction}

{learning_state_context}
```

### Action Parsing

Post-process the LLM response to extract `[ACTION:type:module_id:lesson_id?]` markers:

- Regex: `\[ACTION:(lesson|module|review):([a-f0-9-]+)(?::([a-f0-9-]+))?\]`
- Strip markers from the response text.
- Build `CoachAction` objects with human-readable labels derived from module titles.
- If no markers found, return empty `actions` array.

This is a pure function, easily unit-tested.

### Conversation Model Change

Make `TutorConversation.lesson_id` nullable:

```python
lesson_id: Mapped[uuid.UUID | None] = mapped_column(
    UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=True
)
```

Alembic migration: `ALTER COLUMN lesson_id DROP NOT NULL`.

Standalone coach conversations have `lesson_id = None`.

### Enriched Lesson Eddie

Add weak concept injection to the existing `chat()` function in `tutor_service.py`:

1. Query `WeakConcept` rows for the lesson's topic where `resolved = False`.
2. If any exist, append to the system prompt:
   ```
   The student has struggled with these concepts in this topic: {concept_list}.
   If relevant to their question, proactively address these gaps.
   ```

No changes to the endpoint signature, request, or response schemas.

### Rate Limiting

Standalone coach uses the same per-conversation limits as lesson Eddie:
- Free: 6 messages per conversation
- Premium: 12 messages per conversation

Same `tutor_rate_limit_per_hour` applies across both surfaces.

## Frontend

### Floating Action Button (FAB)

- Rendered inside `Shell.tsx`, positioned `fixed bottom-20 right-4` (above BottomTabBar).
- Shows 💡 icon with "Coach Eddie" tooltip.
- Badge dot when `review_summary.due_count > 0` (from existing `useRecommendations` cache).
- `onClick` navigates to `/coach`.
- Hidden on `/coach` itself and on admin routes.

### Coach Page (`/coach`)

**Template greeting (no LLM):** Built client-side from `useRecommendations()` + `useStrengths()` + `useChildSession()`:

```
Hey {username}! {greeting_line}
```

Greeting line priority:
1. Due reviews > 0: "You have {N} concepts ready for review — want to go over them?"
2. continue_learning non-empty: "You're {pct}% through {module_title} — want to keep going?"
3. something_new non-empty: "I found something new for you: {module_title}!"
4. Fallback: "What would you like to learn about today?"

**Suggestion chips:** 3 tappable pills below the greeting:
- "What should I learn next?"
- "Review my weak spots"
- "How am I doing?"

Tapping a chip sends that text as the first user message.

**Chat UI:** Same bubble layout as `ChartCoachPanel` — user messages right-aligned amber gradient, Eddie messages left-aligned amber-50. "Thinking..." indicator while waiting.

**Action buttons:** When the API response includes `actions`, render them as tappable pills below Eddie's message bubble:

```tsx
{actions.map(a => (
  <Link to={actionToPath(a)} className="...pill styles...">
    {a.label} →
  </Link>
))}
```

`actionToPath` mapping:
- `lesson` → `/lessons/{module_id}/{lesson_id}`
- `module` → `/lessons/{module_id}`
- `review` → `/lessons/{module_id}` (same as module for now)

**API client:** New functions in `api/ai.ts`:
- `coachApi.sendMessage(req: CoachChatRequest): Promise<CoachChatResponse>`

**Greeting hook:** `useCoachGreeting()` — composes the template string from cached TanStack Query data. No new network request.

### Route

Add `/coach` route in `App.tsx` inside the authenticated Shell, lazy-loaded.

## Testing

### Backend Unit Tests

- `test_build_coach_context` — pure function: new user (empty), user with strengths + gaps, user with due reviews. Verify the formatted string contains expected data.
- `test_parse_actions` — pure function: no markers, single `[ACTION:lesson:...]`, multiple actions, malformed markers (ignored), markers with missing optional lesson_id.
- `test_coach_endpoint` — mock LLM, verify response has `actions` array, `conversation_id`, correct shape. Verify conversation created with `lesson_id = None`.
- `test_enriched_lesson_prompt` — verify system prompt includes weak concepts when they exist for the topic. Verify prompt unchanged when no weak concepts.

### Frontend Unit Tests

- `EddieFAB` — renders, shows badge when due_count > 0, hides badge when 0, navigates on click, hidden on /coach route.
- `CoachPanel` — renders template greeting with username, renders suggestion chips, sends message on chip tap, renders action buttons in response, action buttons link to correct paths.
- `useCoachGreeting` — returns correct greeting for: due reviews, continue learning, something new, fallback.

### Accessibility Tests

- axe audit on `/coach` page.
- FAB has `aria-label="Open Coach Eddie"`.
- Action buttons are accessible links with descriptive text.
- Chat messages use appropriate ARIA roles.

## Out of Scope

- Conversation history persistence across sessions (each visit starts fresh).
- Eddie remembering context from previous conversations.
- Voice input/output.
- Eddie inside the stock simulator (ChartCoach remains separate).
- Custom Eddie avatar/animations.
