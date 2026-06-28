"""Idempotent concept taxonomy seed — upsert by slug.

Covers all 9 topics (stocks, savings, real_estate, budgeting, risk,
crypto, taxes, debt, entrepreneurship) with 3–6 concepts each.
Slugs are stable kebab-case identifiers; names are kid-friendly (ages 10–18).
difficulty_tier: 1 = foundational, 2 = intermediate, 3 = advanced.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.concept import Concept

CONCEPTS: list[dict] = [
    # ── stocks ────────────────────────────────────────────────────────────────
    {
        "topic": "stocks",
        "slug": "what-is-a-stock",
        "name": "What Is a Stock?",
        "blurb": "A stock is a tiny piece of ownership in a company. When the company grows, your piece grows too.",
        "difficulty_tier": 1,
        "order_index": 1,
    },
    {
        "topic": "stocks",
        "slug": "stock-market-basics",
        "name": "How the Stock Market Works",
        "blurb": "The stock market is a place where buyers and sellers trade shares of companies.",
        "difficulty_tier": 1,
        "order_index": 2,
    },
    {
        "topic": "stocks",
        "slug": "bull-vs-bear-market",
        "name": "Bull vs Bear Markets",
        "blurb": "A bull market means prices are rising; a bear market means prices are falling. Both are normal.",
        "difficulty_tier": 2,
        "order_index": 3,
    },
    {
        "topic": "stocks",
        "slug": "dividends",
        "name": "Dividends: Getting Paid to Own Shares",
        "blurb": "Some companies share part of their profits with shareholders as cash payments called dividends.",
        "difficulty_tier": 2,
        "order_index": 4,
    },
    {
        "topic": "stocks",
        "slug": "index-funds",
        "name": "Index Funds",
        "blurb": "An index fund lets you own a slice of hundreds of companies at once, spreading your risk.",
        "difficulty_tier": 2,
        "order_index": 5,
    },
    {
        "topic": "stocks",
        "slug": "price-to-earnings-ratio",
        "name": "The Price-to-Earnings Ratio",
        "blurb": "The P/E ratio compares a stock's price to how much the company earns — a key valuation signal.",
        "difficulty_tier": 3,
        "order_index": 6,
    },
    # ── savings ───────────────────────────────────────────────────────────────
    {
        "topic": "savings",
        "slug": "why-save",
        "name": "Why Save Money?",
        "blurb": "Saving means keeping money for later instead of spending it now — so you're ready when you need it.",
        "difficulty_tier": 1,
        "order_index": 1,
    },
    {
        "topic": "savings",
        "slug": "emergency-fund",
        "name": "Emergency Fund",
        "blurb": "An emergency fund is money set aside for surprises — like a broken phone or a sick pet.",
        "difficulty_tier": 1,
        "order_index": 2,
    },
    {
        "topic": "savings",
        "slug": "interest-basics",
        "name": "What Is Interest?",
        "blurb": "Interest is money the bank pays YOU for keeping your savings with them.",
        "difficulty_tier": 1,
        "order_index": 3,
    },
    {
        "topic": "savings",
        "slug": "saving-goals",
        "name": "Setting a Savings Goal",
        "blurb": "A savings goal gives your money a purpose — decide what you're saving for and how long it will take.",
        "difficulty_tier": 1,
        "order_index": 4,
    },
    {
        "topic": "savings",
        "slug": "compound-interest",
        "name": "Compound Interest: Money That Grows Itself",
        "blurb": "With compound interest, you earn interest on your interest — the longer you save, the faster it grows.",
        "difficulty_tier": 2,
        "order_index": 5,
    },
    {
        "topic": "savings",
        "slug": "high-yield-savings",
        "name": "High-Yield Savings Accounts",
        "blurb": "High-yield accounts pay much more interest than a regular bank account — your money works harder.",
        "difficulty_tier": 3,
        "order_index": 6,
    },
    # ── real_estate ───────────────────────────────────────────────────────────
    {
        "topic": "real_estate",
        "slug": "what-is-real-estate",
        "name": "What Is Real Estate?",
        "blurb": "Real estate means land and the buildings on it — homes, shops, and offices are all real estate.",
        "difficulty_tier": 1,
        "order_index": 1,
    },
    {
        "topic": "real_estate",
        "slug": "renting-vs-buying",
        "name": "Renting vs Buying a Home",
        "blurb": "Renting gives you flexibility; buying builds equity. Both have pros and cons depending on your life.",
        "difficulty_tier": 2,
        "order_index": 2,
    },
    {
        "topic": "real_estate",
        "slug": "mortgage-basics",
        "name": "What Is a Mortgage?",
        "blurb": "A mortgage is a loan used to buy a home. You repay it over many years, plus interest.",
        "difficulty_tier": 2,
        "order_index": 3,
    },
    {
        "topic": "real_estate",
        "slug": "property-as-investment",
        "name": "Property as an Investment",
        "blurb": "People buy property hoping its value rises over time, or to earn rental income from tenants.",
        "difficulty_tier": 2,
        "order_index": 4,
    },
    {
        "topic": "real_estate",
        "slug": "reits",
        "name": "REITs: Investing in Property Without Buying a Building",
        "blurb": "Real Estate Investment Trusts (REITs) let you invest in large property portfolios like buying shares.",
        "difficulty_tier": 3,
        "order_index": 5,
    },
    # ── budgeting ─────────────────────────────────────────────────────────────
    {
        "topic": "budgeting",
        "slug": "needs-vs-wants",
        "name": "Needs vs Wants",
        "blurb": "Needs are things you must have (food, shelter). Wants are extras. Knowing the difference helps you budget.",
        "difficulty_tier": 1,
        "order_index": 1,
    },
    {
        "topic": "budgeting",
        "slug": "budget-basics",
        "name": "Making a Budget",
        "blurb": "A budget is a plan for your money — you decide in advance how much you'll spend and save.",
        "difficulty_tier": 1,
        "order_index": 2,
    },
    {
        "topic": "budgeting",
        "slug": "tracking-spending",
        "name": "Tracking Your Spending",
        "blurb": "Tracking where your money goes helps you spot wasteful habits and make smarter choices.",
        "difficulty_tier": 1,
        "order_index": 3,
    },
    {
        "topic": "budgeting",
        "slug": "fifty-thirty-twenty-rule",
        "name": "The 50/30/20 Rule",
        "blurb": "A popular budgeting guide: 50% on needs, 30% on wants, 20% on savings and debt repayment.",
        "difficulty_tier": 2,
        "order_index": 4,
    },
    {
        "topic": "budgeting",
        "slug": "opportunity-cost",
        "name": "Opportunity Cost",
        "blurb": "Every time you spend money on one thing, you give up the chance to spend it on something else.",
        "difficulty_tier": 2,
        "order_index": 5,
    },
    # ── risk ──────────────────────────────────────────────────────────────────
    {
        "topic": "risk",
        "slug": "risk-vs-reward",
        "name": "Risk vs Reward",
        "blurb": "Higher potential rewards usually come with higher risk. Understanding this trade-off is key to investing.",
        "difficulty_tier": 1,
        "order_index": 1,
    },
    {
        "topic": "risk",
        "slug": "diversification",
        "name": "Diversification: Don't Put All Your Eggs in One Basket",
        "blurb": "Spreading your money across many investments means one bad one won't wipe you out.",
        "difficulty_tier": 2,
        "order_index": 2,
    },
    {
        "topic": "risk",
        "slug": "volatility",
        "name": "What Is Volatility?",
        "blurb": "Volatility describes how much an investment's price jumps up and down over time.",
        "difficulty_tier": 2,
        "order_index": 3,
    },
    {
        "topic": "risk",
        "slug": "time-horizon",
        "name": "Time Horizon",
        "blurb": "Your time horizon is how long you plan to keep your money invested. Longer = can take more risk.",
        "difficulty_tier": 2,
        "order_index": 4,
    },
    {
        "topic": "risk",
        "slug": "risk-tolerance",
        "name": "Risk Tolerance",
        "blurb": "Risk tolerance is how comfortable you feel with the chance of losing money. It's personal to everyone.",
        "difficulty_tier": 3,
        "order_index": 5,
    },
    # ── crypto ────────────────────────────────────────────────────────────────
    {
        "topic": "crypto",
        "slug": "what-is-cryptocurrency",
        "name": "What Is Cryptocurrency?",
        "blurb": "Cryptocurrency is digital money secured by code — it exists only online, with no central bank controlling it.",
        "difficulty_tier": 1,
        "order_index": 1,
    },
    {
        "topic": "crypto",
        "slug": "blockchain-basics",
        "name": "How Blockchain Works",
        "blurb": "A blockchain is a shared digital record book — every transaction is stored and can't be secretly changed.",
        "difficulty_tier": 2,
        "order_index": 2,
    },
    {
        "topic": "crypto",
        "slug": "crypto-volatility",
        "name": "Why Crypto Prices Swing So Much",
        "blurb": "Crypto prices can soar or crash within hours — it's one of the most volatile asset classes.",
        "difficulty_tier": 2,
        "order_index": 3,
    },
    {
        "topic": "crypto",
        "slug": "crypto-wallets",
        "name": "Crypto Wallets",
        "blurb": "A crypto wallet stores the keys that prove you own your cryptocurrency — like a digital safe.",
        "difficulty_tier": 2,
        "order_index": 4,
    },
    {
        "topic": "crypto",
        "slug": "defi-intro",
        "name": "Decentralised Finance (DeFi)",
        "blurb": "DeFi uses code (smart contracts) to offer banking services — lending, borrowing — without a bank.",
        "difficulty_tier": 3,
        "order_index": 5,
    },
    # ── taxes ─────────────────────────────────────────────────────────────────
    {
        "topic": "taxes",
        "slug": "what-are-taxes",
        "name": "What Are Taxes?",
        "blurb": "Taxes are money collected by the government to pay for schools, roads, hospitals, and more.",
        "difficulty_tier": 1,
        "order_index": 1,
    },
    {
        "topic": "taxes",
        "slug": "income-tax-basics",
        "name": "Income Tax Basics",
        "blurb": "Income tax is a percentage of the money you earn that goes to the government.",
        "difficulty_tier": 1,
        "order_index": 2,
    },
    {
        "topic": "taxes",
        "slug": "tax-brackets",
        "name": "Tax Brackets",
        "blurb": "Tax brackets mean you pay a higher percentage only on earnings above a certain level — not on everything.",
        "difficulty_tier": 2,
        "order_index": 3,
    },
    {
        "topic": "taxes",
        "slug": "capital-gains-tax",
        "name": "Capital Gains Tax",
        "blurb": "When you sell an investment for a profit, you may owe capital gains tax on that profit.",
        "difficulty_tier": 3,
        "order_index": 4,
    },
    {
        "topic": "taxes",
        "slug": "tax-advantaged-accounts",
        "name": "Tax-Advantaged Accounts",
        "blurb": "Accounts like ISAs or 401(k)s let your money grow with lower (or no) tax on the gains.",
        "difficulty_tier": 3,
        "order_index": 5,
    },
    # ── debt ──────────────────────────────────────────────────────────────────
    {
        "topic": "debt",
        "slug": "what-is-debt",
        "name": "What Is Debt?",
        "blurb": "Debt means borrowing money you must pay back later — usually with extra interest on top.",
        "difficulty_tier": 1,
        "order_index": 1,
    },
    {
        "topic": "debt",
        "slug": "good-debt-vs-bad-debt",
        "name": "Good Debt vs Bad Debt",
        "blurb": "Good debt can build your future (e.g., a student loan). Bad debt drains you with high interest.",
        "difficulty_tier": 1,
        "order_index": 2,
    },
    {
        "topic": "debt",
        "slug": "credit-cards",
        "name": "How Credit Cards Work",
        "blurb": "Credit cards let you borrow money for purchases and pay it back. Miss a payment and interest piles up fast.",
        "difficulty_tier": 2,
        "order_index": 3,
    },
    {
        "topic": "debt",
        "slug": "interest-rates-on-debt",
        "name": "Interest Rates on Debt",
        "blurb": "The interest rate on a loan tells you how much extra you'll pay for borrowing — the higher, the worse.",
        "difficulty_tier": 2,
        "order_index": 4,
    },
    {
        "topic": "debt",
        "slug": "debt-snowball-avalanche",
        "name": "Paying Off Debt: Snowball vs Avalanche",
        "blurb": "Snowball = pay smallest debt first; Avalanche = pay highest-rate first. Both beat paying minimums.",
        "difficulty_tier": 3,
        "order_index": 5,
    },
    # ── entrepreneurship ──────────────────────────────────────────────────────
    {
        "topic": "entrepreneurship",
        "slug": "what-is-an-entrepreneur",
        "name": "What Is an Entrepreneur?",
        "blurb": "An entrepreneur is someone who spots a problem, creates a solution, and builds a business around it.",
        "difficulty_tier": 1,
        "order_index": 1,
    },
    {
        "topic": "entrepreneurship",
        "slug": "revenue-vs-profit",
        "name": "Revenue vs Profit",
        "blurb": "Revenue is total money earned; profit is what's left after paying all costs. You need profit to survive.",
        "difficulty_tier": 1,
        "order_index": 2,
    },
    {
        "topic": "entrepreneurship",
        "slug": "business-model",
        "name": "What Is a Business Model?",
        "blurb": "A business model explains how a company makes money — selling products, subscriptions, ads, and more.",
        "difficulty_tier": 2,
        "order_index": 3,
    },
    {
        "topic": "entrepreneurship",
        "slug": "startup-funding",
        "name": "How Startups Get Funded",
        "blurb": "Startups can raise money from friends, angel investors, or venture capitalists in exchange for equity.",
        "difficulty_tier": 3,
        "order_index": 4,
    },
    {
        "topic": "entrepreneurship",
        "slug": "break-even-point",
        "name": "Break-Even Point",
        "blurb": "The break-even point is when your revenue equals your costs — you're no longer losing money.",
        "difficulty_tier": 2,
        "order_index": 5,
    },
]


async def seed_concepts(session: AsyncSession) -> int:
    """Upsert the concept taxonomy by slug; refreshes all mutable fields. Returns total count."""
    existing = {
        row.slug: row
        for row in (await session.scalars(select(Concept))).all()
    }
    for spec in CONCEPTS:
        row = existing.get(spec["slug"])
        if row is None:
            session.add(Concept(**spec))
        else:
            row.topic = spec["topic"]
            row.name = spec["name"]
            row.blurb = spec.get("blurb")
            row.difficulty_tier = spec["difficulty_tier"]
            row.order_index = spec["order_index"]
    await session.flush()
    return len(CONCEPTS)
