# Educational Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three educational features to the stock simulator — Investment Time Machine (historical returns), Investing Tips carousel with 5-year charts, and Coach Eddie chat for chart Q&A.

**Architecture:** Two new backend endpoints (time-machine, chart-coach) plus one static tips endpoint added to the simulator router. One new DB model for chart coach conversations with an Alembic migration. Three new frontend components (InvestmentTimeMachine, InvestingTips, ChartCoachPanel) plus modifications to ChartGuide, Stock page, and Market page. All LLM calls use `premium=False`.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL, Alembic, React 18, React Query, Recharts, Tailwind CSS

---

### Task 1: ChartCoachConversation DB Model + Alembic Migration

**Files:**
- Modify: `backend/app/models/tutor.py`
- Create: `backend/alembic/versions/xxxx_add_chart_coach_conversations.py` (auto-generated)

- [ ] **Step 1: Add ChartCoachConversation model**

Add the following class to `backend/app/models/tutor.py` after the `TutorConversation` class:

```python
class ChartCoachConversation(Base):
    __tablename__ = "chart_coach_conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    exchange: Mapped[str] = mapped_column(String(20), nullable=False)
    messages: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    model_used: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
```

- [ ] **Step 2: Generate Alembic migration**

Run: `cd backend && alembic revision --autogenerate -m "add chart_coach_conversations table"`
Expected: New migration file created in `backend/alembic/versions/`

- [ ] **Step 3: Apply migration**

Run: `cd backend && alembic upgrade head`
Expected: Migration applies successfully, `chart_coach_conversations` table created

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/tutor.py backend/alembic/versions/
git commit -m "feat: add ChartCoachConversation model and migration"
```

---

### Task 2: Chart Coach Backend Service + Endpoint

**Files:**
- Create: `backend/app/services/chart_coach_service.py`
- Modify: `backend/app/schemas/simulator.py`
- Modify: `backend/app/routers/simulator.py`

- [ ] **Step 1: Add request schema to `backend/app/schemas/simulator.py`**

Add at the bottom of the file:

```python
class ChartCoachRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    exchange: str = Field(min_length=1, max_length=20)
    period: str = Field(min_length=1, max_length=10)
    message: str = Field(min_length=1, max_length=200)
    conversation_id: uuid.UUID | None = None
```

Note: `uuid` is already imported in this file. Add `Field` to the existing pydantic import if not already there (it is — see `TradeRequest`).

- [ ] **Step 2: Create the chart coach service at `backend/app/services/chart_coach_service.py`**

```python
from __future__ import annotations

import re
import uuid
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.tutor import ChartCoachConversation
from app.models.user import User
from app.services.llm_client import get_llm_client
from app.services.price_provider import PricePoint


class ChartCoachLimitReached(Exception):
    """User has hit the message limit for this conversation."""


class ChartCoachInputTooLong(Exception):
    """User message exceeds the maximum character limit."""


_ADVICE_PATTERNS = re.compile(
    r"\byou should (buy|sell|invest|spend|save|trade)\b"
    r"|\b(buy|sell|invest in) [A-Z][a-z]",
    re.IGNORECASE,
)

_SAFE_FALLBACK = (
    "That's a great question! Ask a parent or teacher for advice "
    "about real money decisions."
)


def _safety_filter(response: str) -> str:
    if _ADVICE_PATTERNS.search(response):
        return _SAFE_FALLBACK
    return response


def _build_stats(ticker: str, period: str, points: list[PricePoint]) -> str:
    start = points[0].close
    end = points[-1].close
    change_pct = ((end - start) / start * 100) if start > 0 else 0
    high = max(p.high for p in points)
    low = min(p.low for p in points)
    avg_vol = sum(p.volume for p in points) / len(points)
    return (
        f"Ticker: {ticker}, Period: {period}\n"
        f"Start price: {start:.2f}, End price: {end:.2f}, Change: {change_pct:+.1f}%\n"
        f"Period high: {high:.2f}, Period low: {low:.2f}\n"
        f"Average daily volume: {avg_vol:,.0f} shares\n"
        f"Number of data points: {len(points)}"
    )


def _build_system_prompt(age: int, ticker: str, name: str, period: str, stats: str) -> str:
    return (
        f"You are Coach Eddie, a friendly investing teacher for a {age}-year-old. "
        f"You're helping them understand a stock chart for {ticker} ({name}).\n\n"
        f"Here's the chart data for the {period} period:\n{stats}\n\n"
        "Rules:\n"
        "1. Only discuss what the chart shows — never give investment advice\n"
        "2. Use age-appropriate language (simple for 8-11, more detail for 12-14, technical terms OK for 15+)\n"
        "3. Reference actual numbers from the chart data\n"
        "4. If asked about something not related to this chart, say: "
        "\"That's a great question, but let's focus on reading this chart! "
        "Try asking about what you see in the graph.\"\n"
        "5. Keep responses under 100 words\n"
        "6. Be encouraging and use questions to make them think"
    )


