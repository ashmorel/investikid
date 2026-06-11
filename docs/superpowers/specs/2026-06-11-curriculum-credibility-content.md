# W3b — Curriculum Credibility Content Pack (standards · sources · objectives)

**Date:** 2026-06-11 · **Status:** Draft — awaiting spot-review · **Repo:** `ashmorel/investikid` · branch `testing`
**Spec:** `2026-06-10-curriculum-credibility-design.md` (W3b). After approval this content lands in `backend/app/seed/content.py` via the W3a seeder upsert.

## Frameworks used (verified against the published documents, 2026-06-11)
- **UK MaPS/YE** — *Financial Education Planning Framework* (Money and Pensions Service, delivered by Young Enterprise; 3-11 & 11-19 years). Four core themes, quoted verbatim: **How to manage money** · **Becoming a critical consumer** · **Managing risks and emotions associated with money** · **Understanding the important role money plays in our lives**. We map at theme level with the age band as the code (the framework does not number its themes — we do not invent codes).
- **US CEE/Jump$tart** — *National Standards for Personal Financial Education* (Council for Economic Education + Jump$tart Coalition, 2021). Six topic areas, quoted verbatim with their standard numbering: **I Earning Income · II Spending · III Saving · IV Investing · V Managing Credit · VI Managing Risk**.

`framework` strings used in data: `"UK MaPS/YE Financial Education Planning Framework"` and `"US National Standards for Personal Financial Education (CEE/Jump$tart 2021)"` — abbreviated below as **MaPS** and **J$**.

---

## 1 · What is a Stock? (`stocks`)
**Standards:** MaPS `11-19` *Understanding the important role money plays in our lives* · J$ `IV` *Investing*
**Sources:** FCA InvestSmart — https://www.fca.org.uk/investsmart · Investor.gov (US SEC), "Stocks" — https://www.investor.gov/introduction-investing/investing-basics/investment-products/stocks
**L1:** Explain that a share is a small piece of a company · Describe why people buy shares (growth and dividends) · Recognise that share prices move up and down
**L2:** Explain what a stock exchange is and that you usually trade with other investors · Use a ticker to find a company and explain what an index (like the FTSE 100) tracks · Compare company sizes using market value
**L3:** Explain why spreading money across companies (diversification) lowers risk · Explain why time in the market usually beats trying to time it · Recognise that higher possible reward comes with higher risk

## 2 · Compound Interest Basics (`savings`)
**Standards:** MaPS `11-19` *How to manage money* · J$ `III` *Saving*
**Sources:** MoneyHelper, "Savings" — https://www.moneyhelper.org.uk/en/savings · Bank of England KnowledgeBank, "What are interest rates?" — https://www.bankofengland.co.uk/explainers/what-are-interest-rates
**L1:** Explain that compound interest is interest earned on interest · Show how money grows faster the longer it is saved · Compare simple and compound growth
**L2:** Explain how compounding frequency changes growth · Use the Rule of 72 to estimate doubling time · Explain why saving regularly gives compounding more to work with — and spot "guaranteed doubling" scams
**L3:** Explain how compounding can work against you on unpaid debt · Describe how inflation erodes buying power · Explain why tax-free wrappers (like a Junior ISA) and starting early boost long-term growth

## 3 · What is a REIT? (`real_estate`)
**Standards:** MaPS `11-19` *Understanding the important role money plays in our lives* · J$ `IV` *Investing*
**Sources:** Investor.gov (US SEC), "Real Estate Investment Trusts (REITs)" — https://www.investor.gov/introduction-investing/investing-basics/investment-products/real-estate-investment-trusts-reits · MoneyHelper, "Investing in property" — https://www.moneyhelper.org.uk/en/savings/types-of-savings/investing-in-property
**L1:** Explain that a REIT lets you invest in property through shares · Describe how REITs make money from rent paid out to shareholders
**L2:** List the kinds of property REITs can own · Explain why REITs pay high dividends and how owning many buildings spreads risk · Explain that REIT shares trade on the stock market
**L3:** Calculate a dividend yield and treat an unusually high one as a warning sign · Explain why rising interest rates can hurt REITs · Place REITs as one slice of a diversified mix

