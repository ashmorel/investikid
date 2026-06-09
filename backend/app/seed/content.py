from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, Level, Module
from app.services.level_service import premium_for_position

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
        "extra_levels": [
            {"title": "Level 2", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Where stocks are bought and sold",
                    "body": "Stocks are traded on a stock exchange — a giant marketplace like the London Stock Exchange (LSE) or the New York Stock Exchange. Here's the surprise: when you buy a share, you're usually not buying it from the company. You're buying it from another investor who wants to sell theirs.",
                }},
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Every stock has a ticker",
                    "body": "A ticker is a short code that names a stock — like AAPL for Apple or TSLA for Tesla. Tickers make companies quick to find. Try searching one in the practice Simulator to see its price!",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "When you buy a share of a big company like Apple, who are you usually buying it from?",
                    "choices": ["The company itself, directly", "Another investor who wants to sell their share", "The government", "Your bank's savings team"],
                    "answer_index": 1,
                    "explanation": "Most of the time you trade with other investors on an exchange — not the company. The company only sold those shares once, long ago.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "What is a stock exchange?",
                    "choices": ["A marketplace where shares are bought and sold", "A shop that only sells company products", "A savings account for grown-ups", "A type of dividend"],
                    "answer_index": 0,
                    "explanation": "An exchange (like the LSE or NYSE) is the marketplace where buyers and sellers trade shares.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "You hear about the 'FTSE 100' or 'S&P 500'. What is an index like that?",
                    "choices": ["A single company's share price", "A scoreboard that tracks many big companies at once", "A tax on investors", "A list of dividends"],
                    "answer_index": 1,
                    "explanation": "An index is like a scoreboard: it follows lots of companies together, so people can see how 'the market' is doing overall.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Company A is worth £1 trillion. Company B is worth £10 million. Which is the 'bigger' company by market value?",
                    "choices": ["Company A", "Company B", "They're exactly the same", "You can't tell from value"],
                    "answer_index": 0,
                    "explanation": "A company's total value is its 'market cap'. £1 trillion is far bigger than £10 million — Company A is the giant.",
                }},
                {"type": "scenario", "xp_reward": 20, "content_json": {
                    "prompt": "You're curious how a real company's share price moves, but you're brand new. What's the smartest first step?",
                    "choices": [
                        {"label": "Put your real birthday money straight into one stock", "outcome": "Risky — never invest real money you can't afford to lose, especially before you've learned the ropes."},
                        {"label": "Search its ticker in the practice Simulator and watch it with pretend money", "outcome": "Perfect — the Simulator lets you explore real prices and practise with zero risk before any real money is involved."},
                        {"label": "Buy whatever a video online tells you to", "outcome": "Be careful — lots of online 'tips' are hype or scams. Learn and practise first, and always ask a trusted grown-up."},
                    ],
                    "correct_index": 1,
                }},
            ]},
            {"title": "Level 3", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Don't put all your eggs in one basket",
                    "body": "If you put all your money into one company and it does badly, you could lose a lot. Spreading your money across many different companies is called diversification — if one struggles, the others can balance it out.",
                }},
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Time in the market beats timing the market",
                    "body": "Nobody — not even experts — can reliably guess the best day to buy or sell. Investors who stay invested for many years usually do better than those who jump in and out trying to be clever.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Which is generally LESS risky?",
                    "choices": ["Putting all your money in one company", "Spreading your money across many different companies", "They're equally risky", "Keeping it all as cash under your bed"],
                    "answer_index": 1,
                    "explanation": "Spreading out (diversifying) means one bad company won't sink everything. That's a core rule of smart investing.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "What is an index fund?",
                    "choices": ["A single risky company", "A basket that holds many companies at once, giving instant diversification", "A loan you take out to invest", "A type of bank fee"],
                    "answer_index": 1,
                    "explanation": "An index fund holds lots of companies together — buying one is like buying a whole scoreboard of businesses at once.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Trying to guess the perfect day to buy or sell is called 'timing the market'. Is it a reliable way to invest?",
                    "choices": ["Yes, anyone can do it easily", "No — even experts can't do it reliably, so staying invested long-term usually works better", "Yes, if you watch the news every hour", "Only on weekends"],
                    "answer_index": 1,
                    "explanation": "Short-term prices are unpredictable. Patience and time usually beat trying to guess the perfect moment.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Investments that could grow a lot usually also carry…",
                    "choices": ["More risk of falling in value", "A guarantee from the government", "No risk at all", "Free money"],
                    "answer_index": 0,
                    "explanation": "Higher possible reward almost always comes with higher risk. There's no reward with zero risk — that's the trade-off.",
                }},
                {"type": "scenario", "xp_reward": 20, "content_json": {
                    "prompt": "You have £100 of pretend money to invest for 10 years in the Simulator. What's the wisest approach?",
                    "choices": [
                        {"label": "Put all £100 into the one stock a friend is hyping", "outcome": "Too risky — if that single company struggles, your whole £100 is exposed. No diversification."},
                        {"label": "Spread it across several companies (or a fund) and leave it to grow", "outcome": "Wise — diversifying and giving it years to grow is exactly how patient investors lower risk and let compounding work."},
                        {"label": "Buy and sell every single day to chase quick wins", "outcome": "This is 'timing the market' — unreliable, stressful, and usually loses to just staying invested."},
                    ],
                    "correct_index": 1,
                }},
            ]},
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
                "youtube_id": "Rm6UdfRs3gw", "caption": "Compound interest explained simply",
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
        "extra_levels": [
            {"title": "Level 2", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "How often does it compound?",
                    "body": "Not all interest is added once a year. Some accounts add interest every month, or even every day. The more often interest is added (or 'compounded'), the more often your interest starts earning its own interest. So two accounts with the same rate can grow by slightly different amounts depending on how often they pay.",
                }},
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "The magic trick: the Rule of 72",
                    "body": "Here's a handy shortcut grown-ups use. Divide 72 by the interest rate to roughly guess how many years it takes for your money to DOUBLE. At 6% interest, 72 ÷ 6 = 12 years to double. It's only an estimate, but it's a brilliant way to picture how powerful a rate really is.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Two accounts both pay 5% a year. Account A adds the interest once a year; Account B adds a little bit every month. Which grows slightly more?",
                    "choices": ["Account A (once a year)", "Account B (a little every month)", "They grow exactly the same", "Neither — frequency never matters"],
                    "answer_index": 1,
                    "explanation": "Adding interest more often means your interest starts earning its own interest sooner, so Account B ends up a tiny bit ahead — even at the same rate.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Using the Rule of 72, roughly how many years would it take to double your money at 8% interest?",
                    "choices": ["About 3 years", "About 9 years", "About 36 years", "It never doubles"],
                    "answer_index": 1,
                    "explanation": "72 ÷ 8 = 9, so it takes roughly 9 years to double. The Rule of 72 is just a quick estimate, not exact maths.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Instead of saving once, Maya adds £10 every month to her account. What happens to the compounding?",
                    "choices": ["Only her very first £10 ever earns interest", "Each new deposit also starts earning interest, so the whole pot keeps growing", "Adding money regularly stops interest being paid", "Compounding only works if you never add more"],
                    "answer_index": 1,
                    "explanation": "Every deposit you add joins the pot and starts earning its own interest. Saving regularly gives compounding even more to work with.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Using the Rule of 72, which rate would double your money the FASTEST?",
                    "choices": ["2% a year", "4% a year", "9% a year", "They all double at the same speed"],
                    "answer_index": 2,
                    "explanation": "72 ÷ 9 = 8 years, much faster than 72 ÷ 2 = 36 years. A higher rate doubles your money in fewer years.",
                }},
                {"type": "scenario", "xp_reward": 20, "content_json": {
                    "prompt": "You spot an account online promising to 'DOUBLE your money in just 3 months, guaranteed!' Using what you know about realistic interest rates, what should you do?",
                    "choices": [
                        {"label": "Send your savings straightaway before the offer ends", "outcome": "Please don't. 'Double in 3 months, guaranteed' is a classic scam — real compound interest takes years, not months. Money sent to scams is usually gone for good."},
                        {"label": "Be very suspicious and ask a trusted grown-up before doing anything", "outcome": "Exactly right. Real savings grow slowly and steadily. Promises of fast, guaranteed doubling are almost always scams — always check with a trusted grown-up first."},
                        {"label": "Borrow money from a friend so you can put in even more", "outcome": "Never borrow to chase an offer like this. Borrowing for a too-good-to-be-true deal turns one bad idea into two."},
                    ],
                    "correct_index": 1,
                }},
            ]},
            {"title": "Level 3", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Compounding can work AGAINST you too",
                    "body": "Compound interest is brilliant when it's growing your savings. But it works the same way on money you OWE. If someone borrows money and doesn't pay it back, the interest piles up on the interest — and the debt can snowball quickly. The same force that grows savings can grow a debt, so borrowing always needs care.",
                }},
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "The quiet thief: inflation",
                    "body": "Prices slowly rise over time — a chocolate bar costs more than it did when your parents were young. That's called inflation. If your savings earn 2% but prices rise 3%, your money actually buys a little LESS each year. Smart savers look for a rate that at least keeps up with rising prices, so their money doesn't quietly shrink in value.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Why do grown-ups warn that an unpaid debt can 'snowball'?",
                    "choices": ["Because the interest can pile up on top of interest, just like savings — but it makes what you owe bigger", "Because debts always get smaller on their own over time", "Because borrowing money never costs anything", "Because interest only ever helps the borrower"],
                    "answer_index": 0,
                    "explanation": "Compounding doesn't care which direction it works. On a debt, interest builds on interest and what you owe can grow fast — which is why unpaid debt is risky.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Your savings earn 2% a year, but prices are rising by 3% a year. What's really happening to your money's buying power?",
                    "choices": ["It's growing quickly", "It's slowly shrinking — your money buys a little less each year", "Nothing changes at all", "Prices don't affect savings"],
                    "answer_index": 1,
                    "explanation": "If prices rise faster than your interest rate, your money buys less over time. Beating inflation is why the rate you earn really matters.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "In the UK, a Junior ISA lets savings grow without paying tax on the interest. Why is that good for compounding?",
                    "choices": ["It means you can never take the money out", "More of your interest stays in the pot to earn its own interest", "It removes all risk completely", "It makes interest rates go up"],
                    "answer_index": 1,
                    "explanation": "If tax isn't taken from your interest, more of it stays invested — and that extra amount keeps compounding year after year.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Two friends each save the same amount at the same rate. Sam starts at 15; Alex starts at 25. Years later, who is likely to have MORE — and why?",
                    "choices": ["Alex, because starting later is always better", "Sam, because those extra 10 years gave compounding much more time to work", "They'll have exactly the same", "Whoever checks their account most often"],
                    "answer_index": 1,
                    "explanation": "Time is compounding's superpower. Sam's extra decade lets interest build on interest for far longer, often beating someone who started later — even with the same deposits.",
                }},
                {"type": "scenario", "xp_reward": 20, "content_json": {
                    "prompt": "You've got £200 of birthday money you won't need for years. A grown-up offers to help you open a tax-free Junior ISA savings account. What's the wisest move?",
                    "choices": [
                        {"label": "Spend it all now while you can", "outcome": "Spending it all means zero growth. There's nothing wrong with treating yourself a little, but money you won't need for years could be quietly growing instead."},
                        {"label": "Open the tax-free account with a trusted grown-up and leave it to grow for years", "outcome": "Smart thinking. A tax-free account means more of your interest stays in to compound, and giving it years lets that snowball really build. Doing it WITH a trusted grown-up keeps it safe."},
                        {"label": "Hide the cash in a drawer so it's 'safe'", "outcome": "Cash in a drawer earns no interest at all — and inflation slowly shrinks what it can buy. It feels safe, but it quietly loses value over time."},
                    ],
                    "correct_index": 1,
                }},
            ]},
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
        "extra_levels": [
            {"title": "Level 2", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Not just houses",
                    "body": "A REIT can own all sorts of property, not just homes. Some own shopping centres, some own warehouses where parcels are stored, some own office blocks, hospitals, or even mobile-phone towers. Different REITs focus on different types — so when you pick one, it helps to know what kind of property is actually inside it.",
                }},
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Why REITs pay out so much",
                    "body": "REITs have a special deal with the rules: to count as a REIT, they must hand out most of their rental profit to shareholders (in the UK it's at least 90%). That regular payout is called a dividend. It's the main reason people who like steady income are drawn to REITs.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Which of these could a REIT own?",
                    "choices": ["Only family houses", "Shopping centres, warehouses, and offices", "Only things you can hold in your hand", "Only cash in a bank"],
                    "answer_index": 1,
                    "explanation": "REITs can own many kinds of income-producing property — shops, warehouses, offices and more — not just houses.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "REITs must hand out most of their rental profit to shareholders. What is that regular payment called?",
                    "choices": ["A dividend", "A deposit", "A loan", "A fee"],
                    "answer_index": 0,
                    "explanation": "Money a REIT pays out to its shareholders from rental profit is called a dividend — the main attraction for income-seekers.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "A single REIT owns 200 different buildings rented to lots of different businesses. Why can that be helpful?",
                    "choices": ["If one building sits empty, the rent from the others can help balance it out", "It means the REIT can never lose value", "It guarantees the dividend will always go up", "It means you own all 200 buildings yourself"],
                    "answer_index": 0,
                    "explanation": "Owning many buildings spreads the risk — one empty shop won't sink everything. That's a kind of diversification inside a single REIT. (It still isn't risk-free.)",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "How do most ordinary investors actually buy a piece of a REIT?",
                    "choices": ["They buy and sell its shares on the stock market, like any other share", "They have to buy a whole building themselves", "They post cash directly to the buildings", "They can only inherit it"],
                    "answer_index": 0,
                    "explanation": "A REIT is listed on the stock market, so you buy and sell its shares just like any other company's — no need to own a whole building.",
                }},
                {"type": "scenario", "xp_reward": 20, "content_json": {
                    "prompt": "You've found a REIT and you like that it pays a dividend. Before putting in any pretend money in the Simulator, what's the smart move?",
                    "choices": [
                        {"label": "Buy straight away because dividends mean free money", "outcome": "Careful — dividends aren't free money, and the share price can still fall. It's worth understanding what you're buying first."},
                        {"label": "Check what kind of property it actually owns and chat it through with a trusted grown-up", "outcome": "Great thinking — knowing whether it owns shops, offices or warehouses tells you a lot, and a trusted grown-up can help you make sense of it."},
                        {"label": "Pick it only because an online video shouted that it's a winner", "outcome": "Be wary — loud online tips are often hype or scams. Learn what's inside it and practise safely first."},
                    ],
                    "correct_index": 1,
                }},
            ]},
            {"title": "Level 3", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Reading the dividend yield",
                    "body": "The 'dividend yield' is a quick way to compare REITs: it's the yearly dividend shown as a percentage of the share price. A REIT priced at £10 paying 40p a year has a 4% yield. A very high yield can look exciting, but it sometimes means investors are worried — so a big number isn't automatically a good number.",
                }},
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "REITs borrow money, and rates matter",
                    "body": "Most REITs borrow money to buy their properties, a bit like a mortgage. When interest rates rise, that borrowing costs more, which can squeeze profits and push share prices down. This is why REIT prices often wobble when the news talks about interest rates changing.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "A REIT's share price is £10 and it pays 50p in dividends a year. What is its dividend yield?",
                    "choices": ["50%", "5%", "0.5%", "£10"],
                    "answer_index": 1,
                    "explanation": "Yield = yearly dividend ÷ share price. 50p ÷ £10 = 0.05 = 5%.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "One REIT has an unusually high dividend yield compared with similar ones. What's the wise way to read that?",
                    "choices": ["It's guaranteed to be the best choice", "It might be a warning sign that investors are worried, so it's worth looking closer", "High yield always means no risk", "Yield tells you nothing at all"],
                    "answer_index": 1,
                    "explanation": "A very high yield can be a red flag, not a prize — sometimes the price has dropped because people are worried. Always look deeper rather than chasing the biggest number.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Why can rising interest rates be tough for REITs?",
                    "choices": ["They make rent illegal", "REITs often borrow to buy property, so higher rates make that borrowing cost more", "They force REITs to give properties away", "They have no effect on REITs at all"],
                    "answer_index": 1,
                    "explanation": "Because REITs usually borrow to fund their buildings, higher interest rates raise their costs and can weigh on profits and share prices.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "A sensible investor sees REITs as…",
                    "choices": ["The only thing anyone should ever own", "One useful slice of a wider mix that might also include shares, funds and savings", "A way to get rich by tomorrow", "A risk-free replacement for a savings account"],
                    "answer_index": 1,
                    "explanation": "REITs can be a helpful part of a diversified mix, but leaning everything on one type of investment is risky. Spreading across different kinds is the calmer path.",
                }},
                {"type": "scenario", "xp_reward": 20, "content_json": {
                    "prompt": "In the Simulator you have £200 of pretend money and you're interested in property. Two REITs catch your eye: one with a steady 4% yield owning warehouses, and one with a flashy 12% yield you don't really understand. What's the wisest approach?",
                    "choices": [
                        {"label": "Pour it all into the 12% one because the number is biggest", "outcome": "Risky — an unusually high yield can be a warning sign, and putting everything into one thing you don't understand is the opposite of careful."},
                        {"label": "Spread some across the steadier REIT and the rest elsewhere, and ask a trusted grown-up to help you understand the high-yield one", "outcome": "Wise — you diversify, you don't chase a number you can't explain, and you get help understanding it before risking anything."},
                        {"label": "Buy and sell every day to chase the dividend", "outcome": "That's trying to time the market — stressful, unreliable, and it usually loses to patiently staying invested."},
                    ],
                    "correct_index": 1,
                }},
            ]},
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
        "extra_levels": [
            {"title": "Level 2", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "A budget only works if you track it",
                    "body": "A plan is a guess until you check it against reality. Tracking means writing down what you actually spend — in a notes app, a little notebook, or a simple spreadsheet. At the end of the week you compare what you planned to spend with what you really spent. The gaps are where the surprises hide, and they're usually the small, easy-to-forget buys.",
                }},
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Fixed costs vs variable costs",
                    "body": "Some costs are the same every month — a phone plan or a bus pass. Those are fixed costs, and they're easy to plan for. Others change month to month — snacks, games, days out. Those are variable costs. Variable costs are where most people overspend, because they feel small in the moment. Knowing which is which tells you where you have room to cut back.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Why is tracking your spending so useful, even if you already made a budget?",
                    "choices": ["A budget is only a plan — tracking shows what you actually spent, so you can spot surprises", "Tracking automatically gives you more money", "Once you write a budget, spending takes care of itself", "Tracking is only for grown-ups with jobs"],
                    "answer_index": 0,
                    "explanation": "A budget is a forecast. Tracking is the reality check — comparing the two is how you find the small, sneaky spends and fix next month's plan.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Which of these is a fixed cost?",
                    "choices": ["A monthly bus pass that costs the same every month", "Snacks at the shop, which change week to week", "Money spent on days out with friends", "Birthday gifts for friends"],
                    "answer_index": 0,
                    "explanation": "A fixed cost stays the same each month (like a bus pass or phone plan). Snacks, days out, and gifts vary, so they're variable costs — the ones easiest to overspend on.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "You know your sister's birthday in 4 months will cost about £20. What's the smart budgeting move?",
                    "choices": ["Set aside £5 a month now so the £20 is ready (a 'sinking fund')", "Forget about it and hope you have £20 that month", "Borrow the £20 when the time comes", "Spend £20 now so it's 'out of the way'"],
                    "answer_index": 0,
                    "explanation": "A sinking fund means saving a little each month for a known future cost. Putting £5 aside for 4 months means the £20 is ready, with no scramble and no borrowing.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "You tracked your month and spending came to £10 more than your income. What should you do first?",
                    "choices": ["Adjust the budget — trim a variable cost or two until the plan adds up", "Ignore it; £10 is too small to matter", "Borrow £10 every month to cover the gap", "Stop tracking so you don't see the problem"],
                    "answer_index": 0,
                    "explanation": "A budget that doesn't balance needs adjusting, not ignoring. Small overspends repeat every month. Trimming a variable cost (the flexible kind) is the quickest way to make the plan add up.",
                }},
                {"type": "scenario", "xp_reward": 20, "content_json": {
                    "prompt": "You set a budget but kept overspending on snacks and small buys, and you're not sure where the money went. What's the best next step?",
                    "choices": [
                        {"label": "Guess what went wrong and set a stricter budget", "outcome": "Guessing rarely works — you don't actually know where the money leaked, so the new plan is just another guess."},
                        {"label": "Track every spend for two weeks, then review it (and ask a grown-up to look it over with you)", "outcome": "This is exactly right. Tracking shows you the real pattern, and reviewing it — ideally with a trusted grown-up — turns a vague worry into a clear, fixable plan."},
                        {"label": "Give up on budgeting — it clearly doesn't work for you", "outcome": "The budget isn't the problem; the missing piece is tracking. Quitting just brings back the not-knowing."},
                    ],
                    "correct_index": 1,
                }},
            ]},
            {"title": "Level 3", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Give every pound a job (zero-based budgeting)",
                    "body": "A powerful method is to plan until your income minus your planned spending-and-saving equals zero — not because you spend it all, but because every pound has been assigned a job (spending, saving, or a sinking fund). Nothing is left 'floating' and unaccounted for, which is exactly where money tends to disappear.",
                }},
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Pay yourself first",
                    "body": "Most people save whatever is left at the end of the month — and usually that's nothing. 'Pay yourself first' flips it: the moment money comes in, you move your savings amount aside before you spend on anything else. Setting it to happen automatically (with a grown-up's help on any account) means you never have to rely on willpower.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "In zero-based budgeting, what does 'getting to zero' actually mean?",
                    "choices": ["Every pound of income has been assigned a job — spending, saving, or a future cost", "You must spend all your money down to nothing", "You're not allowed to save anything", "Your bank balance must literally read £0"],
                    "answer_index": 0,
                    "explanation": "Zero-based means planned income minus planned jobs equals zero — every pound is assigned, including the ones you save. It's about leaving nothing unaccounted for, not about spending it all.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "What does 'pay yourself first' mean?",
                    "choices": ["Move your savings aside as soon as money comes in, before spending on anything else", "Buy yourself a treat before paying any bills", "Only save whatever happens to be left at month's end", "Pay friends back before you save"],
                    "answer_index": 0,
                    "explanation": "Saving first — ideally automatically — means your savings goal gets met before spending nibbles it away. Saving 'what's left' usually leaves nothing.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Your income is different every month (some months £40, some £90). What's a sensible way to budget?",
                    "choices": ["Plan around your lower typical months, and save extra in the bigger months", "Plan as if every month is your best month ever", "Refuse to budget until your income is steady", "Spend more in good months to 'balance out' the lean ones"],
                    "answer_index": 0,
                    "explanation": "With irregular income, budgeting around a lower, reliable amount keeps you safe in lean months, while the surplus from good months builds a cushion.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "You get a small pay rise and immediately start spending more on wants, so you're no better off. What's this called?",
                    "choices": ["Lifestyle creep — spending rising to swallow up extra income", "Compound interest", "A sinking fund", "A budget surplus"],
                    "answer_index": 0,
                    "explanation": "Lifestyle creep is when spending quietly grows to match any extra money, so you never get ahead. The fix: when income rises, send some of the increase straight to savings.",
                }},
                {"type": "scenario", "xp_reward": 20, "content_json": {
                    "prompt": "You start a weekend job earning more than your old allowance. How do you handle the extra money wisely?",
                    "choices": [
                        {"label": "Upgrade everything now — new clothes, more takeaways, the lot", "outcome": "That's lifestyle creep in action. Spending swells to match the new income and you end up no better off than before, just with more stuff."},
                        {"label": "Decide a savings amount first, move it aside automatically, then budget the rest — checking the plan with a grown-up", "outcome": "Excellent. Paying yourself first locks in your savings, automating it removes the willpower battle, and a grown-up's second look keeps the plan realistic."},
                        {"label": "Keep no plan and just see what's left at the end of each month", "outcome": "'Saving what's left' almost always leaves nothing, especially with more money tempting you. Without a plan the extra income just slips away."},
                    ],
                    "correct_index": 1,
                }},
            ]},
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
        "extra_levels": [
            {"title": "Level 2", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "The 'wait a bit' test",
                    "body": "When you really want something, try the wait-a-bit test: give yourself a short pause — a day, or even just a sleep on it — before buying. Lots of wants feel huge in the moment and much smaller the next day. If you still want it after waiting, it's probably a genuine choice, not just an impulse. Waiting costs you nothing and often saves you money.",
                }},
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Cost per use: the real value",
                    "body": "Price isn't the same as value. A £40 pair of shoes you wear every day can be better value than a £15 pair you wear twice. A handy trick is cost per use: roughly, the price divided by how many times you'll actually use it. Something cheap that you never use is expensive in disguise.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "What is the 'wait a bit' test?",
                    "choices": ["A basic phone you must have for school", "Giving yourself a short pause before buying, to check it's not just an impulse", "Buying something only if it's on sale", "Asking a shop to lower the price"],
                    "answer_index": 1,
                    "explanation": "Pausing before you buy lets the first rush of 'I want it NOW' fade, so you can decide calmly. If you still want it after waiting, that's a real choice.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "£40 boots you'll wear 200 times, or £15 boots you'll wear 5 times. Which is better value (cost per use)?",
                    "choices": ["The £15 boots, because they cost less", "The £40 boots — about 20p per wear vs £3 per wear", "They're exactly the same value", "You can't compare them"],
                    "answer_index": 1,
                    "explanation": "£40 ÷ 200 ≈ 20p each time; £15 ÷ 5 = £3 each time. The pricier boots are far better value because you'll actually use them. Cheap-but-unused is expensive in disguise.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "You spend your last £20 on a game instead of a cinema trip with friends. The cinema trip you gave up is called the…",
                    "choices": ["Bonus", "Opportunity cost", "Refund", "Interest"],
                    "answer_index": 1,
                    "explanation": "Every choice has an opportunity cost — the next-best thing you gave up. Money spent once can't be spent again, so it's worth asking 'what am I saying no to?'",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "A toy is reduced from £50 to £30. Which question best tells you if it's a smart buy?",
                    "choices": ["'How big is the discount?'", "'Would I want this and use it even at £30 if it had never been £50?'", "'Will it sell out today?'", "'What colour is it?'"],
                    "answer_index": 1,
                    "explanation": "A discount only saves money if you'd genuinely want and use the thing anyway. 'It's 40% off!' isn't a reason to buy — the real question is whether it's worth £30 to you.",
                }},
                {"type": "scenario", "xp_reward": 20, "content_json": {
                    "prompt": "You see a £35 gadget online and you really want it right now. You've got the money. What's the smartest move?",
                    "choices": [
                        {"label": "Add it to a wishlist and check again in a few days", "outcome": "Great use of the wait-a-bit test. If you still want it later, you can buy it as a calm choice — and you'll often find the urge has faded."},
                        {"label": "Buy it instantly before the feeling passes", "outcome": "That rush is exactly what impulse buying feels like. Buying before you've thought it through is how wants win over sensible choices."},
                        {"label": "Buy two in case one breaks", "outcome": "That's spending even more on an impulse you haven't tested. One is already an unplanned want; two doubles the regret risk."},
                    ],
                    "correct_index": 0,
                }},
            ]},
            {"title": "Level 3", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Adverts are made to make you want",
                    "body": "Adverts, sponsored posts and influencer videos exist to make you feel you need something. Bright colours, happy faces, 'everyone has it' — these are clever tools, not facts. Spotting that an advert is designed to nudge you is a superpower: once you see the trick, it has far less power over you. Wanting something because an advert told you to isn't the same as actually needing it.",
                }},
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "'Limited time!' and other hurry-up tricks",
                    "body": "'Only 2 left!', 'Sale ends tonight!', 'Don't miss out!' — these messages are built to make you panic-buy before you've had time to think. Real needs don't have a countdown timer. When something is shouting at you to hurry, that's exactly the moment to slow down, breathe, and ask a trusted grown-up if you're unsure.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "What is the main job of an advert?",
                    "choices": ["To give you honest, balanced advice", "To make you want the product and feel you should buy it", "To save you money on purpose", "To tell you what you genuinely need"],
                    "answer_index": 1,
                    "explanation": "Adverts are made to sell, not to advise. Knowing that helps you enjoy them without letting them decide your spending for you.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "A site flashes 'Only 1 left — sale ends in 5 minutes!' What is this mostly designed to do?",
                    "choices": ["Help you make a calm, careful decision", "Rush you into buying before you've thought it through", "Give you a guaranteed best price", "Remind you of something you truly need"],
                    "answer_index": 1,
                    "explanation": "Countdown timers and 'almost gone!' messages create false panic. A genuine need doesn't expire in five minutes — so that pressure is your cue to slow right down.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Your friends all bought the same trainers and say you 'have to' get them too. That pressure to want what the group wants is called…",
                    "choices": ["Opportunity cost", "Peer pressure", "Compound interest", "A refund"],
                    "answer_index": 1,
                    "explanation": "Wanting something just because friends have it is peer pressure. It's normal to feel it — but it's your money and your choice. Real friends won't mind if you spend differently.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "A favourite influencer is paid to show off a £60 hoodie. What's the wisest way to think about it?",
                    "choices": ["'They love it, so I obviously need it'", "'They're being paid to promote it, so I'll decide for myself if it's worth £60 to me'", "'Everything they recommend must be a great deal'", "'I should buy it fast before it sells out'"],
                    "answer_index": 1,
                    "explanation": "Sponsored posts are paid adverts. The person may be lovely, but the question is still whether the item is worth the price to you — not whether someone famous showed it.",
                }},
                {"type": "scenario", "xp_reward": 20, "content_json": {
                    "prompt": "A big online sale is on. An influencer you follow is hyping a £45 jacket, the page says 'Only a few left!', and two friends have already bought it. You've got £45 saved for something else. What do you do?",
                    "choices": [
                        {"label": "Buy it right now so you don't miss out or feel left out", "outcome": "That's ads, hype and peer pressure all pulling at once — the exact mix designed to make you spend without thinking."},
                        {"label": "Pause, remember it's all designed to rush you, and chat to a trusted grown-up before deciding", "outcome": "Spot-on. Naming the pressure (advert + countdown + friends) takes its power away, and a trusted grown-up can help you decide calmly."},
                        {"label": "Borrow money so you can buy it AND keep your £45", "outcome": "Borrowing for a hyped-up want is how small wants turn into money you owe. Never take on debt because of a countdown timer."},
                    ],
                    "correct_index": 1,
                }},
            ]},
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
        "extra_levels": [
            {"title": "Level 2", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "There's more than one kind of risk",
                    "body": "Risk isn't just one thing. 'Company-specific risk' is the danger that one business does badly — maybe its product flops. 'Market risk' is when lots of investments fall together, like during a downturn. Diversifying across many companies helps with company-specific risk, but market risk affects almost everyone at once. Knowing the difference helps you understand what you can and can't protect against.",
                }},
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Risk isn't only about losing money",
                    "body": "Two sneaky risks don't look scary but matter a lot. Inflation risk is when prices rise faster than your money grows — £10 today may buy less in ten years, so cash sitting still can quietly lose value. Liquidity risk is not being able to turn something into cash quickly when you need it (a house can't be sold in a day). Good plans think about all of these, not just 'will it crash?'.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "A company you invested in has a bad year, but the rest of the market is fine. What type of risk is this an example of?",
                    "choices": ["Company-specific risk", "Inflation risk", "Liquidity risk", "No risk at all"],
                    "answer_index": 0,
                    "explanation": "When trouble hits just one business while others are fine, that's company-specific risk — the kind diversification helps reduce most.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Why can keeping ALL your money as cash for many years still be risky?",
                    "choices": ["Banks always lose your money", "Inflation can make that cash buy less over time", "Cash is the riskiest thing of all", "Cash earns the highest returns"],
                    "answer_index": 1,
                    "explanation": "This is inflation risk. Cash feels safe, but if prices rise faster than your savings grow, your money slowly buys less. That's why people invest some money for the long term.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "You'll need your money in 6 months to buy something important. Where does it make most sense to keep it?",
                    "choices": ["All in one exciting stock", "In a savings account, where the value won't suddenly drop", "Spread across lots of risky shares", "In something you can't sell for years"],
                    "answer_index": 1,
                    "explanation": "Money you need soon should be kept somewhere steady. Shares can fall right when you need them — a short time horizon means lower risk is sensible.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "What does 'time horizon' mean when deciding how much risk to take?",
                    "choices": ["How many companies you own", "How long until you'll actually need the money", "What time the stock market opens", "How old a company is"],
                    "answer_index": 1,
                    "explanation": "Your time horizon is how long you can leave money invested. Longer horizons can usually handle more ups and downs, because there's time to recover.",
                }},
                {"type": "scenario", "xp_reward": 20, "content_json": {
                    "prompt": "You've saved £200. You want to start investing, but you don't have any spare money set aside for emergencies (like a broken phone or an unexpected trip). What's the wisest first move?",
                    "choices": [
                        {"label": "Invest all £200 right away, emergencies can wait", "outcome": "Risky. If something unexpected happens, you might have to sell investments at a bad time. Most sensible plans build a small emergency fund first."},
                        {"label": "Set some aside as an emergency fund, then invest the rest", "outcome": "Smart. An emergency fund is money kept safe and easy to reach. With that cushion in place, you can invest the rest without panic if life surprises you."},
                        {"label": "Spend it all now so there's nothing to risk", "outcome": "Spending it isn't a plan — that money can't grow or protect you later. Saving a cushion and investing the rest is the balanced move."},
                    ],
                    "correct_index": 1,
                }},
            ]},
            {"title": "Level 3", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Risk tolerance vs risk capacity",
                    "body": "These sound the same but aren't. Risk tolerance is how comfortable you feel when investments wobble — some people stay calm, others lose sleep. Risk capacity is how much risk you can actually afford to take, based on your money and how soon you need it. A wise plan respects both: never take more risk than you can handle emotionally or financially. Grown-ups think about both before deciding.",
                }},
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Bonds: the steadier teammate",
                    "body": "Shares can grow a lot but bounce around. A bond is more like lending money to a company or government that promises to pay you back with a little interest — usually steadier, but with smaller growth. Many people mix shares and bonds so the steadier part cushions the bumpy part. Mixing different types of investment, not just different companies, is diversification at the next level.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Jordan can afford to invest for 20 years but feels sick whenever prices drop. What's the best description?",
                    "choices": ["High risk capacity, low risk tolerance", "Low risk capacity, high risk tolerance", "No risk at all", "Jordan should borrow money to invest"],
                    "answer_index": 0,
                    "explanation": "Jordan can afford long-term risk (high capacity) but doesn't cope well emotionally with drops (low tolerance). A good plan respects the lower of the two so Jordan can stick with it.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "The market drops 20% in a month and the news is gloomy. For a long-term investor, what's usually the wisest reaction?",
                    "choices": ["Sell everything immediately to stop the loss", "Stay calm and stick to the long-term plan", "Borrow money to buy ten times as much", "Check the price every five minutes"],
                    "answer_index": 1,
                    "explanation": "Ups and downs (volatility) are normal. Selling in a panic often locks in losses. For someone with a long time horizon, staying calm and patient usually wins.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Over time, your shares grow so much that they're now a much bigger slice of your money than you planned. Selling a little and topping up your steadier investments to get back to your target mix is called…",
                    "choices": ["Rebalancing", "Day trading", "Inflation", "Going all in"],
                    "answer_index": 0,
                    "explanation": "Rebalancing means gently adjusting back to your planned mix so one part doesn't grow too risky. It's a calm, routine habit — not a reaction to hype.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "How does buying insurance (like for a phone or a bike) relate to managing risk?",
                    "choices": ["It's a way to invest in the stock market", "It moves the cost of a rare, expensive problem off you for a small regular payment", "It guarantees your investments will grow", "It removes all risk from your life"],
                    "answer_index": 1,
                    "explanation": "Insurance is risk transfer — you pay a little regularly so a big unexpected cost doesn't fall entirely on you. It's another everyday tool people use to handle risk, alongside diversifying and saving.",
                }},
                {"type": "scenario", "xp_reward": 20, "content_json": {
                    "prompt": "An online video promises 'guaranteed 50% returns every month — no risk!' if you move all your savings into it today. What do you do?",
                    "choices": [
                        {"label": "Move everything in fast before the chance disappears", "outcome": "A huge warning sign. 'Guaranteed high returns, no risk' doesn't exist — higher reward always comes with higher risk. Pressure to act now is a classic scam tactic."},
                        {"label": "Stop, stay sceptical, and talk to a trusted grown-up first", "outcome": "Exactly right. 'No risk, huge guaranteed returns' is a red flag for a scam. Slowing down and asking a trusted adult protects you from get-rich-quick traps."},
                        {"label": "Put in just half — that seems safer", "outcome": "Still risky. The problem isn't the amount, it's the promise. Anything claiming guaranteed big returns with no risk is not to be trusted at all."},
                    ],
                    "correct_index": 1,
                }},
            ]},
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
        "extra_levels": [
            {"title": "Level 2", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "A chain that's hard to cheat",
                    "body": "A blockchain stores transactions in 'blocks' that are joined in order, like links in a chain. Each new block carries a fingerprint of the one before it, so if anyone tried to secretly change an old block, the fingerprints would stop matching and the whole network would notice. Thousands of computers keep their own copy and compare notes, so there's no single record a cheat could quietly rewrite. Trust comes from lots of computers agreeing, not from one boss in charge.",
                }},
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Your keys, your responsibility",
                    "body": "A crypto wallet doesn't really 'hold' coins — it holds keys. Your public key is like an account number you can share so people can send to you. Your private key is the secret that lets you spend, and it must NEVER be shared. The scary part: if you lose your private key there's no 'forgot password' button and no bank to ring — the crypto is usually gone forever. And if a scammer gets your private key or 'seed phrase', they can take everything in seconds.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Why is it so hard to secretly change an old transaction on a blockchain?",
                    "choices": ["Because a security guard checks every block", "Because each block carries a fingerprint of the one before it, and thousands of computers compare copies", "Because the government keeps the only copy", "Because old blocks are printed out on paper"],
                    "answer_index": 1,
                    "explanation": "Each block is linked to the previous one by a fingerprint, and thousands of computers hold matching copies — so a secret change would break the chain and everyone would spot it.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Which key should you NEVER share with anyone?",
                    "choices": ["Your public key (like an account number)", "Your private key or seed phrase (the secret that lets you spend)", "The name of the coin", "The price you paid"],
                    "answer_index": 1,
                    "explanation": "Your public key is fine to share so people can send to you. Your private key (or seed phrase) is the secret that controls everything — sharing it is like handing someone the keys to your whole wallet.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "A website promises 'Send 1 coin and we'll send you 2 coins back — guaranteed, today only!' What is this most likely?",
                    "choices": ["A normal, safe way to grow money", "A scam — 'double your money, guaranteed, act now' is a classic crypto trick", "A government savings scheme", "A bank offering interest"],
                    "answer_index": 1,
                    "explanation": "Guaranteed doubling, 'today only' pressure, and 'send first' are textbook scam signs. Real investing is never guaranteed, and nobody legit asks you to send crypto to get more back.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "You forget the private key to your crypto wallet. What usually happens?",
                    "choices": ["You ring a helpline and they reset it", "The bank refunds you", "There is often no way to recover it, and the crypto can be lost for good", "It automatically emails you a new key"],
                    "answer_index": 2,
                    "explanation": "Unlike a bank account, most crypto has no 'forgot password' and no customer-service reset. Lose the key and the crypto is usually gone — which is one reason it's risky.",
                }},
                {"type": "scenario", "xp_reward": 20, "content_json": {
                    "prompt": "You're playing an online game and someone you've never met messages: 'I'll give you free crypto — just send me your wallet's secret recovery phrase so I can add it.' What do you do?",
                    "choices": [
                        {"label": "Refuse and tell a trusted grown-up", "outcome": "Exactly right. Your secret recovery phrase controls everything in the wallet. Nobody genuine ever needs it — anyone asking is trying to steal from you. Telling a trusted adult is the safe move."},
                        {"label": "Send it — free crypto sounds great", "outcome": "This is a trap. Handing over your recovery phrase lets a scammer empty the wallet instantly. 'Free crypto' used as bait is one of the most common online scams."},
                        {"label": "Send just half of the phrase to be safe", "outcome": "Still unsafe — you should never share any part of a secret recovery phrase, and a stranger asking for it at all is a red flag. Stop and tell a trusted grown-up."},
                    ],
                    "correct_index": 0,
                }},
            ]},
            {"title": "Level 3", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "What makes 'money' actually money?",
                    "body": "Normal money like the pound does three jobs well: you can spend it almost anywhere, its value stays fairly steady day to day, and the Bank of England helps manage it. Most crypto struggles with those jobs — few shops accept it, its price can swing wildly in a single day, and no central body steadies it. That doesn't make crypto 'fake', but it's why many experts treat it more like a risky bet than like everyday money. Understanding the difference helps you see through people who call it 'the future of all money'.",
                }},
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Why rules and energy both matter",
                    "body": "If a UK bank fails, the FSCS protects your savings up to £85,000 — but crypto usually has no such safety net, so if a platform collapses or gets hacked your money may simply be gone. Regulators like the FCA also warn that crypto is high-risk and largely unprotected. There's an environment angle too: some cryptocurrencies (like Bitcoin) use enormous amounts of electricity to run, which has a real climate cost. A thoughtful investor weighs all of this — safety, rules, and impact — not just the price.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Which is a job that ordinary money (like the pound) does much better than most crypto?",
                    "choices": ["Keeping a fairly steady value you can spend almost anywhere", "Doubling in value every week", "Being impossible to ever lose", "Earning guaranteed profits"],
                    "answer_index": 0,
                    "explanation": "A currency works best when its value is steady and widely accepted. Most crypto swings too much and is accepted in too few places to do that job well — a key difference from everyday money.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "If a crypto platform gets hacked and your crypto is stolen, what protection usually applies?",
                    "choices": ["The FSCS refunds you up to £85,000", "The government replaces it", "Usually none — crypto generally isn't covered by the protections that guard bank savings", "Your school insurance covers it"],
                    "answer_index": 2,
                    "explanation": "FSCS protection covers savings in regulated UK banks, not most crypto. That missing safety net is a big reason regulators call crypto high-risk.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "A famous person posts 'Buy this new coin NOW before you miss out!' What's the smartest reaction?",
                    "choices": ["Buy immediately so you don't miss out", "Copy them — famous people can't be wrong", "Pause, be sceptical of hype and 'fear of missing out', and talk to a trusted grown-up before doing anything", "Borrow money to buy more"],
                    "answer_index": 2,
                    "explanation": "'Buy now or miss out' is designed to rush you. Famous people are sometimes paid to promote coins. Slowing down, questioning the hype, and asking a trusted adult protects you from FOMO-driven mistakes.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Why do some people raise concerns about the environmental impact of certain cryptocurrencies?",
                    "choices": ["They use too much paper", "Some use huge amounts of electricity to run, which has a climate cost", "They are made of plastic", "They require lots of water to print"],
                    "answer_index": 1,
                    "explanation": "Cryptocurrencies like Bitcoin can use enormous amounts of electricity. That energy use is a real-world cost a thoughtful person factors in, alongside the financial risks.",
                }},
                {"type": "scenario", "xp_reward": 20, "content_json": {
                    "prompt": "Your older cousin is excited: 'I'm putting ALL my birthday money into one new coin a YouTuber promoted — it's going to the moon!' They ask what you think. What's the wisest thing to say?",
                    "choices": [
                        {"label": "Sounds amazing — put mine in too!", "outcome": "Risky. Following hype from a video and betting everything on one volatile coin is exactly how people lose money fast. 'Going to the moon' is a promise nobody can actually make."},
                        {"label": "Maybe slow down — that's a lot of risk on one hyped coin. Let's read about it and talk to a trusted grown-up first.", "outcome": "Brilliant. You're spotting hype, the danger of putting everything in one place, and the value of caution and adult guidance. That's exactly how a careful thinker responds."},
                        {"label": "Borrow more so you can buy even more!", "outcome": "Never a good idea. Borrowing to buy something this volatile can leave you owing money AND losing the investment. One of the most dangerous moves in investing."},
                    ],
                    "correct_index": 1,
                }},
            ]},
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
        "extra_levels": [
            {"title": "Level 2", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Income tax isn't the only tax",
                    "body": "Income tax is just one of many. The government also collects tax when you spend money (VAT), when you earn money in other ways, and through National Insurance. Most adults pay several different taxes without even noticing. Learning the main ones helps you understand the true cost of things — and where that money goes.",
                }},
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "VAT: the tax hidden in the price",
                    "body": "VAT (Value Added Tax) is added to the price of most things you buy — toys, games, clothes for older kids, eating out. The price on the shelf usually already includes it, so you don't see it as a separate line. The standard rate is 20% (for example, on a £12 toy, about £2 is VAT). Some things have no VAT at all, like most food in the supermarket and children's clothes — which keeps everyday basics cheaper.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "What is VAT?",
                    "choices": ["A tax added to the price of most things you buy", "A discount shops give to children", "Money the government pays you for shopping", "A type of savings account"],
                    "answer_index": 0,
                    "explanation": "VAT (Value Added Tax) is a tax on spending. It's usually built into the price you see, so a chunk of what you pay on many items goes to the government.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Which of these would normally have NO VAT added in the UK?",
                    "choices": ["A video game console", "Most basic food in a supermarket", "A meal at a restaurant", "A cinema ticket"],
                    "answer_index": 1,
                    "explanation": "Most everyday food in shops is 'zero-rated' for VAT, and so are children's clothes. This helps keep essentials affordable for families.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "National Insurance (NI) is a tax workers and employers pay. What does it mainly help fund?",
                    "choices": ["The state pension and the NHS", "Only the person's own bank account", "Football stadiums", "Nothing — it's just kept as a fee"],
                    "answer_index": 0,
                    "explanation": "NI is a tax that helps pay for things like the state pension and the NHS. (You'll see how it appears on a payslip in the 'Your First Paycheque' module — here we just learn what it's for.)",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Which of these is usually paid for by taxes?",
                    "choices": ["The NHS, schools, and roads", "Your family's weekly shopping", "A friend's birthday present", "Pocket money from your parents"],
                    "answer_index": 0,
                    "explanation": "Taxes fund shared services everyone can use — the NHS, state schools, roads, police, fire services, libraries and more. Personal spending like presents and pocket money comes out of your own money, not tax.",
                }},
                {"type": "scenario", "xp_reward": 20, "content_json": {
                    "prompt": "You buy a £10 toy and the receipt says 'includes VAT £1.67'. Your little sister says 'the shop is stealing some of your money!' What's the best thing to say?",
                    "choices": [
                        {"label": "You're right, let's complain to the shop.", "outcome": "Not quite. The shop isn't taking it for themselves — VAT is a tax that's collected at the till and passed on to the government to help pay for shared things like hospitals and schools."},
                        {"label": "That's VAT — a tax built into the price that helps pay for things like hospitals and schools.", "outcome": "Spot on! VAT is included in most prices. The shop collects it and sends it to the government. It's normal, and it's the law."},
                        {"label": "Receipts are always wrong, ignore it.", "outcome": "Receipts are usually correct. The VAT line just shows how much of the price was tax — a handy way to see the hidden cost of things."},
                    ],
                    "correct_index": 1,
                }},
            ]},
            {"title": "Level 3", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Why 'progressive' tax tries to be fair",
                    "body": "A 'progressive' tax means people who earn more pay a higher rate on the extra they earn — not on everything. Think of income split into slices: the first slice is tax-free, the next slice is taxed at a lower rate, and only the highest slices are taxed more. The idea is that those who can afford to contribute more, do — while a tax-free slice protects people on lower incomes. Whether that balance is 'fair' is something adults genuinely debate.",
                }},
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Tax and benefits: a two-way street",
                    "body": "Tax money doesn't just disappear — it flows back out as things the country needs and as support for people who need it: the NHS when you're poorly, schools, the state pension for older people, and help for families having a hard time. So tax is a bit like everyone putting into a shared pot, and the pot paying for things no single person could buy alone.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "In a progressive tax system, what happens when someone earns a bit more and moves into a higher band?",
                    "choices": ["Only the extra money in the higher band is taxed at the higher rate", "Their entire income is suddenly taxed at the higher rate", "They stop paying any tax at all", "They have to pay last year's tax again"],
                    "answer_index": 0,
                    "explanation": "Only the slice of income inside each band is taxed at that band's rate. Earning more always means more take-home pay — moving up a band never makes you worse off overall.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "How are taxes and 'benefits' (government support) connected?",
                    "choices": ["Tax money is collected, then some of it is paid back out as support and services", "They have nothing to do with each other", "Benefits are paid for by shops, not tax", "Everyone gets exactly back what they paid in"],
                    "answer_index": 0,
                    "explanation": "It's a two-way flow. Taxes fill a shared pot; that pot funds services for everyone and extra support for people who need it. It's not a personal savings account — it's shared.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "People disagree about the 'fairest' way to tax. Which statement is true?",
                    "choices": ["There's one correct answer everyone agrees on", "It's a genuine debate — thoughtful people weigh it up differently", "Only the government's opinion matters", "Tax fairness can be proved with a single sum"],
                    "answer_index": 1,
                    "explanation": "Reasonable people disagree about how much different earners should pay and what tax should fund. Understanding the trade-offs matters more than picking a 'winning' side — and it's a great thing to discuss with a grown-up.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "What does being a responsible taxpayer mean?",
                    "choices": ["Paying the tax you genuinely owe, honestly and on time", "Hiding earnings so you never pay anything", "Paying tax only if someone is watching", "Refusing to pay because you don't like it"],
                    "answer_index": 0,
                    "explanation": "Paying your fair share honestly keeps the shared services running for everyone. Deliberately hiding income to dodge tax is illegal and unfair on others. If tax ever feels confusing, that's normal — a trusted adult or the official HMRC guidance can help.",
                }},
                {"type": "scenario", "xp_reward": 20, "content_json": {
                    "prompt": "Imagine you're older and doing weekend work. A neighbour offers to pay you in cash and says 'don't tell anyone, then neither of us pays any tax on it.' What's the wise response?",
                    "choices": [
                        {"label": "Great, free money!", "outcome": "Hiding earnings to avoid tax is illegal, even when it's cash. It might feel like a win, but it can land both people in trouble and it's unfair on everyone who pays their share."},
                        {"label": "I'll keep things honest and check with a grown-up about how tax works for my earnings.", "outcome": "Wise choice. Being honest about what you earn is the right thing to do, and a trusted adult can help you understand whether you even owe anything (often, under the Personal Allowance, young earners don't)."},
                        {"label": "I'll just decide the tax rules don't apply to me.", "outcome": "Tax rules apply to everyone, whatever their age. The good news is that low earnings are often below the tax-free allowance anyway — so honesty usually costs you nothing and keeps you safe."},
                    ],
                    "correct_index": 1,
                }},
            ]},
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
        "extra_levels": [
            {"title": "Level 2", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "How interest piles up (not just once)",
                    "body": "APR is a yearly price tag, but interest on a credit card is usually added every month on whatever you still owe. So if you don't clear the balance, next month's interest is charged on the old amount PLUS last month's interest. It's compound interest working in reverse — against you instead of for you. The longer a debt sits unpaid, the faster it grows.",
                }},
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Four common types of credit",
                    "body": "Not all borrowing is the same. A credit card lets you spend up to a limit and is free if you clear it each month. A personal loan gives you a lump sum you repay in fixed monthly amounts. An overdraft lets your bank balance dip below £0 (often with fees). Buy Now Pay Later (BNPL) splits a purchase into instalments — handy, but easy to lose track of, and the missed-payment fees can sting. Knowing which is which helps you choose wisely.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "On most credit cards, how often is interest added to what you owe if you don't clear the balance?",
                    "choices": ["Once a year only", "Usually every month, on the amount still owed", "Never — credit cards don't charge interest", "Only when you close the account"],
                    "answer_index": 1,
                    "explanation": "Card interest is normally added monthly on your remaining balance, so an unpaid debt can grow faster than the yearly APR alone makes it sound.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "What is 'Buy Now Pay Later' (BNPL)?",
                    "choices": ["A way to get items completely free", "A savings account that pays you later", "A way to split a purchase into instalments you pay over time", "A type of credit score"],
                    "answer_index": 2,
                    "explanation": "BNPL spreads the cost of something into smaller payments. It can be useful, but missing a payment often means fees, so it needs care and tracking.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "You owe £100 on a card at roughly 2% interest a month and only pay the small minimum each month. What tends to happen?",
                    "choices": ["The debt disappears after one payment", "The debt shrinks very slowly and you pay extra in interest along the way", "The interest rate drops to zero", "The bank cancels the balance"],
                    "answer_index": 1,
                    "explanation": "Minimum payments barely dent the balance, so interest keeps being charged on what's left. The debt lingers and costs more overall — paying more than the minimum clears it faster and cheaper.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Which of these is the most responsible way to use a credit card?",
                    "choices": ["Spend right up to the limit every month", "Only ever pay the minimum", "Spend only what you can clear in full when the bill arrives", "Take out cash on it as often as possible"],
                    "answer_index": 2,
                    "explanation": "Spending only what you can repay in full means you pay no interest and still build a positive borrowing history. That's the card working for you, not against you.",
                }},
                {"type": "scenario", "xp_reward": 20, "content_json": {
                    "prompt": "Your phone breaks and a £180 replacement is offered as 'BNPL — just £30 a month for 6 months, 0% interest.' You get £20 a month pocket money. What's the smartest move?",
                    "choices": [
                        {"label": "Take the BNPL deal — it's 0% so it's basically free", "outcome": "It looks free, but £30 a month is more than your £20 income, so you'd likely miss a payment — and missed BNPL payments bring fees and can hurt your record. The maths has to add up first."},
                        {"label": "Buy an even pricier phone since you're paying monthly anyway", "outcome": "Spreading the cost can tempt you to overspend. A bigger debt is still a debt, and it's even harder to keep up with. This is exactly how easy credit catches people out."},
                        {"label": "Pause, and talk it through with a trusted grown-up before agreeing to anything", "outcome": "Smart. A grown-up can help you check whether the payments fit your money, whether a cheaper phone would do, or whether saving up first is better. Never rush into a credit deal."},
                    ],
                    "correct_index": 2,
                }},
            ]},
            {"title": "Level 3", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "How to build (and protect) a good credit score",
                    "body": "A credit score grows with steady, boring good habits: paying every bill on time, not using your whole limit, and keeping accounts open for a long while. One missed payment can dent it, and using almost all your available credit makes lenders nervous. You can't build a score overnight — it's a long game of small, reliable actions. Protecting it means checking statements, never ignoring a bill, and being cautious about how many credit deals you sign up for.",
                }},
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "What a debt spiral looks like (and how to step out)",
                    "body": "A debt spiral is when you borrow to cover borrowing — paying one card with another, or taking a new loan to clear an old one. Each step adds more interest, so the total keeps climbing even though it feels like you're 'dealing with it.' The way out is to stop adding new debt, list what you owe, and ask for help early. In the UK there are free charities and services (your bank can point you to them) that help people make a plan — getting help is a strong, sensible move, never something to feel ashamed of.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Which habit best helps build a strong credit score over time?",
                    "choices": ["Missing the odd payment to save money that month", "Paying bills on time and using only a small part of your limit", "Maxing out every card you have", "Opening lots of new credit accounts at once"],
                    "answer_index": 1,
                    "explanation": "Lenders like steady, reliable behaviour: on-time payments and low credit use. Those small habits, repeated over time, build trust.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Someone takes out a new loan to pay off an old loan, then borrows again to cover that. What is this an example of?",
                    "choices": ["Smart investing", "A debt spiral", "Building a strong emergency fund", "Earning compound interest"],
                    "answer_index": 1,
                    "explanation": "Borrowing to repay borrowing just moves debt around while adding more interest. That's a debt spiral — the fix is to stop adding new debt and ask for help making a plan.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "When is borrowing more likely to be a wise decision?",
                    "choices": ["To buy the latest trainers everyone has", "To fund something that lasts or grows in value, with repayments you can comfortably afford", "To impress friends with a big purchase", "Whenever a deal says '0%' — no matter the cost"],
                    "answer_index": 1,
                    "explanation": "Borrowing can be sensible when it buys lasting value (like training or a reliable essential) AND the repayments fit your money. If it's just to consume more now, it's usually unwise.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "If you or your family were ever worried about debt, what's the best first step?",
                    "choices": ["Hide the bills and hope it sorts itself out", "Borrow even more to cover it", "Talk to a trusted grown-up and look into free UK debt-help services", "Ignore letters from the lender"],
                    "answer_index": 2,
                    "explanation": "Debt worries get easier the sooner they're shared. A trusted grown-up plus free UK debt-advice charities can help build a plan — asking for help early is the smart, brave choice.",
                }},
                {"type": "scenario", "xp_reward": 20, "content_json": {
                    "prompt": "A friend says, 'Just get a credit card, max it out on a holiday, then sort the payments later — everyone does it.' What's the wisest response?",
                    "choices": [
                        {"label": "Do it — you only live once, and you'll figure out repayments somehow", "outcome": "Maxing out a card with no plan to repay is how debt spirals start. Interest piles up monthly and your credit score takes a hit. 'Sort it later' rarely works."},
                        {"label": "Pass for now, and only ever borrow what you've planned to repay — and ask a grown-up if unsure", "outcome": "Spot on. Borrowing with a clear repayment plan you can afford keeps you in control. When a deal sounds too easy, slowing down and checking with a trusted grown-up protects you."},
                        {"label": "Get the card but never use it at all, just to copy your friend", "outcome": "Getting credit just because a friend said so isn't a plan. Decisions about borrowing should be yours, based on what you can afford — not peer pressure."},
                    ],
                    "correct_index": 1,
                }},
            ]},
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
        "extra_levels": [
            {"title": "Level 2", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Test before you build",
                    "body": "Before you spend time or money, find out if people actually want your thing. This is called testing your idea. Ask a few people: 'Would you buy this? What would you pay?' Even better — try to make one real sale. A 'yes, here's the money' tells you far more than ten people saying 'that sounds nice.' Real customers are the best teachers.",
                }},
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Your first customers are closest to home",
                    "body": "You don't need strangers to start. Your first customers are usually people who already know and trust you: family, neighbours, friends' parents, people at a club or school fair (always with a grown-up's help when money or strangers are involved). Do a brilliant job for a few people, and they'll tell others. That's word of mouth — the cheapest and most powerful advertising there is.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "What's the best way to find out if your side-hustle idea will work?",
                    "choices": ["Spend all your savings on supplies first", "Try to make a real sale to a real customer and see what happens", "Keep the idea secret until it's perfect", "Wait until lots of other people are doing it"],
                    "answer_index": 1,
                    "explanation": "A real sale is the strongest proof people want what you offer. Testing cheaply first means you learn fast without risking much.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "You're not sure what to charge for washing cars. What's a sensible way to set a fair price?",
                    "choices": ["Pick the biggest number you can think of", "Charge nothing so everyone likes you", "Ask around what others charge locally and start somewhere fair", "Change your price every single customer"],
                    "answer_index": 2,
                    "explanation": "Looking at what similar things cost nearby gives you a fair starting point. You can always adjust later — but free isn't a business, and wild prices scare customers off.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "A happy customer offers to tell their friends about your dog-walking. Why is that valuable?",
                    "choices": ["It isn't — only paid adverts work", "Word of mouth from a happy customer is trusted and costs you nothing", "It means you must lower your prices", "It only matters if they post it online"],
                    "answer_index": 1,
                    "explanation": "People trust a recommendation from someone they know more than any advert. Looking after your customers turns them into your best marketers — for free.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "What's the smartest 'advert' for a brand-new side hustle with no money?",
                    "choices": ["A huge billboard in the city", "A TV commercial", "A simple flyer or a friendly word to people nearby (with a grown-up's help)", "Paying a celebrity"],
                    "answer_index": 2,
                    "explanation": "Starting small and local costs little or nothing. Big, expensive adverts make no sense before you've proven people will buy.",
                }},
                {"type": "scenario", "xp_reward": 20, "content_json": {
                    "prompt": "You want to start a baking side hustle. A friend says 'just buy loads of ingredients and packaging now — you'll definitely sell out!' What's the wisest first step?",
                    "choices": [
                        {"label": "Spend everything you have on ingredients and fancy boxes straight away", "outcome": "Risky. You don't yet know if people will buy or what they'll pay. Spending big before testing can leave you stuck with stock no one wants."},
                        {"label": "Bake a small batch, offer it to a few people you know (with a grown-up's help), and see if they buy", "outcome": "Smart. A small, cheap test tells you whether there's real demand and what price feels right, before you risk much. Then you can grow with confidence."},
                        {"label": "Keep it secret and tell no one in case someone copies you", "outcome": "If nobody knows about it, nobody can buy it. Telling people is how a side hustle finds its first customers."},
                    ],
                    "correct_index": 1,
                }},
            ]},
            {"title": "Level 3", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Reputation is everything",
                    "body": "When you run anything, your reputation is what people say about you when you're not in the room. Doing a great job, being on time, and being honest make customers come back and recommend you. One brilliant experience can bring you three new customers; one broken promise can lose you ten. Treat every customer like you want them to tell their friends — because they will, either way.",
                }},
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Reinvest your time and earnings wisely",
                    "body": "A growing side hustle gives you two things back: a little money and a little experience. Smart founders reinvest some of it — maybe better supplies, a skill to learn, or simply more practice — instead of spending it all. And your time is precious too: don't take on so many customers that the quality slips or your schoolwork suffers. Growing steadily beats growing too fast and burning out.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "A customer's order goes wrong and it's your mistake. What builds the best reputation?",
                    "choices": ["Pretend it didn't happen and hope they forget", "Own up honestly, apologise, and put it right", "Blame the customer", "Block them so they can't complain"],
                    "answer_index": 1,
                    "explanation": "Honesty and fixing your mistakes turn an unhappy moment into trust. People remember how you handled a problem far more than the problem itself.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Your side hustle is making a bit of money. What's a wise thing to do with some of it?",
                    "choices": ["Spend every penny immediately", "Reinvest some into better supplies or learning a useful skill", "Hide it and never use it for anything", "Promise it to someone before you've earned it"],
                    "answer_index": 1,
                    "explanation": "Putting some earnings back into your hustle (or your skills) helps it grow steadily. Reinvesting is how small things become bigger over time.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "You're getting more orders than you can handle alongside school. What's the healthiest move?",
                    "choices": ["Stay up all night and let your schoolwork slide", "Accept everything and let the quality drop", "Manage your time — take what you can do well, and pause, raise prices, or get a grown-up's help to grow", "Quit completely with no warning to customers"],
                    "answer_index": 2,
                    "explanation": "Protecting your time and the quality of your work keeps both your customers and your studies happy. Growing well means knowing your limits.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "A stranger online wants to buy from you and asks you to meet alone or share your home address. What should you do?",
                    "choices": ["Go and meet them by yourself to make the sale", "Share all your details so they trust you", "Stop, and talk to a trusted grown-up before doing anything", "Keep it secret from your parents"],
                    "answer_index": 2,
                    "explanation": "Your safety always comes before any sale. Never meet strangers alone or share personal details — bring a trusted grown-up into any deal with someone you don't know.",
                }},
                {"type": "scenario", "xp_reward": 20, "content_json": {
                    "prompt": "A customer messages to say the bracelet you sold them broke after one day. They're upset. Your side hustle has a good reputation so far. What do you do?",
                    "choices": [
                        {"label": "Ignore the message and hope they go away", "outcome": "A customer you ignore tells everyone how you let them down. Silence is the fastest way to wreck the good reputation you built."},
                        {"label": "Reply honestly, apologise, and offer to repair or replace it", "outcome": "Excellent. Owning the problem and putting it right keeps the customer's trust and protects your reputation. Honest businesses earn loyal customers and word-of-mouth recommendations."},
                        {"label": "Argue that it must be their fault and refuse to help", "outcome": "Even if you're unsure whose fault it is, being defensive loses the customer and the people they'll talk to. Care and honesty win in the long run."},
                    ],
                    "correct_index": 1,
                }},
            ]},
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
        "extra_levels": [
            {"title": "Level 2", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Profit margin: how much of each £ you keep",
                    "body": "Profit margin tells you how much of every pound you actually keep. If you sell something for £5 and it costs you £3 to make, your profit is £2. Your margin is £2 out of £5 — that's 40%. A bigger margin means more of each sale stays with you. Two stalls can both make sales, but the one with the better margin keeps more.",
                }},
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Break-even: the moment you stop losing money",
                    "body": "Before you make a profit, you first have to cover your costs. The break-even point is the number of items you need to sell just to get your money back — not a penny more, not a penny less. Say a stall costs you £20 to run, and you make £4 profit on each item. You break even after selling 5 items (5 × £4 = £20). Sale number 6 is where real profit begins.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "You sell a bracelet for £10. It costs you £6 to make. What is your profit margin?",
                    "choices": ["4%", "40%", "60%", "100%"],
                    "answer_index": 1,
                    "explanation": "Profit is £10 − £6 = £4. Your margin is £4 out of the £10 price = 40%. You keep 40p of every pound.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "It costs you £2 to make one candle, and you want £3 of profit on each one. What price should you charge?",
                    "choices": ["£3", "£2", "£5", "£1"],
                    "answer_index": 2,
                    "explanation": "Price = cost + the profit you want = £2 + £3 = £5. Pricing below £5 wouldn't leave the £3 profit you wanted.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Your stall costs £30 to run (a fixed cost). You make £2 profit on each badge after materials. How many badges must you sell to break even?",
                    "choices": ["10", "15", "30", "60"],
                    "answer_index": 1,
                    "explanation": "Break-even = fixed cost ÷ profit per item = £30 ÷ £2 = 15 badges. After 15, every extra badge is real profit.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Which stall keeps MORE of each pound it takes in?",
                    "choices": ["Stall A: sells for £4, costs £3 to make", "Stall B: sells for £4, costs £1 to make", "They keep the same amount", "You can't compare margins"],
                    "answer_index": 1,
                    "explanation": "Stall A keeps £1 of £4 (25%). Stall B keeps £3 of £4 (75%). Stall B has the bigger margin, so it keeps far more of every pound.",
                }},
                {"type": "scenario", "xp_reward": 20, "content_json": {
                    "prompt": "You're planning a lemonade stall. Each cup costs you 50p to make, and the stall (your fixed cost) is £10 for the day. You decide to sell each cup for £1.50. How should you think about it?",
                    "choices": [
                        {"label": "I make £1 profit per cup, so I break even after 10 cups — then it's all profit", "outcome": "Spot on. Profit per cup = £1.50 − 50p = £1. £10 fixed ÷ £1 = 10 cups to break even. Cup 11 onwards is real profit."},
                        {"label": "Every cup I sell is £1.50 of pure profit", "outcome": "Not quite. £1.50 is the price, not the profit. Each cup costs 50p to make, and you still have the £10 stall to cover first."},
                        {"label": "I should price each cup at 50p so it sells fast", "outcome": "At 50p you'd only just cover the cup's own cost and make £0 profit, never covering the £10 stall. A fair price needs to be above your cost."},
                    ],
                    "correct_index": 0,
                }},
            ]},
            {"title": "Level 3", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Profit isn't the same as cash in your pocket",
                    "body": "You can be profitable on paper but still short of cash right now. Imagine you sell £100 of cookies to a café, but they'll pay you next month. Meanwhile you spent £40 on ingredients today. Your profit will be £60 — but right now you're actually £40 out of pocket until the café pays. That gap between money earned and money actually in hand is called cash flow. Healthy businesses watch both.",
                }},
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Reinvesting: using profit to grow",
                    "body": "Reinvesting means putting some of your profit back into your business instead of spending it all. Made £50 profit selling bracelets? You could buy a bigger batch of beads so you can make more next time. Reinvesting can help you grow — but it's wise to keep some cash aside too, so a quiet week doesn't catch you out. It's a balance, not all-or-nothing.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "You sold £100 of goods, but the customer pays you next month. You spent £40 on supplies today. How much CASH do you actually have in hand right now?",
                    "choices": ["£100", "£60", "−£40 (you're £40 out of pocket)", "£140"],
                    "answer_index": 2,
                    "explanation": "The £100 hasn't arrived yet, but the £40 has already gone out. So right now you're £40 down on cash — even though your eventual profit will be £60. That's the difference between profit and cash flow.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "You made £50 profit. What does it mean to 'reinvest' some of it?",
                    "choices": ["Spend it all on sweets as a treat", "Put some back into the business — like buying more materials to sell more", "Hide it and never use it", "Give all of it away"],
                    "answer_index": 1,
                    "explanation": "Reinvesting means putting profit back in to help the business grow, such as buying more materials. Keeping some cash aside too is sensible.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "One craft stall makes you about £30 profit a day. You set up 3 similar stalls run by friends. Roughly how much profit a day might you expect (before any extra costs)?",
                    "choices": ["About £30", "About £90", "About £10", "About £300"],
                    "answer_index": 1,
                    "explanation": "Three stalls each making about £30 is roughly 3 × £30 = £90 a day. That's the simple idea of scaling — doing more of what works. (In real life extra stalls bring extra costs too, so it's a rough guide.)",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Your end-of-day stall summary says: Revenue £120, Total costs £80. Did the stall make money, and how much profit?",
                    "choices": ["Lost money, −£40", "Made money, £40 profit", "Broke even, £0", "Made money, £120 profit"],
                    "answer_index": 1,
                    "explanation": "Profit = revenue − costs = £120 − £80 = £40. Revenue is bigger than costs, so the stall made a £40 profit.",
                }},
                {"type": "scenario", "xp_reward": 20, "content_json": {
                    "prompt": "Your weekend stall summary reads: Revenue £200, Costs £140, Profit £60. But £50 of that £200 is still owed by customers who'll pay later — so you only have £10 actual cash in hand right now. A friend says 'spend the whole £60 profit on more stock for next week!' What's the wisest move?",
                    "choices": [
                        {"label": "Spend the full £60 on stock straight away", "outcome": "Careful: you only have £10 cash right now. £50 is still owed and hasn't arrived. Spending £60 you don't yet hold could leave you stuck if a customer pays late."},
                        {"label": "Reinvest a sensible amount from the cash you actually have, and wait for the £50 owed to arrive before spending it", "outcome": "Wise. You separate profit (£60, on paper) from cash in hand (£10). Reinvest within what you really have, and grow as the money owed comes in."},
                        {"label": "Decide the stall failed because you only have £10 in hand", "outcome": "Not so. The stall made a real £60 profit; the £50 simply hasn't been paid yet. Once it arrives, your cash catches up with your profit."},
                    ],
                    "correct_index": 1,
                }},
            ]},
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
        "extra_levels": [
            {"title": "Level 2", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Where your deductions actually go",
                    "body": "On Level 1 you met the names on a payslip. Here's where the money goes: Income Tax and National Insurance are sent to HMRC (the government's tax office) to pay for shared things like the NHS and the state pension. A pension deduction isn't a tax at all — it's YOUR own money being saved for your future. So your deductions split two ways: money that leaves for good (tax, NI) and money that's still yours, just locked away for later (pension).",
                }},
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Your tax code and 'YTD': the small print",
                    "body": "A payslip has a few extra clues. Your tax code (like 1257L) tells your employer how much you can earn before Income Tax starts — get the wrong code and you might pay too much or too little. YTD means 'year to date': the running total of what you've earned and paid since the tax year began (6 April). And by law you should get a payslip every payday — keep them, they're proof of what you earned.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "On your payslip, which deduction is actually YOUR own savings rather than money sent to the government?",
                    "choices": ["Income Tax", "National Insurance", "Your pension contribution", "The 'net pay' line"],
                    "answer_index": 2,
                    "explanation": "Income Tax and National Insurance go to HMRC. Your pension contribution is your own money being saved for your future — it's still yours, just put away for later.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "A payslip shows 'YTD' next to some numbers. What does YTD mean?",
                    "choices": ["'Year to date' — the running total since the tax year started", "'Yesterday's total deductions'", "'Your tax discount'", "'Yearly take-home difference'"],
                    "answer_index": 0,
                    "explanation": "YTD means 'year to date' — it adds up everything you've earned and paid in deductions since the tax year began on 6 April.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Many workplaces automatically sign you up to a pension when you start a job. What is this called?",
                    "choices": ["Auto-enrolment", "A tax refund", "Overtime", "A bonus scheme"],
                    "answer_index": 0,
                    "explanation": "Auto-enrolment means you're automatically put into a workplace pension when you start. You can opt out, but you'd give up your employer's contribution — so most people stay in.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Mia earns £9 an hour and works 10 hours. Her gross pay is £90. Deductions come to £18. What is her net (take-home) pay?",
                    "choices": ["£90", "£108", "£72", "£18"],
                    "answer_index": 2,
                    "explanation": "Net pay = gross pay − deductions. £90 − £18 = £72. The £18 covers things like NI and pension; the £72 is what lands in her bank.",
                }},
                {"type": "scenario", "xp_reward": 20, "content_json": {
                    "prompt": "It's your first part-time job and your first payslip looks confusing — there's a tax code, some YTD numbers, and deductions you didn't expect. What's the sensible thing to do?",
                    "choices": [
                        {"label": "Bin it — payslips don't matter once you've been paid", "outcome": "Not wise. Your payslip is proof of what you earned and what was deducted. Keep every one safe; you may need them later."},
                        {"label": "Look it over, and ask a trusted grown-up to help you check the tax code and deductions make sense", "outcome": "Great move. Reading your payslip and checking it with someone you trust helps you spot a wrong tax code or an error early — and you learn what every line means."},
                        {"label": "Assume it's wrong and refuse to work again", "outcome": "Deductions are normal and required by law. If something genuinely looks off, the calm step is to ask a grown-up or your employer, not to give up."},
                    ],
                    "correct_index": 1,
                }},
            ]},
            {"title": "Level 3", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Pay yourself first",
                    "body": "Most people spend, then save whatever's left — and usually nothing's left. Flip it: the moment your net pay lands, move a small slice into savings BEFORE you spend anything. That's 'paying yourself first'. Even £1 in every £10 (10%) adds up, and because it happens first, you never miss it. Some people even set up an automatic transfer on payday so the choice is made for them.",
                }},
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Build a buffer, then beware 'lifestyle creep'",
                    "body": "A small emergency buffer — a bit of savings for surprises like a broken phone — means one unlucky week doesn't wreck your month. Once that's growing, watch out for 'lifestyle creep': when your pay rises and your spending quietly rises to match, so you're earning more but saving nothing. The trick when your pay goes up is to lift your saving at least as much as your spending.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "What does 'pay yourself first' mean?",
                    "choices": ["Spend on yourself before paying any bills", "Move some money into savings as soon as you're paid, before spending", "Ask your employer to pay you before your colleagues", "Only save the coins left at the end of the month"],
                    "answer_index": 1,
                    "explanation": "'Pay yourself first' means saving a slice the moment you're paid — before spending — so saving actually happens instead of relying on leftovers.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "You get a pay rise, and straight away you upgrade your phone plan, buy more takeaways, and end up saving nothing extra. What is this called?",
                    "choices": ["Lifestyle creep", "Compound interest", "Auto-enrolment", "Gross pay"],
                    "answer_index": 0,
                    "explanation": "Lifestyle creep is when spending rises to match a higher income, so you earn more but don't save more. Lifting your saving when your pay rises keeps it in check.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Why is having a small 'emergency buffer' of savings a smart habit?",
                    "choices": ["So a surprise cost doesn't force you to borrow or panic", "Because the government doubles your buffer", "So you never have to pay any tax", "Because it makes your gross pay bigger"],
                    "answer_index": 0,
                    "explanation": "An emergency buffer means an unexpected cost — like a broken phone — is just an annoyance, not a crisis, and you avoid borrowing at high interest.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Your net pay is £200 this month and you decide to 'pay yourself first' at 10%. How much goes straight into savings?",
                    "choices": ["£2", "£10", "£20", "£200"],
                    "answer_index": 2,
                    "explanation": "10% of £200 is £20. Moving that £20 into savings first — before spending — is paying yourself first. The other £180 is yours to budget.",
                }},
                {"type": "scenario", "xp_reward": 20, "content_json": {
                    "prompt": "Your first month's wages have landed. You want to be sensible but also enjoy your money. What's the smartest plan?",
                    "choices": [
                        {"label": "Spend it all now — there'll be more next month", "outcome": "Risky. Spending everything leaves nothing for surprises, and the habit sticks. A surprise cost would then mean borrowing."},
                        {"label": "Move a small slice to savings first, keep a little buffer for emergencies, then enjoy the rest — and ask a grown-up to help you set it up", "outcome": "Brilliant balance. Pay yourself first, build a buffer, then spend the rest guilt-free. Setting up an automatic transfer with a trusted grown-up makes it effortless."},
                        {"label": "Put every single penny into savings and never spend any of it", "outcome": "Saving matters, but you're allowed to enjoy money you earned. The healthy habit is balance — save some, buffer some, enjoy some — not all-or-nothing."},
                    ],
                    "correct_index": 1,
                }},
            ]},
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


