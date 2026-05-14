# Adaptive AI — Personalised Learning Engine

## Goal

Add an AI layer that learns from each user's behaviour and skill level, then adapts content ordering, generates supplementary practice material, and provides an optional AI tutor — making learning feel personal rather than one-size-fits-all.

## Scope

- Skill profile tracking (topic mastery + weak concept tagging)
- Deterministic recommendation engine for smart quest ordering
- LLM-powered practice content generation (grounded in existing lessons)
- Optional AI tutor character ("Coach Eddie") on quiz/scenario lessons
- Provider-agnostic LLM client (OpenAI / Anthropic via config)
- Premium tier: stronger model, higher tutor message limits
- Hallucination controls throughout

## Design Decisions

### Skill Profile — Data Model

Two new tables track what each user knows and where they struggle.

**`topic_mastery`** — one row per user per topic:

| Column | Type | Purpose |
|--------|------|---------|
| user_id | UUID FK → users | |
| topic | VARCHAR(30) | Matches Module.topic |
| mastery_score | FLOAT | 0.0 to 1.0, starts at 0 |
| quizzes_attempted | INT | Total quiz/scenario attempts in this topic |
| quizzes_correct | INT | Total correct answers |
| last_activity_at | TIMESTAMP | For recency-weighted recommendations |

Primary key: `(user_id, topic)`. No separate `id` column needed.

**`weak_concepts`** — one row per concept the user has struggled with:

| Column | Type | Purpose |
|--------|------|---------|
| id | UUID PK | |
| user_id | UUID FK → users | |
| topic | VARCHAR(30) | |
| concept | VARCHAR(200) | Extracted from lesson title / question text |
| times_wrong | INT | How many times they got related questions wrong |
| times_reinforced | INT | How many times they've since got it right or done practice |
| resolved | BOOL | True once times_reinforced >= 2 |
| created_at | TIMESTAMP | |

Index on `(user_id, topic, resolved)` for efficient lookups.

**Update logic (in `complete_lesson`):**

1. Look up the lesson's module to get the topic.
2. Upsert `topic_mastery`: increment `quizzes_attempted`, and if correct also increment `quizzes_correct`. Recalculate `mastery_score` as `quizzes_correct / quizzes_attempted`. Update `last_activity_at`.
3. If the answer was wrong: upsert `weak_concepts` using the lesson title as the concept name. Increment `times_wrong`.
4. If the answer was right and a matching unresolved `weak_concepts` row exists for this topic: increment `times_reinforced`. If `times_reinforced >= 2`, set `resolved = True`.

Card lessons (no right/wrong) update `last_activity_at` only.

### Recommendation Engine

Pure Python logic in `backend/app/services/recommendation_service.py`. No LLM calls — deterministic, fast, testable.

**What it decides:**
- Which quest to suggest next on the Home page ("Your Next Quest")
- Personalised ordering of modules on the Quests grid
- Which topics need reinforcement

**Scoring algorithm — each module gets a composite score:**

| Factor | Weight | Logic |
|--------|--------|-------|
| Readiness | 0.4 | Prefer modules whose prerequisite topics the user has mastery >= 0.5 on. Modules with unmet prerequisites score 0 for this factor. |
| Weakness | 0.3 | Boost modules whose topic matches unresolved weak concepts. More unresolved concepts = higher score. |
| Freshness | 0.2 | Prefer topics the user hasn't engaged with recently. Calculated as days since last_activity_at, capped at 30. |
| Completion | 0.1 | Partially-started modules score highest (momentum). Untouched modules score medium. Fully completed modules score lowest. |

Final score = weighted sum, normalised to 0-1. Ties broken by `Module.order_index`.

**Topic prerequisite map:**

```python
TOPIC_PREREQUISITES: dict[str, list[str]] = {
    "stocks": [],
    "savings": [],
    "budgeting": [],
    "risk": ["stocks"],
    "real_estate": ["stocks"],
    "crypto": ["stocks", "risk"],
    "taxes": ["budgeting"],
    "debt": ["budgeting"],
    "entrepreneurship": ["budgeting"],
}
```

**API:**

`GET /recommendations` returns:
```json
{
  "next_quest": {
    "module_id": "uuid",
    "lesson_id": "uuid",
    "reason": "Practice your weak spots in budgeting"
  },
  "suggested_modules": [
    { "module_id": "uuid", "score": 0.85, "reason": "You're ready for this" },
    { "module_id": "uuid", "score": 0.72, "reason": "Reinforce compound interest" }
  ]
}
```

Reason strings are template-based (not LLM-generated): "Practice your weak spots in {topic}", "You're ready for a new topic: {title}", "Continue where you left off", "Reinforce {concept}".

### AI Content Generator

LLM-powered supplementary practice for users who get questions wrong. New service `backend/app/services/ai_content_service.py`.

**Trigger:** When a user completes a quiz/scenario lesson incorrectly, the completion response includes `practice_available: true`. The frontend shows a "Practice this" button.

**Endpoint:** `POST /lessons/{lesson_id}/practice`

Request body: `{ "wrong_answer_index": 2 }` (optional, helps the LLM understand the misconception).