## 4 · Budgeting Basics (`budgeting`)
**Standards:** MaPS `11-19` *How to manage money* · J$ `II` *Spending*
**Sources:** MoneyHelper, "Budgeting" — https://www.moneyhelper.org.uk/en/everyday-money/budgeting · FDIC Money Smart — https://www.fdic.gov/consumer-resource-center/money-smart
**L1:** Explain what a budget is and why it helps · Apply a simple rule (like 50/30/20) to split money between spending and saving
**L2:** Explain why tracking real spending against the plan reveals surprises · Tell fixed costs from variable costs · Plan ahead for known costs with a sinking fund
**L3:** Give every pound a job (zero-based budgeting) · Pay yourself first when money comes in · Budget with variable income and spot lifestyle creep

## 5 · Needs vs Wants (`budgeting`)
**Standards:** MaPS `11-19` *Becoming a critical consumer* · J$ `II` *Spending*
**Sources:** MoneyHelper, "Everyday money" — https://www.moneyhelper.org.uk/en/everyday-money · FDIC Money Smart — https://www.fdic.gov/consumer-resource-center/money-smart
**L1:** Tell the difference between a need and a want · Explain why the difference isn't always obvious and depends on context
**L2:** Use the "wait a bit" test to avoid impulse buys · Compare value using cost-per-use · Recognise opportunity cost and judge whether a "sale" is really a smart buy
**L3:** Explain that adverts are designed to make you want things · Spot hurry-up tricks ("limited time!", scarcity) and peer/influencer pressure · Decide for yourself whether something is worth its price

## 6 · Risk & Diversification (`risk`)
**Standards:** MaPS `11-19` *Managing risks and emotions associated with money* · J$ `IV` *Investing* · J$ `VI` *Managing Risk*
**Sources:** FCA InvestSmart, "Understanding investment risk" — https://www.fca.org.uk/investsmart · Investor.gov (US SEC), "Diversification" — https://www.investor.gov/additional-resources/information/youth/teachers-classroom-resources/what-diversification
**L1:** Explain what investment risk is · Explain why putting all your eggs in one basket is dangerous and how diversification helps
**L2:** Name different kinds of risk (company-specific, market, inflation, liquidity) · Match where you keep money to when you'll need it (time horizon) · Build an emergency fund before investing
**L3:** Tell risk tolerance from risk capacity · Describe bonds as a steadier complement to shares · Stay calm in a downturn and explain rebalancing · Explain how insurance transfers risk — and spot "no risk, guaranteed" scams

## 7 · What is Crypto? (`crypto`)
**Standards:** MaPS `11-19` *Managing risks and emotions associated with money* · J$ `IV` *Investing* · J$ `VI` *Managing Risk*
**Sources:** FCA, "Cryptoassets" consumer guidance — https://www.fca.org.uk/consumers/cryptoassets · Bank of England KnowledgeBank, "What are cryptoassets?" — https://www.bankofengland.co.uk/explainers/what-are-cryptocurrencies
**L1:** Describe crypto as digital money recorded on a shared ledger · Explain why crypto prices are far more volatile than ordinary money
**L2:** Explain why a blockchain is hard to tamper with · Keep private keys/seed phrases secret and explain why lost keys usually mean lost crypto · Spot classic crypto scams ("send 1, get 2 back")
**L3:** Compare crypto with ordinary money on the jobs money must do · Explain that crypto usually lacks bank-style protections · Resist hype/FOMO from celebrities and consider the environmental cost

## 8 · How Taxes Work (`taxes`)
**Standards:** MaPS `11-19` *Understanding the important role money plays in our lives* · J$ `I` *Earning Income*
**Sources:** GOV.UK, "Income Tax" — https://www.gov.uk/income-tax · GOV.UK, "How VAT works" — https://www.gov.uk/how-vat-works
**L1:** Explain why we pay tax and what it funds · Describe income tax basics (allowances and bands)
**L2:** Recognise taxes beyond income tax (VAT, National Insurance) · Explain that VAT is built into prices and what NI helps fund · Connect taxes to public services like the NHS, schools and roads
**L3:** Explain how progressive tax bands work (only the extra is taxed at the higher rate) · Describe how tax and benefits flow both ways · Act as an honest taxpayer and recognise that "cash in hand, tell no one" is not OK

