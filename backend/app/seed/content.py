from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, Level, Module

_MODULES = [
    {
        "topic": "stocks", "title": "What is a Stock?",
        "country_codes": [], "is_premium": False, "order_index": 0, "icon": "📈",
        "lessons": [
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "A stock is a slice of a company",
                "body": "When you buy a stock, you own a tiny piece of that business. If the business does well, your piece can be worth more.",
            }},
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "Why do people buy stocks?",
                "body": "Stocks can grow in value over time and some pay dividends — small cash payments to shareholders.",
            }},
            {"type": "video", "xp_reward": 10, "content_json": {
                "youtube_id": "p7HKvqRI_Bo", "caption": "What is a stock? (intro)",
                "captions_available": True,
                "transcript": (
                    "A stock is a small piece of ownership in a company. When you buy "
                    "a share, you own a tiny fraction of that business. If the company "
                    "does well and grows, your share can become worth more. If it does "
                    "poorly, your share can be worth less. Companies sell shares to "
                    "raise money, and people buy them hoping the company will grow over "
                    "time. Owning a stock does not mean you run the company — it means "
                    "you own a part of it along with many other shareholders."
                )}},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "If you own one stock in a company with 1,000,000 shares, what fraction of the company do you own?",
                "choices": ["1/100", "1/1,000,000", "1%", "All of it"],
                "answer_index": 1,
                "explanation": "One share out of one million is 1/1,000,000 of the company.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "What does it mean when a company 'pays a dividend'?",
                "choices": [
                    "It shares part of its profits with shareholders, usually as cash",
                    "It charges shareholders a yearly fee",
                    "It splits every share into two",
                    "It buys your shares back whether you want to sell or not",
                ],
                "answer_index": 0,
                "explanation": "A dividend is a slice of the company's profits paid out to shareholders — often as a small cash payment.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "A share's price rises from £2 to £3. If you owned 10 shares, how much did your investment grow?",
                "choices": ["£1", "£10", "£30", "£100"],
                "answer_index": 1,
                "explanation": "Each share gained £1 (£3 − £2). 10 shares × £1 = £10 increase in value.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Why might a company's share price go DOWN?",
                "choices": [
                    "Its profits fell, or people expect it to do worse",
                    "The stock market is open for trading",
                    "It hired a few new staff",
                    "Share prices can only ever go up over time",
                ],
                "answer_index": 0,
                "explanation": "Prices fall when more people want to sell than buy — usually because they expect the company to do worse.",
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "A share you bought for £50 is now worth £40. A friend says 'sell now before it drops more!' What's the wisest first step?",
                "choices": [
                    {"label": "Sell immediately to avoid losing more", "outcome": "Selling locks in the £10 loss. Panic-selling on a dip is one of the most common mistakes — the price may well recover."},
                    {"label": "Check WHY it dropped before deciding anything", "outcome": "Best move. If the company is still healthy, a dip can be temporary. Decisions should be based on the company, not on fear."},
                    {"label": "Borrow money to buy lots more", "outcome": "Never borrow to invest. 'Buying the dip' can work, but only after research — and never with money you can't afford to lose."},
                ],
                "correct_index": 1,
            }},
        ],
    },
    {
        "topic": "savings", "title": "Compound Interest Basics",
        "country_codes": [], "is_premium": False, "order_index": 1, "icon": "🏦",
        "lessons": [
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "Interest on your interest",
                "body": "Compound interest means you earn interest not only on your original money, but also on the interest you've already earned.",
            }},
            {"type": "video", "xp_reward": 10, "content_json": {
                "youtube_id": "MqZmwQoHmAA", "caption": "Compound interest explained simply",
                "captions_available": True,
                "transcript": (
                    "Compound interest means you earn interest on your original money "
                    "and also on the interest you have already earned. Imagine you save "
                    "100 pounds and earn 5 percent each year. After the first year you "
                    "have 105 pounds. In the second year you earn 5 percent on 105 "
                    "pounds, not just on the original 100, so you earn a little more. "
                    "Each year the amount grows faster because your interest earns its "
                    "own interest. Over many years this snowball effect can turn small "
                    "savings into a much larger amount."
                )}},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "What makes compound interest different from simple interest?",
                "choices": [
                    "You earn interest on your interest, not just your original money",
                    "It is always paid at a higher rate",
                    "It is only ever paid once",
                    "It only applies to loans, never savings",
                ],
                "answer_index": 0,
                "explanation": "Compound interest pays you on your original savings AND on the interest already earned, so it grows faster over time.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "You save £100 at 10% interest a year, compounded yearly. How much after 2 years?",
                "choices": ["£110", "£120", "£121", "£200"],
                "answer_index": 2,
                "explanation": "Year 1: £100 → £110. Year 2: £110 + 10% (£11) = £121. That extra £1 over simple interest is interest earning its own interest.",
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "You deposit £100 at 5% annual interest. How much after 10 years?",
                "choices": [
                    {"label": "£150", "outcome": "Close — but that's simple interest."},
                    {"label": "£163", "outcome": "Correct! Compounding added £13 extra."},
                    {"label": "£200", "outcome": "Too high — compounding isn't that fast at 5%."},
                ],
                "correct_index": 1,
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "You're 15. You could start saving £10 a month now, or wait until you're 25. Which is better for long-term growth?",
                "choices": [
                    {"label": "Start now at 15", "outcome": "Starting early is the single biggest advantage in saving. Those extra 10 years of compounding can more than double your final amount — even with the same monthly deposit."},
                    {"label": "Wait until 25 when you earn more", "outcome": "It feels sensible, but you'd lose 10 years of compounding. When you're young, TIME matters even more than the amount."},
                    {"label": "It makes no real difference", "outcome": "It makes a huge difference — time is compound interest's best friend."},
                ],
                "correct_index": 0,
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "Account A pays 3% interest. Account B pays 1% but gives a one-off £5 gift. You'll save £500 for one year. Which earns more?",
                "choices": [
                    {"label": "Account A (3%)", "outcome": "Correct. 3% of £500 = £15. Account B gives £5 + 1% (£5) = £10. A wins by £5 — and keeps paying 3% every year after."},
                    {"label": "Account B (the free gift)", "outcome": "The gift is tempting but one-off. A's higher rate (£15 vs £10) beats it this year and every year after."},
                    {"label": "They earn exactly the same", "outcome": "Do the maths: A earns £15, B earns £10 in total. A is better."},
                ],
                "correct_index": 0,
            }},
        ],
    },
    {
        "topic": "real_estate", "title": "What is a REIT?",
        "country_codes": [], "is_premium": False, "order_index": 2, "icon": "🏠",
        "lessons": [
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "Real Estate Investment Trust",
                "body": "A REIT is a company that owns income-producing property. You can buy shares like a stock to invest in property without buying a house.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Which is true of REITs?",
                "choices": [
                    "You need £100,000 to buy into one",
                    "They let you invest in real estate via the stock market",
                    "They are only available in the US",
                ],
                "answer_index": 1,
                "explanation": "REITs trade on exchanges like stocks.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "What is the main way a REIT makes money for investors?",
                "choices": [
                    "Rental income from the properties it owns, paid out to shareholders",
                    "Charging investors a monthly membership fee",
                    "Mining gold and selling it",
                    "Lending people money for cars",
                ],
                "answer_index": 0,
                "explanation": "REITs own income-producing property — offices, shops, flats — and pass most of the rental income to shareholders.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "What's one advantage of a REIT over buying a house to rent out?",
                "choices": [
                    "You can invest a small amount and sell your shares easily",
                    "You get to live in all of the properties",
                    "A REIT can never lose value",
                    "It removes all investment risk",
                ],
                "answer_index": 0,
                "explanation": "REITs let you invest in property with a small amount and sell quickly. A house needs a big deposit and can take months to sell.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "If property prices and rents fall sharply, what's most likely to happen to a REIT's share price?",
                "choices": [
                    "It's likely to fall too",
                    "It always rises in a downturn",
                    "It instantly turns into cash",
                    "Nothing — REIT prices are fixed",
                ],
                "answer_index": 0,
                "explanation": "REITs are tied to property, so when the property market weakens their value usually falls too. They carry real risk.",
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "You have £100 and want some exposure to property. What's realistic?",
                "choices": [
                    {"label": "Buy a house", "outcome": "£100 won't buy a house — you'd need a large deposit (often tens of thousands of pounds) plus a mortgage."},
                    {"label": "Buy shares in a REIT", "outcome": "Realistic. With £100 you can buy REIT shares, earn a slice of rental income, and sell whenever you like."},
                    {"label": "Wait until you've saved £500,000", "outcome": "You don't need to wait — REITs exist precisely so people can invest in property with small amounts."},
                ],
                "correct_index": 1,
            }},
        ],
    },
    {
        "topic": "budgeting", "title": "Budgeting Basics",
        "country_codes": [], "is_premium": False, "order_index": 3, "icon": "💰",
        "lessons": [
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "What is a budget?",
                "body": "A budget is simply a plan for your money. Each month, money comes in (income — allowance, wages, gifts) and money goes out (expenses — food, transport, fun). A budget helps you see where it all goes so you can make sure you're not spending more than you earn. Think of it like a game plan: without one, you're guessing.",
            }},
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "The 50/30/20 rule",
                "body": "A popular starting point: spend roughly 50% of your money on needs (food, transport, phone bill), 30% on wants (games, eating out, clothes you don't strictly need), and save 20%. It's not a law — just a handy guideline. If you can save more, brilliant. The point is to be intentional, not perfect.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Your income is £100 and you've spent £90. If you save the remaining £10, what does a budget call it?",
                "choices": [
                    "A surplus you can save or invest",
                    "A debt",
                    "A fixed cost",
                    "A loss",
                ],
                "answer_index": 0,
                "explanation": "Spending less than you earn leaves a surplus — money you can save or invest. Spending MORE than you earn creates a deficit (debt).",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Using the 50/30/20 rule, which of these is a 'need'?",
                "choices": [
                    "Concert tickets",
                    "Bus pass to school",
                    "New trainers when your old ones still work",
                    "A streaming subscription",
                ],
                "answer_index": 1,
                "explanation": "A bus pass for getting to school is a need — it's essential transport. The others are wants, even if they feel important!",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Alex earns £150/month and budgets: £80 food & transport, £50 entertainment, £40 clothes. What's wrong?",
                "choices": [
                    "Nothing — it's a solid budget",
                    "Too much on entertainment",
                    "Total spending (£170) exceeds income (£150)",
                    "Not enough on clothes",
                ],
                "answer_index": 2,
                "explanation": "£80 + £50 + £40 = £170, but Alex only earns £150. This budget is £20 over — it doesn't add up. The first rule: don't plan to spend more than you have.",
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "You get £200 per month from a part-time job. How would you split it?",
                "choices": [
                    {"label": "Spend it all — you earned it!", "outcome": "It feels great now, but one unexpected cost (broken phone, birthday gift) and you're stuck. No cushion."},
                    {"label": "50/30/20 split: £100 needs, £60 wants, £40 savings", "outcome": "Solid plan. You cover essentials, still have fun, and build a safety net. After 6 months you'd have £240 saved."},
                    {"label": "Save every penny", "outcome": "Impressive discipline, but unsustainable. You'll likely crack and splurge. A balanced approach lasts longer."},
                ],
                "correct_index": 1,
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "Your phone screen cracks and a repair costs £80. You have £120 in savings. What do you do?",
                "choices": [
                    {"label": "Use £80 from savings", "outcome": "This is exactly what savings are for — unexpected costs. You still have £40 left, and you can rebuild. Smart move."},
                    {"label": "Borrow £80 from a friend", "outcome": "It works short-term, but now you owe someone. If you have savings, using them avoids the social awkwardness and potential interest."},
                    {"label": "Ignore it — just use the cracked phone", "outcome": "Sometimes this is fine for a cosmetic crack, but if it's affecting usability, delaying can make it worse and cost more later."},
                ],
                "correct_index": 0,
            }},
        ],
    },
    {
        "topic": "budgeting", "title": "Needs vs Wants",
        "country_codes": [], "is_premium": False, "order_index": 4, "icon": "🛒",
        "lessons": [
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "The difference isn't always obvious",
                "body": "A need is something you genuinely can't do without — food, shelter, transport to school. A want is something nice to have. But the line is blurry: is internet a need? Probably yes in 2026. Is Netflix? Probably not. The trick is being honest with yourself about which category something really falls into.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Which of these is most clearly a 'need'?",
                "choices": [
                    "The latest iPhone",
                    "A school uniform",
                    "Takeaway coffee",
                    "A Spotify subscription",
                ],
                "answer_index": 1,
                "explanation": "A school uniform is required — you literally can't attend without it. The others are wants, even if they feel essential. A basic phone is a need; the latest model is a want.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Which pair is correctly sorted as (need, then want)?",
                "choices": [
                    "School lunch, then designer trainers",
                    "Cinema ticket, then bus fare",
                    "Video game, then electricity bill",
                    "Concert ticket, then weekly food shop",
                ],
                "answer_index": 0,
                "explanation": "School lunch is a need; designer trainers are a want. In every other pair, a want is listed before the need.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "A '£3 a day' treat seems tiny. Bought every school day for a month (20 days), roughly what does it cost?",
                "choices": ["£6", "£20", "£60", "£3"],
                "answer_index": 2,
                "explanation": "£3 × 20 = £60 a month. Small, frequent wants add up fast — which is exactly why tracking them matters.",
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "Your friends invite you to a music festival (£150 ticket). You've been saving for a laptop (£500, currently saved £350). What do you do?",
                "choices": [
                    {"label": "Go to the festival — YOLO", "outcome": "It'll be fun, but your laptop fund drops to £200 and you're months further from your goal. Big wants can derail bigger plans."},
                    {"label": "Skip it and keep saving", "outcome": "You'll reach your laptop goal sooner, but you might feel left out. Consider: is there a cheaper way to see your friends that weekend?"},
                    {"label": "Go but set a stricter budget for the next 2 months to catch up", "outcome": "A balanced approach — you enjoy the experience and commit to recovering. Just make sure the 'stricter budget' is realistic, not wishful thinking."},
                ],
                "correct_index": 2,
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "You have £40 left this month. You need a £25 school item, but there's a £30 game you really want. What do you do?",
                "choices": [
                    {"label": "Buy the game now and sort the school item later", "outcome": "Risky — the school item is a need with a deadline. Spending on the want first could leave you stuck."},
                    {"label": "Buy the school item, save the £15 toward the game", "outcome": "Smart. Needs come first; the £15 left over starts you toward the game, which you can buy guilt-free next month."},
                    {"label": "Buy both using buy-now-pay-later", "outcome": "You only have £40, so borrowing £15 for a want means fees or owing money. Avoid debt for wants."},
                ],
                "correct_index": 1,
            }},
        ],
    },
    {
        "topic": "risk", "title": "Risk & Diversification",
        "country_codes": [], "is_premium": False, "order_index": 5, "icon": "🎲",
        "lessons": [
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "What is investment risk?",
                "body": "Risk is the chance that you lose some or all of the money you invest. Every investment carries some risk — even a savings account (inflation can eat away its value). Generally, the higher the potential reward, the higher the risk. Understanding this trade-off is the single most important concept in investing.",
            }},
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "Don't put all your eggs in one basket",
                "body": "Diversification means spreading your money across different investments — different companies, different sectors, even different countries. If one investment tanks, the others can cushion the blow. It's not about avoiding risk entirely; it's about not letting one bad bet ruin everything.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Why can holding shares in 20 different companies be safer than holding just one?",
                "choices": [
                    "If one company does badly, the others can cushion the loss",
                    "Holding 20 companies guarantees a profit",
                    "20 companies can never all fail",
                    "It makes all the fees disappear",
                ],
                "answer_index": 0,
                "explanation": "Spreading money across many companies means one failure hurts less. Diversification reduces risk — though it never removes it entirely.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Which portfolio is most diversified?",
                "choices": [
                    "100% in one tech company's shares",
                    "50% in a tech company, 50% in another tech company",
                    "A mix of UK stocks, international stocks, bonds, and a savings account",
                ],
                "answer_index": 2,
                "explanation": "The mix spreads risk across asset types and geographies. Two tech stocks are both exposed to the same sector risk — if tech crashes, both fall.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Rank these from lowest to highest risk: savings account, single stock, index fund.",
                "choices": [
                    "Single stock, index fund, savings account",
                    "Savings account, index fund, single stock",
                    "Index fund, savings account, single stock",
                ],
                "answer_index": 1,
                "explanation": "Savings accounts are lowest risk (protected up to £85k by FSCS). Index funds spread risk across many stocks. Single stocks are highest risk — one company's fate determines your return.",
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "Your friend tells you to put all your money into one company because 'it's definitely going to 10x'. What do you do?",
                "choices": [
                    {"label": "Go all in — your friend seems confident", "outcome": "Confidence isn't evidence. Even experts get single-stock picks wrong regularly. If it crashes, you lose everything."},
                    {"label": "Invest a small amount and diversify the rest", "outcome": "Smart. You get some upside if your friend is right, but you're protected if they're wrong. This is how professionals think."},
                    {"label": "Research the company yourself before deciding", "outcome": "Great instinct. Never invest based on someone else's hype alone. Look at the company's financials, what it does, and whether the price makes sense."},
                ],
                "correct_index": 1,
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "You have £1,000 to invest for 5 years. How do you split it?",
                "choices": [
                    {"label": "£1,000 in a single exciting stock", "outcome": "High risk. It could double — or halve. With your entire amount in one stock, there's no safety net."},
                    {"label": "£500 in an index fund, £300 in a savings account, £200 in individual stocks", "outcome": "Well balanced. The index fund gives broad market exposure, savings provide stability, and the individual stocks add growth potential without betting everything."},
                    {"label": "£1,000 in a savings account", "outcome": "Very safe, but over 5 years inflation may eat into your returns. A little more risk could mean significantly more growth."},
                ],
                "correct_index": 1,
            }},
        ],
    },
    {
        "topic": "crypto", "title": "What is Crypto?",
        "country_codes": [], "is_premium": True, "order_index": 6, "icon": "₿",  # SAMPLE premium gating fixture — real premium curriculum is sub-project #4
        "lessons": [
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "Digital money on a shared ledger",
                "body": "Cryptocurrency is digital money that runs on a technology called blockchain — a public ledger shared across thousands of computers. No single bank or government controls it. Bitcoin, created in 2009, was the first. Since then, thousands of cryptocurrencies have appeared. The key idea: transactions are verified by the network, not by a bank.",
            }},
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "Why is crypto so volatile?",
                "body": "Unlike stocks, crypto has no earnings, no dividends, and no physical assets backing it. Its price is driven almost entirely by what people believe it's worth — sentiment and speculation. That's why it can rise 50% in a month and drop 50% the next. It's exciting but extremely risky, especially for money you can't afford to lose.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "What mainly drives the price of a cryptocurrency day to day?",
                "choices": [
                    "What people believe it's worth — sentiment and speculation",
                    "The company's profits and dividends",
                    "A fixed rate set by the government",
                    "The amount of gold stored behind it",
                ],
                "answer_index": 0,
                "explanation": "Most crypto has no profits, dividends, or assets behind it, so its price swings on sentiment alone — which is why it's so volatile.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Comparing crypto, stocks, and savings accounts — which has the HIGHEST risk?",
                "choices": [
                    "Savings account",
                    "Stocks (diversified index fund)",
                    "Cryptocurrency",
                ],
                "answer_index": 2,
                "explanation": "Crypto is the most volatile of the three. Savings accounts are protected (up to £85k by FSCS). Diversified stock funds spread risk across many companies. Crypto has no such protections and can swing wildly in value.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Which of these statements about cryptocurrency is TRUE?",
                "choices": [
                    "Crypto transactions are completely anonymous",
                    "Crypto is guaranteed to increase in value over time",
                    "Blockchain technology has uses beyond just cryptocurrency",
                    "Crypto is backed by gold reserves",
                ],
                "answer_index": 2,
                "explanation": "Blockchain is used in supply chain tracking, digital identity, and more. Crypto isn't truly anonymous (most are pseudonymous — traceable). It's not guaranteed to go up, and it's not backed by gold or any physical asset.",
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "A classmate says 'Crypto is guaranteed money — I've already doubled my investment.' They want you to invest your savings too. What do you do?",
                "choices": [
                    {"label": "Invest all your savings — they seem to know what they're doing", "outcome": "Past gains don't guarantee future ones. Your classmate got lucky timing. Investing money you can't afford to lose based on someone else's experience is one of the most common mistakes in investing."},
                    {"label": "Ask them what evidence they have beyond personal experience", "outcome": "Great critical thinking. 'It went up for me' is anecdotal, not analysis. Survivorship bias is real — you don't hear from the people who lost money."},
                    {"label": "Research independently before making any decision", "outcome": "The best approach. Look at historical volatility, understand what you're actually buying, and never invest more than you could afford to lose entirely."},
                ],
                "correct_index": 2,
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "You have £50 of savings. How much of it is sensible to put into crypto, if any?",
                "choices": [
                    {"label": "All £50 — go big or go home", "outcome": "Putting all your savings into something this volatile is very risky. A 50% drop (common in crypto) would instantly halve your money."},
                    {"label": "Only money you could afford to lose entirely — if anything", "outcome": "The right mindset. Crypto can crash hard, so never risk money you need. Plenty of sensible investors hold little or none."},
                    {"label": "Borrow extra so you can buy more", "outcome": "Never borrow to buy something this risky — you could end up owing money AND losing the investment."},
                ],
                "correct_index": 1,
            }},
        ],
    },
    {
        "topic": "taxes", "title": "How Taxes Work",
        "country_codes": [], "is_premium": False, "order_index": 7, "icon": "🧾",
        "lessons": [
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "Why do we pay tax?",
                "body": "Tax funds the things we all share: the NHS, schools, roads, police, fire services, and more. When you earn money, a portion goes to the government to pay for these services. It's not optional — it's the law — but it's also how society functions. Understanding tax means understanding where your money goes and why.",
            }},
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "Income tax basics",
                "body": "In the UK, you don't pay tax on the first £12,570 you earn each year — that's your Personal Allowance. After that, you pay 20% on earnings up to £50,270 (basic rate), then 40% above that (higher rate). Crucially, it's progressive: only the money in each band gets taxed at that band's rate, not your whole income.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "What is the UK 'Personal Allowance'?",
                "choices": [
                    "The amount you can earn each year before paying any income tax",
                    "A cash gift the government sends everyone",
                    "The most you're allowed to save in a year",
                    "A type of student loan",
                ],
                "answer_index": 0,
                "explanation": "The Personal Allowance (£12,570) is the amount you can earn each year tax-free. You only pay income tax on earnings above it.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Someone earns £20,000 per year. How much income tax do they pay?",
                "choices": [
                    "£4,000 (20% of the whole amount)",
                    "£1,486 (20% of the amount above £12,570)",
                    "£0 (under the tax threshold)",
                    "£2,000 (10% flat rate)",
                ],
                "answer_index": 1,
                "explanation": "Only the amount above the Personal Allowance is taxed: £20,000 − £12,570 = £7,430. At 20%, that's £1,486. A common mistake is thinking the entire £20,000 is taxed at 20%.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "True or false: 'If a pay rise pushes you into the higher tax band, all your income gets taxed at the higher rate.'",
                "choices": [
                    "True — your whole salary is taxed at the new rate",
                    "False — only the portion above the threshold is taxed at the higher rate",
                ],
                "answer_index": 1,
                "explanation": "This is the most common tax myth! Tax bands are progressive. If you earn £51,000, only £730 (the amount above £50,270) is taxed at 40%. The rest is taxed at lower rates. A pay rise always means more take-home pay.",
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "You start a part-time job: £8/hour, 10 hours/week, 48 weeks/year. That's £3,840/year. Will you pay income tax?",
                "choices": [
                    {"label": "Yes — everyone who works pays income tax", "outcome": "Not quite. £3,840 is well below the £12,570 Personal Allowance, so you owe £0 income tax. You might still see National Insurance on your payslip if you earn above £242/week though."},
                    {"label": "No — it's under the Personal Allowance", "outcome": "Correct! You won't pay income tax because your total earnings (£3,840) are below the £12,570 tax-free allowance. You keep every penny of your income tax — though NI may still apply."},
                    {"label": "Only if you're over 18", "outcome": "Age doesn't determine income tax — your earnings do. A 14-year-old earning £15,000 would pay the same tax as a 30-year-old earning £15,000."},
                ],
                "correct_index": 1,
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "You earn £14,000 this year. A friend says 'you'll pay 20% on all of it'. Are they right?",
                "choices": [
                    {"label": "Yes — 20% of £14,000 = £2,800", "outcome": "No — that's the common myth. Tax bands are progressive, so the whole amount isn't taxed at 20%."},
                    {"label": "No — only the £1,430 above the £12,570 allowance is taxed", "outcome": "Correct. £14,000 − £12,570 = £1,430, taxed at 20% = £286. The first £12,570 is tax-free."},
                    {"label": "No — you pay no tax at all", "outcome": "Not quite — you earn above the allowance, so the portion above £12,570 is taxed at 20%."},
                ],
                "correct_index": 1,
            }},
        ],
    },
    {
        "topic": "debt", "title": "Debt & Credit Explained",
        "country_codes": [], "is_premium": False, "order_index": 8, "icon": "💳",
        "lessons": [
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "Borrowing money costs money",
                "body": "When you borrow money — whether through a loan, credit card, or buy-now-pay-later — you usually pay it back with interest. APR (Annual Percentage Rate) tells you how much borrowing costs per year. For example, borrow £100 at 10% APR and after a year you owe £110. That extra £10 is the price of borrowing.",
            }},
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "Good debt vs bad debt",
                "body": "Not all debt is equal. A mortgage can be 'good debt' — you're borrowing to buy an asset that typically grows in value. A student loan increases your earning potential. But racking up credit card debt on things that lose value (fast fashion, gadgets you'll replace) is generally 'bad debt'. The question to ask: is this borrowing helping me build something, or just letting me consume more now?",
            }},
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "What is a credit score?",
                "body": "A credit score is a number (usually 0–999 in the UK) that shows lenders how reliable you are at repaying debt. It's built over time based on your history: do you pay bills on time? Have you ever missed payments? How much credit do you use? A good score means cheaper borrowing (lower interest rates on mortgages, easier phone contracts). A bad score means higher costs or being declined.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "What does 'APR' tell you?",
                "choices": [
                    "How much borrowing costs per year, as a percentage",
                    "How much you're allowed to borrow",
                    "Your current bank balance",
                    "The price of the item you're buying",
                ],
                "answer_index": 0,
                "explanation": "APR (Annual Percentage Rate) shows the yearly cost of borrowing. A higher APR means more expensive debt.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "You borrow £500 at 10% APR for one year. How much do you pay back in total?",
                "choices": [
                    "£500",
                    "£510",
                    "£550",
                    "£600",
                ],
                "answer_index": 2,
                "explanation": "10% of £500 = £50 in interest. So you repay £500 + £50 = £550. The interest is the cost of borrowing — it's how lenders make money.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Which of these is a warning sign of risky borrowing?",
                "choices": [
                    "Taking out a mortgage to buy a house",
                    "Borrowing money to repay other debts",
                    "Using a student loan for university",
                    "Paying off your credit card in full each month",
                ],
                "answer_index": 1,
                "explanation": "Borrowing to repay other debts is a debt spiral — you're not reducing what you owe, just moving it around (often at higher interest). The other options are either 'good debt' or responsible credit use.",
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "You want to buy a £300 guitar. You have three options. Which is the smartest?",
                "choices": [
                    {"label": "Save £50/month for 6 months, then buy it", "outcome": "The financially optimal choice. You pay exactly £300, earn a bit of interest while saving, and feel the satisfaction of buying it outright. Plus, the wait helps you confirm you really want it."},
                    {"label": "Buy Now Pay Later — 0% if paid within 3 months", "outcome": "This works IF you're disciplined. You'd need to pay £100/month for 3 months. Miss the deadline and interest kicks in — often 20%+. It's a trap for the disorganised."},
                    {"label": "Put it on a credit card at 20% APR", "outcome": "The most expensive option. If you only make minimum payments, that £300 guitar could end up costing £350+ over a year. Credit cards are useful for building credit history, but carrying a balance is costly."},
                ],
                "correct_index": 0,
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "You have a £200 credit card bill. You can pay it all now, or pay just the £10 minimum. What's wiser?",
                "choices": [
                    {"label": "Pay it all now", "outcome": "Best choice. Paying in full means £0 interest and it builds a good credit history. This is how to use a credit card well."},
                    {"label": "Pay just the £10 minimum", "outcome": "The remaining £190 starts charging interest (often 20%+). Minimum-only payments can stretch a small debt out for years and cost far more."},
                    {"label": "Ignore the bill this month", "outcome": "Missing payments adds fees AND damages your credit score, making future borrowing harder and more expensive."},
                ],
                "correct_index": 0,
            }},
        ],
    },
    {
        "topic": "entrepreneurship", "title": "Starting a Side Hustle",
        "country_codes": [], "is_premium": False, "order_index": 9, "icon": "🚀",
        "lessons": [
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "Everyone starts somewhere",
                "body": "A side hustle is a way to earn money outside of a regular job, usually doing something you enjoy or are good at. Examples: tutoring younger students, reselling vintage clothes, walking dogs, making and selling crafts, freelance graphic design. You don't need a business plan or an investor — just a skill, some initiative, and your first customer.",
            }},
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "Finding your thing",
                "body": "The sweet spot for a side hustle is where your skills meet demand. Ask yourself: what am I good at? What do people around me need? Where do those overlap? Good at maths? Tutoring. Love baking? Sell at school fairs. Great at social media? Help a local shop with their posts. Start small, learn fast, and don't be afraid to pivot if something isn't working.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "What's the best foundation for a side hustle?",
                "choices": [
                    "A skill you have that other people will pay for",
                    "A big bank loan to get started",
                    "An expensive office to work from",
                    "Waiting until you find the perfect idea",
                ],
                "answer_index": 0,
                "explanation": "The best side hustles match a skill you already have with something people need — so you can start small with little or no money.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Which side hustle best matches someone who's good at explaining things clearly?",
                "choices": [
                    "Reselling trainers",
                    "Dog walking",
                    "Tutoring younger students",
                    "Selling handmade jewellery",
                ],
                "answer_index": 2,
                "explanation": "Tutoring directly uses the skill of explaining things clearly. The best side hustles build on what you're already good at — it makes the work easier and the results better.",
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "You're a talented artist. A friend suggests you could make money from it. What's your first move?",
                "choices": [
                    {"label": "Sell prints online through a platform like Etsy", "outcome": "Good thinking. Platforms like Etsy give you instant access to buyers. Start with 5-10 designs, price them to cover costs + a profit margin, and see what sells. Low risk, low cost to start."},
                    {"label": "Offer pet portrait commissions to people you know", "outcome": "Smart — commissions mean you get paid before you do the work. Start with friends and family at a lower price to build a portfolio, then raise prices as demand grows. Word of mouth is powerful."},
                    {"label": "Do free work to 'build your portfolio'", "outcome": "A small amount of free work is fine to get started, but don't make it a habit. Your time and skill have value. If someone wants your work, they should pay for it — even a small amount sets the right expectation."},
                ],
                "correct_index": 1,
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "You bake great cookies. What's a sensible FIRST step to earning from it?",
                "choices": [
                    {"label": "Sell a small batch to neighbours or at a school fair and see if people buy", "outcome": "Smart — test cheaply before scaling. Real sales tell you whether there's demand and what price works."},
                    {"label": "Spend £500 on packaging and a logo first", "outcome": "Too risky up front. Prove people will actually buy before spending big on branding."},
                    {"label": "Give them all away free, forever", "outcome": "Free samples can build interest, but a business needs to charge. Your time and ingredients cost money."},
                ],
                "correct_index": 0,
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "Your dog-walking side hustle is booming and you can't keep up with bookings. What's a good growth move?",
                "choices": [
                    {"label": "Raise prices a little, and/or bring in a friend to help and split the work", "outcome": "Sensible. More demand than you can meet means you can charge more, or expand by sharing the work — both grow your earnings."},
                    {"label": "Take every booking even if quality slips", "outcome": "Overpromising hurts your reputation. Unhappy customers don't come back or recommend you."},
                    {"label": "Quit while you're ahead", "outcome": "Walking away from a working business that has demand throws away your effort — manage the growth instead."},
                ],
                "correct_index": 0,
            }},
        ],
    },
    {
        "topic": "entrepreneurship", "title": "Revenue, Costs & Profit",
        "country_codes": [], "is_premium": True, "order_index": 10, "icon": "📊",  # SAMPLE premium gating fixture — real premium curriculum is sub-project #4
        "lessons": [
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "Revenue isn't profit",
                "body": "Revenue is the total money that comes in from sales. Profit is what's left after you subtract all your costs. A lemonade stand that takes in £50 but spends £40 on supplies only makes £10 profit. Big revenue can mean zero profit if costs are too high. Always think: what am I actually keeping?",
            }},
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "Fixed vs variable costs",
                "body": "Fixed costs stay the same regardless of how much you sell: website hosting, a market stall fee, insurance. Variable costs change with each sale: ingredients, packaging, shipping. Knowing the difference helps you predict your expenses. If you sell nothing, you still pay fixed costs — that's your risk.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "What is 'profit'?",
                "choices": [
                    "Revenue minus all your costs",
                    "The total money that comes in from sales",
                    "The selling price of one item",
                    "The amount of money you borrow to start",
                ],
                "answer_index": 0,
                "explanation": "Profit is what's left after subtracting all costs from revenue. High revenue can still mean low profit if your costs are high.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "You sell 50 cupcakes at £2 each. Ingredients cost £40, packaging £10, stall fee £15. What's your profit?",
                "choices": [
                    "£100",
                    "£50",
                    "£35",
                    "£65",
                ],
                "answer_index": 2,
                "explanation": "Revenue: 50 × £2 = £100. Costs: £40 + £10 + £15 = £65. Profit: £100 − £65 = £35. That's your actual earnings — less than half the revenue.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "You sell 20 bracelets at £5 each. Materials cost £30 and a stall costs £20. What's your profit?",
                "choices": ["£100", "£70", "£50", "£30"],
                "answer_index": 2,
                "explanation": "Revenue: 20 × £5 = £100. Costs: £30 + £20 = £50. Profit: £100 − £50 = £50.",
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "Your sticker business made £200 in revenue this month, but you spent £150 on supplies and shipping. Your profit is only £50. How could you improve?",
                "choices": [
                    {"label": "Raise your prices slightly", "outcome": "Often the simplest fix. If you raise prices by 20% (e.g., £2 stickers become £2.40), your revenue jumps to £240 with the same costs — doubling your profit to £90. Just make sure the price is still fair for the market."},
                    {"label": "Find cheaper supplies without sacrificing quality", "outcome": "Smart. Buying materials in bulk, switching suppliers, or reducing packaging can cut variable costs. Even saving £20/month on supplies would boost your profit by 40%."},
                    {"label": "Sell more volume at the same prices", "outcome": "More sales mean more revenue, but also more variable costs (supplies, shipping). You'd need to sell significantly more to make a big difference. It works, but it's harder than improving margins."},
                ],
                "correct_index": 0,
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "Your craft stall made £80 revenue but only £10 profit because costs were £70. What's the best fix to try FIRST?",
                "choices": [
                    {"label": "Raise prices a little, or buy materials in bulk to cut the cost per item", "outcome": "Best first move. Improving your margin — a higher price or a lower cost per item — lifts profit without needing to sell any more."},
                    {"label": "Sell loads more at the same thin margin", "outcome": "More sales also means more costs. With tiny profit per item you'd have to sell a huge amount — fixing the margin is far easier."},
                    {"label": "Give up — it's clearly not worth it", "outcome": "£10 profit is a start. Small tweaks to price or cost often turn a thin profit into a healthy one."},
                ],
                "correct_index": 0,
            }},
        ],
    },
    {
        "topic": "taxes", "title": "Your First Paycheque",
        "country_codes": [], "is_premium": True, "order_index": 11, "icon": "💷",
        "lessons": [
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "Reading a payslip",
                "body": "Your payslip shows two key numbers: gross pay (what you earned before anything is taken off) and net pay (what actually lands in your bank). The difference? Deductions — income tax, National Insurance (NI), and sometimes a pension contribution. It's not the company taking your money; it's taxes and savings being handled automatically.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "What's the difference between 'gross pay' and 'net pay'?",
                "choices": [
                    "Gross is before deductions; net is what actually lands in your bank",
                    "Gross is your savings; net is your spending money",
                    "They mean exactly the same thing",
                    "Net is before tax; gross is after tax",
                ],
                "answer_index": 0,
                "explanation": "Gross pay is what you earned before anything is taken off. Net pay is your take-home after tax, National Insurance, and pension.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "On a payslip, what does 'NI' stand for?",
                "choices": [
                    "National Insurance",
                    "New Income",
                    "Net Interest",
                    "No Income",
                ],
                "answer_index": 0,
                "explanation": "NI is National Insurance — a deduction that helps pay for things like the state pension and the NHS.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Match the payslip term to its meaning: 'Net pay' is…",
                "choices": [
                    "Your total earnings before any deductions",
                    "The National Insurance contribution",
                    "The amount that actually goes into your bank account",
                    "Your employer's pension contribution",
                ],
                "answer_index": 2,
                "explanation": "Net pay is your take-home pay — what's left after income tax, National Insurance, and any other deductions. Gross pay is the 'before deductions' number.",
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "Your first payslip shows: Gross pay £600, Income tax £30, NI £25, Pension £15, Net pay £530. But you expected £600! What happened?",
                "choices": [
                    {"label": "The company made an error — demand the full £600", "outcome": "No error here. Deductions are normal and required by law. Income tax and NI go to HMRC; pension is saving for your future. Your actual earnings were £600 — you just don't keep all of it."},
                    {"label": "These deductions are normal — tax, NI, and pension are standard", "outcome": "Exactly right. £30 tax + £25 NI + £15 pension = £70 in deductions. Your net pay of £530 is correct. This happens every pay cycle and it's completely normal."},
                    {"label": "Opt out of everything to get the full £600", "outcome": "You can opt out of the pension (though it's usually unwise — your employer often matches contributions). But income tax and NI are mandatory. There's no way to get the full gross amount."},
                ],
                "correct_index": 1,
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "Your payslip has a pension deduction, and your employer adds a matching contribution on top. Should you usually opt out to get more cash now?",
                "choices": [
                    {"label": "Opt out — take the maximum cash today", "outcome": "Usually unwise. Opting out means giving up your employer's free matching money and decades of compound growth for your future self."},
                    {"label": "Usually stay in — the employer match is free money for your future", "outcome": "Right. A workplace pension with an employer match is one of the best deals around: free money now, plus long-term compounding."},
                    {"label": "It never makes any difference either way", "outcome": "It makes a big difference over time — small contributions now, plus the match, grow significantly by the time you retire."},
                ],
                "correct_index": 1,
            }},
        ],
    },
]


