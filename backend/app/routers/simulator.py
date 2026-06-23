import asyncio
from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.rate_limit import limiter
from app.models.audit import AuditLog
from app.models.content import LessonCompletion
from app.models.simulator import Holding, Portfolio, Trade
from app.models.user import User, UserProgress
from app.routers.users import get_current_user
from app.schemas.ai import TutorChatResponse
from app.schemas.simulator import (
    ChartCoachRequest,
    ExchangeMoversOut,
    HoldingOut,
    InvestingTipOut,
    MarketMoverOut,
    MissionRewardOut,
    NewsSummaryOut,
    PortfolioOut,
    PortfolioSnapshot,
    PortfolioSummaryOut,
    PricePointOut,
    QuoteOut,
    RewardsOut,
    SetCurrencyRequest,
    StockNewsOut,
    TimeMachineOut,
    TimeMachinePeriod,
    TradeConfigOut,
    TradeOut,
    TradeRequest,
    TradeResultOut,
)
from app.services.app_settings import get_trade_commission_pct
from app.services.chart_coach_service import (
    ChartCoachInputTooLong,
    ChartCoachLimitReached,
    chart_coach_chat,
)
from app.services.content_service import record_daily_activity
from app.services.entitlements import is_premium
from app.services.fx import APPROX_USD_RATES
from app.services.gamification_service import (
    evaluate_and_award_badges,
    update_challenge_progress,
)
from app.services.guardrails import log_guardrail_event, with_guardrail_preamble
from app.services.llm_client import LLMError, get_llm_client
from app.services.moderation import moderate_output
from app.services.premium_config import premium_required_error
from app.services.price_provider import (
    LivePriceProvider,
    TickerNotAvailableError,
)
from app.services.simulator_rewards import (
    award_trade_xp,
    evaluate_apply_missions,
)
from app.services.simulator_service import (
    InsufficientFundsError,
    InsufficientSharesError,
    execute_trade,
    get_or_create_portfolio,
    reset_portfolio,
    set_portfolio_currency,
)
from app.services.tips_service import (
    generate_generic_tips,
    generate_personalised_tips,
    learning_stage,
)

router = APIRouter(tags=["simulator"])

_price_provider = LivePriceProvider()

_QUOTE_CONCURRENCY = 8


def get_price_provider():
    """Dependency so tests can override with a fake provider."""
    return _price_provider


async def _gather_quotes(provider, pairs: list[tuple[str, str]]) -> list:
    """Fetch quotes for (ticker, exchange) pairs with bounded parallelism.

    Returns a list aligned with `pairs`; failed lookups are the raised
    exception instance (callers decide the fallback).
    """
    sem = asyncio.Semaphore(_QUOTE_CONCURRENCY)

    async def _one(ticker: str, exchange: str):
        async with sem:
            try:
                return await asyncio.to_thread(provider.get_quote, ticker, exchange)
            except Exception as exc:  # caller picks fallback per item
                return exc

    return await asyncio.gather(*(_one(t, e) for t, e in pairs))


@router.get("/market/search", response_model=list[QuoteOut])
async def search_market(
    q: str,
    refresh: bool = False,
    _current: User = Depends(get_current_user),
    provider=Depends(get_price_provider),
):
    if refresh and hasattr(provider, "clear_cache"):
        provider.clear_cache()
    results = await asyncio.to_thread(provider.search, q)
    return [
        QuoteOut(ticker=r.ticker, exchange=r.exchange, name=r.name, price=r.price, currency=r.currency)
        for r in results
    ]


@router.get("/market/quote/{exchange}/{ticker}", response_model=QuoteOut)
async def get_quote(
    exchange: str,
    ticker: str,
    _current: User = Depends(get_current_user),
    provider=Depends(get_price_provider),
):
    try:
        q = await asyncio.to_thread(provider.get_quote, ticker, exchange)
    except TickerNotAvailableError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticker not available")
    return QuoteOut(ticker=q.ticker, exchange=q.exchange, name=q.name, price=q.price, currency=q.currency)


