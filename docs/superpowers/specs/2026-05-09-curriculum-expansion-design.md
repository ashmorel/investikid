# Plan 7: Curriculum Expansion

## Goal

Expand the lesson library from 3 modules (7 lessons) to 12 modules (~49 lessons) covering six topic areas. No new code — seed data only.

## Scope

- Modify one file: `backend/app/seed/content.py`
- Add 9 new modules with ~42 new lessons
- All lessons use existing types: `card`, `quiz`, `scenario` (no `video` in this batch)
- All modules are free (`is_premium: False`)
- Seed function remains idempotent — safe to re-run

## Content Design Principles

**Progression per module:** teach → test → apply
1. Cards (1-2) introduce the concept in plain language
2. Quizzes (1-2) test understanding with multiple choice + explanations
3. Scenarios (1-2, in deeper modules) pose "what would you do?" situations with outcome feedback

**XP rewards** (matching existing pattern):
- Card: 10 XP
- Quiz: 25 XP
- Scenario: 20 XP

**Tone:** Conversational, UK-friendly (£, "paycheque", "colour"). Age-appropriate for 12-18. No condescension — explain like a smart older sibling.

**Content format:** Each lesson is a Python dict in the seed file following the existing `_MODULES` pattern. The `content_json` field structure depends on type:
- `card`: `{ "title": str, "body": str }`
- `quiz`: `{ "question": str, "choices": [str], "answer_index": int, "explanation": str }`
- `scenario`: `{ "prompt": str, "choices": [{ "label": str, "outcome": str }], "correct_index": int }`

## Curriculum

### Existing Modules (unchanged)

| # | Module | Topic | Lessons |
|---|--------|-------|---------|
| 1 | What is a Stock? | stocks | 3 |
| 2 | Compound Interest Basics | savings | 2 |
| 3 | What is a REIT? | real_estate | 2 |

### New Modules

#### Module 4: Budgeting Basics (topic: `budgeting`, 6 lessons)

1. **Card** — "What is a budget?"
   - Income vs expenses, why tracking matters, a budget is a plan for your money.

2. **Card** — "The 50/30/20 rule"
   - 50% needs (rent, food, transport), 30% wants (fun, hobbies), 20% savings. Simple starting framework.

3. **Quiz** — "Categorise these expenses"
   - Question: categorise rent, concert tickets, groceries, new trainers, savings deposit.
   - Tests understanding of needs/wants/savings split.

4. **Scenario** — "You get £200/month allowance"
   - Choices: spend it all on fun / split 50-30-20 / save it all. Outcome feedback on each approach.

5. **Quiz** — "Spot the budget mistake"
   - Shows a monthly budget where spending exceeds income. Student identifies the problem.

6. **Scenario** — "Phone screen cracks"
   - Unexpected expense. Choices: dip into savings / borrow from a friend / ignore it. Teaches emergency funds.

#### Module 5: Needs vs Wants (topic: `budgeting`, 3 lessons)

1. **Card** — "The difference isn't always obvious"
   - Internet might be a need, Netflix is a want. Context matters. Grey areas exist.

2. **Quiz** — "Need or want?"
   - Categorise 5 items: school uniform, latest phone, bus pass, takeaway coffee, toothpaste.

3. **Scenario** — "Festival vs laptop"
   - Friends want to go to a music festival (£150) but you're saving for a laptop. Trade-off thinking.

#### Module 6: Risk & Diversification (topic: `risk`, 6 lessons)

1. **Card** — "What is investment risk?"
   - Chance of losing money. Volatility. Value can go down as well as up.

2. **Card** — "Don't put all your eggs in one basket"
   - Diversification = spreading money across different investments. Reduces impact of one failing.

3. **Quiz** — "Which portfolio is more diversified?"
   - Compare three portfolios: all in one stock / two stocks same sector / mix of stocks, bonds, property.

4. **Scenario** — "Your friend's hot stock tip"
   - Friend says put everything in one company. Choices: go all in / invest a small amount / research first.

5. **Quiz** — "Risk vs reward"
   - Match investment types to risk levels: savings account (low), index fund (medium), single stock (high).

6. **Scenario** — "Build a simple portfolio"
   - You have £1,000. Choose how to split across stocks, bonds, and savings. Outcome feedback on balance.

#### Module 7: What is Crypto? (topic: `crypto`, 5 lessons)

1. **Card** — "Digital money on a shared ledger"
   - Blockchain basics: a public record of transactions. No bank in the middle. Bitcoin was the first.

2. **Card** — "Why is crypto so volatile?"
   - No earnings or dividends to anchor value. Price driven by speculation and sentiment. Can drop 50% in weeks.

3. **Quiz** — "True or false about crypto"
   - Test common misconceptions: crypto is anonymous (mostly false), crypto is guaranteed to go up (false), blockchain has uses beyond money (true).

4. **Scenario** — "Classmate says crypto is guaranteed money"
   - Choices: invest your savings / ask what evidence they have / research independently. Teaches critical thinking.

5. **Quiz** — "Crypto vs stocks vs savings"
   - Compare risk, potential return, and liquidity across three asset types.

