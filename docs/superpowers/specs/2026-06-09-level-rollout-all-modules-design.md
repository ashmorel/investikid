# Level 2 & 3 Rollout — All Remaining Modules (Design + Full Content)

**Date:** 2026-06-09
**Status:** Draft — awaiting your spot-review
**Repo:** `ashmorel/investikid` · branch `testing`
**Programme:** Rolls the approved *What is a Stock?* Level 2/3 pilot pattern out to the **11 remaining single-level modules**. AI-drafted, seed-authored, reviewed by you here.

## What this adds
Each of the 11 modules below gains a **Level 2 (free)** and a **Level 3 (premium)**, matching the pilot exactly:
- **2 cards + 4 quizzes + 1 scenario** per level (REIT mirrors this after a top-up). XP: card 10, quiz 25, scenario 20. No video lessons.
- **Premium model (unchanged from #2):** Level 1 & 2 are free; Level 3 is premium (`is_premium` derived from `order_index >= 2` via `premium_for_position`). The seeder creates them through the existing idempotent `extra_levels` path — no new mechanism.
- **Safety:** kids-safe, UK context, age-appropriate; crypto kept extra-cautious; every scam/hype scenario steers to a trusted grown-up.

## Scope / process
- **154 new lessons** total (11 modules × 14). Full content is rendered below for review; the machine-readable `extra_levels` literals live in `docs/superpowers/specs/level-rollout-drafts/`.
- After your spot-review approval → implementation plan adds each module's `extra_levels` to `backend/app/seed/content.py`, extends `test_seed_content.py` / `test_stock_level_pilot.py`-style coverage, regression, push to `testing` (green CI). **No promotion** without your go-ahead.

---

## Module index

- **Budgeting Basics** (`budgeting`) — see below
- **Needs vs Wants** (`budgeting`) — see below
- **What is Crypto?** (`crypto`) — see below
- **Credit & Debt** (`debt`) — see below
- **Revenue, Costs & Profit** (`entrepreneurship`) — see below
- **Your Side Hustle** (`entrepreneurship`) — see below
- **What is a REIT?** (`real-estate`) — see below
- **Diversification** (`risk`) — see below
- **Compound Interest** (`savings`) — see below
- **Your First Paycheque** (`taxes`) — see below
- **How Taxes Work** (`taxes`) — see below

---

## Budgeting Basics  
`topic: budgeting` · draft file: `level-rollout-drafts/budgeting__basics.md`

### Level 2 — Level 2 (free)

1. **Card** · 10 XP — *A budget only works if you track it*
   > A plan is a guess until you check it against reality. Tracking means writing down what you actually spend — in a notes app, a little notebook, or a simple spreadsheet. At the end of the week you compare what you planned to spend with what you really spent. The gaps are where the surprises hide, and they're usually the small, easy-to-forget buys.

2. **Card** · 10 XP — *Fixed costs vs variable costs*
   > Some costs are the same every month — a phone plan or a bus pass. Those are fixed costs, and they're easy to plan for. Others change month to month — snacks, games, days out. Those are variable costs. Variable costs are where most people overspend, because they feel small in the moment. Knowing which is which tells you where you have room to cut back.

3. **Quiz** · 25 XP — Why is tracking your spending so useful, even if you already made a budget?
   - a) A budget is only a plan — tracking shows what you actually spent, so you can spot surprises ✅
   - b) Tracking automatically gives you more money
   - c) Once you write a budget, spending takes care of itself
   - d) Tracking is only for grown-ups with jobs
   - *Explanation:* A budget is a forecast. Tracking is the reality check — comparing the two is how you find the small, sneaky spends and fix next month's plan.

4. **Quiz** · 25 XP — Which of these is a fixed cost?
   - a) A monthly bus pass that costs the same every month ✅
   - b) Snacks at the shop, which change week to week
   - c) Money spent on days out with friends
   - d) Birthday gifts for friends
   - *Explanation:* A fixed cost stays the same each month (like a bus pass or phone plan). Snacks, days out, and gifts vary, so they're variable costs — the ones easiest to overspend on.

5. **Quiz** · 25 XP — You know your sister's birthday in 4 months will cost about £20. What's the smart budgeting move?
   - a) Set aside £5 a month now so the £20 is ready (a 'sinking fund') ✅
   - b) Forget about it and hope you have £20 that month
   - c) Borrow the £20 when the time comes
   - d) Spend £20 now so it's 'out of the way'
   - *Explanation:* A sinking fund means saving a little each month for a known future cost. Putting £5 aside for 4 months means the £20 is ready, with no scramble and no borrowing.

6. **Quiz** · 25 XP — You tracked your month and spending came to £10 more than your income. What should you do first?
   - a) Adjust the budget — trim a variable cost or two until the plan adds up ✅
   - b) Ignore it; £10 is too small to matter
   - c) Borrow £10 every month to cover the gap
   - d) Stop tracking so you don't see the problem
   - *Explanation:* A budget that doesn't balance needs adjusting, not ignoring. Small overspends repeat every month. Trimming a variable cost (the flexible kind) is the quickest way to make the plan add up.

7. **Scenario** · 20 XP — You set a budget but kept overspending on snacks and small buys, and you're not sure where the money went. What's the best next step?
   - a) Guess what went wrong and set a stricter budget
     → Guessing rarely works — you don't actually know where the money leaked, so the new plan is just another guess.
   - b) Track every spend for two weeks, then review it (and ask a grown-up to look it over with you) ✅
     → This is exactly right. Tracking shows you the real pattern, and reviewing it — ideally with a trusted grown-up — turns a vague worry into a clear, fixable plan.
   - c) Give up on budgeting — it clearly doesn't work for you
     → The budget isn't the problem; the missing piece is tracking. Quitting just brings back the not-knowing.

### Level 3 — Level 3 (premium 🔒)

1. **Card** · 10 XP — *Give every pound a job (zero-based budgeting)*
   > A powerful method is to plan until your income minus your planned spending-and-saving equals zero — not because you spend it all, but because every pound has been assigned a job (spending, saving, or a sinking fund). Nothing is left 'floating' and unaccounted for, which is exactly where money tends to disappear.

2. **Card** · 10 XP — *Pay yourself first*
   > Most people save whatever is left at the end of the month — and usually that's nothing. 'Pay yourself first' flips it: the moment money comes in, you move your savings amount aside before you spend on anything else. Setting it to happen automatically (with a grown-up's help on any account) means you never have to rely on willpower.

3. **Quiz** · 25 XP — In zero-based budgeting, what does 'getting to zero' actually mean?
   - a) Every pound of income has been assigned a job — spending, saving, or a future cost ✅
   - b) You must spend all your money down to nothing
   - c) You're not allowed to save anything
   - d) Your bank balance must literally read £0
   - *Explanation:* Zero-based means planned income minus planned jobs equals zero — every pound is assigned, including the ones you save. It's about leaving nothing unaccounted for, not about spending it all.

4. **Quiz** · 25 XP — What does 'pay yourself first' mean?
   - a) Move your savings aside as soon as money comes in, before spending on anything else ✅
   - b) Buy yourself a treat before paying any bills
   - c) Only save whatever happens to be left at month's end
   - d) Pay friends back before you save
   - *Explanation:* Saving first — ideally automatically — means your savings goal gets met before spending nibbles it away. Saving 'what's left' usually leaves nothing.

5. **Quiz** · 25 XP — Your income is different every month (some months £40, some £90). What's a sensible way to budget?
   - a) Plan around your lower typical months, and save extra in the bigger months ✅
   - b) Plan as if every month is your best month ever
   - c) Refuse to budget until your income is steady
   - d) Spend more in good months to 'balance out' the lean ones
   - *Explanation:* With irregular income, budgeting around a lower, reliable amount keeps you safe in lean months, while the surplus from good months builds a cushion.

6. **Quiz** · 25 XP — You get a small pay rise and immediately start spending more on wants, so you're no better off. What's this called?
   - a) Lifestyle creep — spending rising to swallow up extra income ✅
   - b) Compound interest
   - c) A sinking fund
   - d) A budget surplus
   - *Explanation:* Lifestyle creep is when spending quietly grows to match any extra money, so you never get ahead. The fix: when income rises, send some of the increase straight to savings.

7. **Scenario** · 20 XP — You start a weekend job earning more than your old allowance. How do you handle the extra money wisely?
   - a) Upgrade everything now — new clothes, more takeaways, the lot
     → That's lifestyle creep in action. Spending swells to match the new income and you end up no better off than before, just with more stuff.
   - b) Decide a savings amount first, move it aside automatically, then budget the rest — checking the plan with a grown-up ✅
     → Excellent. Paying yourself first locks in your savings, automating it removes the willpower battle, and a grown-up's second look keeps the plan realistic.
   - c) Keep no plan and just see what's left at the end of each month
     → 'Saving what's left' almost always leaves nothing, especially with more money tempting you. Without a plan the extra income just slips away.

---

## Needs vs Wants  
`topic: budgeting` · draft file: `level-rollout-drafts/budgeting__needs-vs-wants.md`

### Level 2 — Level 2 (free)

1. **Card** · 10 XP — *The 'wait a bit' test*
   > When you really want something, try the wait-a-bit test: give yourself a short pause — a day, or even just a sleep on it — before buying. Lots of wants feel huge in the moment and much smaller the next day. If you still want it after waiting, it's probably a genuine choice, not just an impulse. Waiting costs you nothing and often saves you money.