async def chart_coach_chat(
    *,
    session: AsyncSession,
    user: User,
    ticker: str,
    exchange: str,
    name: str,
    period: str,
    message: str,
    conversation_id: uuid.UUID | None,
    points: list[PricePoint],
) -> dict[str, Any]:
    max_chars = settings.tutor_max_input_chars
    if len(message) > max_chars:
        raise ChartCoachInputTooLong(f"Message must be under {max_chars} characters")

    max_messages = settings.tutor_max_messages_free

    conversation: ChartCoachConversation | None = None
    if conversation_id:
        conversation = await session.get(ChartCoachConversation, conversation_id)

    model_name = settings.llm_free_model

    if conversation is None:
        conversation = ChartCoachConversation(
            user_id=user.id,
            ticker=ticker,
            exchange=exchange,
            messages=[],
            message_count=0,
            model_used=model_name,
        )
        session.add(conversation)
        await session.flush()

    if conversation.message_count >= max_messages:
        raise ChartCoachLimitReached(
            f"Message limit reached ({max_messages}). Start a new conversation to keep learning!"
        )

    age = (date.today() - user.dob).days // 365
    stats = _build_stats(ticker, period, points)
    system_prompt = _build_system_prompt(age, ticker, name, period, stats)

    history = [
        {"role": m["role"], "content": m["content"]}
        for m in conversation.messages
    ]
    history.append({"role": "user", "content": message})

    client = get_llm_client(premium=False)
    raw_response = await client.complete(
        system_prompt=system_prompt,
        messages=history,
        temperature=0.5,
        max_tokens=settings.tutor_max_response_tokens,
    )

    filtered_response = _safety_filter(raw_response)

    conversation.messages = [
        *conversation.messages,
        {"role": "user", "content": message},
        {"role": "assistant", "content": filtered_response},
    ]
    conversation.message_count += 2
    await session.flush()

    return {
        "response": filtered_response,
        "conversation_id": conversation.id,
        "messages_remaining": max(0, max_messages - conversation.message_count),
    }
```

- [ ] **Step 3: Add the chart-coach endpoint to `backend/app/routers/simulator.py`**

Add to the imports at the top:

```python
from app.schemas.simulator import ChartCoachRequest
from app.schemas.ai import TutorChatResponse
from app.services.chart_coach_service import (
    ChartCoachInputTooLong,
    ChartCoachLimitReached,
    chart_coach_chat,
)
```

Add the endpoint before the `/portfolio` route (after the `get_chart_guide` endpoint, around line 323):

```python
@router.post("/market/chart-coach", response_model=TutorChatResponse)
async def chart_coach(
    payload: ChartCoachRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    provider=Depends(get_price_provider),
):
    try:
        quote = provider.get_quote(payload.ticker, payload.exchange)
    except TickerNotAvailableError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticker not available")

    points = []
    if hasattr(provider, "get_history"):
        points = provider.get_history(payload.ticker, payload.exchange, payload.period)

    if len(points) < 2:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Not enough chart data for coaching")

    try:
        result = await chart_coach_chat(
            session=session,
            user=current_user,
            ticker=payload.ticker,
            exchange=payload.exchange,
            name=quote.name,
            period=payload.period,
            message=payload.message,
            conversation_id=payload.conversation_id,
            points=points,
        )
    except ChartCoachInputTooLong as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    except ChartCoachLimitReached as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(exc))

    await session.commit()
    return result
```

- [ ] **Step 4: Run type check**

Run: `cd backend && python -m py_compile app/services/chart_coach_service.py && python -m py_compile app/routers/simulator.py`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/simulator.py backend/app/services/chart_coach_service.py backend/app/routers/simulator.py
git commit -m "feat: add chart coach service and POST /market/chart-coach endpoint"
```

---

### Task 3: Time Machine Backend Endpoint

**Files:**
- Modify: `backend/app/schemas/simulator.py`
- Modify: `backend/app/routers/simulator.py`

- [ ] **Step 1: Add Time Machine schemas to `backend/app/schemas/simulator.py`**

Add at the bottom of the file:

```python
class TimeMachinePeriod(BaseModel):
    years_ago: int
    invested: str
    current_value: str
    return_pct: float
    currency: str
    usd_equivalent: str | None = None


class TimeMachineOut(BaseModel):
    ticker: str
    periods: list[TimeMachinePeriod]
    fun_fact: str
```

- [ ] **Step 2: Add the time-machine endpoint to `backend/app/routers/simulator.py`**

Add `TimeMachineOut, TimeMachinePeriod` to the import from `app.schemas.simulator`.

Add the endpoint after the `chart_coach` endpoint (before `/portfolio`):

```python
_APPROX_USD_RATES: dict[str, float] = {
    "USD": 1.0,
    "GBP": 1.27,
    "HKD": 0.128,
    "EUR": 1.08,
    "JPY": 0.0067,
    "CAD": 0.73,
    "AUD": 0.65,
}


@router.get("/market/time-machine/{exchange}/{ticker}", response_model=TimeMachineOut)
async def get_time_machine(
    exchange: str,
    ticker: str,
    current_user: User = Depends(get_current_user),
    provider=Depends(get_price_provider),
):
    if not hasattr(provider, "get_history"):
        return TimeMachineOut(ticker=ticker, periods=[], fun_fact="")

    points = provider.get_history(ticker, exchange, "max")
    if len(points) < 2:
        return TimeMachineOut(ticker=ticker, periods=[], fun_fact="")

    try:
        quote = provider.get_quote(ticker, exchange)
    except TickerNotAvailableError:
        return TimeMachineOut(ticker=ticker, periods=[], fun_fact="")

    current_price = float(quote.price)
    currency = quote.currency
    usd_rate = _APPROX_USD_RATES.get(currency, 1.0)
    invest_amount = 5000.0

    today = date.today()
    periods: list[TimeMachinePeriod] = []

    for years_ago in [5, 10, 15]:
        target_date = today.replace(year=today.year - years_ago)
        target_str = target_date.isoformat()

        # Find the point closest to the target date
        best = None
        best_diff = float("inf")
        for p in points:
            diff = abs((date.fromisoformat(p.date[:10]) - target_date).days)
            if diff < best_diff:
                best_diff = diff
                best = p
            if diff == 0:
                break

        if best is None or best_diff > 60:
            continue

        historical_price = best.close
        if historical_price <= 0:
            continue

        growth = current_price / historical_price
        current_value = invest_amount * growth
        return_pct = (growth - 1) * 100

        usd_equiv = None
        if currency != "USD":
            usd_equiv = f"{current_value * usd_rate:.2f}"

        periods.append(TimeMachinePeriod(
            years_ago=years_ago,
            invested=f"{invest_amount:.2f}",
            current_value=f"{current_value:.2f}",
            return_pct=round(return_pct, 1),
            currency=currency,
            usd_equivalent=usd_equiv,
        ))

    fun_fact = ""
    if periods:
        age = (date.today() - current_user.dob).days // 365
        best_period = max(periods, key=lambda p: p.return_pct)
        llm = get_llm_client(premium=False)
        try:
            fun_fact = await llm.complete(
                system_prompt=(
                    f"You are a friendly investing teacher for a {age}-year-old. "
                    "Write ONE short, fun 'Did you know?' fact comparing the investment return to "
                    "something relatable for a young person (university fees, a car, a holiday, "
                    "a gaming setup, etc). Keep it to 1-2 sentences. Be encouraging but never "
                    "give investment advice. Use the reader's perspective ('you' not 'they')."
                ),
                messages=[{
                    "role": "user",
                    "content": (
                        f"If someone invested ${invest_amount:.0f} in {ticker} "
                        f"{best_period.years_ago} years ago, it would be worth "
                        f"${float(best_period.current_value):,.0f} today "
                        f"({best_period.return_pct:+.0f}% return)."
                    ),
                }],
                temperature=0.7,
                max_tokens=100,
            )
            fun_fact = fun_fact.strip()
        except LLMError:
            fun_fact = ""

    return TimeMachineOut(ticker=ticker, periods=periods, fun_fact=fun_fact)
```

- [ ] **Step 3: Run type check**

Run: `cd backend && python -m py_compile app/routers/simulator.py`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/simulator.py backend/app/routers/simulator.py
git commit -m "feat: add GET /market/time-machine endpoint with LLM fun facts"
```

---

### Task 4: Tips Backend Endpoint

**Files:**
- Modify: `backend/app/schemas/simulator.py`
- Modify: `backend/app/routers/simulator.py`

- [ ] **Step 1: Add Tips schema to `backend/app/schemas/simulator.py`**

Add at the bottom of the file:

```python
class InvestingTipOut(BaseModel):
    id: str
    title: str
    description: str
    example_ticker: str
    example_exchange: str