**Flow:**

1. Load the original lesson's `content_json` and the module's topic.
2. Check `generated_content` cache for this lesson + concept combination.
3. Cache hit → return cached quiz JSON.
4. Cache miss → build a grounded prompt:
   - System: "You are a quiz generator for a children's financial education app. Generate a single multiple-choice question that tests the same concept as the provided lesson, but from a different angle. Only use facts from the provided lesson content. Do not introduce new financial claims, mention real companies, or give financial advice. Return valid JSON matching the schema exactly."
   - User: the original `content_json` + the user's wrong answer + the correct explanation.
5. LLM returns JSON. Pydantic validates against the quiz schema (`question: str`, `choices: list[str]` with 3-4 items, `answer_index: int` within bounds, `explanation: str`).
6. Validation failure → retry once with "Your response was not valid JSON. Try again."
7. Second failure → return a fallback: re-serve the original question with shuffled choices.
8. Store valid response in `generated_content` table.
9. Return to frontend in the same shape as a quiz lesson.

**Hallucination controls:**

| Control | Implementation |
|---------|---------------|
| Grounded prompts | Every call includes the original lesson content as the sole source of facts |
| Structured output | LLM must return JSON matching the quiz Pydantic schema |
| Fact boundary | System prompt: "Only use facts from the provided lesson content. Do not introduce new financial claims." |
| Low temperature | 0.3 for content generation |
| Response validation | Pydantic schema check, answer_index bounds check, non-empty fields |
| Graceful fallback | If LLM fails twice, serve the original question with shuffled choices |

**Caching — `generated_content` table:**

| Column | Type | Purpose |
|--------|------|---------|
| id | UUID PK | |
| lesson_id | UUID FK → lessons | The source lesson |
| concept | VARCHAR(200) | The concept being practised |
| content_json | JSON | The generated quiz in standard quiz format |
| model_used | VARCHAR(50) | Which LLM model generated this |
| created_at | TIMESTAMP | |

Unique constraint on `(lesson_id, concept, model_used)`. Multiple users with the same weak concept on the same lesson and model tier share the cached content.

**Premium:** Free users get the cheap model (GPT-4o-mini / Claude Haiku). Premium users get the stronger model (GPT-4o / Claude Sonnet). Premium-generated content is cached separately (keyed by model tier) so free users don't get served premium-quality content from cache.

Practice quizzes do not award XP but do update the skill profile (reinforcing weak concepts if answered correctly).

### Coach Eddie — AI Tutor

An optional conversational tutor on quiz and scenario lessons. Not a general chatbot — strictly scoped to the current lesson.

**UX:**
- "Ask Coach Eddie" button appears below quiz/scenario questions
- Opens a slide-up chat panel within the lesson page
- Child can type questions; Eddie responds in a friendly, encouraging tone
- Tone adapts to skill level: low mastery (< 0.3) gets very simple language and encouragement, medium (0.3-0.7) gets clear explanations, high (> 0.7) gets deeper challenges

**Conversation constraints (all configurable via .env):**

```
TUTOR_MAX_MESSAGES_FREE=6
TUTOR_MAX_MESSAGES_PREMIUM=12
TUTOR_RATE_LIMIT_PER_HOUR=10
TUTOR_MAX_INPUT_CHARS=200
TUTOR_MAX_RESPONSE_TOKENS=150
```

**System prompt:**

"You are Coach Eddie, a friendly and encouraging money tutor for kids learning about finance. You are helping with a specific lesson — its content is provided below. Rules: (1) Only explain concepts from the provided lesson content. (2) Never give real financial advice or suggest the child spend, save, or invest real money. (3) Never mention specific real companies, stock prices, or crypto values. (4) Keep responses under 100 words. (5) Use simple, encouraging language. (6) If the child asks something outside the lesson topic, say: 'Great question! That's outside what we're covering in this quest — ask a parent or teacher!' (7) Adapt your language to the child's skill level: {skill_level_instruction}."

**Backend:**

Endpoint: `POST /tutor/chat`

Request body:
```json
{
  "lesson_id": "uuid",
  "message": "I don't understand why that's the answer",
  "conversation_id": "uuid or null"
}
```

Response: Server-Sent Events (SSE) stream of text chunks, plus a final JSON event with the complete message and updated conversation_id.

**`tutor_conversations` table:**

| Column | Type | Purpose |
|--------|------|---------|
| id | UUID PK | conversation_id |
| user_id | UUID FK → users | |
| lesson_id | UUID FK → lessons | |
| messages | JSON | Array of `{ role, content, timestamp }` |
| message_count | INT | For enforcing limits |
| created_at | TIMESTAMP | |
| model_used | VARCHAR(50) | Which model powered this conversation |

**Safety:**
- Input: reject messages over 200 chars, rate limit per config
- Output: regex scan for financial advice patterns ("you should buy/invest/spend"). If matched, replace with: "That's a great question! Ask a parent or teacher for advice about real money decisions."
- All conversations persisted for audit
- Conversations are isolated per lesson — no cross-lesson context