2. **Card** · 10 XP — *Cost per use: the real value*
   > Price isn't the same as value. A £40 pair of shoes you wear every day can be better value than a £15 pair you wear twice. A handy trick is cost per use: roughly, the price divided by how many times you'll actually use it. Something cheap that you never use is expensive in disguise.

3. **Quiz** · 25 XP — What is the 'wait a bit' test?
   - a) A basic phone you must have for school
   - b) Giving yourself a short pause before buying, to check it's not just an impulse ✅
   - c) Buying something only if it's on sale
   - d) Asking a shop to lower the price
   - *Explanation:* Pausing before you buy lets the first rush of 'I want it NOW' fade, so you can decide calmly. If you still want it after waiting, that's a real choice.

4. **Quiz** · 25 XP — £40 boots you'll wear 200 times, or £15 boots you'll wear 5 times. Which is better value (cost per use)?
   - a) The £15 boots, because they cost less
   - b) The £40 boots — about 20p per wear vs £3 per wear ✅
   - c) They're exactly the same value
   - d) You can't compare them
   - *Explanation:* £40 ÷ 200 ≈ 20p each time; £15 ÷ 5 = £3 each time. The pricier boots are far better value because you'll actually use them. Cheap-but-unused is expensive in disguise.

5. **Quiz** · 25 XP — You spend your last £20 on a game instead of a cinema trip with friends. The cinema trip you gave up is called the…
   - a) Bonus
   - b) Opportunity cost ✅
   - c) Refund
   - d) Interest
   - *Explanation:* Every choice has an opportunity cost — the next-best thing you gave up. Money spent once can't be spent again, so it's worth asking 'what am I saying no to?'

6. **Quiz** · 25 XP — A toy is reduced from £50 to £30. Which question best tells you if it's a smart buy?
   - a) 'How big is the discount?'
   - b) 'Would I want this and use it even at £30 if it had never been £50?' ✅
   - c) 'Will it sell out today?'
   - d) 'What colour is it?'
   - *Explanation:* A discount only saves money if you'd genuinely want and use the thing anyway. 'It's 40% off!' isn't a reason to buy — the real question is whether it's worth £30 to you.

7. **Scenario** · 20 XP — You see a £35 gadget online and you really want it right now. You've got the money. What's the smartest move?
   - a) Add it to a wishlist and check again in a few days ✅
     → Great use of the wait-a-bit test. If you still want it later, you can buy it as a calm choice — and you'll often find the urge has faded.
   - b) Buy it instantly before the feeling passes
     → That rush is exactly what impulse buying feels like. Buying before you've thought it through is how wants win over sensible choices.
   - c) Buy two in case one breaks
     → That's spending even more on an impulse you haven't tested. One is already an unplanned want; two doubles the regret risk.

### Level 3 — Level 3 (premium 🔒)

1. **Card** · 10 XP — *Adverts are made to make you want*
   > Adverts, sponsored posts and influencer videos exist to make you feel you need something. Bright colours, happy faces, 'everyone has it' — these are clever tools, not facts. Spotting that an advert is designed to nudge you is a superpower: once you see the trick, it has far less power over you. Wanting something because an advert told you to isn't the same as actually needing it.

2. **Card** · 10 XP — *'Limited time!' and other hurry-up tricks*
   > 'Only 2 left!', 'Sale ends tonight!', 'Don't miss out!' — these messages are built to make you panic-buy before you've had time to think. Real needs don't have a countdown timer. When something is shouting at you to hurry, that's exactly the moment to slow down, breathe, and ask a trusted grown-up if you're unsure.

3. **Quiz** · 25 XP — What is the main job of an advert?
   - a) To give you honest, balanced advice
   - b) To make you want the product and feel you should buy it ✅
   - c) To save you money on purpose
   - d) To tell you what you genuinely need
   - *Explanation:* Adverts are made to sell, not to advise. Knowing that helps you enjoy them without letting them decide your spending for you.

4. **Quiz** · 25 XP — A site flashes 'Only 1 left — sale ends in 5 minutes!' What is this mostly designed to do?
   - a) Help you make a calm, careful decision
   - b) Rush you into buying before you've thought it through ✅
   - c) Give you a guaranteed best price
   - d) Remind you of something you truly need
   - *Explanation:* Countdown timers and 'almost gone!' messages create false panic. A genuine need doesn't expire in five minutes — so that pressure is your cue to slow right down.

5. **Quiz** · 25 XP — Your friends all bought the same trainers and say you 'have to' get them too. That pressure to want what the group wants is called…
   - a) Opportunity cost
   - b) Peer pressure ✅
   - c) Compound interest
   - d) A refund
   - *Explanation:* Wanting something just because friends have it is peer pressure. It's normal to feel it — but it's your money and your choice. Real friends won't mind if you spend differently.

6. **Quiz** · 25 XP — A favourite influencer is paid to show off a £60 hoodie. What's the wisest way to think about it?
   - a) 'They love it, so I obviously need it'
   - b) 'They're being paid to promote it, so I'll decide for myself if it's worth £60 to me' ✅
   - c) 'Everything they recommend must be a great deal'
   - d) 'I should buy it fast before it sells out'
   - *Explanation:* Sponsored posts are paid adverts. The person may be lovely, but the question is still whether the item is worth the price to you — not whether someone famous showed it.

7. **Scenario** · 20 XP — A big online sale is on. An influencer you follow is hyping a £45 jacket, the page says 'Only a few left!', and two friends have already bought it. You've got £45 saved for something else. What do you do?
   - a) Buy it right now so you don't miss out or feel left out
     → That's ads, hype and peer pressure all pulling at once — the exact mix designed to make you spend without thinking.
   - b) Pause, remember it's all designed to rush you, and chat to a trusted grown-up before deciding ✅
     → Spot-on. Naming the pressure (advert + countdown + friends) takes its power away, and a trusted grown-up can help you decide calmly.
   - c) Borrow money so you can buy it AND keep your £45
     → Borrowing for a hyped-up want is how small wants turn into money you owe. Never take on debt because of a countdown timer.

---

## What is Crypto?  
`topic: crypto` · draft file: `level-rollout-drafts/crypto__what-is-crypto.md`

### Level 2 — Level 2 (free)

1. **Card** · 10 XP — *A chain that's hard to cheat*
   > A blockchain stores transactions in 'blocks' that are joined in order, like links in a chain. Each new block carries a fingerprint of the one before it, so if anyone tried to secretly change an old block, the fingerprints would stop matching and the whole network would notice. Thousands of computers keep their own copy and compare notes, so there's no single record a cheat could quietly rewrite. Trust comes from lots of computers agreeing, not from one boss in charge.

2. **Card** · 10 XP — *Your keys, your responsibility*
   > A crypto wallet doesn't really 'hold' coins — it holds keys. Your public key is like an account number you can share so people can send to you. Your private key is the secret that lets you spend, and it must NEVER be shared. The scary part: if you lose your private key there's no 'forgot password' button and no bank to ring — the crypto is usually gone forever. And if a scammer gets your private key or 'seed phrase', they can take everything in seconds.

3. **Quiz** · 25 XP — Why is it so hard to secretly change an old transaction on a blockchain?
   - a) Because a security guard checks every block
   - b) Because each block carries a fingerprint of the one before it, and thousands of computers compare copies ✅
   - c) Because the government keeps the only copy
   - d) Because old blocks are printed out on paper
   - *Explanation:* Each block is linked to the previous one by a fingerprint, and thousands of computers hold matching copies — so a secret change would break the chain and everyone would spot it.

4. **Quiz** · 25 XP — Which key should you NEVER share with anyone?
   - a) Your public key (like an account number)
   - b) Your private key or seed phrase (the secret that lets you spend) ✅
   - c) The name of the coin
   - d) The price you paid
   - *Explanation:* Your public key is fine to share so people can send to you. Your private key (or seed phrase) is the secret that controls everything — sharing it is like handing someone the keys to your whole wallet.

5. **Quiz** · 25 XP — A website promises 'Send 1 coin and we'll send you 2 coins back — guaranteed, today only!' What is this most likely?
   - a) A normal, safe way to grow money
   - b) A scam — 'double your money, guaranteed, act now' is a classic crypto trick ✅
   - c) A government savings scheme
   - d) A bank offering interest
   - *Explanation:* Guaranteed doubling, 'today only' pressure, and 'send first' are textbook scam signs. Real investing is never guaranteed, and nobody legit asks you to send crypto to get more back.

6. **Quiz** · 25 XP — You forget the private key to your crypto wallet. What usually happens?
   - a) You ring a helpline and they reset it
   - b) The bank refunds you
   - c) There is often no way to recover it, and the crypto can be lost for good ✅
   - d) It automatically emails you a new key
   - *Explanation:* Unlike a bank account, most crypto has no 'forgot password' and no customer-service reset. Lose the key and the crypto is usually gone — which is one reason it's risky.

7. **Scenario** · 20 XP — You're playing an online game and someone you've never met messages: 'I'll give you free crypto — just send me your wallet's secret recovery phrase so I can add it.' What do you do?
   - a) Refuse and tell a trusted grown-up ✅
     → Exactly right. Your secret recovery phrase controls everything in the wallet. Nobody genuine ever needs it — anyone asking is trying to steal from you. Telling a trusted adult is the safe move.
   - b) Send it — free crypto sounds great
     → This is a trap. Handing over your recovery phrase lets a scammer empty the wallet instantly. 'Free crypto' used as bait is one of the most common online scams.
   - c) Send just half of the phrase to be safe
     → Still unsafe — you should never share any part of a secret recovery phrase, and a stranger asking for it at all is a red flag. Stop and tell a trusted grown-up.

