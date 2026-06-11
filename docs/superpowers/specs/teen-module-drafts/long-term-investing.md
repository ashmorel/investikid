# Investing for the Long Term — teen module draft

**Level 1 (free) — Funds.** Why most long-term investors hold funds instead of picking stocks: what a fund is, index vs active, and how fees compound. The anchor example: £1,000 growing at 7% a year for 30 years ends at about £7,200 with a 0.2% fee but only about £4,980 with a 1.5% fee.

**Level 2 (free) — Wrappers & accounts.** The account around an investment matters as much as the investment: ISAs (tax-free growth, the Junior ISA they already know becomes an adult ISA at 18), workplace pensions and employer matching as free money, the US parallels (401(k)/Roth IRA), and the locked-away trade-off. Worked example: £100 a month at 6% from 18 vs 28 — roughly £227,000 vs £116,000 by age 60.

**Level 3 (premium) — Staying the course.** Asset allocation by time horizon (a 60/40 mix falls ~18% when shares fall 30% and bonds hold flat), drawdowns of 30–50% as a normal, historically recoverable feature, the asymmetry of losses (a 40% fall needs a ~67% gain back), pound-cost averaging with real prices, and rebalancing as selling high and buying low by rule.

```python
module = {
    "topic": "stocks", "title": "Investing for the Long Term",
    "standards_alignment": [
        {"framework": "UK MaPS/YE Financial Education Planning Framework", "code": "11-19", "label": "Understanding the important role money plays in our lives"},
        {"framework": "US National Standards for Personal Financial Education (CEE/Jump$tart 2021)", "code": "IV", "label": "Investing"},
    ],
    "sources": [
        {"title": "FCA InvestSmart", "url": "https://www.fca.org.uk/investsmart"},
        {"title": "GOV.UK — Individual Savings Accounts (ISAs)", "url": "https://www.gov.uk/individual-savings-accounts"},
        {"title": "Investor.gov (US SEC) — Mutual funds and ETFs", "url": "https://www.investor.gov/introduction-investing/investing-basics/investment-products/mutual-funds-and-exchange-traded-funds-etfs"},
    ],
    "learning_objectives": [
        "Explain what a fund is and why most long-term investors hold funds rather than individual stocks",
        "Compare index funds and active funds on cost and typical results",
        "Show with a worked example how a small annual fee compounds into a large difference over decades",
    ],
    "conversation_prompt": "Ask them why a 1.5% fee costs so much more than it sounds over 30 years, and what an employer pension match is actually worth. Work one example out together — the numbers make the argument.",
    "country_codes": [], "is_premium": False, "order_index": 13, "icon": "🌱", "min_age": 14,
    "lessons": [
        {"type": "card", "xp_reward": 10, "content_json": {
            "title": "What a fund actually is",
            "body": "A fund pools money from thousands of investors and buys a wide basket of investments — often hundreds of companies in one go. You buy units of the fund, and a manager (or a computer following rules) handles the rest. One purchase can spread your money across an entire market. That is why most long-term investors hold funds rather than trying to pick a handful of winning stocks themselves.",
        }},
        {"type": "card", "xp_reward": 10, "content_json": {
            "title": "Fees compound too",
            "body": "An index fund simply copies an index like the FTSE 100 and might charge 0.2% a year. An active fund pays managers to try to beat the market and often charges 1.5% or more. That gap compounds. £1,000 growing at 7% a year becomes about £7,200 after 30 years on a 0.2% fee, but only about £4,980 on 1.5%. Same money, same market — the fee quietly ate the rest. Most active funds fail to beat the index after fees.",
        }},
        {"type": "quiz", "xp_reward": 25, "content_json": {
            "question": "What does an index fund do?",
            "choices": [
                "Pays managers to hunt for the next big winner",
                "Guarantees your money can never fall in value",
                "Buys every company in an index, like the FTSE 100, so you own a slice of the whole market",
                "Lends your money to the government",
            ],
            "answer_index": 2,
            "explanation": "An index fund copies an index rather than trying to beat it. One purchase gives you a small slice of every company on that scoreboard — instant, cheap diversification.",
        }},
        {"type": "quiz", "xp_reward": 25, "content_json": {
            "question": "You hold £10,000 in a fund. Roughly what does a 1.5% annual fee cost you this year, compared with a 0.2% fee?",
            "choices": [
                "£150 vs £20 — a £130 gap, taken every single year",
                "£15 vs £2 — too small to matter",
                "£1,500 vs £200",
                "Nothing, because fees only apply when you sell",
            ],
            "answer_index": 0,
            "explanation": "1.5% of £10,000 is £150; 0.2% is £20. The fee comes out every year whether the fund does well or badly — and the money it removes can never compound for you.",
        }},
        {"type": "quiz", "xp_reward": 25, "content_json": {
            "question": "Over long periods, how do most active funds compare with a cheap index fund tracking the same market?",
            "choices": [
                "Active funds nearly always win — that's what the managers are paid for",
                "Active funds win in good years and index funds win in bad years",
                "It's exactly 50/50 over any period",
                "Most active funds end up behind the index once their higher fees are taken out",
            ],
            "answer_index": 3,
            "explanation": "Studies repeatedly find that after fees, the majority of active funds underperform their index over long periods. A few beat it — but picking which ones in advance is the hard part.",
        }},
        {"type": "quiz", "xp_reward": 25, "content_json": {
            "question": "Why does holding a fund with hundreds of companies usually carry less risk than holding three stocks you picked?",
            "choices": [
                "Funds are protected from ever losing money",
                "If one company in the fund fails, it's a tiny slice of the basket — with three stocks, it's a third of everything",
                "Fund managers can see the future",
                "Three stocks are illegal to hold in the UK",
            ],
            "answer_index": 1,
            "explanation": "This builds on diversification: a fund spreads each pound across so many companies that no single failure can sink you. With three stocks, one disaster takes out a third of your money.",
        }},
        {"type": "scenario", "xp_reward": 20, "content_json": {
            "prompt": "You're choosing a first long-term investment in the practice Simulator: a single stock everyone at school is talking about, a global index fund charging 0.2%, or an active fund charging 1.6% whose advert says 'expert managers working for you'. Which fits a decades-long plan best?",
            "choices": [
                {"label": "The single stock — it's clearly popular", "outcome": "Popularity isn't a plan. One company is one set of risks, and hot stocks are often already expensive. For money you'll hold for decades, concentration is the enemy."},
                {"label": "The global index fund at 0.2%", "outcome": "Strong reasoning. You own thousands of companies worldwide, and the low fee means almost all the growth stays compounding in your pot. This is what many long-term investors actually hold."},
                {"label": "The 1.6% active fund — experts must be worth it", "outcome": "The advert is selling the fee. Most active funds trail the index after costs, and over 30 years that 1.4% gap can eat thousands of pounds of growth. Experts have to beat the market by more than they charge — most don't."},
            ],
            "correct_index": 1,
        }},
    ],
    "extra_levels": [
        {"title": "Level 2", "learning_objectives": [
             "Explain how an ISA wrapper makes investment growth tax-free and what happens to a Junior ISA at 18",
             "Calculate what an employer pension match is worth and explain the locked-away trade-off",
             "Show how starting ten years earlier changes a final pot far more than the extra contributions alone",
         ], "lessons": [
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "The wrapper matters as much as the investment",
                "body": "An ISA isn't an investment — it's a wrapper around one. Inside a stocks and shares ISA, the same index fund grows free of UK tax, and withdrawals are tax-free too. Adults can add up to £20,000 a year. You may already know the Junior ISA: at 18 it becomes yours and turns into an adult ISA. Outside a wrapper, tax can skim your gains every year — and anything skimmed can never compound for you.",
            }},
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "Pensions: the match is free money",
                "body": "A workplace pension takes money from your pay before you see it — and your employer adds more. On a £24,000 salary, putting in 5% (£1,200 a year) might be matched with 3% from your employer: £720 of free money, a 60% boost before any market growth. The trade-off: pensions are locked until your late fifties. The US versions: a 401(k) is the workplace pension with a match; a Roth IRA works much like an ISA.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "What is the main advantage of holding an index fund inside a stocks and shares ISA rather than in a plain account?",
                "choices": [
                    "The fund inside an ISA is guaranteed to grow faster",
                    "Growth and withdrawals are free of UK tax, so everything the fund earns stays compounding",
                    "ISAs remove all investment risk",
                    "ISAs pay a bonus interest rate on top of the fund",
                ],
                "answer_index": 1,
                "explanation": "The investment is identical — the wrapper changes the tax. No tax on growth or withdrawals means more stays in the pot, and that extra keeps compounding year after year.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "On a £24,000 salary you put 5% (£1,200 a year) into a workplace pension and your employer matches with 3%. How much goes in per year in total?",
                "choices": ["£1,200 — the match is taken from your pay too", "£720", "£1,440", "£1,920 — your £1,200 plus £720 of employer money"],
                "answer_index": 3,
                "explanation": "3% of £24,000 is £720, added on top of your £1,200 — £1,920 in total. That £720 is money you simply don't get if you opt out, which is why the match is called free money.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Two people each invest £100 a month at 6% a year until age 60. One starts at 18, the other at 28. Roughly how do their pots compare?",
                "choices": [
                    "About £227,000 vs £116,000 — ten extra years nearly doubles the pot",
                    "About the same, because the rate is equal",
                    "£50,400 vs £38,400 — pots simply equal what you paid in",
                    "The 28-year-old ends ahead because they're earning more by then",
                ],
                "answer_index": 0,
                "explanation": "The 18-year-old pays in £50,400 and ends with about £227,000; the 28-year-old pays in £38,400 and ends with about £116,000. Only £12,000 more went in, but the pot is about £111,000 bigger — the early money compounded for an extra decade.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Which US account works most like a UK ISA — pay in from taxed money, then growth and withdrawals are tax-free?",
                "choices": ["A 401(k)", "A current account", "A Roth IRA", "A FTSE 100 tracker"],
                "answer_index": 2,
                "explanation": "A Roth IRA is the closest US cousin of the ISA: taxed money in, tax-free growth and withdrawals out. A 401(k) is closer to a UK workplace pension — pre-tax money, often matched, locked until later life.",
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "You're 18, starting a first job at £20,000. The employer offers a pension matching your contributions up to 4%. You also want savings you can actually reach. What's the soundest setup?",
                "choices": [
                    {"label": "Join the pension up to the full match, and build accessible savings (such as an ISA) alongside it", "outcome": "Sound framework. Contributing 4% (£800) gets another £800 of employer money — a 100% instant return you can't get anywhere else — while the ISA keeps some money reachable. Many people use exactly this split."},
                    {"label": "Opt out of the pension — retirement is 40+ years away and the money is locked", "outcome": "Opting out turns down £800 a year of free money, and those early pounds are the ones with four decades to compound. The lock-up is real, but it's the reason to balance a pension with accessible savings — not to refuse the match."},
                    {"label": "Put every spare pound into the pension to maximise the tax break", "outcome": "The maths of pensions is strong, but money for emergencies, study or a first home can't wait until your late fifties. Locking up everything forces expensive borrowing later. Capture the match, keep some accessible."},
                ],
                "correct_index": 0,
            }},
        ]},
        {"title": "Level 3", "learning_objectives": [
             "Choose a shares/bonds mix that fits a time horizon and explain what rebalancing does",
             "Explain why large market falls are historically normal and why selling in a crash locks in the loss",
             "Show how pound-cost averaging lowers the average price paid when markets are volatile",
         ], "lessons": [
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "Match the mix to the horizon",
                "body": "Shares grow more over decades but swing hard; bonds grow less and swing less. The mix is the dial. In a year where shares fall 30% and bonds hold flat, an all-shares portfolio is down 30% — a 60/40 shares-bonds mix is down about 18%. With 40 years ahead, many long-term investors hold mostly shares and ride the swings; with five years left, they shift towards bonds because there's no time to recover from a crash.",
            }},
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "Falls are normal — selling makes them permanent",
                "body": "Markets have fallen 30–50% several times — 2000, 2008, 2020 — and historically recovered and gone on to new highs, though it sometimes took years. The maths of losses is asymmetric: £10,000 falling 40% leaves £6,000, which then needs a 67% gain just to get back. Selling during the crash converts a paper loss into a real one and means missing the recovery. The plan, not the panic, decides when to sell.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Your £10,000 portfolio falls 40% to £6,000. What gain does it now need to get back to £10,000?",
                "choices": ["40% — the same as the fall", "50%", "60%", "About 67%"],
                "answer_index": 3,
                "explanation": "£6,000 needs to grow by £4,000, and £4,000 ÷ £6,000 ≈ 67%. Losses need bigger gains to undo than most people expect — one reason avoiding panic-selling at the bottom matters so much.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "You invest £50 a month for five months while a fund's price goes £10, £8, £5, £8, £10. What did pound-cost averaging do for you?",
                "choices": [
                    "Nothing — you paid the average price of £8.20",
                    "Your £250 bought 32.5 units at an average of £7.69 each — below the £8.20 average price — and is worth £325 at the end",
                    "You lost money because the price fell mid-way",
                    "You bought fewer units when the price was low",
                ],
                "answer_index": 1,
                "explanation": "A fixed £50 buys more units when the price is low (10 units at £5) and fewer when high (5 at £10). Total: 32.5 units for £250 — £7.69 average versus the £8.20 average price. At £10 a unit, that's £325.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "A year of strong share growth drifts your portfolio from its 60/40 shares-bonds target to 75/25. What does rebalancing mean here?",
                "choices": [
                    "Selling everything and waiting in cash for a better moment",
                    "Buying more shares, since they're clearly the winners",
                    "Selling some shares and buying bonds to return to 60/40 — trimming what's expensive, topping up what's cheap, by rule not by feeling",
                    "Switching to a fund with a higher fee",
                ],
                "answer_index": 2,
                "explanation": "Rebalancing restores the risk level you chose. As a side effect it systematically sells what has risen and buys what has lagged — a disciplined version of selling high and buying low, with no forecasting required.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "£1,000 left invested at 7% a year for 40 years grows to roughly how much?",
                "choices": ["About £15,000 — nearly fifteen times the original", "About £3,800", "About £7,000", "About £28,000"],
                "answer_index": 0,
                "explanation": "1.07 to the power 40 is about 15, so £1,000 becomes roughly £14,970. The last decade adds more than the first three combined — which is why time in the market is the asset that's hardest to replace.",
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "Two years into a 30-year plan — a global index fund inside an ISA, £100 added monthly — markets fall 35% in six months. The news is grim and your pot shows a large red number. What do you do?",
                "choices": [
                    {"label": "Sell everything before it falls further", "outcome": "This converts the paper loss into a permanent one and parks you in cash for the recovery — and recoveries often start before the news improves. Investors who sold in 2008 or 2020 and waited to feel safe missed the sharpest rebound days."},
                    {"label": "Keep what you hold, but pause contributions until things look safer", "outcome": "Better than selling, but notice what you'd be doing: refusing to buy units at the cheapest prices in years. 'Looking safe' usually returns only after prices already have — you'd resume buying high."},
                    {"label": "Keep contributing on schedule, and rebalance if the mix has drifted from target", "outcome": "This is the plan working under pressure. With 28 years left there is historically ample recovery time, your £100 now buys roughly half as many units more each month, and rebalancing quietly buys low. Falls like this are why the plan was written calm."},
                ],
                "correct_index": 2,
            }},
        ]},
    ],
}
```