**Premium:**
- Free: cheap model, `TUTOR_MAX_MESSAGES_FREE` messages per conversation, no history between sessions
- Premium: stronger model, `TUTOR_MAX_MESSAGES_PREMIUM` messages, can revisit past conversations

### LLM Client — Provider Abstraction

A thin interface all AI features call through. New file `backend/app/services/llm_client.py`.

**Interface:**

```python
class LLMClient(Protocol):
    async def complete(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 500,
        response_format: Literal["text", "json"] = "text",
    ) -> str: ...

    async def stream(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> AsyncIterator[str]: ...
```

**Implementations:**
- `OpenAIClient` — wraps the `openai` Python SDK (AsyncOpenAI)
- `AnthropicClient` — wraps the `anthropic` Python SDK (AsyncAnthropic)

**Config:**

```
LLM_PROVIDER=openai              # or "anthropic"
LLM_API_KEY=sk-...
LLM_MODEL_FREE=gpt-4o-mini       # cheap model for free tier
LLM_MODEL_PREMIUM=gpt-4o         # quality model for premium tier
```

**Usage:** `get_llm_client(premium: bool)` returns the configured provider with the appropriate model. Both `ai_content_service` and `tutor_service` call this, passing the user's `is_premium` flag.

**Error handling:** Both methods handle retries (1 retry on timeout/5xx) and raise `LLMError` on persistent failure. Callers handle gracefully — content generator falls back to the original question, tutor returns "Coach Eddie is taking a break. Try again in a moment!"

### Frontend Changes

**Modified pages:**

- `Home.tsx` — Call `GET /recommendations` instead of showing the first incomplete lesson. Display the reason string below the quest card.
- `Lesson.tsx` — After incorrect quiz/scenario completion, show "Practice this" button when `practice_available: true`. Render practice quiz using existing `QuizLesson` component.
- `QuizLesson.tsx` / `ScenarioLesson.tsx` — Add "Ask Coach Eddie" button. Opens `CoachEddiePanel`.

**New components:**

- `CoachEddiePanel.tsx` — Slide-up chat panel. Text input, message list, streaming response display. Shows message count remaining. Handles SSE stream from `/tutor/chat`.
- `PracticeQuiz.tsx` — Thin wrapper that fetches from `/lessons/{id}/practice` and renders `QuizLesson` with the generated content. Shows "Practice — no XP" label.
- `MasteryBadge.tsx` — Small component showing topic mastery as a progress ring. Used on module cards in the Quests grid.

**New API client functions in `frontend/src/api/`:**

- `getRecommendations()` → `GET /recommendations`
- `getPracticeQuiz(lessonId, wrongAnswerIndex?)` → `POST /lessons/{id}/practice`
- `sendTutorMessage(lessonId, message, conversationId?)` → `POST /tutor/chat` (SSE)
- `getMasteryProfile()` → `GET /profile/mastery`

### Endpoints Summary

**New:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/recommendations` | GET | Personalised module/quest ranking |
| `/lessons/{id}/practice` | POST | Generate/serve practice quiz |
| `/tutor/chat` | POST | Coach Eddie conversation (SSE) |
| `/profile/mastery` | GET | User's topic mastery scores + weak concepts |

**Modified:**

| Endpoint | Change |
|----------|--------|
| `POST /lessons/{id}/complete` | Updates topic_mastery, upserts weak_concepts, returns `practice_available` flag |

### New Dependencies

| Package | Purpose |
|---------|---------|
| `openai>=1.0` | OpenAI LLM client |
| `anthropic>=0.30` | Anthropic LLM client |
| `sse-starlette>=1.6` | Server-Sent Events for streaming tutor responses |

Only one of `openai`/`anthropic` is needed at runtime (based on `LLM_PROVIDER`), but both are listed as dependencies so switching is config-only.

## What Does NOT Change

- Existing lesson content, module structure, or seed data
- Auth, consent, parent dashboard
- Simulator pages
- XP/level/streak/badge systems (they continue working as-is)
- The UI refresh styling (adaptive features layer on top)

## Testing Strategy

- **Recommendation engine:** Unit tests with synthetic skill profiles. Assert correct ordering for known scenarios (new user, user with weak concepts, advanced user).
- **Skill profile updates:** Unit tests for mastery_score calculation, weak_concept upsert/resolve logic.
- **AI content generator:** Integration test with a mock LLM client that returns valid/invalid JSON. Verify Pydantic validation, caching, and fallback behaviour.
- **Coach Eddie:** Integration test with mock LLM client. Verify message limits, rate limiting, safety filter, SSE streaming.
- **LLM client:** Unit tests for each provider implementation with mocked HTTP responses. Test retry and error handling.
- **Frontend:** Manual verification of practice flow, Coach Eddie panel, recommendation display.
- **Build:** `npm run build` — no TypeScript errors. `pytest -v` — all tests pass.

## Future Work (not in scope)

- Dashboard for parents showing their child's skill profile and AI interactions
- Admin tool for reviewing/approving generated content
- Spaced repetition scheduling (revisiting resolved concepts after N days)
- Voice-based tutor interaction
- Multi-language support for Coach Eddie
- Analytics on which generated questions are most effective