### Level 3 — Level 3 (premium 🔒)

1. **Card** · 10 XP — *What makes 'money' actually money?*
   > Normal money like the pound does three jobs well: you can spend it almost anywhere, its value stays fairly steady day to day, and the Bank of England helps manage it. Most crypto struggles with those jobs — few shops accept it, its price can swing wildly in a single day, and no central body steadies it. That doesn't make crypto 'fake', but it's why many experts treat it more like a risky bet than like everyday money. Understanding the difference helps you see through people who call it 'the future of all money'.

2. **Card** · 10 XP — *Why rules and energy both matter*
   > If a UK bank fails, the FSCS protects your savings up to £85,000 — but crypto usually has no such safety net, so if a platform collapses or gets hacked your money may simply be gone. Regulators like the FCA also warn that crypto is high-risk and largely unprotected. There's an environment angle too: some cryptocurrencies (like Bitcoin) use enormous amounts of electricity to run, which has a real climate cost. A thoughtful investor weighs all of this — safety, rules, and impact — not just the price.

3. **Quiz** · 25 XP — Which is a job that ordinary money (like the pound) does much better than most crypto?
   - a) Keeping a fairly steady value you can spend almost anywhere ✅
   - b) Doubling in value every week
   - c) Being impossible to ever lose
   - d) Earning guaranteed profits
   - *Explanation:* A currency works best when its value is steady and widely accepted. Most crypto swings too much and is accepted in too few places to do that job well — a key difference from everyday money.

4. **Quiz** · 25 XP — If a crypto platform gets hacked and your crypto is stolen, what protection usually applies?
   - a) The FSCS refunds you up to £85,000
   - b) The government replaces it
   - c) Usually none — crypto generally isn't covered by the protections that guard bank savings ✅
   - d) Your school insurance covers it
   - *Explanation:* FSCS protection covers savings in regulated UK banks, not most crypto. That missing safety net is a big reason regulators call crypto high-risk.

5. **Quiz** · 25 XP — A famous person posts 'Buy this new coin NOW before you miss out!' What's the smartest reaction?
   - a) Buy immediately so you don't miss out
   - b) Copy them — famous people can't be wrong
   - c) Pause, be sceptical of hype and 'fear of missing out', and talk to a trusted grown-up before doing anything ✅
   - d) Borrow money to buy more
   - *Explanation:* 'Buy now or miss out' is designed to rush you. Famous people are sometimes paid to promote coins. Slowing down, questioning the hype, and asking a trusted adult protects you from FOMO-driven mistakes.

6. **Quiz** · 25 XP — Why do some people raise concerns about the environmental impact of certain cryptocurrencies?
   - a) They use too much paper
   - b) Some use huge amounts of electricity to run, which has a climate cost ✅
   - c) They are made of plastic
   - d) They require lots of water to print
   - *Explanation:* Cryptocurrencies like Bitcoin can use enormous amounts of electricity. That energy use is a real-world cost a thoughtful person factors in, alongside the financial risks.

7. **Scenario** · 20 XP — Your older cousin is excited: 'I'm putting ALL my birthday money into one new coin a YouTuber promoted — it's going to the moon!' They ask what you think. What's the wisest thing to say?
   - a) Sounds amazing — put mine in too!
     → Risky. Following hype from a video and betting everything on one volatile coin is exactly how people lose money fast. 'Going to the moon' is a promise nobody can actually make.
   - b) Maybe slow down — that's a lot of risk on one hyped coin. Let's read about it and talk to a trusted grown-up first. ✅
     → Brilliant. You're spotting hype, the danger of putting everything in one place, and the value of caution and adult guidance. That's exactly how a careful thinker responds.
   - c) Borrow more so you can buy even more!
     → Never a good idea. Borrowing to buy something this volatile can leave you owing money AND losing the investment. One of the most dangerous moves in investing.

---

## Credit & Debt  
`topic: debt` · draft file: `level-rollout-drafts/debt__credit.md`

### Level 2 — Level 2 (free)

1. **Card** · 10 XP — *How interest piles up (not just once)*
   > APR is a yearly price tag, but interest on a credit card is usually added every month on whatever you still owe. So if you don't clear the balance, next month's interest is charged on the old amount PLUS last month's interest. It's compound interest working in reverse — against you instead of for you. The longer a debt sits unpaid, the faster it grows.

2. **Card** · 10 XP — *Four common types of credit*
   > Not all borrowing is the same. A credit card lets you spend up to a limit and is free if you clear it each month. A personal loan gives you a lump sum you repay in fixed monthly amounts. An overdraft lets your bank balance dip below £0 (often with fees). Buy Now Pay Later (BNPL) splits a purchase into instalments — handy, but easy to lose track of, and the missed-payment fees can sting. Knowing which is which helps you choose wisely.

3. **Quiz** · 25 XP — On most credit cards, how often is interest added to what you owe if you don't clear the balance?
   - a) Once a year only
   - b) Usually every month, on the amount still owed ✅
   - c) Never — credit cards don't charge interest
   - d) Only when you close the account
   - *Explanation:* Card interest is normally added monthly on your remaining balance, so an unpaid debt can grow faster than the yearly APR alone makes it sound.

4. **Quiz** · 25 XP — What is 'Buy Now Pay Later' (BNPL)?
   - a) A way to get items completely free
   - b) A savings account that pays you later
   - c) A way to split a purchase into instalments you pay over time ✅
   - d) A type of credit score
   - *Explanation:* BNPL spreads the cost of something into smaller payments. It can be useful, but missing a payment often means fees, so it needs care and tracking.

5. **Quiz** · 25 XP — You owe £100 on a card at roughly 2% interest a month and only pay the small minimum each month. What tends to happen?
   - a) The debt disappears after one payment
   - b) The debt shrinks very slowly and you pay extra in interest along the way ✅
   - c) The interest rate drops to zero
   - d) The bank cancels the balance
   - *Explanation:* Minimum payments barely dent the balance, so interest keeps being charged on what's left. The debt lingers and costs more overall — paying more than the minimum clears it faster and cheaper.

6. **Quiz** · 25 XP — Which of these is the most responsible way to use a credit card?
   - a) Spend right up to the limit every month
   - b) Only ever pay the minimum
   - c) Spend only what you can clear in full when the bill arrives ✅
   - d) Take out cash on it as often as possible
   - *Explanation:* Spending only what you can repay in full means you pay no interest and still build a positive borrowing history. That's the card working for you, not against you.

7. **Scenario** · 20 XP — Your phone breaks and a £180 replacement is offered as 'BNPL — just £30 a month for 6 months, 0% interest.' You get £20 a month pocket money. What's the smartest move?
   - a) Take the BNPL deal — it's 0% so it's basically free
     → It looks free, but £30 a month is more than your £20 income, so you'd likely miss a payment — and missed BNPL payments bring fees and can hurt your record. The maths has to add up first.
   - b) Buy an even pricier phone since you're paying monthly anyway
     → Spreading the cost can tempt you to overspend. A bigger debt is still a debt, and it's even harder to keep up with. This is exactly how easy credit catches people out.
   - c) Pause, and talk it through with a trusted grown-up before agreeing to anything ✅
     → Smart. A grown-up can help you check whether the payments fit your money, whether a cheaper phone would do, or whether saving up first is better. Never rush into a credit deal.

### Level 3 — Level 3 (premium 🔒)

1. **Card** · 10 XP — *How to build (and protect) a good credit score*
   > A credit score grows with steady, boring good habits: paying every bill on time, not using your whole limit, and keeping accounts open for a long while. One missed payment can dent it, and using almost all your available credit makes lenders nervous. You can't build a score overnight — it's a long game of small, reliable actions. Protecting it means checking statements, never ignoring a bill, and being cautious about how many credit deals you sign up for.

2. **Card** · 10 XP — *What a debt spiral looks like (and how to step out)*
   > A debt spiral is when you borrow to cover borrowing — paying one card with another, or taking a new loan to clear an old one. Each step adds more interest, so the total keeps climbing even though it feels like you're 'dealing with it.' The way out is to stop adding new debt, list what you owe, and ask for help early. In the UK there are free charities and services (your bank can point you to them) that help people make a plan — getting help is a strong, sensible move, never something to feel ashamed of.

3. **Quiz** · 25 XP — Which habit best helps build a strong credit score over time?
   - a) Missing the odd payment to save money that month
   - b) Paying bills on time and using only a small part of your limit ✅
   - c) Maxing out every card you have
   - d) Opening lots of new credit accounts at once
   - *Explanation:* Lenders like steady, reliable behaviour: on-time payments and low credit use. Those small habits, repeated over time, build trust.

4. **Quiz** · 25 XP — Someone takes out a new loan to pay off an old loan, then borrows again to cover that. What is this an example of?
   - a) Smart investing
   - b) A debt spiral ✅
   - c) Building a strong emergency fund
   - d) Earning compound interest
   - *Explanation:* Borrowing to repay borrowing just moves debt around while adding more interest. That's a debt spiral — the fix is to stop adding new debt and ask for help making a plan.