def _lesson_identity(lesson_type: str, content_json: dict) -> str:
    """Stable identity for a lesson so re-seeding doesn't duplicate it."""
    if lesson_type == "quiz":
        return f"quiz:{content_json.get('question', '')}"
    if lesson_type == "scenario":
        return f"scenario:{content_json.get('prompt', '')}"
    if lesson_type == "video":
        return f"video:{content_json.get('youtube_id', '')}"
    return f"card:{content_json.get('title', '')}"


# Difficulty ranking by lesson type, foundational → challenging:
# cards (concepts) → intro video → quizzes (recall/calculation) →
# scenarios (real-world application). Used to slot newly-appended lessons
# into the right band without disturbing lessons already placed.
_TYPE_RANK = {"card": 0, "video": 1, "quiz": 2, "scenario": 3}


def _insert_position(ordered_types: list[str], new_type: str) -> int:
    """Index at which to insert a new lesson so it lands at the END of its
    difficulty band: just after the last existing lesson whose type ranks at or
    below the new lesson's type. Preserves the relative order of every existing
    lesson (so manual admin reordering is never disturbed)."""
    rank = _TYPE_RANK.get(new_type, _TYPE_RANK["quiz"])
    pos = 0
    for idx, t in enumerate(ordered_types):
        if _TYPE_RANK.get(t, _TYPE_RANK["quiz"]) <= rank:
            pos = idx + 1
    return pos