async def _ensure_level_lessons(session, module, level, lesson_specs):
    ordered = list((await session.scalars(
        select(Lesson).where(Lesson.level_id == level.id).order_by(Lesson.order_index)
    )).all())
    by_ident = {_lesson_identity(le.type, le.content_json): le for le in ordered}
    for lesson_spec in lesson_specs:
        ident = _lesson_identity(lesson_spec["type"], lesson_spec["content_json"])
        if ident in by_ident:
            continue
        new_lesson = Lesson(
            module_id=module.id, level_id=level.id,
            type=lesson_spec["type"], content_json=lesson_spec["content_json"],
            xp_reward=lesson_spec["xp_reward"], order_index=0,
        )
        session.add(new_lesson)
        by_ident[ident] = new_lesson
        pos = _insert_position([le.type for le in ordered], new_lesson.type)
        ordered.insert(pos, new_lesson)
    for i, le in enumerate(ordered):
        le.order_index = i


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
                is_premium=premium_for_position(0), pass_threshold=0.7, content_source="authored",
            )
            session.add(level)
            await session.flush()

        # Only insert lessons missing from the curriculum, slotting each into
        # its difficulty band by type. Lessons already placed keep their
        # relative order (so manual admin reordering survives re-seeding).
        await _ensure_level_lessons(session, module, level, spec["lessons"])

        for i, extra in enumerate(spec.get("extra_levels", []), start=1):
            lv = await session.scalar(
                select(Level).where(Level.module_id == module.id, Level.order_index == i)
            )
            if lv is None:
                lv = Level(
                    module_id=module.id, title=extra["title"], order_index=i,
                    is_premium=premium_for_position(i), pass_threshold=0.7,
                    content_source="authored",
                )
                session.add(lv)
                await session.flush()
            else:
                lv.title = extra["title"]
                lv.is_premium = premium_for_position(i)
            await _ensure_level_lessons(session, module, lv, extra["lessons"])