5. **Quiz** · 25 XP — When is borrowing more likely to be a wise decision?
   - a) To buy the latest trainers everyone has
   - b) To fund something that lasts or grows in value, with repayments you can comfortably afford ✅
   - c) To impress friends with a big purchase
   - d) Whenever a deal says '0%' — no matter the cost
   - *Explanation:* Borrowing can be sensible when it buys lasting value (like training or a reliable essential) AND the repayments fit your money. If it's just to consume more now, it's usually unwise.

6. **Quiz** · 25 XP — If you or your family were ever worried about debt, what's the best first step?
   - a) Hide the bills and hope it sorts itself out
   - b) Borrow even more to cover it
   - c) Talk to a trusted grown-up and look into free UK debt-help services ✅
   - d) Ignore letters from the lender
   - *Explanation:* Debt worries get easier the sooner they're shared. A trusted grown-up plus free UK debt-advice charities can help build a plan — asking for help early is the smart, brave choice.

7. **Scenario** · 20 XP — A friend says, 'Just get a credit card, max it out on a holiday, then sort the payments later — everyone does it.' What's the wisest response?
   - a) Do it — you only live once, and you'll figure out repayments somehow
     → Maxing out a card with no plan to repay is how debt spirals start. Interest piles up monthly and your credit score takes a hit. 'Sort it later' rarely works.
   - b) Pass for now, and only ever borrow what you've planned to repay — and ask a grown-up if unsure ✅
     → Spot on. Borrowing with a clear repayment plan you can afford keeps you in control. When a deal sounds too easy, slowing down and checking with a trusted grown-up protects you.
   - c) Get the card but never use it at all, just to copy your friend
     → Getting credit just because a friend said so isn't a plan. Decisions about borrowing should be yours, based on what you can afford — not peer pressure.

---

## Revenue, Costs & Profit  
`topic: entrepreneurship` · draft file: `level-rollout-drafts/entrepreneurship__revenue-costs-profit.md`

### Level 2 — Level 2 (free)

1. **Card** · 10 XP — *Profit margin: how much of each £ you keep*
   > Profit margin tells you how much of every pound you actually keep. If you sell something for £5 and it costs you £3 to make, your profit is £2. Your margin is £2 out of £5 — that's 40%. A bigger margin means more of each sale stays with you. Two stalls can both make sales, but the one with the better margin keeps more.

2. **Card** · 10 XP — *Break-even: the moment you stop losing money*
   > Before you make a profit, you first have to cover your costs. The break-even point is the number of items you need to sell just to get your money back — not a penny more, not a penny less. Say a stall costs you £20 to run, and you make £4 profit on each item. You break even after selling 5 items (5 × £4 = £20). Sale number 6 is where real profit begins.

3. **Quiz** · 25 XP — You sell a bracelet for £10. It costs you £6 to make. What is your profit margin?
   - a) 4%
   - b) 40% ✅
   - c) 60%
   - d) 100%
   - *Explanation:* Profit is £10 − £6 = £4. Your margin is £4 out of the £10 price = 40%. You keep 40p of every pound.

4. **Quiz** · 25 XP — It costs you £2 to make one candle, and you want £3 of profit on each one. What price should you charge?
   - a) £3
   - b) £2
   - c) £5 ✅
   - d) £1
   - *Explanation:* Price = cost + the profit you want = £2 + £3 = £5. Pricing below £5 wouldn't leave the £3 profit you wanted.

5. **Quiz** · 25 XP — Your stall costs £30 to run (a fixed cost). You make £2 profit on each badge after materials. How many badges must you sell to break even?
   - a) 10
   - b) 15 ✅
   - c) 30
   - d) 60
   - *Explanation:* Break-even = fixed cost ÷ profit per item = £30 ÷ £2 = 15 badges. After 15, every extra badge is real profit.

6. **Quiz** · 25 XP — Which stall keeps MORE of each pound it takes in?
   - a) Stall A: sells for £4, costs £3 to make
   - b) Stall B: sells for £4, costs £1 to make ✅
   - c) They keep the same amount
   - d) You can't compare margins
   - *Explanation:* Stall A keeps £1 of £4 (25%). Stall B keeps £3 of £4 (75%). Stall B has the bigger margin, so it keeps far more of every pound.

7. **Scenario** · 20 XP — You're planning a lemonade stall. Each cup costs you 50p to make, and the stall (your fixed cost) is £10 for the day. You decide to sell each cup for £1.50. How should you think about it?
   - a) I make £1 profit per cup, so I break even after 10 cups — then it's all profit ✅
     → Spot on. Profit per cup = £1.50 − 50p = £1. £10 fixed ÷ £1 = 10 cups to break even. Cup 11 onwards is real profit.
   - b) Every cup I sell is £1.50 of pure profit
     → Not quite. £1.50 is the price, not the profit. Each cup costs 50p to make, and you still have the £10 stall to cover first.
   - c) I should price each cup at 50p so it sells fast
     → At 50p you'd only just cover the cup's own cost and make £0 profit, never covering the £10 stall. A fair price needs to be above your cost.

### Level 3 — Level 3 (premium 🔒)

1. **Card** · 10 XP — *Profit isn't the same as cash in your pocket*
   > You can be profitable on paper but still short of cash right now. Imagine you sell £100 of cookies to a café, but they'll pay you next month. Meanwhile you spent £40 on ingredients today. Your profit will be £60 — but right now you're actually £40 out of pocket until the café pays. That gap between money earned and money actually in hand is called cash flow. Healthy businesses watch both.

2. **Card** · 10 XP — *Reinvesting: using profit to grow*
   > Reinvesting means putting some of your profit back into your business instead of spending it all. Made £50 profit selling bracelets? You could buy a bigger batch of beads so you can make more next time. Reinvesting can help you grow — but it's wise to keep some cash aside too, so a quiet week doesn't catch you out. It's a balance, not all-or-nothing.

3. **Quiz** · 25 XP — You sold £100 of goods, but the customer pays you next month. You spent £40 on supplies today. How much CASH do you actually have in hand right now?
   - a) £100
   - b) £60
   - c) −£40 (you're £40 out of pocket) ✅
   - d) £140
   - *Explanation:* The £100 hasn't arrived yet, but the £40 has already gone out. So right now you're £40 down on cash — even though your eventual profit will be £60. That's the difference between profit and cash flow.

4. **Quiz** · 25 XP — You made £50 profit. What does it mean to 'reinvest' some of it?
   - a) Spend it all on sweets as a treat
   - b) Put some back into the business — like buying more materials to sell more ✅
   - c) Hide it and never use it
   - d) Give all of it away
   - *Explanation:* Reinvesting means putting profit back in to help the business grow, such as buying more materials. Keeping some cash aside too is sensible.

5. **Quiz** · 25 XP — One craft stall makes you about £30 profit a day. You set up 3 similar stalls run by friends. Roughly how much profit a day might you expect (before any extra costs)?
   - a) About £30
   - b) About £90 ✅
   - c) About £10
   - d) About £300
   - *Explanation:* Three stalls each making about £30 is roughly 3 × £30 = £90 a day. That's the simple idea of scaling — doing more of what works. (In real life extra stalls bring extra costs too, so it's a rough guide.)

6. **Quiz** · 25 XP — Your end-of-day stall summary says: Revenue £120, Total costs £80. Did the stall make money, and how much profit?
   - a) Lost money, −£40
   - b) Made money, £40 profit ✅
   - c) Broke even, £0
   - d) Made money, £120 profit
   - *Explanation:* Profit = revenue − costs = £120 − £80 = £40. Revenue is bigger than costs, so the stall made a £40 profit.

7. **Scenario** · 20 XP — Your weekend stall summary reads: Revenue £200, Costs £140, Profit £60. But £50 of that £200 is still owed by customers who'll pay later — so you only have £10 actual cash in hand right now. A friend says 'spend the whole £60 profit on more stock for next week!' What's the wisest move?
   - a) Spend the full £60 on stock straight away
     → Careful: you only have £10 cash right now. £50 is still owed and hasn't arrived. Spending £60 you don't yet hold could leave you stuck if a customer pays late.
   - b) Reinvest a sensible amount from the cash you actually have, and wait for the £50 owed to arrive before spending it ✅
     → Wise. You separate profit (£60, on paper) from cash in hand (£10). Reinvest within what you really have, and grow as the money owed comes in.
   - c) Decide the stall failed because you only have £10 in hand
     → Not so. The stall made a real £60 profit; the £50 simply hasn't been paid yet. Once it arrives, your cash catches up with your profit.

---

## Your Side Hustle  
`topic: entrepreneurship` · draft file: `level-rollout-drafts/entrepreneurship__side-hustle.md`

### Level 2 — Level 2 (free)

1. **Card** · 10 XP — *Test before you build*
   > Before you spend time or money, find out if people actually want your thing. This is called testing your idea. Ask a few people: 'Would you buy this? What would you pay?' Even better — try to make one real sale. A 'yes, here's the money' tells you far more than ten people saying 'that sounds nice.' Real customers are the best teachers.

2. **Card** · 10 XP — *Your first customers are closest to home*
   > You don't need strangers to start. Your first customers are usually people who already know and trust you: family, neighbours, friends' parents, people at a club or school fair (always with a grown-up's help when money or strangers are involved). Do a brilliant job for a few people, and they'll tell others. That's word of mouth — the cheapest and most powerful advertising there is.

3. **Quiz** · 25 XP — What's the best way to find out if your side-hustle idea will work?
   - a) Spend all your savings on supplies first
   - b) Try to make a real sale to a real customer and see what happens ✅
   - c) Keep the idea secret until it's perfect
   - d) Wait until lots of other people are doing it
   - *Explanation:* A real sale is the strongest proof people want what you offer. Testing cheaply first means you learn fast without risking much.