```

- [ ] **Step 2: Add the tips endpoint to `backend/app/routers/simulator.py`**

Add `InvestingTipOut` to the import from `app.schemas.simulator`.

Add the static tip data and endpoint after the time-machine endpoint:

```python
_INVESTING_TIPS = [
    InvestingTipOut(
        id="price-vs-value",
        title="Price Doesn't Equal Value",
        description="A $10 stock can grow just as much as a $1,000 stock. What matters is the percentage change, not the dollar amount. A stock going from $10 to $15 is the same 50% gain as one going from $1,000 to $1,500!",
        example_ticker="F",
        example_exchange="NYSE",
    ),
    InvestingTipOut(
        id="repeat-success",
        title="Companies Repeat Success",
        description="Great companies often keep finding ways to grow. Look for consistent upward trends over years, not days. Companies with strong brands and loyal customers tend to keep winning.",
        example_ticker="AAPL",
        example_exchange="NASDAQ",
    ),
    InvestingTipOut(
        id="time-in-market",
        title="Time in the Market",
        description="The longer you hold, the more likely you are to see gains. Even after big drops, patient investors usually recover. Trying to time the market is nearly impossible — time IN the market is what counts.",
        example_ticker="MSFT",
        example_exchange="NASDAQ",
    ),
    InvestingTipOut(
        id="diversification",
        title="Don't Put All Your Eggs in One Basket",
        description="Spreading your money across different companies and industries protects you if one has a bad year. This is called diversification — it's one of the most important rules of investing!",
        example_ticker="JNJ",
        example_exchange="NYSE",
    ),
    InvestingTipOut(
        id="recovery",
        title="What Goes Down Can Come Back",
        description="Stock prices fall sometimes, but many strong companies bounce back. Selling during a dip locks in your losses. If the company is still strong, patience often pays off.",
        example_ticker="AMZN",
        example_exchange="NASDAQ",
    ),
    InvestingTipOut(
        id="small-amounts",
        title="Small Amounts Add Up",
        description="You don't need thousands to start investing. Even small regular investments grow over time thanks to compounding — when your returns earn their own returns. Starting early is the biggest advantage!",
        example_ticker="KO",
        example_exchange="NYSE",
    ),
]


@router.get("/market/tips", response_model=list[InvestingTipOut])
async def get_investing_tips(
    _current: User = Depends(get_current_user),
):
    return _INVESTING_TIPS
```

- [ ] **Step 3: Run type check**

Run: `cd backend && python -m py_compile app/routers/simulator.py`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/simulator.py backend/app/routers/simulator.py
git commit -m "feat: add GET /market/tips endpoint with static investing tips"
```

---

### Task 5: Backend Tests for New Endpoints

**Files:**
- Modify: `backend/tests/test_simulator.py`

- [ ] **Step 1: Add tests for the three new endpoints**

Append the following tests to `backend/tests/test_simulator.py`:

```python
async def test_time_machine_returns_periods(client):
    await _login(client)
    r = await client.get("/market/time-machine/NASDAQ/AAPL")
    assert r.status_code == 200
    body = r.json()
    assert body["ticker"] == "AAPL"
    assert isinstance(body["periods"], list)
    # Static provider may return empty periods (no max history) — just check shape
    assert "fun_fact" in body


async def test_time_machine_unknown_ticker(client):
    await _login(client, email="tm2@example.com", username="tm2")
    r = await client.get("/market/time-machine/NASDAQ/ZZZZZZ")
    assert r.status_code == 200
    body = r.json()
    assert body["periods"] == []


async def test_tips_returns_list(client):
    await _login(client, email="tips@example.com", username="tipster")
    r = await client.get("/market/tips")
    assert r.status_code == 200
    tips = r.json()
    assert len(tips) == 6
    assert tips[0]["id"] == "price-vs-value"
    assert tips[0]["title"] == "Price Doesn't Equal Value"
    assert "example_ticker" in tips[0]


async def test_chart_coach_requires_auth(client):
    r = await client.post("/market/chart-coach", json={
        "ticker": "AAPL", "exchange": "NASDAQ", "period": "1mo", "message": "What does this chart show?"
    })
    assert r.status_code == 401
```

- [ ] **Step 2: Run the new tests**

