# Your Brain on Money — teen module draft

**L1 — Meet your money brain (free).** Introduces System 1 (fast, automatic) vs System 2 (slow, deliberate) thinking and frames money mistakes as ancient survival software running on modern problems. Covers loss aversion (losing £10 hurts roughly twice as much as winning £10 feels good) and FOMO as a wired-in herd response rather than a personal weakness or a signal that an opportunity is real.

**L2 — Biases in the wild (free).** Four named biases with teen-real examples: anchoring reframed as a bias (not just a shop trick — including trainers-resale anchor pricing), social proof and herd behaviour (why "everyone's buying" is a warning, not a signal), the sunk-cost fallacy ("I've already spent so much…" in games and crypto), and present bias (why future-you keeps losing to now-you).

**L3 — Outsmarting yourself (premium).** You can't delete biases, so you design around them: personal money rules set while calm ("I wait 48 hours on anything over £30"), automation that beats willpower, pre-commitment, a decision checklist plus the "what would I tell a friend?" test — and the payoff insight that a scammer's toolkit is exactly this module, stacking urgency, social proof, anchors and greed against System 2.

```python
module = {
    "topic": "risk", "title": "Your Brain on Money",
    "standards_alignment": [
        {"framework": "UK MaPS/YE Financial Education Planning Framework", "code": "11-19", "label": "Managing risks and emotions associated with money"},
        {"framework": "US National Standards for Personal Financial Education (CEE/Jump$tart 2021)", "code": "VI", "label": "Managing Risk"},
    ],
    "sources": [
        {"title": "MoneyHelper — Money and emotional wellbeing", "url": "https://www.moneyhelper.org.uk/en/money-troubles/way-forward/money-and-mental-health"},
        {"title": "FCA InvestSmart — Avoiding hype and scams", "url": "https://www.fca.org.uk/investsmart"},
    ],
    "learning_objectives": [
        "Distinguish fast, automatic System 1 reactions from slow, deliberate System 2 thinking in money decisions",
        "Explain loss aversion — losses feel roughly twice as strong as equal gains — and how it drives poor choices",
        "Recognise FOMO as a wired-in group response, not a signal that an opportunity is real",
    ],
    "conversation_prompt": "Each name one bias the family fell for this month — an anchor ('was £80'), FOMO, or sunk cost ('we've already paid for it'). No blame: everyone's brain does this. Then agree one shared money rule to try for a month.",
    "country_codes": [], "is_premium": False, "order_index": 14, "icon": "🧠", "min_age": 14,
    "lessons": [
        {"type": "card", "xp_reward": 10, "content_json": {
            "title": "Your brain is running 200,000-year-old software",
            "body": "Your brain has two systems. System 1 is fast and automatic — it decides in milliseconds whether something feels good or dangerous. System 2 is slow and deliberate — it does the maths, weighs options, reads the small print. System 1 evolved for spotting predators and grabbing food before someone else did. It did not evolve for in-app purchases or trading apps. Most money mistakes happen when System 1 answers a question that System 2 should have got.",
        }},
        {"type": "card", "xp_reward": 10, "content_json": {
            "title": "Losses hurt twice as much",
            "body": "Losing £10 hurts roughly twice as much as winning £10 feels good. Psychologists call this loss aversion, and it's measurable, not a metaphor. It explains a lot: why people hold a falling investment for years rather than admit a loss, why 'don't miss out' works better in adverts than 'here's a gain', and why a refund feels like a win. Your brain isn't weighing money fairly — it's weighing pain. Knowing the scale is rigged is step one.",
        }},
        {"type": "quiz", "xp_reward": 25, "content_json": {
            "question": "You see 'FLASH SALE — 1 hour left' and feel a jolt of urgency. Which part of your thinking just fired?",
            "choices": [
                "System 2 — careful, deliberate analysis",
                "Your long-term planning",
                "System 1 — the fast, automatic reaction",
                "Nothing — urgency is always a free, conscious choice",
            ],
            "answer_index": 2,
            "explanation": "That jolt arrives before you've consciously decided anything — pure System 1. Countdown timers are aimed straight at it, because System 2 needs time, and time is exactly what they remove.",
        }},
        {"type": "quiz", "xp_reward": 25, "content_json": {
            "question": "Research on loss aversion suggests that losing £10 feels about as intense as…",
            "choices": [
                "Winning £20 feels good",
                "Winning £10 feels good",
                "Winning £5 feels good",
                "Nothing — small losses don't register",
            ],
            "answer_index": 0,
            "explanation": "Losses weigh roughly twice as much as equal gains. That 2:1 asymmetry is why the fear of losing drives more decisions — good and bad — than the hope of winning.",
        }},
        {"type": "quiz", "xp_reward": 25, "content_json": {
            "question": "A coin you bought for £40 is now worth £25. What does loss aversion push most people to do?",
            "choices": [
                "Check the project's actual prospects before deciding",
                "Sell instantly, whatever the facts",
                "Work out the exact loss in a spreadsheet",
                "Hold it indefinitely rather than 'make the loss real' — even when selling is the rational move",
            ],
            "answer_index": 3,
            "explanation": "Selling turns a paper loss into a felt one, and brains will do almost anything to dodge that pain. The sharper question is 'would I buy this today at £25?' — not 'how do I avoid feeling the loss?'",
        }},
        {"type": "quiz", "xp_reward": 25, "content_json": {
            "question": "Why does FOMO feel so physical — that genuine pull when everyone seems to be buying something?",
            "choices": [
                "It's a personal weakness that only some people have",
                "It's an ancient survival response — being left out of what the group was doing used to be genuinely dangerous",
                "It's proof the opportunity is real",
                "It's caused by too much screen time",
            ],
            "answer_index": 1,
            "explanation": "For most of human history, missing what the group was doing could cost you food or safety. The wiring is still there — it just fires at trainers drops and coins now. Feeling it is normal; obeying it is optional.",
        }},
        {"type": "scenario", "xp_reward": 20, "content_json": {
            "prompt": "It's 11pm. A limited skin bundle just dropped in your favourite game — 'exclusive, gone in 24 hours'. Your heart rate actually goes up. You have the money. What do you do?",
            "choices": [
                {"label": "Buy it — the strength of the feeling proves you really want it", "outcome": "The feeling proves System 1 fired, nothing more. Urgency plus exclusivity is engineered to produce exactly that jolt. A real preference survives until morning; a manufactured one usually doesn't."},
                {"label": "Name the jolt as System 1, and decide in the morning with System 2", "outcome": "That's the core skill of this whole module. Naming the reaction takes its power away — and a 24-hour window means the bundle will still be there after you've slept on it."},
                {"label": "Ask the group chat whether you should buy it", "outcome": "Risky — your friends' System 1s are firing too. A group of excited brains isn't a second opinion; it's social proof, which you'll meet properly in the next level."},
            ],
            "correct_index": 1,
        }},
    ],
    "extra_levels": [
        {"title": "Level 2", "learning_objectives": [
             "Spot anchoring, social proof, sunk-cost thinking and present bias in real purchases and investments",
             "Explain why 'everyone is buying it' is usually a warning rather than a signal",
             "Treat money already spent as irrelevant to the next decision",
         ], "lessons": [
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "Anchoring: the first number wins",
                "body": "'Was £80, now £40' isn't really information about the jacket — it's information about your brain. The first number you see becomes an anchor, and every other number gets judged against it. £40 feels cheap next to £80, even if the jacket was never worth £80 to anyone. Resale sites run it too: list trainers at a silly price, then 'accept offers'. The fix is blunt and effective: ignore the first number and ask what it's worth to you, starting from zero.",
            }},
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "Future-you keeps losing to now-you",
                "body": "It isn't a fair fight. Your brain treats a reward today as far more valuable than a bigger reward later — that's present bias. It's why £15 of food delivery beats £15 towards something you genuinely want more, and why 'I'll start saving next month' repeats forever. To your brain, future-you is basically a stranger, and it doesn't hand strangers money. The trick isn't caring harder — it's making the decision before now-you shows up.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Trainers are listed for resale at £300, then the seller 'accepts your offer' of £180. £180 suddenly feels like a win. What actually happened?",
                "choices": [
                    "£180 is objectively a great price for any trainers",
                    "The £300 anchor reset your sense of what they're worth — the seller likely wanted around £180 all along",
                    "The seller made a mistake in your favour",
                    "Resale prices are fixed by the manufacturer",
                ],
                "answer_index": 1,
                "explanation": "The £300 was never the price — it was the anchor. Judged against it, £180 feels like a bargain; judged from zero, it might not. Anchoring works even when you know the first number is inflated.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "A coin is rocketing and everyone on your feed is buying it. Why is that closer to a warning than a signal?",
                "choices": [
                    "Crowds are always wrong about everything",
                    "Social media posts about money are illegal",
                    "Popular things never make money",
                    "By the time everyone is buying, the price already contains their excitement — you'd be paying for the hype, often near the top",
                ],
                "answer_index": 3,
                "explanation": "Herd behaviour means the crowd's optimism is already in the price. The people who profited bought before it was everywhere. 'Everyone's in' usually means the easy gains are gone and the risk is at its highest.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "You've spent £120 on a game you no longer enjoy. 'I've put too much in to stop playing now' is a textbook example of…",
                "choices": [
                    "The sunk-cost fallacy — money already spent shouldn't steer what you do next",
                    "Sensible loyalty to a purchase",
                    "Compound interest",
                    "Anchoring",
                ],
                "answer_index": 0,
                "explanation": "The £120 is gone whether you play or not — it's a sunk cost. Spending more time (or money) to 'justify' it just adds new losses to old ones. The only question that matters: is the next hour or pound worth it on its own?",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Offered £20 today or £30 in a month, plenty of people grab the £20 — even though waiting pays a 50% return. Which bias is doing the grabbing?",
                "choices": [
                    "Anchoring",
                    "Social proof",
                    "Present bias — rewards now feel oversized compared with rewards later",
                    "Loss aversion",
                ],
                "answer_index": 2,
                "explanation": "Present bias inflates the value of 'right now'. Almost no investment reliably pays 50% in a month, yet brains routinely turn it down to avoid waiting. Spotting that gap is the start of beating it.",
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "You bought a hyped coin at £60. It's now at £25, and you're tempted to put in another £40 to 'win the loss back'. What's the sharpest way to think about it?",
                "choices": [
                    {"label": "Buy more — you can't quit while you're down", "outcome": "That's sunk cost and loss aversion driving together. The £35 drop has happened whether you buy or not, and chasing it is exactly how small losses become big ones."},
                    {"label": "Ask: 'If I had £40 fresh and didn't own this coin, would I buy it at £25 today?'", "outcome": "That question deletes the sunk cost from the maths. If the honest answer is no, the only reason to buy is to soothe the loss — and the market doesn't care how you feel."},
                    {"label": "Sell everything instantly and swear off investing forever", "outcome": "Swinging to the opposite extreme is still System 1 in charge — just running on fear instead of hope. The lesson isn't 'never invest'; it's 'decide on today's facts, not yesterday's spend'."},
                ],
                "correct_index": 1,
            }},
        ]},
        {"title": "Level 3", "learning_objectives": [
             "Design personal money rules, automation and pre-commitments that work even when willpower fails",
             "Apply a decision checklist and the 'friend test' before any big purchase or investment",
             "Recognise when hype or a scam is deliberately stacking biases against you",
         ], "lessons": [
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "You can't patch the brain — build guardrails instead",
                "body": "Here's the uncomfortable truth: knowing about biases barely protects you from them. Even the researchers who discovered loss aversion still feel it. So don't rely on willpower in the hot moment — design the moment out. Personal rules ('anything over £30 waits 48 hours') make the decision before the temptation arrives. Automation goes further: a standing transfer into savings the day money lands means future-you gets paid first, with zero willpower spent. You're not fixing the bug — you're routing around it.",
            }},
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "The scammer's toolkit is this module",
                "body": "Read a scam pitch closely and you'll find this module inside it. 'Guaranteed returns' target loss aversion. 'Spots close tonight' weaponises urgency against System 2. Screenshots of strangers' profits are social proof. A 'normally £500, today free' course is an anchor. Scammers don't hack your phone — they hack your biases, several at once. So before any big decision, run a checklist: What am I being rushed past? Who profits if I say yes? What would I tell a friend who showed me this?",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Why does an automatic transfer into savings beat 'saving whatever's left at the end of the month'?",
                "choices": [
                    "It removes the decision entirely, so present bias never gets a vote",
                    "Banks pay extra interest on automatic transfers",
                    "It's the only way savings are protected",
                    "It stops you ever spending money on anything",
                ],
                "answer_index": 0,
                "explanation": "Willpower is a rematch you have to win every single month; automation is winning once, permanently. By the time now-you wants to spend, the money has already gone where calm-you sent it.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "A rule like 'I wait 48 hours on anything over £30' works mainly because…",
                "choices": [
                    "48 is a scientifically magic number",
                    "It guarantees you never buy anything again",
                    "You set it while calm, so the hot, impulsive moment is no longer the one making the decision",
                    "Retailers are required to honour it",
                ],
                "answer_index": 2,
                "explanation": "This is pre-commitment: calm-you writes the rule, so excited-you doesn't have to win an argument at the checkout. The exact numbers are yours to tune — the point is deciding before the urge arrives.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Before a big buy or investment, asking 'what would I tell a friend who showed me this?' helps because…",
                "choices": [
                    "Friends always know more about money than you do",
                    "Distance switches off the emotional pull, so you judge the deal instead of your feelings about it",
                    "It delays the purchase until the sale ends",
                    "It legally transfers the risk to the friend",
                ],
                "answer_index": 1,
                "explanation": "Advice for a friend runs on System 2; decisions for yourself run hot. The same brain that whispers 'go on, it's fine' to you will calmly tell a friend 'that's an obvious trap'. Borrow that voice.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "A pitch stacks 'guaranteed 10x returns', a countdown timer, screenshots of winners, and 'normally £500 — today free'. What's the most reliable conclusion?",
                "choices": [
                    "At least one of the claims is probably true",
                    "The free price means there's nothing to lose",
                    "It's worth testing with a small amount",
                    "It's pressing four separate biases at once — the signature of a scam, not an opportunity",
                ],
                "answer_index": 3,
                "explanation": "Greed, urgency, social proof and an anchor, all in one pitch. Real opportunities don't need to stack psychological pressure — manufactured ones can't work without it. The stacking itself is the red flag.",
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "A TikTok 'mentor' shows a method for turning £100 into £1,000, flashes screenshots of followers' wins, and says the free group closes at midnight. You have £100 saved. What do you do?",
                "choices": [
                    {"label": "Join now — it's free, so there's nothing to lose", "outcome": "'Free' is the anchor that gets you through the door; the cost arrives later, inside the group. A midnight deadline on something free exists to stop you doing the one thing that defeats it: thinking."},
                    {"label": "Run the checklist — rushed? who profits? would I tell a friend to do this? — then walk away and report the account", "outcome": "The checklist catches it instantly: urgency, social proof and impossible returns stacked together. Real opportunities survive being slept on; this one is built so you won't try. Walking away and reporting protects the next person too."},
                    {"label": "Put in the £100 but promise yourself you'll stop if it starts going wrong", "outcome": "That promise is made by calm-you but must be kept by losing-you — the version with loss aversion shouting to win it back. Pre-commitment is powerful, but it can't operate inside a setup designed to fleece you."},
                ],
                "correct_index": 1,
            }},
        ]},
    ],
}
```