4. **Quiz** · 25 XP — You're not sure what to charge for washing cars. What's a sensible way to set a fair price?
   - a) Pick the biggest number you can think of
   - b) Charge nothing so everyone likes you
   - c) Ask around what others charge locally and start somewhere fair ✅
   - d) Change your price every single customer
   - *Explanation:* Looking at what similar things cost nearby gives you a fair starting point. You can always adjust later — but free isn't a business, and wild prices scare customers off.

5. **Quiz** · 25 XP — A happy customer offers to tell their friends about your dog-walking. Why is that valuable?
   - a) It isn't — only paid adverts work
   - b) Word of mouth from a happy customer is trusted and costs you nothing ✅
   - c) It means you must lower your prices
   - d) It only matters if they post it online
   - *Explanation:* People trust a recommendation from someone they know more than any advert. Looking after your customers turns them into your best marketers — for free.

6. **Quiz** · 25 XP — What's the smartest 'advert' for a brand-new side hustle with no money?
   - a) A huge billboard in the city
   - b) A TV commercial
   - c) A simple flyer or a friendly word to people nearby (with a grown-up's help) ✅
   - d) Paying a celebrity
   - *Explanation:* Starting small and local costs little or nothing. Big, expensive adverts make no sense before you've proven people will buy.

7. **Scenario** · 20 XP — You want to start a baking side hustle. A friend says 'just buy loads of ingredients and packaging now — you'll definitely sell out!' What's the wisest first step?
   - a) Spend everything you have on ingredients and fancy boxes straight away
     → Risky. You don't yet know if people will buy or what they'll pay. Spending big before testing can leave you stuck with stock no one wants.
   - b) Bake a small batch, offer it to a few people you know (with a grown-up's help), and see if they buy ✅
     → Smart. A small, cheap test tells you whether there's real demand and what price feels right, before you risk much. Then you can grow with confidence.
   - c) Keep it secret and tell no one in case someone copies you
     → If nobody knows about it, nobody can buy it. Telling people is how a side hustle finds its first customers.

### Level 3 — Level 3 (premium 🔒)

1. **Card** · 10 XP — *Reputation is everything*
   > When you run anything, your reputation is what people say about you when you're not in the room. Doing a great job, being on time, and being honest make customers come back and recommend you. One brilliant experience can bring you three new customers; one broken promise can lose you ten. Treat every customer like you want them to tell their friends — because they will, either way.

2. **Card** · 10 XP — *Reinvest your time and earnings wisely*
   > A growing side hustle gives you two things back: a little money and a little experience. Smart founders reinvest some of it — maybe better supplies, a skill to learn, or simply more practice — instead of spending it all. And your time is precious too: don't take on so many customers that the quality slips or your schoolwork suffers. Growing steadily beats growing too fast and burning out.

3. **Quiz** · 25 XP — A customer's order goes wrong and it's your mistake. What builds the best reputation?
   - a) Pretend it didn't happen and hope they forget
   - b) Own up honestly, apologise, and put it right ✅
   - c) Blame the customer
   - d) Block them so they can't complain
   - *Explanation:* Honesty and fixing your mistakes turn an unhappy moment into trust. People remember how you handled a problem far more than the problem itself.

4. **Quiz** · 25 XP — Your side hustle is making a bit of money. What's a wise thing to do with some of it?
   - a) Spend every penny immediately
   - b) Reinvest some into better supplies or learning a useful skill ✅
   - c) Hide it and never use it for anything
   - d) Promise it to someone before you've earned it
   - *Explanation:* Putting some earnings back into your hustle (or your skills) helps it grow steadily. Reinvesting is how small things become bigger over time.

5. **Quiz** · 25 XP — You're getting more orders than you can handle alongside school. What's the healthiest move?
   - a) Stay up all night and let your schoolwork slide
   - b) Accept everything and let the quality drop
   - c) Manage your time — take what you can do well, and pause, raise prices, or get a grown-up's help to grow ✅
   - d) Quit completely with no warning to customers
   - *Explanation:* Protecting your time and the quality of your work keeps both your customers and your studies happy. Growing well means knowing your limits.

6. **Quiz** · 25 XP — A stranger online wants to buy from you and asks you to meet alone or share your home address. What should you do?
   - a) Go and meet them by yourself to make the sale
   - b) Share all your details so they trust you
   - c) Stop, and talk to a trusted grown-up before doing anything ✅
   - d) Keep it secret from your parents
   - *Explanation:* Your safety always comes before any sale. Never meet strangers alone or share personal details — bring a trusted grown-up into any deal with someone you don't know.

7. **Scenario** · 20 XP — A customer messages to say the bracelet you sold them broke after one day. They're upset. Your side hustle has a good reputation so far. What do you do?
   - a) Ignore the message and hope they go away
     → A customer you ignore tells everyone how you let them down. Silence is the fastest way to wreck the good reputation you built.
   - b) Reply honestly, apologise, and offer to repair or replace it ✅
     → Excellent. Owning the problem and putting it right keeps the customer's trust and protects your reputation. Honest businesses earn loyal customers and word-of-mouth recommendations.
   - c) Argue that it must be their fault and refuse to help
     → Even if you're unsure whose fault it is, being defensive loses the customer and the people they'll talk to. Care and honesty win in the long run.

---

## What is a REIT?  
`topic: real-estate` · draft file: `level-rollout-drafts/real-estate__reit.md`

### Level 2 — Level 2 (free)

1. **Card** · 10 XP — *Not just houses*
   > A REIT can own all sorts of property, not just homes. Some own shopping centres, some own warehouses where parcels are stored, some own office blocks, hospitals, or even mobile-phone towers. Different REITs focus on different types — so when you pick one, it helps to know what kind of property is actually inside it.

2. **Card** · 10 XP — *Why REITs pay out so much*
   > REITs have a special deal with the rules: to count as a REIT, they must hand out most of their rental profit to shareholders (in the UK it's at least 90%). That regular payout is called a dividend. It's the main reason people who like steady income are drawn to REITs.

3. **Quiz** · 25 XP — Which of these could a REIT own?
   - a) Only family houses
   - b) Shopping centres, warehouses, and offices ✅
   - c) Only things you can hold in your hand
   - d) Only cash in a bank
   - *Explanation:* REITs can own many kinds of income-producing property — shops, warehouses, offices and more — not just houses.

4. **Quiz** · 25 XP — REITs must hand out most of their rental profit to shareholders. What is that regular payment called?
   - a) A dividend ✅
   - b) A deposit
   - c) A loan
   - d) A fee
   - *Explanation:* Money a REIT pays out to its shareholders from rental profit is called a dividend — the main attraction for income-seekers.

5. **Quiz** · 25 XP — A single REIT owns 200 different buildings rented to lots of different businesses. Why can that be helpful?
   - a) If one building sits empty, the rent from the others can help balance it out ✅
   - b) It means the REIT can never lose value
   - c) It guarantees the dividend will always go up
   - d) It means you own all 200 buildings yourself
   - *Explanation:* Owning many buildings spreads the risk — one empty shop won't sink everything. That's a kind of diversification inside a single REIT. (It still isn't risk-free.)

6. **Quiz** · 25 XP — How do most ordinary investors actually buy a piece of a REIT?
   - a) They buy and sell its shares on the stock market, like any other share ✅
   - b) They have to buy a whole building themselves
   - c) They post cash directly to the buildings
   - d) They can only inherit it
   - *Explanation:* A REIT is listed on the stock market, so you buy and sell its shares just like any other company's — no need to own a whole building.

7. **Scenario** · 20 XP — You've found a REIT and you like that it pays a dividend. Before putting in any pretend money in the Simulator, what's the smart move?
   - a) Buy straight away because dividends mean free money
     → Careful — dividends aren't free money, and the share price can still fall. It's worth understanding what you're buying first.
   - b) Check what kind of property it actually owns and chat it through with a trusted grown-up ✅
     → Great thinking — knowing whether it owns shops, offices or warehouses tells you a lot, and a trusted grown-up can help you make sense of it.
   - c) Pick it only because an online video shouted that it's a winner
     → Be wary — loud online tips are often hype or scams. Learn what's inside it and practise safely first.

### Level 3 — Level 3 (premium 🔒)

1. **Card** · 10 XP — *Reading the dividend yield*
   > The 'dividend yield' is a quick way to compare REITs: it's the yearly dividend shown as a percentage of the share price. A REIT priced at £10 paying 40p a year has a 4% yield. A very high yield can look exciting, but it sometimes means investors are worried — so a big number isn't automatically a good number.

2. **Card** · 10 XP — *REITs borrow money, and rates matter*
   > Most REITs borrow money to buy their properties, a bit like a mortgage. When interest rates rise, that borrowing costs more, which can squeeze profits and push share prices down. This is why REIT prices often wobble when the news talks about interest rates changing.

3. **Quiz** · 25 XP — A REIT's share price is £10 and it pays 50p in dividends a year. What is its dividend yield?
   - a) 50%
   - b) 5% ✅
   - c) 0.5%
   - d) £10
   - *Explanation:* Yield = yearly dividend ÷ share price. 50p ÷ £10 = 0.05 = 5%.