Run: `cd backend && python -m pytest tests/test_simulator.py::test_time_machine_returns_periods tests/test_simulator.py::test_time_machine_unknown_ticker tests/test_simulator.py::test_tips_returns_list tests/test_simulator.py::test_chart_coach_requires_auth -v`
Expected: All 4 tests PASS

- [ ] **Step 3: Run the full simulator test suite to check for regressions**

Run: `cd backend && python -m pytest tests/test_simulator.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_simulator.py
git commit -m "test: add tests for time-machine, tips, and chart-coach endpoints"
```

---

### Task 6: Frontend API Layer for New Endpoints

**Files:**
- Modify: `frontend/src/api/simulator.ts`

- [ ] **Step 1: Add types and API calls to `frontend/src/api/simulator.ts`**

Add the following types after the existing `NewsSummary` type:

```typescript
export type TimeMachinePeriod = {
  years_ago: number;
  invested: string;
  current_value: string;
  return_pct: number;
  currency: string;
  usd_equivalent: string | null;
};

export type TimeMachineData = {
  ticker: string;
  periods: TimeMachinePeriod[];
  fun_fact: string;
};

export type InvestingTip = {
  id: string;
  title: string;
  description: string;
  example_ticker: string;
  example_exchange: string;
};

export type ChartCoachRequest = {
  ticker: string;
  exchange: string;
  period: string;
  message: string;
  conversation_id?: string | null;
};

export type ChartCoachResponse = {
  response: string;
  conversation_id: string;
  messages_remaining: number;
};
```

Add the following methods to the `simulatorApi` object:

```typescript
  getTimeMachine: (exchange: string, ticker: string) =>
    apiFetch<TimeMachineData>(`/market/time-machine/${exchange}/${ticker}`),

  getInvestingTips: () =>
    apiFetch<InvestingTip[]>('/market/tips'),

  sendChartCoachMessage: (req: ChartCoachRequest) =>
    apiFetch<ChartCoachResponse>('/market/chart-coach', {
      method: 'POST',
      body: JSON.stringify(req),
    }),
```

- [ ] **Step 2: Run type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/simulator.ts
git commit -m "feat: add frontend API calls for time-machine, tips, and chart-coach"
```

---

### Task 7: InvestmentTimeMachine Frontend Component

**Files:**
- Create: `frontend/src/components/child/simulator/InvestmentTimeMachine.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/child/simulator/InvestmentTimeMachine.tsx`:

```tsx
import { useQuery } from '@tanstack/react-query';
import { Clock, BookOpen } from 'lucide-react';
import { simulatorApi, type TimeMachineData } from '@/api/simulator';
import { ApiError } from '@/api/client';

type Props = {
  exchange: string;
  ticker: string;
  currency: string;
};

const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: '$',
  GBP: '£',
  HKD: 'HK$',
  EUR: '€',
  JPY: '¥',
  CAD: 'C$',
  AUD: 'A$',
};