#### Module 8: How Taxes Work (topic: `taxes`, 5 lessons)

1. **Card** — "Why do we pay tax?"
   - Public services: NHS, schools, roads, police. Government needs funding. Tax is your contribution.

2. **Card** — "Income tax basics"
   - Personal allowance (first £12,570 tax-free), basic rate (20%), higher rate (40%). Progressive = only the portion above each band is taxed at that rate.

3. **Quiz** — "How much tax on £20,000?"
   - Apply the bands: £12,570 at 0%, remaining £7,430 at 20% = £1,486. Common mistake: thinking the whole £20k is taxed at 20%.

4. **Scenario** — "Your first part-time job"
   - £8/hr, 10 hrs/week, 48 weeks/year = £3,840. Under personal allowance = no income tax. But you still see NI on your payslip.

5. **Quiz** — "Tax myths busted"
   - "Moving into a higher tax band means all your income is taxed at the higher rate" — false. Progressive taxation.

#### Module 9: Debt & Credit Explained (topic: `debt`, 6 lessons)

1. **Card** — "Borrowing money costs money"
   - Interest on loans. APR = annual percentage rate. £100 at 10% APR = £110 after a year.

2. **Card** — "Good debt vs bad debt"
   - Good: mortgage (asset appreciates), student loan (increases earning potential). Bad: credit card on depreciating stuff.

3. **Quiz** — "Calculate loan cost"
   - £500 loan at 10% APR for one year. How much do you pay back total? Answer: £550.

4. **Card** — "What is a credit score?"
   - A number showing how reliable you are at repaying. Built over time. Affects mortgage rates, phone contracts.

5. **Scenario** — "Guitar: save or buy now pay later?"
   - £300 guitar. Choices: save £50/month for 6 months / BNPL at 0% if paid in 3 months / credit card at 20% APR.

6. **Quiz** — "Spot the risky borrowing"
   - Identify warning signs: borrowing to repay other debt, missing minimum payments, using credit for daily expenses.

#### Module 10: Starting a Side Hustle (topic: `entrepreneurship`, 4 lessons)

1. **Card** — "Everyone starts somewhere"
   - Examples: tutoring younger students, reselling vintage clothes, dog walking, freelance design.

2. **Card** — "Finding your thing"
   - Skills + demand = opportunity. What are you good at? What do people need? Where do those overlap?

3. **Quiz** — "Match skills to side hustles"
   - Good at maths → tutoring. Good at baking → bake sales. Good at social media → content creation.

4. **Scenario** — "You're good at art"
   - Choices: sell prints online / offer pet portrait commissions / do free work for exposure. Business thinking.

#### Module 11: Revenue, Costs & Profit (topic: `entrepreneurship`, 4 lessons)

1. **Card** — "Revenue isn't profit"
   - Revenue = total money in. Costs = money out. Profit = what's left. You can have high revenue and no profit.

2. **Card** — "Fixed vs variable costs"
   - Fixed: same every month (website hosting, market stall fee). Variable: change with sales (materials, packaging).

3. **Quiz** — "Calculate bake sale profit"
   - Revenue: sold 50 cupcakes at £2 = £100. Costs: ingredients £40, packaging £10, stall fee £15. Profit = £35.

4. **Scenario** — "Your sticker business"
   - Made £200 revenue, spent £150 on supplies and shipping. Only £50 profit. How to improve margins?

#### Module 12: Your First Paycheque (topic: `taxes`, 3 lessons)

1. **Card** — "Reading a payslip"
   - Gross pay (before deductions), net pay (what you take home). Deductions: income tax, National Insurance, pension.

2. **Quiz** — "Match the payslip line"
   - Match: gross pay, NI, income tax, pension contribution, net pay to their definitions.

3. **Scenario** — "Where did your money go?"
   - Payslip shows £600 gross but £480 net. Walk through each deduction. Teaches it's normal, not an error.

## Technical Details

All changes are in `backend/app/seed/content.py`:
- Append 9 new module dicts to the `_MODULES` list
- Each dict follows the existing structure: `topic`, `title`, `country_codes` (empty = all), `is_premium` (False), `order_index` (continuing from 3), `lessons` list
- Each lesson dict: `type`, `xp_reward`, `order_index` (auto-assigned by position), `content_json`
- The existing `seed_modules_and_lessons()` function handles insertion — no changes to the function itself

## Testing Strategy

- Run seed: `cd backend && python -m app.seed.run`
- Verify modules appear: `psql investedb -c "SELECT title, topic FROM modules ORDER BY order_index;"`
- Verify lesson count: `psql investedb -c "SELECT m.title, count(l.id) FROM modules m JOIN lessons l ON l.module_id = m.id GROUP BY m.title ORDER BY m.title;"`
- Open frontend at `http://localhost:5173/lessons` — all 12 modules should appear
- Click into each new module — lessons should render with correct types
- Complete a quiz and scenario — XP should be awarded

## Future Work (not in scope)

- Premium modules (gated behind `is_premium: True`)
- Video lessons (need actual YouTube content IDs)
- Localised content per country (using `country_codes` filter)
- More advanced topics: ETFs, ISAs, pensions, insurance