4. **Quiz** · 25 XP — One REIT has an unusually high dividend yield compared with similar ones. What's the wise way to read that?
   - a) It's guaranteed to be the best choice
   - b) It might be a warning sign that investors are worried, so it's worth looking closer ✅
   - c) High yield always means no risk
   - d) Yield tells you nothing at all
   - *Explanation:* A very high yield can be a red flag, not a prize — sometimes the price has dropped because people are worried. Always look deeper rather than chasing the biggest number.

5. **Quiz** · 25 XP — Why can rising interest rates be tough for REITs?
   - a) They make rent illegal
   - b) REITs often borrow to buy property, so higher rates make that borrowing cost more ✅
   - c) They force REITs to give properties away
   - d) They have no effect on REITs at all
   - *Explanation:* Because REITs usually borrow to fund their buildings, higher interest rates raise their costs and can weigh on profits and share prices.

6. **Quiz** · 25 XP — A sensible investor sees REITs as…
   - a) The only thing anyone should ever own
   - b) One useful slice of a wider mix that might also include shares, funds and savings ✅
   - c) A way to get rich by tomorrow
   - d) A risk-free replacement for a savings account
   - *Explanation:* REITs can be a helpful part of a diversified mix, but leaning everything on one type of investment is risky. Spreading across different kinds is the calmer path.

7. **Scenario** · 20 XP — In the Simulator you have £200 of pretend money and you're interested in property. Two REITs catch your eye: one with a steady 4% yield owning warehouses, and one with a flashy 12% yield you don't really understand. What's the wisest approach?
   - a) Pour it all into the 12% one because the number is biggest
     → Risky — an unusually high yield can be a warning sign, and putting everything into one thing you don't understand is the opposite of careful.
   - b) Spread some across the steadier REIT and the rest elsewhere, and ask a trusted grown-up to help you understand the high-yield one ✅
     → Wise — you diversify, you don't chase a number you can't explain, and you get help understanding it before risking anything.
   - c) Buy and sell every day to chase the dividend
     → That's trying to time the market — stressful, unreliable, and it usually loses to patiently staying invested.

---

## Diversification  
`topic: risk` · draft file: `level-rollout-drafts/risk__diversification.md`

### Level 2 — Level 2 (free)

1. **Card** · 10 XP — *There's more than one kind of risk*
   > Risk isn't just one thing. 'Company-specific risk' is the danger that one business does badly — maybe its product flops. 'Market risk' is when lots of investments fall together, like during a downturn. Diversifying across many companies helps with company-specific risk, but market risk affects almost everyone at once. Knowing the difference helps you understand what you can and can't protect against.

2. **Card** · 10 XP — *Risk isn't only about losing money*
   > Two sneaky risks don't look scary but matter a lot. Inflation risk is when prices rise faster than your money grows — £10 today may buy less in ten years, so cash sitting still can quietly lose value. Liquidity risk is not being able to turn something into cash quickly when you need it (a house can't be sold in a day). Good plans think about all of these, not just 'will it crash?'.

3. **Quiz** · 25 XP — A company you invested in has a bad year, but the rest of the market is fine. What type of risk is this an example of?
   - a) Company-specific risk ✅
   - b) Inflation risk
   - c) Liquidity risk
   - d) No risk at all
   - *Explanation:* When trouble hits just one business while others are fine, that's company-specific risk — the kind diversification helps reduce most.

4. **Quiz** · 25 XP — Why can keeping ALL your money as cash for many years still be risky?
   - a) Banks always lose your money
   - b) Inflation can make that cash buy less over time ✅
   - c) Cash is the riskiest thing of all
   - d) Cash earns the highest returns
   - *Explanation:* This is inflation risk. Cash feels safe, but if prices rise faster than your savings grow, your money slowly buys less. That's why people invest some money for the long term.

5. **Quiz** · 25 XP — You'll need your money in 6 months to buy something important. Where does it make most sense to keep it?
   - a) All in one exciting stock
   - b) In a savings account, where the value won't suddenly drop ✅
   - c) Spread across lots of risky shares
   - d) In something you can't sell for years
   - *Explanation:* Money you need soon should be kept somewhere steady. Shares can fall right when you need them — a short time horizon means lower risk is sensible.

6. **Quiz** · 25 XP — What does 'time horizon' mean when deciding how much risk to take?
   - a) How many companies you own
   - b) How long until you'll actually need the money ✅
   - c) What time the stock market opens
   - d) How old a company is
   - *Explanation:* Your time horizon is how long you can leave money invested. Longer horizons can usually handle more ups and downs, because there's time to recover.

7. **Scenario** · 20 XP — You've saved £200. You want to start investing, but you don't have any spare money set aside for emergencies (like a broken phone or an unexpected trip). What's the wisest first move?
   - a) Invest all £200 right away, emergencies can wait
     → Risky. If something unexpected happens, you might have to sell investments at a bad time. Most sensible plans build a small emergency fund first.
   - b) Set some aside as an emergency fund, then invest the rest ✅
     → Smart. An emergency fund is money kept safe and easy to reach. With that cushion in place, you can invest the rest without panic if life surprises you.
   - c) Spend it all now so there's nothing to risk
     → Spending it isn't a plan — that money can't grow or protect you later. Saving a cushion and investing the rest is the balanced move.

### Level 3 — Level 3 (premium 🔒)

1. **Card** · 10 XP — *Risk tolerance vs risk capacity*
   > These sound the same but aren't. Risk tolerance is how comfortable you feel when investments wobble — some people stay calm, others lose sleep. Risk capacity is how much risk you can actually afford to take, based on your money and how soon you need it. A wise plan respects both: never take more risk than you can handle emotionally or financially. Grown-ups think about both before deciding.

2. **Card** · 10 XP — *Bonds: the steadier teammate*
   > Shares can grow a lot but bounce around. A bond is more like lending money to a company or government that promises to pay you back with a little interest — usually steadier, but with smaller growth. Many people mix shares and bonds so the steadier part cushions the bumpy part. Mixing different types of investment, not just different companies, is diversification at the next level.

3. **Quiz** · 25 XP — Jordan can afford to invest for 20 years but feels sick whenever prices drop. What's the best description?
   - a) High risk capacity, low risk tolerance ✅
   - b) Low risk capacity, high risk tolerance
   - c) No risk at all
   - d) Jordan should borrow money to invest
   - *Explanation:* Jordan can afford long-term risk (high capacity) but doesn't cope well emotionally with drops (low tolerance). A good plan respects the lower of the two so Jordan can stick with it.

4. **Quiz** · 25 XP — The market drops 20% in a month and the news is gloomy. For a long-term investor, what's usually the wisest reaction?
   - a) Sell everything immediately to stop the loss
   - b) Stay calm and stick to the long-term plan ✅
   - c) Borrow money to buy ten times as much
   - d) Check the price every five minutes
   - *Explanation:* Ups and downs (volatility) are normal. Selling in a panic often locks in losses. For someone with a long time horizon, staying calm and patient usually wins.

5. **Quiz** · 25 XP — Over time, your shares grow so much that they're now a much bigger slice of your money than you planned. Selling a little and topping up your steadier investments to get back to your target mix is called…
   - a) Rebalancing ✅
   - b) Day trading
   - c) Inflation
   - d) Going all in
   - *Explanation:* Rebalancing means gently adjusting back to your planned mix so one part doesn't grow too risky. It's a calm, routine habit — not a reaction to hype.

6. **Quiz** · 25 XP — How does buying insurance (like for a phone or a bike) relate to managing risk?
   - a) It's a way to invest in the stock market
   - b) It moves the cost of a rare, expensive problem off you for a small regular payment ✅
   - c) It guarantees your investments will grow
   - d) It removes all risk from your life
   - *Explanation:* Insurance is risk transfer — you pay a little regularly so a big unexpected cost doesn't fall entirely on you. It's another everyday tool people use to handle risk, alongside diversifying and saving.

7. **Scenario** · 20 XP — An online video promises 'guaranteed 50% returns every month — no risk!' if you move all your savings into it today. What do you do?
   - a) Move everything in fast before the chance disappears
     → A huge warning sign. 'Guaranteed high returns, no risk' doesn't exist — higher reward always comes with higher risk. Pressure to act now is a classic scam tactic.
   - b) Stop, stay sceptical, and talk to a trusted grown-up first ✅
     → Exactly right. 'No risk, huge guaranteed returns' is a red flag for a scam. Slowing down and asking a trusted adult protects you from get-rich-quick traps.
   - c) Put in just half — that seems safer
     → Still risky. The problem isn't the amount, it's the promise. Anything claiming guaranteed big returns with no risk is not to be trusted at all.

---

## Compound Interest  
`topic: savings` · draft file: `level-rollout-drafts/savings__compound-interest.md`

### Level 2 — Level 2 (free)

1. **Card** · 10 XP — *How often does it compound?*
   > Not all interest is added once a year. Some accounts add interest every month, or even every day. The more often interest is added (or 'compounded'), the more often your interest starts earning its own interest. So two accounts with the same rate can grow by slightly different amounts depending on how often they pay.

2. **Card** · 10 XP — *The magic trick: the Rule of 72*
   > Here's a handy shortcut grown-ups use. Divide 72 by the interest rate to roughly guess how many years it takes for your money to DOUBLE. At 6% interest, 72 ÷ 6 = 12 years to double. It's only an estimate, but it's a brilliant way to picture how powerful a rate really is.