function formatValue(value: string, currency: string): string {
  const sym = CURRENCY_SYMBOLS[currency] ?? '$';
  const num = parseFloat(value);
  if (num >= 1000) {
    return `${sym}${num.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
  }
  return `${sym}${num.toFixed(2)}`;
}

export function InvestmentTimeMachine({ exchange, ticker, currency }: Props) {
  const { data, isLoading } = useQuery<TimeMachineData | null, ApiError>({
    queryKey: ['time-machine', exchange, ticker],
    queryFn: () => simulatorApi.getTimeMachine(exchange, ticker),
    staleTime: 10 * 60 * 1000,
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="rounded-2xl border-2 border-purple-200 bg-white p-4">
        <p className="text-sm text-muted-foreground">Calculating historical returns…</p>
      </div>
    );
  }

  if (!data || data.periods.length === 0) return null;

  return (
    <div className="rounded-2xl border-2 border-purple-200 bg-white p-4">
      <div className="mb-3 flex items-center gap-2">
        <Clock className="h-5 w-5 text-purple-600" />
        <h3 className="text-base font-semibold text-gray-800">Investment Time Machine</h3>
      </div>

      <p className="mb-3 text-sm text-gray-600">
        If you'd invested $5,000 in {ticker}…
      </p>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {data.periods.map((p) => (
          <div
            key={p.years_ago}
            className="rounded-xl bg-purple-50 p-3 text-center"
          >
            <div className="text-xs font-semibold text-purple-700">
              {p.years_ago} years ago
            </div>
            <div className="my-1 text-xl font-bold text-green-600">
              {formatValue(p.current_value, p.currency)}
            </div>
            <div className="text-xs text-gray-500">
              +{p.return_pct.toFixed(0)}%
            </div>
            {p.usd_equivalent && (
              <div className="mt-1 text-xs text-gray-400">
                {formatValue(p.current_value, p.currency)} · ${parseFloat(p.usd_equivalent).toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </div>
            )}
          </div>
        ))}
      </div>

      {data.fun_fact && (
        <div className="mt-3 rounded-lg bg-amber-50 p-3">
          <div className="flex items-start gap-2">
            <BookOpen className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-600" />
            <p className="text-sm text-amber-900">
              <span className="font-semibold">Did you know?</span> {data.fun_fact}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Run type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/child/simulator/InvestmentTimeMachine.tsx
git commit -m "feat: add InvestmentTimeMachine component"
```

---

### Task 8: InvestingTips Frontend Component

**Files:**
- Create: `frontend/src/components/child/simulator/InvestingTips.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/child/simulator/InvestingTips.tsx`:

```tsx
import { useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ResponsiveContainer, AreaChart, Area } from 'recharts';
import { Lightbulb } from 'lucide-react';
import { simulatorApi, type InvestingTip, type PricePoint } from '@/api/simulator';

function MiniChart({ exchange, ticker }: { exchange: string; ticker: string }) {
  const { data } = useQuery<PricePoint[] | null>({
    queryKey: ['stock-history', exchange, ticker, '5y'],
    queryFn: () => simulatorApi.getStockHistory(exchange, ticker, '5y'),
    staleTime: 30 * 60 * 1000,
  });

  const points = data ?? [];
  if (points.length < 2) {
    return (
      <div className="flex h-12 items-center justify-center rounded-md bg-amber-100 text-xs text-amber-600">
        Loading chart…
      </div>
    );
  }

  const isPositive = points[points.length - 1].close >= points[0].close;
  const color = isPositive ? '#16a34a' : '#dc2626';

  return (
    <ResponsiveContainer width="100%" height={48}>
      <AreaChart data={points}>
        <defs>
          <linearGradient id={`tipGrad-${ticker}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.3} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="close"
          stroke={color}
          strokeWidth={1.5}
          fill={`url(#tipGrad-${ticker})`}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

type Props = {
  contextTicker?: string;
  contextExchange?: string;
};

export function InvestingTips({ contextTicker, contextExchange }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeIndex, setActiveIndex] = useState(0);

  const { data: tips } = useQuery<InvestingTip[] | null>({
    queryKey: ['investing-tips'],
    queryFn: () => simulatorApi.getInvestingTips(),
    staleTime: 30 * 60 * 1000,
  });

  if (!tips || tips.length === 0) return null;

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollLeft, clientWidth } = scrollRef.current;
    const idx = Math.round(scrollLeft / (clientWidth * 0.65));
    setActiveIndex(Math.min(idx, tips.length - 1));
  };

  return (
    <div className="rounded-2xl border-2 border-amber-200 bg-white p-4">
      <div className="mb-3 flex items-center gap-2">
        <Lightbulb className="h-5 w-5 text-amber-600" />
        <h3 className="text-base font-semibold text-gray-800">Investing Tips</h3>
      </div>

      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex gap-3 overflow-x-auto scroll-smooth pb-2"
        style={{ scrollSnapType: 'x mandatory' }}
      >
        {tips.map((tip) => {
          const chartTicker = contextTicker ?? tip.example_ticker;
          const chartExchange = contextExchange ?? tip.example_exchange;
          return (
            <div
              key={tip.id}
              className="min-w-[220px] max-w-[260px] flex-shrink-0 rounded-xl border border-amber-200 bg-amber-50 p-3"
              style={{ scrollSnapAlign: 'start' }}
            >
              <h4 className="mb-1.5 text-xs font-bold text-amber-800">{tip.title}</h4>
              <p className="mb-2 text-xs leading-relaxed text-gray-700">{tip.description}</p>
              <div className="overflow-hidden rounded-md">
                <MiniChart exchange={chartExchange} ticker={chartTicker} />
              </div>
              <p className="mt-1 text-center text-[10px] text-gray-400">
                {chartTicker} · 5yr
              </p>
            </div>
          );
        })}
      </div>

      <div className="mt-2 flex justify-center gap-1">
        {tips.map((_, i) => (
          <span
            key={i}
            className={`inline-block h-1.5 w-1.5 rounded-full ${
              i === activeIndex ? 'bg-amber-500' : 'bg-gray-200'
            }`}
          />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Run type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/child/simulator/InvestingTips.tsx
git commit -m "feat: add InvestingTips carousel component with mini charts"
```

---

### Task 9: ChartCoachPanel Frontend Component

**Files:**
- Create: `frontend/src/components/child/simulator/ChartCoachPanel.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/child/simulator/ChartCoachPanel.tsx`:

```tsx
import { useState, useRef, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { simulatorApi, type ChartCoachResponse } from '@/api/simulator';
import { Button } from '@/components/ui/button';

type Message = { role: 'user' | 'assistant'; content: string };

type Props = {
  ticker: string;
  exchange: string;
  period: string;
  onClose: () => void;
};

export function ChartCoachPanel({ ticker, exchange, period, onClose }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [remaining, setRemaining] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = useMutation<ChartCoachResponse | null, Error, string>({
    mutationFn: (msg) =>
      simulatorApi.sendChartCoachMessage({
        ticker,
        exchange,
        period,
        message: msg,
        conversation_id: conversationId ?? null,
      }),
    onSuccess: (data) => {
      if (!data) return;
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data.response },
      ]);
      setConversationId(data.conversation_id);
      setRemaining(data.messages_remaining);
    },
  });

  const handleSend = () => {
    const msg = input.trim();
    if (!msg || sendMessage.isPending) return;
    setMessages((prev) => [...prev, { role: 'user', content: msg }]);
    setInput('');
    sendMessage.mutate(msg);
  };

  return (
    <div className="fixed inset-x-0 bottom-0 z-50 mx-auto max-w-2xl animate-in slide-in-from-bottom">
      <div className="rounded-t-2xl border-2 border-amber-200 bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-amber-100 px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="text-xl">💡</span>
            <span className="font-bold text-gray-900">Coach Eddie</span>
            <span className="rounded-full bg-purple-100 px-2 py-0.5 text-xs text-purple-700">{ticker} Chart</span>
          </div>
          <div className="flex items-center gap-3">
            {remaining !== null && (
              <span className="text-xs text-gray-400">{remaining} messages left</span>
            )}
            <button onClick={onClose} className="text-lg text-gray-400 hover:text-gray-600">✕</button>
          </div>
        </div>

        <div className="max-h-64 space-y-3 overflow-y-auto p-4">
          {messages.length === 0 && (
            <p className="text-center text-sm text-gray-400">
              Ask me anything about this {ticker} chart! 📊
            </p>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[80%] rounded-xl px-3 py-2 text-sm ${
                  m.role === 'user'
                    ? 'bg-gradient-to-r from-amber-400 to-orange-500 text-white'
                    : 'bg-amber-50 text-gray-800'
                }`}
              >
                {m.content}
              </div>
            </div>
          ))}
          {sendMessage.isPending && (
            <div className="flex justify-start">
              <div className="rounded-xl bg-amber-50 px-3 py-2 text-sm text-gray-400">
                Thinking…
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="flex gap-2 border-t border-amber-100 p-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask about the chart…"
            maxLength={200}
            className="flex-1 rounded-xl border border-amber-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-300"
            disabled={remaining === 0}
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || sendMessage.isPending || remaining === 0}
            className="rounded-xl bg-gradient-to-r from-amber-400 to-orange-500 px-4 text-white"
          >
            Send
          </Button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Run type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/child/simulator/ChartCoachPanel.tsx
git commit -m "feat: add ChartCoachPanel component for interactive chart Q&A"
```

---

### Task 10: Wire Components into Stock Page

**Files:**
- Modify: `frontend/src/components/child/simulator/ChartGuide.tsx`
- Modify: `frontend/src/pages/child/Stock.tsx`

- [ ] **Step 1: Add "Ask Coach Eddie" button to ChartGuide**

In `frontend/src/components/child/simulator/ChartGuide.tsx`, add an `onAskEddie` callback prop and a button at the bottom.

Change the `Props` type:

```tsx
type Props = {
  exchange: string;
  ticker: string;
  period: string;
  onAskEddie?: () => void;
};
```

Update the function signature to include the new prop:

```tsx
export function ChartGuide({ exchange, ticker, period, onAskEddie }: Props) {
```

Add the following just before the closing `</div>` of the outer container (after the static tip `<div>`):

```tsx
      {onAskEddie && (
        <button
          onClick={onAskEddie}
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-full bg-amber-500 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-amber-600"
        >
          <span>💡</span>
          Ask Coach Eddie about this chart
        </button>
      )}
```

- [ ] **Step 2: Update Stock.tsx to render new components and Coach Eddie panel**

In `frontend/src/pages/child/Stock.tsx`, add the imports:

```tsx
import { InvestmentTimeMachine } from '@/components/child/simulator/InvestmentTimeMachine';
import { InvestingTips } from '@/components/child/simulator/InvestingTips';
import { ChartCoachPanel } from '@/components/child/simulator/ChartCoachPanel';
```

Add state for the Coach Eddie panel near the other state declarations:

```tsx
const [showCoachEddie, setShowCoachEddie] = useState(false);
```

Add `useState` to the react import if not already there (it is already imported).

In the JSX return, update the `<ChartGuide>` to pass the `onAskEddie` callback:

```tsx
<ChartGuide
  exchange={quote.exchange}
  ticker={quote.ticker}
  period={chartPeriod}
  onAskEddie={() => setShowCoachEddie(true)}
/>
```

After the `<ChartGuide>` section and before the `<TradeForm>`, add the two new sections:

```tsx
      <div className="mb-4">
        <InvestmentTimeMachine
          exchange={quote.exchange}
          ticker={quote.ticker}
          currency={quote.currency}
        />
      </div>

      <div className="mb-4">
        <InvestingTips
          contextTicker={quote.ticker}
          contextExchange={quote.exchange}
        />
      </div>
```

After the closing `</div>` of the main container (at the very end before the closing fragment or `</div>` of the outermost wrapper), add the Coach Eddie panel:

```tsx
      {showCoachEddie && (
        <ChartCoachPanel
          ticker={quote.ticker}
          exchange={quote.exchange}
          period={chartPeriod}
          onClose={() => setShowCoachEddie(false)}
        />
      )}
```

- [ ] **Step 3: Run type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/child/simulator/ChartGuide.tsx frontend/src/pages/child/Stock.tsx
git commit -m "feat: wire InvestmentTimeMachine, InvestingTips, and ChartCoachPanel into stock page"
```

---

### Task 11: Wire InvestingTips into Market Page

**Files:**
- Modify: `frontend/src/pages/child/Market.tsx`

- [ ] **Step 1: Add InvestingTips to the market page**

In `frontend/src/pages/child/Market.tsx`, add the import:

```tsx
import { InvestingTips } from '@/components/child/simulator/InvestingTips';
```

In the `{!isSearching && ...}` block, add `<InvestingTips />` between `<MarketMovers />` and `<MarketNews />`:

```tsx
      {!isSearching && (
        <div className="mt-4 space-y-4">
          <MarketMovers />
          <InvestingTips />
          <MarketNews />
        </div>
      )}
```

- [ ] **Step 2: Run type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/child/Market.tsx
git commit -m "feat: add InvestingTips carousel to market browse page"
```

---

### Task 12: End-to-End Verification

**Files:** None (verification only)

- [ ] **Step 1: Run full backend test suite**

Run: `cd backend && python -m pytest tests/test_simulator.py -v`
Expected: All tests PASS

- [ ] **Step 2: Run frontend type check and unit tests**

Run: `cd frontend && npx tsc --noEmit && npx vitest run`
Expected: No type errors, all unit tests PASS

- [ ] **Step 3: Restart the backend server**

Kill any existing backend process and restart:
```bash
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- [ ] **Step 4: Browser-test the stock page**

Navigate to `http://localhost:5173/simulator/stock/NASDAQ/AAPL` and verify:
1. Price chart renders with period selector
2. Chart Guide with AI insight shows
3. "Ask Coach Eddie about this chart" button appears at the bottom of Chart Guide
4. Investment Time Machine section appears with 5y/10y/15y cards (if AAPL has enough history)
5. "Did you know?" fun fact appears below the time machine cards
6. Investing Tips carousel scrolls horizontally with mini 5-year charts
7. Trade Form renders below tips
8. Stock News section at the bottom

- [ ] **Step 5: Browser-test Coach Eddie**

Click the "Ask Coach Eddie about this chart" button and verify:
1. Floating panel slides up from the bottom
2. Placeholder text says "Ask me anything about this AAPL chart!"
3. Type a question like "Why is the chart green?" and send
4. Coach Eddie responds with age-appropriate analysis referencing real chart numbers
5. "Messages left" counter decrements
6. Close button dismisses the panel

- [ ] **Step 6: Browser-test the market page**

Navigate to `http://localhost:5173/simulator/market` and verify:
1. Market Movers section renders
2. Investing Tips carousel appears between movers and news
3. Tips show general example stocks (F, AAPL, MSFT, etc.) not the current stock
4. Scrolling the carousel updates the dot indicator
5. News for Your Stocks with AI summary still renders correctly

- [ ] **Step 7: Commit verification**

```bash
git log --oneline -12
```
Expected: All feature commits present in order