@router.get("/market/history/{exchange}/{ticker}", response_model=list[PricePointOut])
async def get_stock_history(
    exchange: str,
    ticker: str,
    period: str = "1mo",
    _current: User = Depends(get_current_user),
    provider=Depends(get_price_provider),
):
    if not hasattr(provider, "get_history"):
        return []
    points = await asyncio.to_thread(provider.get_history, ticker, exchange, period)
    return [
        PricePointOut(date=p.date, open=p.open, high=p.high, low=p.low, close=p.close, volume=p.volume)
        for p in points
    ]


@router.get("/market/movers", response_model=dict[str, ExchangeMoversOut])
async def get_market_movers(
    region: Literal["US", "GB", "HK"] = "US",
    _current: User = Depends(get_current_user),
    provider=Depends(get_price_provider),
):
    if not hasattr(provider, "get_market_movers"):
        return {}
    raw = await asyncio.to_thread(provider.get_market_movers, region)
    return {
        exchange: ExchangeMoversOut(
            winners=[MarketMoverOut(**m.__dict__) for m in data.get("winners", [])],
            losers=[MarketMoverOut(**m.__dict__) for m in data.get("losers", [])],
        )
        for exchange, data in raw.items()
    }


@router.get("/market/news", response_model=list[StockNewsOut])
async def get_market_news(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    provider=Depends(get_price_provider),
):
    if not hasattr(provider, "get_news"):
        return []
    portfolio = await session.scalar(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    if not portfolio:
        return []
    holdings = (await session.scalars(
        select(Holding).where(Holding.portfolio_id == portfolio.id)
    )).all()
    if not holdings:
        return []
    ticker_pairs = [(h.ticker, h.exchange) for h in holdings]
    items = await asyncio.to_thread(provider.get_news, ticker_pairs)
    return [StockNewsOut(**i.__dict__) for i in items]


@router.get("/market/news-summary", response_model=NewsSummaryOut)
@limiter.limit("20/hour")
async def get_news_summary(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    provider=Depends(get_price_provider),
):
    if not hasattr(provider, "get_news"):
        return NewsSummaryOut(summary="No news available right now.", tickers_mentioned=[])

    portfolio = await session.scalar(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    if not portfolio:
        return NewsSummaryOut(summary="Start investing to see personalised news!", tickers_mentioned=[])

    holdings = (await session.scalars(
        select(Holding).where(Holding.portfolio_id == portfolio.id)
    )).all()
    if not holdings:
        return NewsSummaryOut(summary="Buy some stocks and news about them will appear here!", tickers_mentioned=[])

    ticker_pairs = [(h.ticker, h.exchange) for h in holdings]
    items = await asyncio.to_thread(provider.get_news, ticker_pairs)
    if not items:
        return NewsSummaryOut(summary="No recent news for your stocks.", tickers_mentioned=[])

    age = (date.today() - current_user.dob).days // 365
    tickers = list({i.related_ticker for i in items})

    headlines = "\n".join(
        f"- [{i.related_ticker}] {i.title}: {i.summary}" for i in items[:12]
    )

    system_prompt = (
        f"You are a friendly financial news reporter for a {age}-year-old who owns "
        "these stocks. Summarise what's actually happening from the headlines below.\n"
        "Rules:\n"
        "- Start IMMEDIATELY with the news. No greeting, no 'Here's what's happening' — "
        "your first words should report the actual story.\n"
        "- Match the reader's age: 8-11 very simple words, short sentences, explain any "
        "business term; 12-14 a bit more detail but still explain jargon; 15+ normal "
        "but accessible language.\n"
        "- Be specific: name the companies/tickers and what actually happened — never a "
        "generic 'your stocks had some news'.\n"
        "- Focus on what it means for someone who owns these stocks.\n"
        "- 2-4 sentences. Encouraging and educational, never scary about losses.\n"
        "- Never give investment advice; never suggest buying or selling."
    )

    llm = get_llm_client(tier="lite")
    try:
        summary = await llm.complete(
            system_prompt=with_guardrail_preamble(
                system_prompt, language=current_user.language, allow_market_summary=True
            ),
            messages=[{"role": "user", "content": f"Here are today's headlines about my stocks:\n{headlines}"}],
            temperature=0.5,
            # "2-4 sentences" can exceed 200 tokens and get cut mid-sentence.
            max_tokens=400,
        )
    except LLMError:
        summary = "Couldn't generate a summary right now — check back soon!"

    # Kid-safe moderation seam. session + current_user are in scope here, so an
    # AuditLog moderation_block row is written when the model output is unsafe.
    _mod = await moderate_output(summary.strip(), surface="news_summary", language=current_user.language)
    if not _mod.safe:
        log_guardrail_event(
            action="output_block", surface="news_summary",
            category=_mod.category, child_id=current_user.id,
        )
        session.add(AuditLog(
            user_id=current_user.id,
            event_type="moderation_block",
            metadata_json={"surface": "news_summary", "category": _mod.category},
        ))
        await session.commit()

    return NewsSummaryOut(summary=_mod.text, tickers_mentioned=tickers)


@router.get("/market/news/{exchange}/{ticker}", response_model=list[StockNewsOut])
async def get_stock_news(
    exchange: str,
    ticker: str,
    _current: User = Depends(get_current_user),
    provider=Depends(get_price_provider),
):
    if not hasattr(provider, "get_news"):
        return []
    items = await asyncio.to_thread(provider.get_news, [(ticker, exchange)])
    return [StockNewsOut(**i.__dict__) for i in items]


@router.get("/market/news-summary/{exchange}/{ticker}", response_model=NewsSummaryOut)
@limiter.limit("20/hour")
async def get_stock_news_summary(
    request: Request,
    exchange: str,
    ticker: str,
    current_user: User = Depends(get_current_user),
    provider=Depends(get_price_provider),
):
    if not hasattr(provider, "get_news"):
        return NewsSummaryOut(summary="", tickers_mentioned=[])
    items = await asyncio.to_thread(provider.get_news, [(ticker, exchange)])
    if not items:
        return NewsSummaryOut(summary="", tickers_mentioned=[])

    age = (date.today() - current_user.dob).days // 365
    headlines = "\n".join(f"- {i.title}: {i.summary}" for i in items[:8])

    system_prompt = (
        f"You are a friendly financial news reporter for a {age}-year-old who owns "
        f"shares in {ticker}. Summarise what's actually happening with {ticker} from "
        "the headlines below.\n"
        "Rules:\n"
        "- Start IMMEDIATELY with the news. No greeting, no 'Here's the latest' — your "
        "first words should report the actual story.\n"
        "- Match the reader's age: 8-11 very simple words, short sentences, explain any "
        "business term; 12-14 a bit more detail but still explain jargon; 15+ normal "
        "but accessible language.\n"
        "- Be specific: say what actually happened in the headlines — never a generic "
        "'there was some news'.\n"
        "- Focus on what this news means for someone who owns this stock.\n"
        "- 2-3 sentences. Encouraging and educational, never scary about losses.\n"
        "- Never give investment advice; never suggest buying or selling."
    )

    llm = get_llm_client(tier="lite")
    try:
        summary = await llm.complete(
            system_prompt=with_guardrail_preamble(
                system_prompt, language=current_user.language, allow_market_summary=True
            ),
            messages=[{"role": "user", "content": f"Recent news about {ticker}:\n{headlines}"}],
            temperature=0.5,
            # "2-3 sentences" can exceed 200 tokens and get cut mid-sentence.
            max_tokens=400,
        )
    except LLMError:
        summary = ""

    # Kid-safe moderation seam. Best-effort: this endpoint has no DB session in
    # scope, so no AuditLog row is written here by design (unlike the
    # session-bearing news-summary/tutor/chart-coach surfaces).
    _mod = await moderate_output(summary.strip(), surface="news_summary", language=current_user.language)
    return NewsSummaryOut(summary=_mod.text, tickers_mentioned=[ticker])


@router.get("/market/chart-guide/{exchange}/{ticker}", response_model=NewsSummaryOut)
@limiter.limit("20/hour")
async def get_chart_guide(
    request: Request,
    exchange: str,
    ticker: str,
    period: str = "1mo",
    current_user: User = Depends(get_current_user),
    provider=Depends(get_price_provider),
):
    age = (date.today() - current_user.dob).days // 365

    if not hasattr(provider, "get_history"):
        return NewsSummaryOut(summary="", tickers_mentioned=[])

    points = await asyncio.to_thread(provider.get_history, ticker, exchange, period)
    if len(points) < 2:
        return NewsSummaryOut(summary="", tickers_mentioned=[])

    start = points[0].close
    end = points[-1].close
    change_pct = ((end - start) / start * 100) if start > 0 else 0
    high = max(p.high for p in points)
    low = min(p.low for p in points)
    avg_vol = sum(p.volume for p in points) / len(points)

    stats = (
        f"Ticker: {ticker}, Period: {period}\n"
        f"Start price: {start:.2f}, End price: {end:.2f}, Change: {change_pct:+.1f}%\n"
        f"Period high: {high:.2f}, Period low: {low:.2f}\n"
        f"Average daily volume: {avg_vol:,.0f} shares\n"
        f"Number of data points: {len(points)}"
    )

    system_prompt = (
        f"You are a friendly investing teacher for a {age}-year-old. Teach them ONE "
        f"concrete skill for READING this {ticker} chart, grounded in its real numbers.\n"
        "Rules:\n"
        "- Start IMMEDIATELY with the lesson. No greeting, no 'Looking at this chart', "
        "no 'That's a great question' — your first words must teach.\n"
        "- Match the reader's age: 8-11 very simple with an everyday analogy; "
        "12-14 a bit more detail and explain any term; 15+ slightly more technical.\n"
        "- Pick the ONE chart-reading skill most relevant to THIS chart and teach it:\n"
        "  * Trend: is it generally rising or falling over the period, and how you can tell\n"
        "  * Green vs red / up vs down moves and what makes a price move\n"
        "  * Volume: what it means and why heavy trading can signal news\n"
        "  * High vs low: what the gap between them says about volatility (steady vs jumpy)\n"
        "  * A big % change vs a small one, and what that tells you about the stock\n"
        "- NAME the skill, say what to look for, AND quote the actual figures from this "
        "chart (start/end price, the % change, the high/low, or the volume) so the "
        "lesson is anchored in real data — not generic.\n"
        "- Exactly 2-3 sentences. End with one question that sends them back to the chart.\n"
        "- Never give investment advice; never suggest buying or selling."
    )

    llm = get_llm_client(tier="standard")
    try:
        summary = await llm.complete(
            system_prompt=with_guardrail_preamble(
                system_prompt, language=current_user.language, allow_market_summary=True
            ),
            messages=[{"role": "user", "content": f"Here's the chart data:\n{stats}"}],
            temperature=0.7,
            # 2-3 sentences + a closing question can exceed 250 tokens and get
            # hard-cut mid-sentence; give headroom so the insight finishes cleanly.
            max_tokens=400,
        )
    except LLMError:
        summary = ""

    # Kid-safe moderation seam. Best-effort: this endpoint has no DB session in
    # scope, so no AuditLog row is written here by design (unlike the
    # session-bearing news-summary/tutor/chart-coach surfaces). Shares the
    # news_summary surface since it returns the same child-facing NewsSummaryOut.
    _mod = await moderate_output(summary.strip(), surface="news_summary", language=current_user.language)
    return NewsSummaryOut(summary=_mod.text, tickers_mentioned=[ticker])


@router.post("/market/chart-coach", response_model=TutorChatResponse)
@limiter.limit("10/hour")
async def chart_coach(
    request: Request,
    payload: ChartCoachRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    provider=Depends(get_price_provider),
):
    try:
        quote = await asyncio.to_thread(provider.get_quote, payload.ticker, payload.exchange)
    except TickerNotAvailableError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticker not available")

    points = []
    if hasattr(provider, "get_history"):
        points = await asyncio.to_thread(provider.get_history, payload.ticker, payload.exchange, payload.period)

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


@router.get("/market/time-machine/{exchange}/{ticker}", response_model=TimeMachineOut)
@limiter.limit("20/hour")
async def get_time_machine(
    request: Request,
    exchange: str,
    ticker: str,
    current_user: User = Depends(get_current_user),
    provider=Depends(get_price_provider),
):
    if not hasattr(provider, "get_history"):
        return TimeMachineOut(ticker=ticker, periods=[], fun_fact="")

    points = await asyncio.to_thread(provider.get_history, ticker, exchange, "max")
    if len(points) < 2:
        return TimeMachineOut(ticker=ticker, periods=[], fun_fact="")

    try:
        quote = await asyncio.to_thread(provider.get_quote, ticker, exchange)
    except TickerNotAvailableError:
        return TimeMachineOut(ticker=ticker, periods=[], fun_fact="")

    current_price = float(quote.price)
    currency = quote.currency
    usd_rate = APPROX_USD_RATES.get(currency, 1.0)
    invest_amount = 5000.0

    today = date.today()
    periods: list[TimeMachinePeriod] = []

    for years_ago in [5, 10, 15]:
        target_date = today.replace(year=today.year - years_ago)

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
        llm = get_llm_client(tier="lite")
        try:
            fun_fact = await llm.complete(
                system_prompt=with_guardrail_preamble(
                    f"You are a friendly investing teacher for a {age}-year-old. "
                    "Write ONE short, fun 'Did you know?' fact comparing the investment return to "
                    "something relatable for a young person (university fees, a car, a holiday, "
                    "a gaming setup, etc). Keep it to 1-2 sentences. Be encouraging but never "
                    "give investment advice. Use the reader's perspective ('you' not 'they').",
                    language=current_user.language,
                    allow_market_summary=True,
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
                # 1-2 sentences with a comparison can brush past 100 tokens.
                max_tokens=150,
            )
            fun_fact = fun_fact.strip()
        except LLMError:
            fun_fact = ""

        # Kid-safe moderation seam. Best-effort: this endpoint has no DB
        # session in scope, so no AuditLog row is written here by design
        # (unlike the session-bearing news-summary/tutor/chart-coach surfaces).
        _mod = await moderate_output(fun_fact, surface="time_machine", language=current_user.language)
        fun_fact = _mod.text

    return TimeMachineOut(ticker=ticker, periods=periods, fun_fact=fun_fact)


@router.get("/market/tips", response_model=list[InvestingTipOut])
@limiter.limit("30/hour")
async def get_investing_tips(
    request: Request,
    refresh: bool = False,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    generic = await generate_generic_tips(language=current_user.language)

    portfolio = await session.scalar(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    holdings: list[tuple[str, str]] = []
    if portfolio:
        rows = (await session.scalars(
            select(Holding).where(Holding.portfolio_id == portfolio.id)
        )).all()
        # Holding has no company-name column, so pass the ticker as both labels.
        holdings = [(h.ticker, h.ticker) for h in rows]

    completed = await session.scalar(
        select(func.count(LessonCompletion.id)).where(
            LessonCompletion.user_id == current_user.id
        )
    ) or 0
    stage = learning_stage(completed)
    age = (date.today() - current_user.dob).days // 365

    personalised, was_unsafe = await generate_personalised_tips(
        user_id=current_user.id, holdings=holdings, stage=stage, age=age, refresh=refresh,
        language=current_user.language,
    )
    if was_unsafe:
        session.add(AuditLog(
            user_id=current_user.id,
            event_type="moderation_block",
            metadata_json={"surface": "tips", "category": "personalised_tips"},
        ))
        await session.commit()

    seen = {t.id for t in personalised}
    merged = personalised + [t for t in generic if t.id not in seen]
    return merged[:6]


@router.get("/portfolio", response_model=PortfolioOut)
async def get_portfolio(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    provider=Depends(get_price_provider),
):
    portfolio = await get_or_create_portfolio(session, current_user)
    await session.commit()

    holdings = (await session.scalars(
        select(Holding).where(Holding.portfolio_id == portfolio.id)
    )).all()

    holding_out: list[HoldingOut] = []
    total_market_value = Decimal("0.00")
    total_unrealized = Decimal("0.00")
    quotes = await _gather_quotes(provider, [(h.ticker, h.exchange) for h in holdings])
    for h, q in zip(holdings, quotes, strict=True):
        if isinstance(q, TickerNotAvailableError):
            current_price = h.avg_buy_price  # fall back
        elif isinstance(q, Exception):
            raise q
        else:
            current_price = q.price
        market_value = (current_price * h.shares).quantize(Decimal("0.01"))
        unrealized = (market_value - (h.avg_buy_price * h.shares)).quantize(Decimal("0.01"))
        total_market_value += market_value
        total_unrealized += unrealized
        holding_out.append(HoldingOut(
            ticker=h.ticker, exchange=h.exchange, shares=h.shares,
            avg_buy_price=h.avg_buy_price, current_price=current_price,
            market_value=market_value, unrealized_pl=unrealized,
        ))

    return PortfolioOut(
        id=portfolio.id, virtual_cash=portfolio.virtual_cash, currency_code=portfolio.currency_code,
        total_value=(portfolio.virtual_cash + total_market_value).quantize(Decimal("0.01")),
        holdings_value=total_market_value.quantize(Decimal("0.01")),
        total_unrealized_pl=total_unrealized.quantize(Decimal("0.01")),
        holdings=holding_out,
    )


@router.get("/market/trade-config", response_model=TradeConfigOut)
async def get_trade_config(
    _current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    pct = await get_trade_commission_pct(session)
    return TradeConfigOut(commission_pct=pct)


@router.post("/portfolio/trades", response_model=TradeResultOut, status_code=201)
async def place_trade(
    payload: TradeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    provider=Depends(get_price_provider),
):
    if not is_premium(current_user) and not provider.is_free_tier(payload.ticker, payload.exchange):
        raise premium_required_error("ticker", payload.ticker)
    try:
        quote = await asyncio.to_thread(provider.get_quote, payload.ticker, payload.exchange)
    except TickerNotAvailableError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticker not available")

    portfolio = await get_or_create_portfolio(session, current_user)

    try:
        execution = await execute_trade(session, portfolio, quote, payload.type, payload.shares)
    except InsufficientFundsError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Insufficient virtual cash")
    except InsufficientSharesError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Insufficient shares")

    # Gamification hooks
    await update_challenge_progress(session, current_user.id, "trades_executed", increment=1)
    progress = await session.get(UserProgress, current_user.id)
    if progress is None:
        progress = UserProgress(user_id=current_user.id)
        session.add(progress)
        await session.flush()

    today_local = datetime.now(UTC).date()
    xp_awarded = await award_trade_xp(session, progress, today_local)
    streak_extended = record_daily_activity(progress, today_local)
    completed_missions = await evaluate_apply_missions(
        session, current_user.id, progress, portfolio,
        market_code=current_user.active_market_code,
    )
    cash_granted = sum(
        (m.cash_reward or Decimal("0") for m in completed_missions), Decimal("0")
    )
    # Award badges AFTER XP/missions so XP/trade-count-based badges see updated state.
    new_badges = await evaluate_and_award_badges(session, current_user.id, progress)

    await session.commit()
    trade = execution.trade
    await session.refresh(trade)
    return TradeResultOut(
        id=trade.id, ticker=trade.ticker, type=trade.type, shares=trade.shares,
        price=trade.price, executed_at=trade.executed_at,
        fee=execution.fee, commission_pct=execution.commission_pct,
        rewards=RewardsOut(
            xp_awarded=xp_awarded,
            streak_extended=streak_extended,
            cash_granted=cash_granted,
            missions_completed=[
                MissionRewardOut(id=m.id, title=m.title) for m in completed_missions
            ],
            badges_unlocked=[b.name for b in new_badges],
        ),
    )


@router.post("/portfolio/currency", response_model=PortfolioSummaryOut)
async def set_currency(
    payload: SetCurrencyRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    portfolio = await set_portfolio_currency(session, current_user, payload.currency_code)
    if portfolio is None:
        portfolio = await get_or_create_portfolio(session, current_user)
    await session.commit()
    return PortfolioSummaryOut(
        id=portfolio.id, virtual_cash=portfolio.virtual_cash, currency_code=portfolio.currency_code,
    )


@router.post("/portfolio/reset", response_model=PortfolioSummaryOut)
async def reset_portfolio_endpoint(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    portfolio = await reset_portfolio(session, current_user)
    await session.commit()
    return PortfolioSummaryOut(
        id=portfolio.id, virtual_cash=portfolio.virtual_cash, currency_code=portfolio.currency_code,
    )


@router.get("/portfolio/trades", response_model=list[TradeOut])
async def list_trades(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    portfolio = await session.scalar(select(Portfolio).where(Portfolio.user_id == current_user.id))
    if not portfolio:
        return []
    trades = (await session.scalars(
        select(Trade).where(Trade.portfolio_id == portfolio.id).order_by(Trade.executed_at.desc())
    )).all()
    return list(trades)


@router.get("/portfolio/history", response_model=list[PortfolioSnapshot])
async def portfolio_history(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    provider=Depends(get_price_provider),
):
    portfolio = await session.scalar(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    if not portfolio:
        return []

    trades = (
        await session.scalars(
            select(Trade)
            .where(Trade.portfolio_id == portfolio.id)
            .order_by(Trade.executed_at.asc())
        )
    ).all()

    if not trades:
        return []

    # Build ticker→exchange map from holdings
    all_holdings = (await session.scalars(
        select(Holding).where(Holding.portfolio_id == portfolio.id)
    )).all()
    ticker_exchange: dict[str, str] = {h.ticker: h.exchange for h in all_holdings}

    shares_held: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    cash = portfolio.virtual_cash
    # Reconstruct starting cash by reversing all trades
    for t in trades:
        cost = t.price * t.shares
        if t.type == "buy":
            cash += cost
        else:
            cash -= cost

    # Prefetch current quotes for every traded ticker in bounded parallel
    # (cached quotes are identical across snapshots; failures fall back per item).
    traded = sorted({t.ticker for t in trades})
    quote_results = await _gather_quotes(
        provider, [(tk, ticker_exchange.get(tk, "")) for tk in traded]
    )
    quote_price: dict[str, Decimal] = {
        tk: q.price for tk, q in zip(traded, quote_results, strict=True)
        if not isinstance(q, Exception)
    }

    snapshots: list[PortfolioSnapshot] = []
    seen_dates: set[str] = set()

    for t in trades:
        cost = t.price * t.shares
        if t.type == "buy":
            cash -= cost
            shares_held[t.ticker] += t.shares
        else:
            cash += cost
            shares_held[t.ticker] -= t.shares

        date_str = t.executed_at.date().isoformat()
        holding_value = Decimal("0")
        for ticker, qty in shares_held.items():
            if qty <= 0:
                continue
            price = quote_price.get(ticker)
            if price is not None:
                holding_value += price * qty
            else:
                holding_value += t.price * qty

        snapshot = PortfolioSnapshot(
            date=date_str, value=float((cash + holding_value).quantize(Decimal("0.01")))
        )
        if date_str in seen_dates:
            snapshots[-1] = snapshot
        else:
            seen_dates.add(date_str)
            snapshots.append(snapshot)

    return snapshots
