# Student Money: University & Beyond — teen module draft

A teen (14-18) module on the money side of life after school. Level 1 demystifies UK student finance — tuition vs maintenance loans, why repayments behave more like a graduate tax than a normal debt, and first-rental basics (deposits, guarantors, bills). Level 2 covers actually living on a student budget: termly loan drops vs weekly spending, the week-1 splurge trap, part-time work balance, real savings vs false economies, and why an overdraft isn't income. Level 3 (premium) tackles risks and big decisions: 0% credit that doesn't stay 0%, housing and job scams (including money muling), budgeting irregular income, and a framework for weighing uni against apprenticeships and gap years.

```python
module = {
    "topic": "budgeting", "title": "Student Money: University & Beyond",
    "standards_alignment": [
        {"framework": "UK MaPS/YE Financial Education Planning Framework", "code": "11-19", "label": "How to manage money"},
        {"framework": "US National Standards for Personal Financial Education (CEE/Jump$tart 2021)", "code": "II", "label": "Spending"},
        {"framework": "US National Standards for Personal Financial Education (CEE/Jump$tart 2021)", "code": "V", "label": "Managing Credit"},
    ],
    "sources": [
        {"title": "GOV.UK — Student finance", "url": "https://www.gov.uk/student-finance"},
        {"title": "MoneyHelper — Student and graduate money", "url": "https://www.moneyhelper.org.uk/en/family-and-care/student-and-graduate-money"},
    ],
    "learning_objectives": [
        "Explain how tuition and maintenance loans work, and why repayments behave more like a graduate tax than a normal debt",
        "Work out what a graduate actually repays at a given salary",
        "Explain what deposits, guarantors and bills mean when renting a first student home",
    ],
    "conversation_prompt": "Try this together: a graduate earns £29,000 and repays 9% of everything above £25,000. Work out the yearly and monthly repayment — then talk about why student loans behave more like a graduate tax than a debt that must be cleared.",
    "country_codes": [], "is_premium": False, "order_index": 12, "icon": "🎓",
    "min_age": 14,
    "lessons": [
        {"type": "card", "xp_reward": 10, "content_json": {
            "title": "Two loans, two different jobs",
            "body": "UK student finance is really two loans. The tuition fee loan covers your course fees and is paid straight to the university — you never see that money. The maintenance loan is for living costs (rent, food, transport) and is paid into your bank account in instalments, usually one per term. How much maintenance loan you get depends mainly on your household income and where you live and study. In the US, federal student aid works similarly via FAFSA.",
        }},
        {"type": "card", "xp_reward": 10, "content_json": {
            "title": "More like a graduate tax than a debt",
            "body": "Student loan repayments don't work like a credit card. You repay 9% of what you earn above a threshold (around £25,000 a year on the newest English plan) — earn less, and you pay nothing that month. Repayments come out of your pay automatically, and whatever is left is written off after a set term (40 years on the newest plan). That's why many people say it behaves more like a graduate tax: it scales with income, then ends.",
        }},
        {"type": "quiz", "xp_reward": 25, "content_json": {
            "question": "Where does the maintenance loan actually go?",
            "choices": [
                "Straight to the university, like the tuition fee loan",
                "To your parents, who pass it on",
                "Into your own bank account, in instalments — usually one per term",
                "It's held back until you graduate",
            ],
            "answer_index": 2,
            "explanation": "The tuition fee loan goes directly to the university; the maintenance loan lands in YOUR account, typically at the start of each term. Making one instalment last a whole term is the core student budgeting challenge.",
        }},
        {"type": "quiz", "xp_reward": 25, "content_json": {
            "question": "A graduate earns £29,000 a year and repays 9% of everything above a £25,000 threshold. What do they repay per year?",
            "choices": [
                "£2,610 — 9% of the whole salary",
                "£360 — 9% of the £4,000 above the threshold",
                "£900 — a flat rate",
                "Nothing until the loan is 10 years old",
            ],
            "answer_index": 1,
            "explanation": "You only repay on income ABOVE the threshold: £29,000 − £25,000 = £4,000, and 9% of £4,000 is £360 a year — £30 a month. Notice how little the size of the loan itself matters to the monthly cost.",
        }},
        {"type": "quiz", "xp_reward": 25, "content_json": {
            "question": "A graduate loses their job and their income drops below the repayment threshold. What happens to their student loan repayments?",
            "choices": [
                "They stop automatically until income rises above the threshold again",
                "They keep going — debt collectors get involved if you miss one",
                "The whole loan becomes due immediately",
                "They must sell assets to keep paying",
            ],
            "answer_index": 0,
            "explanation": "Repayments are taken through the pay system and only on income above the threshold, so they pause automatically when earnings fall. This built-in safety valve is a key way student loans differ from ordinary debt.",
        }},
        {"type": "quiz", "xp_reward": 25, "content_json": {
            "question": "Your first student house asks for a guarantor. What is that?",
            "choices": [
                "A friend who witnesses you signing the contract",
                "An insurance policy that covers broken furniture",
                "A council officer who inspects the property",
                "Someone (often a parent) who legally agrees to pay the rent if you can't",
            ],
            "answer_index": 3,
            "explanation": "Landlords often ask students for a guarantor because students rarely have an income or renting history. The guarantor signs a legal promise to cover rent you don't pay — a serious commitment for them, so discuss it properly.",
        }},
        {"type": "scenario", "xp_reward": 20, "content_json": {
            "prompt": "You're about to sign for your first student house: £120 a week, a five-week deposit, and 'bills not included'. What do you do before signing?",
            "choices": [
                {"label": "Sign now — good houses go fast and the landlord is pressuring you", "outcome": "Pressure to sign instantly is itself a warning sign. Once you sign, you're legally committed for the year — including the rent of housemates who drop out, if it's a joint tenancy."},
                {"label": "Ask the landlord to skip the deposit in exchange for three months' rent up front", "outcome": "That's worse: you'd hand over more cash with less protection. A deposit in a government-approved protection scheme is safer than a large upfront payment with nothing safeguarding it."},
                {"label": "Read the contract, confirm the deposit will go into a government-backed protection scheme, add up rent plus estimated bills, and have someone you trust look it over", "outcome": "Exactly right. In England deposits must be protected in an approved scheme, 'bills not included' can add £15-25 a week each, and a second pair of eyes on your first ever contract catches what you'll miss."},
            ],
            "correct_index": 2,
        }},
    ],
    "extra_levels": [
        {"title": "Level 2", "learning_objectives": [
            "Stretch a termly loan instalment across all the weeks it has to cover",
            "Balance part-time work with study, and tell real savings from false economies",
            "Explain why a 0% student overdraft is still borrowed money, not income",
        ], "lessons": [
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "Three big drops, a year of spending",
                "body": "Student money arrives in a strange rhythm: the maintenance loan usually lands in three termly instalments, but your costs run week after week. The classic trap is week one — the loan hits your account, it's the most money you've ever held, and freshers' events are everywhere. The fix is simple arithmetic before anything else: divide the instalment by the number of weeks it must cover, and that's your real weekly budget. Everything above that number is borrowed from a future week.",
            }},
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "An overdraft is not income",
                "body": "Most student bank accounts offer a 0% arranged overdraft — often £1,500 or more. Used as a buffer for a genuinely tight week, it's a useful tool. Treated as extra spending money, it's a slow leak: every pound of overdraft is borrowing that must be repaid, and after you graduate the 0% deal ends and interest starts. A balance that sits at minus £1,500 all year isn't a budget working — it's a debt growing quietly.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Your maintenance loan instalment is £2,400 and it has to last a 12-week term. What's your weekly budget?",
                "choices": [
                    "£300 — you can always cut back later",
                    "£200 a week",
                    "£240 a week",
                    "There's no way to work it out in advance",
                ],
                "answer_index": 1,
                "explanation": "£2,400 ÷ 12 = £200 a week — and that has to cover rent, food, transport and fun. Spend £300 in week one and you've already taken £100 from a later week. Do this division the day the loan lands.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "You're offered extra shifts at your part-time job during term. What's the sensible way to think about it?",
                "choices": [
                    "Always say yes — more money is always better",
                    "Never work during term — jobs and study can't mix",
                    "Weigh it against study and rest: many universities suggest keeping term-time work to roughly 15 hours a week",
                    "Only the pay rate matters; hours are irrelevant",
                ],
                "answer_index": 2,
                "explanation": "A part-time job can fund your budget and build your CV, but your degree is the bigger investment. Many universities recommend around 15 hours a week or less in term time — past that, grades tend to pay the price.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "A 16-25 Railcard costs about £30 a year and cuts a third off most rail fares. You expect to spend £180 on train tickets this year. What's the maths?",
                "choices": [
                    "You'd lose money — the card costs more than it saves",
                    "You'd save £180 — travel becomes free",
                    "It saves nothing unless you travel first class",
                    "You'd save £60 on fares, so you're about £30 better off after the card's cost",
                ],
                "answer_index": 3,
                "explanation": "A third off £180 is £60 saved; subtract the £30 card and you're £30 ahead — and further ahead the more you travel. Always run this sum: discount schemes only pay off if you'd genuinely spend enough.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Which of these is a FALSE economy — something that looks like saving but costs more overall?",
                "choices": [
                    "Skipping the weekly food shop, then buying every meal at the campus café because the fridge is empty",
                    "Batch-cooking with flatmates and freezing portions",
                    "Walking the 15 minutes to campus instead of taking the bus",
                    "Buying second-hand textbooks or using the library copy",
                ],
                "answer_index": 0,
                "explanation": "Skipping a £25 shop feels like saving until five £6 café meals replace it. Batch-cooking, walking and second-hand books are real savings: same outcome, lower cost. A false economy cuts the upfront price but raises the total.",
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "It's the first day of term and £2,800 of maintenance loan just landed — the most money you've ever had. Freshers' week starts tonight. What's your move?",
                "choices": [
                    {"label": "Enjoy week one properly — you'll budget whatever is left afterwards", "outcome": "This is the week-1 splurge trap. Spend £400 in seven days and the remaining 11 weeks drop from £233 to £218 each — and that's before rent. Budgeting 'what's left' means the splurge sets your budget, not you."},
                    {"label": "Pay rent for the term first, divide the rest by the weeks it must cover, and set a weekly number — with a modest amount ring-fenced for freshers' week", "outcome": "Exactly right. Securing rent removes the biggest risk, the division gives you a real weekly figure, and planning fun money means you join in without quietly spending next month's food budget."},
                    {"label": "Leave it all untouched and live off your 0% overdraft instead — it's interest-free anyway", "outcome": "Backwards, sadly. The overdraft is borrowing with a deadline: the 0% deal ends after graduation. Spending borrowed money while your own sits idle just builds a debt you'll repay later."},
                ],
                "correct_index": 1,
            }},
        ]},
        {"title": "Level 3", "learning_objectives": [
            "Spot housing and job scams that target students — and explain why money muling is a crime, not a job",
            "Budget on an irregular income by planning around the lean months",
            "Compare university, apprenticeships and gap years as financial decisions using a simple framework",
        ], "lessons": [
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "0% isn't 0% forever",
                "body": "Student overdrafts and 0% credit card deals share a trick: the zero has an expiry date. A student overdraft typically stays interest-free for a while after graduation, then converts to a standard overdraft — often at very high rates. A 0% purchase card flips to its full APR (which you met in Debt & Credit Explained) the day the promotional period ends. Before using any 0% deal, find the end date and write down your plan for clearing the balance before it arrives.",
            }},
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "If a 'job' pays you to receive money, it isn't a job",
                "body": "A common scam targets students: someone offers easy cash to receive money into your bank account and forward it on. This is money muling — moving stolen or criminal money — and it's money laundering, a serious crime even if you didn't know the source. Consequences can include your account being closed, a fraud marker that blocks you from bank accounts and loans for years, and prosecution. No legitimate employer ever needs your account to move their money.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "A flat listing is suspiciously cheap. The 'landlord' is abroad, can't do viewings, but will post you the keys once you transfer a £400 deposit. What's the right move?",
                "choices": [
                    "Walk away and verify independently: insist on a real viewing, check the landlord or agent is genuine, and ask someone you trust before sending anything",
                    "Send the £400 quickly — at that price it'll be gone by tomorrow",
                    "Send half now as a compromise and the rest after you get the keys",
                    "It's fine as long as they email you a contract first",
                ],
                "answer_index": 0,
                "explanation": "Cheap price, no viewing, urgency and bank transfer is the classic fake-listing pattern — the flat usually doesn't exist or isn't theirs. Scammers can fake contracts easily. Never pay a deposit for a property no one you trust has seen.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Why is money muling so dangerous for the 'mule', even if they never stole anything themselves?",
                "choices": [
                    "It isn't — only the original thief commits a crime",
                    "The only risk is losing the commission you were promised",
                    "Moving criminal money through your account is money laundering: you can face a closed account, a fraud marker lasting years, and prosecution",
                    "Banks always refund mules, so there's no lasting harm",
                ],
                "answer_index": 2,
                "explanation": "Letting criminal money pass through your account is itself a crime. A fraud marker can block you from accounts, loans, phone contracts and even some jobs for years. 'I didn't know' is hard to argue when you were paid to do it.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Your income is lumpy: a termly loan drop, occasional shifts, the odd gift. Some months you get £600, others £150. How do you budget?",
                "choices": [
                    "Budget for the £600 months — be optimistic",
                    "Build the plan around the lean months, and move the surplus from good months into a buffer",
                    "Don't budget at all until your income is steady",
                    "Spend freely in good months; the lean ones will average out",
                ],
                "answer_index": 1,
                "explanation": "Plan around what you can rely on, not what you hope for. A budget built on £150-200 months always works; the extra from £600 months becomes a buffer that smooths the gaps instead of vanishing.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "You're weighing university, a degree apprenticeship and a gap year. What's the soundest way to compare them financially?",
                "choices": [
                    "University always wins — graduates earn more, end of story",
                    "An apprenticeship always wins — no tuition fees, end of story",
                    "Money shouldn't enter the decision at all",
                    "Compare each path's costs, likely earnings, and what you give up meanwhile — then weigh that against what you actually want to do",
                ],
                "answer_index": 3,
                "explanation": "Each route has a different shape: uni has fees and living costs but may raise long-term earnings; an apprenticeship pays you to train; a gap year delays both. There's no universal winner — the framework is costs vs likely earnings vs what you give up, applied to YOUR plans. Talk it through with a parent or adviser.",
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "A flatmate's contact offers you £200 to 'process a payment': £2,000 will arrive in your account and you forward £1,800 to another account, keeping the rest. You could really use £200. What do you do?",
                "choices": [
                    {"label": "Do it once — it's your account and £200 is £200", "outcome": "That single transfer is money laundering. The £2,000 is almost certainly stolen, and when the bank traces it — they usually do — you face an account closure, a fraud marker that can follow you for years, and possible prosecution. No £200 is worth that."},
                    {"label": "Ask the contact more questions about where the money comes from first", "outcome": "Scammers have smooth answers ready — 'it's a business workaround', 'it's from selling abroad'. You can't verify any of it through them, and the act itself would still be illegal. The question to ask isn't theirs to answer: a real job never routes money through your personal account."},
                    {"label": "Refuse, and talk it over with someone you trust — and report the approach to your bank or Action Fraud", "outcome": "Exactly right. Refusing protects you; telling a parent or adviser sense-checks anything you're unsure about; reporting it helps protect other students the recruiter approaches. Be wary too of 'friends of friends' — that's exactly how mule recruiters spread."},
                ],
                "correct_index": 2,
            }},
        ]},
    ],
}
```
