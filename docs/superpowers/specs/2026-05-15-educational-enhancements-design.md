# Educational Enhancements Design

**Goal:** Add three educational features to the stock simulator — an Investment Time Machine showing historical returns, an Investing Tips carousel with 5-year mini charts, and Coach Eddie integration for interactive chart Q&A.

**Context:** Invest-Ed is an educational finance app for children. The simulator already has per-stock price charts, AI chart insights, news with AI summaries, and a Coach Eddie tutor (lesson-scoped). These features extend the educational depth of the simulator specifically.

---

## Feature 1: Investment Time Machine

### What It Does

A per-stock section showing what a $5,000 investment made 5, 10, and 15 years ago would be worth today. Helps users understand long-term compounding and relate returns to real-world costs like university fees.

### Backend

**New endpoint:** `GET /market/time-machine/{exchange}/{ticker}`

- Fetches the stock's `max` period history from Yahoo Finance (already supported by `LivePriceProvider.get_history`)
- Finds the closing price closest to exactly 5, 10, and 15 years ago
- Calculates growth: `current_price / historical_price * 5000`
- Returns percentage gain and final value for each available period
- If a stock doesn't have enough history (e.g. IPO'd 3 years ago), omit that period — only return periods with data

**Currency handling:**
- Primary value shown in the stock's native currency (USD for NASDAQ/NYSE, GBP for LSE, HKD for HKEX)
- USD equivalent shown alongside for non-USD stocks
- Exchange rate derived from the price data itself (no external FX API needed) — for USD stocks the USD line is the primary; for GBP stocks, show GBP primary with approximate USD conversion using a hardcoded rate (updated periodically)

**"Did you know?" fact:**
- LLM-generated (`premium=False`, cheapest model) age-appropriate comparison
- System prompt provides the dollar amounts and asks for a single relatable comparison (university fees, car, house deposit, etc.)
- Cached per ticker (10-minute TTL, same pattern as chart guide)

**Response schema:**
```python
class TimeMachinePeriod(BaseModel):
    years_ago: int
    invested: str          # "5000.00"
    current_value: str     # "14230.00"
    return_pct: float      # 184.6
    currency: str          # "USD"
    usd_equivalent: str | None  # null for USD stocks

class TimeMachineOut(BaseModel):
    ticker: str
    periods: list[TimeMachinePeriod]
    fun_fact: str          # LLM-generated age-appropriate comparison
```

### Frontend

**New component:** `InvestmentTimeMachine.tsx`

- Renders below the Chart Guide section on stock pages
- Purple border (matching the AI/educational theme)
- Three cards in a row (responsive: stack on mobile) showing 5y, 10y, 15y
- Each card: period label, final value in large green text, percentage return, and smaller currency conversion line
- Below the cards: amber "Did you know?" box with the LLM fact
- React Query with 10-minute staleTime
- Shows nothing if no periods are available (stock too new)

---

## Feature 2: Investing Tips Carousel

### What It Does

A horizontally scrollable carousel of educational tip cards. Each card teaches one investing concept with a short explanation and a 5-year mini chart from a well-known stock as a visual example. Appears on both the market browse page (general tips) and individual stock pages (contextualised tips).

### Tip Library (Static Content)

Six core tips, each with a designated example stock:

1. **"Price Doesn't Equal Value"** — A $10 stock can grow just as much as a $1,000 stock. What matters is the percentage change, not the dollar amount. Example: Compare 5yr charts of a high-price stock (BRK-B) vs a low-price stock (F) that both gained ~40%.

2. **"Companies Repeat Success"** — Great companies often keep finding ways to grow. Look for consistent upward trends over years, not days. Example: AAPL 5yr chart showing repeated growth cycles.

3. **"Time in the Market"** — The longer you hold, the more likely you are to see gains. Even after big drops, patient investors usually recover. Example: MSFT 5yr chart showing recovery from dips.

4. **"Don't Put All Your Eggs in One Basket"** — Spreading your money across different companies and industries protects you if one has a bad year. Example: Show two contrasting 5yr charts.

5. **"What Goes Down Can Come Back"** — Stock prices fall sometimes, but many strong companies bounce back. Selling during a dip locks in losses. Example: A stock that dipped then recovered over 5yr.

6. **"Small Amounts Add Up"** — You don't need thousands to start. Even small regular investments grow over time thanks to compounding. Example: Show a steadily growing 5yr chart.

### Backend

**New endpoint:** `GET /market/tips`

- Returns the static tip list with metadata (title, description, example ticker/exchange)
- No LLM call needed — tips are static content
- The frontend fetches 5-year chart data separately for each tip's example stock using the existing `getStockHistory` API