## 9 · Debt & Credit Explained (`debt`)
**Standards:** MaPS `11-19` *How to manage money* · J$ `V` *Managing Credit*
**Sources:** MoneyHelper, "Everyday money — credit" — https://www.moneyhelper.org.uk/en/everyday-money/credit · FDIC Money Smart — https://www.fdic.gov/consumer-resource-center/money-smart
**L1:** Explain that borrowing money costs money (interest) · Tell good debt from bad debt · Describe what a credit score is
**L2:** Explain how interest compounds monthly on unpaid balances · Name common types of credit (cards, loans, BNPL, overdrafts) · Use credit responsibly: spend only what you can clear
**L3:** Build and protect a good credit score (pay on time, low utilisation) · Recognise a debt spiral and how to step out (including free UK debt help) · Judge when borrowing is a wise decision

## 10 · Starting a Side Hustle (`entrepreneurship`)
**Standards:** MaPS `11-19` *Understanding the important role money plays in our lives* · J$ `I` *Earning Income*
**Sources:** Young Enterprise — https://www.young-enterprise.org.uk · GOV.UK, "Tax-free allowances on trading income" — https://www.gov.uk/guidance/tax-free-allowances-on-property-and-trading-income
**L1:** Recognise that everyone starts somewhere · Match a side-hustle idea to your skills and interests
**L2:** Test an idea with a real sale before spending big · Set a fair price by checking the local market · Win first customers nearby and use word of mouth
**L3:** Build reputation by fixing mistakes honestly · Reinvest time and earnings wisely while protecting school/life balance · Stay safe with strangers online — involve a trusted grown-up

## 11 · Revenue, Costs & Profit (`entrepreneurship`)
**Standards:** MaPS `11-19` *Understanding the important role money plays in our lives* · J$ `I` *Earning Income*
**Sources:** Young Enterprise — https://www.young-enterprise.org.uk · Bank of England KnowledgeBank — https://www.bankofengland.co.uk/explainers
**L1:** Explain that revenue isn't profit · Tell fixed costs from variable costs
**L2:** Calculate profit margin and set a price from cost plus desired profit · Work out a break-even point
**L3:** Explain why profit isn't the same as cash in hand · Decide how much profit to reinvest · Read a simple revenue/costs/profit summary and scale sensibly

## 12 · Your First Paycheque (`taxes`)
**Standards:** MaPS `11-19` *How to manage money* · J$ `I` *Earning Income*
**Sources:** MoneyHelper, "Understanding your payslip" — https://www.moneyhelper.org.uk/en/work/employment/understanding-your-payslip · GOV.UK, "Understanding your pay" — https://www.gov.uk/understanding-your-pay
**L1:** Read a payslip (gross vs net pay) · Identify common deductions
**L2:** Explain where deductions go and that your pension contribution is your own savings · Read your tax code and YTD figures, and describe auto-enrolment · Calculate net pay from gross and deductions
**L3:** Pay yourself first from each paycheque · Build an emergency buffer and spot lifestyle creep after a pay rise · Plan a first wage sensibly: save a slice, keep a buffer, enjoy the rest

---

## Authoring notes
- Mapping is at **theme/topic-area level** with verbatim names from the published frameworks; we deliberately do not cite individual benchmark numbers (brittle across framework editions, and the app spans both UK & US bands).
- Objectives are written child-readable ("Explain… / Tell… / Use…"), 2-3 per level, each traceable to lessons that actually exist in the seed (L2/L3 objectives derive from the Level 2/3 rollout content; L1 from the original curriculum).
- Sources are official/consumer-protection bodies only (MaPS MoneyHelper, FCA, Bank of England, GOV.UK, US SEC Investor.gov, FDIC, Young Enterprise) — no commercial content sites.