3. **Quiz** · 25 XP — Two accounts both pay 5% a year. Account A adds the interest once a year; Account B adds a little bit every month. Which grows slightly more?
   - a) Account A (once a year)
   - b) Account B (a little every month) ✅
   - c) They grow exactly the same
   - d) Neither — frequency never matters
   - *Explanation:* Adding interest more often means your interest starts earning its own interest sooner, so Account B ends up a tiny bit ahead — even at the same rate.

4. **Quiz** · 25 XP — Using the Rule of 72, roughly how many years would it take to double your money at 8% interest?
   - a) About 3 years
   - b) About 9 years ✅
   - c) About 36 years
   - d) It never doubles
   - *Explanation:* 72 ÷ 8 = 9, so it takes roughly 9 years to double. The Rule of 72 is just a quick estimate, not exact maths.

5. **Quiz** · 25 XP — Instead of saving once, Maya adds £10 every month to her account. What happens to the compounding?
   - a) Only her very first £10 ever earns interest
   - b) Each new deposit also starts earning interest, so the whole pot keeps growing ✅
   - c) Adding money regularly stops interest being paid
   - d) Compounding only works if you never add more
   - *Explanation:* Every deposit you add joins the pot and starts earning its own interest. Saving regularly gives compounding even more to work with.

6. **Quiz** · 25 XP — Using the Rule of 72, which rate would double your money the FASTEST?
   - a) 2% a year
   - b) 4% a year
   - c) 9% a year ✅
   - d) They all double at the same speed
   - *Explanation:* 72 ÷ 9 = 8 years, much faster than 72 ÷ 2 = 36 years. A higher rate doubles your money in fewer years.

7. **Scenario** · 20 XP — You spot an account online promising to 'DOUBLE your money in just 3 months, guaranteed!' Using what you know about realistic interest rates, what should you do?
   - a) Send your savings straightaway before the offer ends
     → Please don't. 'Double in 3 months, guaranteed' is a classic scam — real compound interest takes years, not months. Money sent to scams is usually gone for good.
   - b) Be very suspicious and ask a trusted grown-up before doing anything ✅
     → Exactly right. Real savings grow slowly and steadily. Promises of fast, guaranteed doubling are almost always scams — always check with a trusted grown-up first.
   - c) Borrow money from a friend so you can put in even more
     → Never borrow to chase an offer like this. Borrowing for a too-good-to-be-true deal turns one bad idea into two.

### Level 3 — Level 3 (premium 🔒)

1. **Card** · 10 XP — *Compounding can work AGAINST you too*
   > Compound interest is brilliant when it's growing your savings. But it works the same way on money you OWE. If someone borrows money and doesn't pay it back, the interest piles up on the interest — and the debt can snowball quickly. The same force that grows savings can grow a debt, so borrowing always needs care.

2. **Card** · 10 XP — *The quiet thief: inflation*
   > Prices slowly rise over time — a chocolate bar costs more than it did when your parents were young. That's called inflation. If your savings earn 2% but prices rise 3%, your money actually buys a little LESS each year. Smart savers look for a rate that at least keeps up with rising prices, so their money doesn't quietly shrink in value.

3. **Quiz** · 25 XP — Why do grown-ups warn that an unpaid debt can 'snowball'?
   - a) Because the interest can pile up on top of interest, just like savings — but it makes what you owe bigger ✅
   - b) Because debts always get smaller on their own over time
   - c) Because borrowing money never costs anything
   - d) Because interest only ever helps the borrower
   - *Explanation:* Compounding doesn't care which direction it works. On a debt, interest builds on interest and what you owe can grow fast — which is why unpaid debt is risky.

4. **Quiz** · 25 XP — Your savings earn 2% a year, but prices are rising by 3% a year. What's really happening to your money's buying power?
   - a) It's growing quickly
   - b) It's slowly shrinking — your money buys a little less each year ✅
   - c) Nothing changes at all
   - d) Prices don't affect savings
   - *Explanation:* If prices rise faster than your interest rate, your money buys less over time. Beating inflation is why the rate you earn really matters.

5. **Quiz** · 25 XP — In the UK, a Junior ISA lets savings grow without paying tax on the interest. Why is that good for compounding?
   - a) It means you can never take the money out
   - b) More of your interest stays in the pot to earn its own interest ✅
   - c) It removes all risk completely
   - d) It makes interest rates go up
   - *Explanation:* If tax isn't taken from your interest, more of it stays invested — and that extra amount keeps compounding year after year.

6. **Quiz** · 25 XP — Two friends each save the same amount at the same rate. Sam starts at 15; Alex starts at 25. Years later, who is likely to have MORE — and why?
   - a) Alex, because starting later is always better
   - b) Sam, because those extra 10 years gave compounding much more time to work ✅
   - c) They'll have exactly the same
   - d) Whoever checks their account most often
   - *Explanation:* Time is compounding's superpower. Sam's extra decade lets interest build on interest for far longer, often beating someone who started later — even with the same deposits.

7. **Scenario** · 20 XP — You've got £200 of birthday money you won't need for years. A grown-up offers to help you open a tax-free Junior ISA savings account. What's the wisest move?
   - a) Spend it all now while you can
     → Spending it all means zero growth. There's nothing wrong with treating yourself a little, but money you won't need for years could be quietly growing instead.
   - b) Open the tax-free account with a trusted grown-up and leave it to grow for years ✅
     → Smart thinking. A tax-free account means more of your interest stays in to compound, and giving it years lets that snowball really build. Doing it WITH a trusted grown-up keeps it safe.
   - c) Hide the cash in a drawer so it's 'safe'
     → Cash in a drawer earns no interest at all — and inflation slowly shrinks what it can buy. It feels safe, but it quietly loses value over time.

---

## Your First Paycheque  
`topic: taxes` · draft file: `level-rollout-drafts/taxes__first-paycheque.md`

### Level 2 — Level 2 (free)

1. **Card** · 10 XP — *Where your deductions actually go*
   > On Level 1 you met the names on a payslip. Here's where the money goes: Income Tax and National Insurance are sent to HMRC (the government's tax office) to pay for shared things like the NHS and the state pension. A pension deduction isn't a tax at all — it's YOUR own money being saved for your future. So your deductions split two ways: money that leaves for good (tax, NI) and money that's still yours, just locked away for later (pension).

2. **Card** · 10 XP — *Your tax code and 'YTD': the small print*
   > A payslip has a few extra clues. Your tax code (like 1257L) tells your employer how much you can earn before Income Tax starts — get the wrong code and you might pay too much or too little. YTD means 'year to date': the running total of what you've earned and paid since the tax year began (6 April). And by law you should get a payslip every payday — keep them, they're proof of what you earned.

3. **Quiz** · 25 XP — On your payslip, which deduction is actually YOUR own savings rather than money sent to the government?
   - a) Income Tax
   - b) National Insurance
   - c) Your pension contribution ✅
   - d) The 'net pay' line
   - *Explanation:* Income Tax and National Insurance go to HMRC. Your pension contribution is your own money being saved for your future — it's still yours, just put away for later.

4. **Quiz** · 25 XP — A payslip shows 'YTD' next to some numbers. What does YTD mean?
   - a) 'Year to date' — the running total since the tax year started ✅
   - b) 'Yesterday's total deductions'
   - c) 'Your tax discount'
   - d) 'Yearly take-home difference'
   - *Explanation:* YTD means 'year to date' — it adds up everything you've earned and paid in deductions since the tax year began on 6 April.

5. **Quiz** · 25 XP — Many workplaces automatically sign you up to a pension when you start a job. What is this called?
   - a) Auto-enrolment ✅
   - b) A tax refund
   - c) Overtime
   - d) A bonus scheme
   - *Explanation:* Auto-enrolment means you're automatically put into a workplace pension when you start. You can opt out, but you'd give up your employer's contribution — so most people stay in.

6. **Quiz** · 25 XP — Mia earns £9 an hour and works 10 hours. Her gross pay is £90. Deductions come to £18. What is her net (take-home) pay?
   - a) £90
   - b) £108
   - c) £72 ✅
   - d) £18
   - *Explanation:* Net pay = gross pay − deductions. £90 − £18 = £72. The £18 covers things like NI and pension; the £72 is what lands in her bank.

7. **Scenario** · 20 XP — It's your first part-time job and your first payslip looks confusing — there's a tax code, some YTD numbers, and deductions you didn't expect. What's the sensible thing to do?
   - a) Bin it — payslips don't matter once you've been paid
     → Not wise. Your payslip is proof of what you earned and what was deducted. Keep every one safe; you may need them later.
   - b) Look it over, and ask a trusted grown-up to help you check the tax code and deductions make sense ✅
     → Great move. Reading your payslip and checking it with someone you trust helps you spot a wrong tax code or an error early — and you learn what every line means.
   - c) Assume it's wrong and refuse to work again
     → Deductions are normal and required by law. If something genuinely looks off, the calm step is to ask a grown-up or your employer, not to give up.

### Level 3 — Level 3 (premium 🔒)

1. **Card** · 10 XP — *Pay yourself first*
   > Most people spend, then save whatever's left — and usually nothing's left. Flip it: the moment your net pay lands, move a small slice into savings BEFORE you spend anything. That's 'paying yourself first'. Even £1 in every £10 (10%) adds up, and because it happens first, you never miss it. Some people even set up an automatic transfer on payday so the choice is made for them.

2. **Card** · 10 XP — *Build a buffer, then beware 'lifestyle creep'*
   > A small emergency buffer — a bit of savings for surprises like a broken phone — means one unlucky week doesn't wreck your month. Once that's growing, watch out for 'lifestyle creep': when your pay rises and your spending quietly rises to match, so you're earning more but saving nothing. The trick when your pay goes up is to lift your saving at least as much as your spending.