**On stock pages:** The tips carousel shows the same tips but the frontend replaces example charts with the current stock's 5-year chart where relevant, making tips contextual.

### Frontend

**New component:** `InvestingTips.tsx`

- Horizontally scrollable container with CSS scroll-snap
- Each card: amber background, bold title, 2-3 sentence explanation, mini `<AreaChart>` (Recharts) showing the example stock's 5-year data
- Dot indicators below showing current position
- On the market page: shown below market movers, above news
- On stock pages: shown below the Time Machine section, above the trade form
- Each tip card's mini chart uses the existing `getStockHistory(exchange, ticker, '5y')` API
- React Query caching with 30-minute staleTime (historical data doesn't change fast)

---

## Feature 3: Coach Eddie for Charts

### What It Does

Extends the existing Coach Eddie AI tutor to answer questions about stock charts. Users can ask things like "Why did this stock drop last week?" or "What does the volume tell me?" and get age-appropriate answers grounded in the actual chart data.

### Backend

**New endpoint:** `POST /simulator/chart-coach`

Request:
```python
class ChartCoachRequest(BaseModel):
    ticker: str
    exchange: str
    period: str            # current chart period being viewed
    message: str
    conversation_id: str | None = None
```

Response: reuses the existing `TutorChatResponse` schema (response text, conversation_id, messages_remaining).

**Implementation:**
- New `ChartCoachConversation` model (separate table from `TutorConversation`, since `tutor_conversations.lesson_id` is a non-nullable FK to lessons). Schema: `id`, `user_id` (FK), `ticker`, `exchange`, `messages` (JSON), `message_count`, `model_used`, `created_at`.
- System prompt is chart-specific: includes the stock's OHLCV stats for the selected period (same computation as existing chart-guide endpoint), plus rules about age-appropriate language and no real financial advice
- Uses `get_llm_client(premium=False)` — cheapest model
- Same message limits as the lesson tutor (configurable via settings)
- Max input length enforced (same as lesson tutor)
- Alembic migration to create the `chart_coach_conversations` table

**System prompt template:**
```
You are Coach Eddie, a friendly investing teacher for a {age}-year-old.
You're helping them understand a stock chart for {ticker} ({name}).

Here's the chart data for the {period} period:
{stats}

Rules:
1. Only discuss what the chart shows — never give investment advice
2. Use age-appropriate language (simple for 8-11, more detail for 12-14, technical terms OK for 15+)
3. Reference actual numbers from the chart data
4. If asked about something not related to this chart, say:
   "That's a great question, but let's focus on reading this chart! Try asking about what you see in the graph."
5. Keep responses under 100 words
6. Be encouraging and use questions to make them think
```

### Frontend

**Modified component:** `ChartGuide.tsx` — add an "Ask Coach Eddie about this chart" button at the bottom

**New component:** `ChartCoachPanel.tsx`
- Reuses the visual design of `CoachEddiePanel.tsx` (floating slide-up panel)
- Same chat interface: message list, input field, send button, messages remaining counter
- Receives `ticker`, `exchange`, `period` as props instead of `lessonId`
- Calls the new `/simulator/chart-coach` endpoint instead of `/tutor/chat`
- Opened by clicking the button in ChartGuide or a floating action button on the stock page

**Modified component:** `Stock.tsx` — add state for Coach Eddie panel visibility, render `ChartCoachPanel` when open

---

## Section Ordering on Stock Page

1. Stock Header (existing)
2. Price Chart (existing)
3. Chart Guide + "Ask Coach Eddie" button (existing, modified)
4. **Investment Time Machine** (new)
5. **Investing Tips Carousel** (new)
6. Trade Form (existing)
7. Stock News + AI Summary (existing)

## Section Ordering on Market Page

1. Search bar (existing)
2. Market Movers (existing)
3. **Investing Tips Carousel** (new — general tips)
4. News for Your Stocks + AI Summary (existing)

---

## Technical Notes

- All new LLM calls use `premium=False` (cheapest model)
- Yahoo Finance `max` period provides up to 30+ years of daily data for established stocks; `5y` provides 5 years — both are already supported by `get_history`
- A new `ChartCoachConversation` table is needed (separate from `tutor_conversations` which has a non-nullable FK to lessons). Requires an Alembic migration.
- Currency display: stock's native currency is primary, USD shown as secondary for non-USD stocks. Approximate conversion rates are acceptable (hardcoded, not live FX).
- All new components follow existing patterns: React Query for data fetching, Tailwind for styling, amber/purple border colour scheme