async def seed_modules_and_lessons(session: AsyncSession) -> None:
    """Idempotent: creates modules (matched by topic+title), ensures each has a
    Level 1, and inserts any lessons missing from the curriculum. New lessons are
    slotted into their difficulty band by type (card → video → quiz → scenario)
    rather than appended at the end; lessons already present keep their relative
    order, so manual admin reordering survives re-seeding. Caller commits."""
    for spec in _MODULES:
        module = await session.scalar(
            select(Module).where(Module.topic == spec["topic"], Module.title == spec["title"])
        )
        if module:
            module.icon = spec.get("icon", "📚")
            module.is_premium = spec["is_premium"]
        else:
            module = Module(
                topic=spec["topic"], title=spec["title"],
                country_codes=spec["country_codes"], is_premium=spec["is_premium"],
                order_index=spec["order_index"], icon=spec.get("icon", "📚"),
            )
            session.add(module)
            await session.flush()

        level = await session.scalar(
            select(Level).where(Level.module_id == module.id, Level.order_index == 0)
        )
        if level is None:
            level = Level(
                module_id=module.id, title="Level 1", order_index=0,
                is_premium=module.is_premium, pass_threshold=0.7, content_source="authored",
            )
            session.add(level)
            await session.flush()

        # Start from the CURRENT order (which reflects any manual admin
        # reordering) and only insert lessons missing from the curriculum,
        # slotting each into its difficulty band by type. Lessons already
        # placed keep their relative order; we only normalise the integer
        # order_index across the merged sequence at the end.
        ordered = list((await session.scalars(
            select(Lesson).where(Lesson.level_id == level.id).order_by(Lesson.order_index)
        )).all())
        by_ident = {_lesson_identity(le.type, le.content_json): le for le in ordered}

        for lesson_spec in spec["lessons"]:
            ident = _lesson_identity(lesson_spec["type"], lesson_spec["content_json"])
            if ident in by_ident:
                continue  # already present — leave its position untouched
            new_lesson = Lesson(
                module_id=module.id, level_id=level.id,
                type=lesson_spec["type"],
                content_json=lesson_spec["content_json"],
                xp_reward=lesson_spec["xp_reward"],
                order_index=0,  # normalised below
            )
            session.add(new_lesson)
            by_ident[ident] = new_lesson
            pos = _insert_position([le.type for le in ordered], new_lesson.type)
            ordered.insert(pos, new_lesson)

        for i, le in enumerate(ordered):
            le.order_index = i