3. **Quiz** · 25 XP — What does 'pay yourself first' mean?
   - a) Spend on yourself before paying any bills
   - b) Move some money into savings as soon as you're paid, before spending ✅
   - c) Ask your employer to pay you before your colleagues
   - d) Only save the coins left at the end of the month
   - *Explanation:* 'Pay yourself first' means saving a slice the moment you're paid — before spending — so saving actually happens instead of relying on leftovers.

4. **Quiz** · 25 XP — You get a pay rise, and straight away you upgrade your phone plan, buy more takeaways, and end up saving nothing extra. What is this called?
   - a) Lifestyle creep ✅
   - b) Compound interest
   - c) Auto-enrolment
   - d) Gross pay
   - *Explanation:* Lifestyle creep is when spending rises to match a higher income, so you earn more but don't save more. Lifting your saving when your pay rises keeps it in check.

5. **Quiz** · 25 XP — Why is having a small 'emergency buffer' of savings a smart habit?
   - a) So a surprise cost doesn't force you to borrow or panic ✅
   - b) Because the government doubles your buffer
   - c) So you never have to pay any tax
   - d) Because it makes your gross pay bigger
   - *Explanation:* An emergency buffer means an unexpected cost — like a broken phone — is just an annoyance, not a crisis, and you avoid borrowing at high interest.

6. **Quiz** · 25 XP — Your net pay is £200 this month and you decide to 'pay yourself first' at 10%. How much goes straight into savings?
   - a) £2
   - b) £10
   - c) £20 ✅
   - d) £200
   - *Explanation:* 10% of £200 is £20. Moving that £20 into savings first — before spending — is paying yourself first. The other £180 is yours to budget.

7. **Scenario** · 20 XP — Your first month's wages have landed. You want to be sensible but also enjoy your money. What's the smartest plan?
   - a) Spend it all now — there'll be more next month
     → Risky. Spending everything leaves nothing for surprises, and the habit sticks. A surprise cost would then mean borrowing.
   - b) Move a small slice to savings first, keep a little buffer for emergencies, then enjoy the rest — and ask a grown-up to help you set it up ✅
     → Brilliant balance. Pay yourself first, build a buffer, then spend the rest guilt-free. Setting up an automatic transfer with a trusted grown-up makes it effortless.
   - c) Put every single penny into savings and never spend any of it
     → Saving matters, but you're allowed to enjoy money you earned. The healthy habit is balance — save some, buffer some, enjoy some — not all-or-nothing.

---

## How Taxes Work  
`topic: taxes` · draft file: `level-rollout-drafts/taxes__how-taxes-work.md`

### Level 2 — Level 2 (free)

1. **Card** · 10 XP — *Income tax isn't the only tax*
   > Income tax is just one of many. The government also collects tax when you spend money (VAT), when you earn money in other ways, and through National Insurance. Most adults pay several different taxes without even noticing. Learning the main ones helps you understand the true cost of things — and where that money goes.

2. **Card** · 10 XP — *VAT: the tax hidden in the price*
   > VAT (Value Added Tax) is added to the price of most things you buy — toys, games, clothes for older kids, eating out. The price on the shelf usually already includes it, so you don't see it as a separate line. The standard rate is 20% (for example, on a £12 toy, about £2 is VAT). Some things have no VAT at all, like most food in the supermarket and children's clothes — which keeps everyday basics cheaper.

3. **Quiz** · 25 XP — What is VAT?
   - a) A tax added to the price of most things you buy ✅
   - b) A discount shops give to children
   - c) Money the government pays you for shopping
   - d) A type of savings account
   - *Explanation:* VAT (Value Added Tax) is a tax on spending. It's usually built into the price you see, so a chunk of what you pay on many items goes to the government.

4. **Quiz** · 25 XP — Which of these would normally have NO VAT added in the UK?
   - a) A video game console
   - b) Most basic food in a supermarket ✅
   - c) A meal at a restaurant
   - d) A cinema ticket
   - *Explanation:* Most everyday food in shops is 'zero-rated' for VAT, and so are children's clothes. This helps keep essentials affordable for families.

5. **Quiz** · 25 XP — National Insurance (NI) is a tax workers and employers pay. What does it mainly help fund?
   - a) The state pension and the NHS ✅
   - b) Only the person's own bank account
   - c) Football stadiums
   - d) Nothing — it's just kept as a fee
   - *Explanation:* NI is a tax that helps pay for things like the state pension and the NHS. (You'll see how it appears on a payslip in the 'Your First Paycheque' module — here we just learn what it's for.)

6. **Quiz** · 25 XP — Which of these is usually paid for by taxes?
   - a) The NHS, schools, and roads ✅
   - b) Your family's weekly shopping
   - c) A friend's birthday present
   - d) Pocket money from your parents
   - *Explanation:* Taxes fund shared services everyone can use — the NHS, state schools, roads, police, fire services, libraries and more. Personal spending like presents and pocket money comes out of your own money, not tax.

7. **Scenario** · 20 XP — You buy a £10 toy and the receipt says 'includes VAT £1.67'. Your little sister says 'the shop is stealing some of your money!' What's the best thing to say?
   - a) You're right, let's complain to the shop.
     → Not quite. The shop isn't taking it for themselves — VAT is a tax that's collected at the till and passed on to the government to help pay for shared things like hospitals and schools.
   - b) That's VAT — a tax built into the price that helps pay for things like hospitals and schools. ✅
     → Spot on! VAT is included in most prices. The shop collects it and sends it to the government. It's normal, and it's the law.
   - c) Receipts are always wrong, ignore it.
     → Receipts are usually correct. The VAT line just shows how much of the price was tax — a handy way to see the hidden cost of things.

### Level 3 — Level 3 (premium 🔒)

1. **Card** · 10 XP — *Why 'progressive' tax tries to be fair*
   > A 'progressive' tax means people who earn more pay a higher rate on the extra they earn — not on everything. Think of income split into slices: the first slice is tax-free, the next slice is taxed at a lower rate, and only the highest slices are taxed more. The idea is that those who can afford to contribute more, do — while a tax-free slice protects people on lower incomes. Whether that balance is 'fair' is something adults genuinely debate.

2. **Card** · 10 XP — *Tax and benefits: a two-way street*
   > Tax money doesn't just disappear — it flows back out as things the country needs and as support for people who need it: the NHS when you're poorly, schools, the state pension for older people, and help for families having a hard time. So tax is a bit like everyone putting into a shared pot, and the pot paying for things no single person could buy alone.

3. **Quiz** · 25 XP — In a progressive tax system, what happens when someone earns a bit more and moves into a higher band?
   - a) Only the extra money in the higher band is taxed at the higher rate ✅
   - b) Their entire income is suddenly taxed at the higher rate
   - c) They stop paying any tax at all
   - d) They have to pay last year's tax again
   - *Explanation:* Only the slice of income inside each band is taxed at that band's rate. Earning more always means more take-home pay — moving up a band never makes you worse off overall.

4. **Quiz** · 25 XP — How are taxes and 'benefits' (government support) connected?
   - a) Tax money is collected, then some of it is paid back out as support and services ✅
   - b) They have nothing to do with each other
   - c) Benefits are paid for by shops, not tax
   - d) Everyone gets exactly back what they paid in
   - *Explanation:* It's a two-way flow. Taxes fill a shared pot; that pot funds services for everyone and extra support for people who need it. It's not a personal savings account — it's shared.

5. **Quiz** · 25 XP — People disagree about the 'fairest' way to tax. Which statement is true?
   - a) There's one correct answer everyone agrees on
   - b) It's a genuine debate — thoughtful people weigh it up differently ✅
   - c) Only the government's opinion matters
   - d) Tax fairness can be proved with a single sum
   - *Explanation:* Reasonable people disagree about how much different earners should pay and what tax should fund. Understanding the trade-offs matters more than picking a 'winning' side — and it's a great thing to discuss with a grown-up.

6. **Quiz** · 25 XP — What does being a responsible taxpayer mean?
   - a) Paying the tax you genuinely owe, honestly and on time ✅
   - b) Hiding earnings so you never pay anything
   - c) Paying tax only if someone is watching
   - d) Refusing to pay because you don't like it
   - *Explanation:* Paying your fair share honestly keeps the shared services running for everyone. Deliberately hiding income to dodge tax is illegal and unfair on others. If tax ever feels confusing, that's normal — a trusted adult or the official HMRC guidance can help.

7. **Scenario** · 20 XP — Imagine you're older and doing weekend work. A neighbour offers to pay you in cash and says 'don't tell anyone, then neither of us pays any tax on it.' What's the wise response?
   - a) Great, free money!
     → Hiding earnings to avoid tax is illegal, even when it's cash. It might feel like a win, but it can land both people in trouble and it's unfair on everyone who pays their share.
   - b) I'll keep things honest and check with a grown-up about how tax works for my earnings. ✅
     → Wise choice. Being honest about what you earn is the right thing to do, and a trusted adult can help you understand whether you even owe anything (often, under the Personal Allowance, young earners don't).
   - c) I'll just decide the tax rules don't apply to me.
     → Tax rules apply to everyone, whatever their age. The good news is that low earnings are often below the tax-free allowance anyway — so honesty usually costs you nothing and keeps you safe.

---

