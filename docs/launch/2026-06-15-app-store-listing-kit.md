# App Store Listing Kit — InvestiKid (M11)

**Date:** 2026-06-15
**Status:** Draft for review — copy is ready to paste; operator items flagged.
**Scope:** Apple App Store (primary). Google Play notes at the end.
**Framing:** parent-outcome story ("your child *masters* real money skills"), not a
feature list — consistent with the M6 outcome-led paywall.

> The app **icon is done** (Penny-in-a-sprouting-coin, generated at all iOS/Android
> resolutions from `frontend/assets/icon.png`). This kit covers the remaining M11
> items: listing copy, ASO keywords, privacy nutrition labels, age rating, and the
> screenshot plan. Screenshots, the privacy questionnaire, and the age-rating
> questionnaire are entered by you in **App Store Connect** — this doc gives you the
> exact content to enter.

---

## 1. App name & subtitle

- **App name:** `InvestiKid` (30 char limit — 9 used)
- **Subtitle (30 chars):** `Money & investing for kids`
  - Alt: `Learn money, master investing` (29)

## 2. Promotional text (170 chars — editable without review)

> Turn screen time into money confidence. Kids learn saving, budgeting and
> investing through bite-size lessons and a safe, play-money market — guided by
> real curriculum standards.

## 3. Description (App Store)

```
InvestiKid teaches children real money skills — saving, budgeting, and how
investing actually works — through short, playful lessons and a safe practice
market that uses play money, never real cash.

Built with parents in mind. You see exactly what your child is mastering: a
Mastery Report shows the real skills they've earned this month, mapped to
financial-literacy curriculum standards — so screen time becomes progress you
can point to.

WHY FAMILIES CHOOSE INVESTIKID
• Real outcomes, not just games — every lesson builds a skill you can see in the
  parent dashboard.
• A safe place to practise investing — a simulated market with play money, live
  prices, and an AI coach that keeps explanations age-appropriate and kind.
• Grows with your child — an Explorer mode for younger kids and a cleaner
  Investor mode for teens.
• Daily habits that stick — a kid-sized daily goal, streaks, and gentle reminders.
• Built safe by default — no third-party ad trackers, parent-managed accounts,
  and content that's always moderated. It's a kids' app, designed to the highest
  child-safety standards.

PREMIUM
One subscription unlocks Premium for ALL your children — the full curriculum,
the AI coach, and advanced scenarios. Monthly or annual; cancel anytime.

InvestiKid is education, not financial advice. The market simulator uses play
money only.
```

## 4. Keywords (ASO — 100 char field, comma-separated, no spaces after commas)

```
money,kids,finance,investing,budget,saving,stocks,STEM,education,learn,allowance,teens,financial literacy
```
(99 chars. Don't repeat the app name or subtitle words — Apple already indexes
those. Tune after launch using Search Ads / impressions.)

## 5. What's New (first release notes)

> First public release. Bite-size money lessons, a safe play-money investing
> simulator, an AI coach, daily goals and streaks, and a parent dashboard with a
> monthly Mastery Report. One subscription covers all your children.

## 6. Category, URLs, contact

- **Primary category:** Education · **Secondary:** Finance
- **Privacy Policy URL:** `https://app.investikid.ai/privacy` (the in-app notice,
  version `PRIVACY_NOTICE_VERSION`)
- **Support URL / email:** confirm the support email used in-app (Send Feedback) and
  a support page URL.
- **Marketing URL (optional):** `https://app.investikid.ai`

## 7. Age rating (App Store Connect questionnaire)

The simulator is **play-money investing education — not gambling** (no real-money
wagering, no prizes of value). Answer the questionnaire honestly; expected result:

- **Recommended: 4+** (no objectionable content; education).
- The roadmap flagged a possible **9+/12+** if you'd rather position it as a
  finance app for older kids — that's a positioning choice, not a content
  requirement. **Decision needed from you.** If you target Apple's **Kids
  category** (under-11 band), note the stricter rules: no third-party
  analytics/ads (already true), and external links/purchases behind a **parental
  gate** (already true via the parent flow) — but Kids-category review is
  stricter. Listing under **Education** (not the Kids category) is the simpler
  path and still appropriate.

## 8. Privacy "nutrition" labels (App Store Connect → App Privacy)

Declare these to **match the privacy notice** at `/privacy`. Verify against the
compliance docs before submitting.

**Data collected & linked to the user**
- **Contact Info — Email address:** account / parental-consent email. *Purpose:
  App Functionality.*
- **User Content:** lesson answers, AI-coach messages (moderated). *App Functionality.*
- **Identifiers — User ID:** account id. *App Functionality.*
- **Usage Data — Product Interaction:** first-party analytics (lesson completion,
  screen views) **for App Functionality / Analytics only**, respecting the
  in-app profiling gate. *Not used for tracking.*
- **Purchases:** subscription status (payment handled by Apple; we don't store card data).

**Data NOT collected:** Location, Contacts, Browsing History, Health, Financial
account info, Photos, Audio.

**Tracking:** **No.** No third-party ad networks or cross-app/cross-site trackers
on child surfaces (COPPA/AADC). "Data used to track you" = **none**.

**Biometric note:** Face ID/Touch ID secrets are stored **on-device** (Keychain,
biometry-bound) and are **not collected by us** — so they are not a privacy-label
data type.

## 9. Screenshots plan (you capture on device / simulator)

Apple needs 6.7" and 6.5" iPhone sets (and 12.9" iPad if you ship iPad). Capture
these 5, with captions framed on outcomes:

1. **Home / Continue** — "One clear thing to do next." (the next-lesson hero)
2. **A lesson in progress** — "Bite-size money lessons kids actually finish."
3. **The simulator / market** — "Practise investing — with play money, never real cash."
4. **Parent dashboard / Mastery Report** — "See the real skills they've mastered."
5. **AI coach** — "A kind, age-appropriate coach for every question."

Tips: use clean, real content (no debug data); consider a one-line caption baked
into each frame; lead with screenshots 1 and 4 (the conversion pair).

---

## Google Play (parallel)

- **Short description (80):** `Real money & investing skills for kids — safe lessons, play-money market.`
- Reuse the long description + keywords above.
- Play requires a **Data safety** form (mirror the privacy labels in §8) and a
  **content rating** questionnaire (IARC) — expect "Everyone." Target audience &
  content: declare children + **Designed for Families** if you opt in (stricter,
  like Apple's Kids category).

## Operator checklist (what's left for you in the consoles)

- [ ] Decide age rating (4+ vs 9+/12+) and Kids-category vs Education-only.
- [ ] Capture + upload the 5 screenshots (per §9) for each required device size.
- [ ] Enter the App Privacy answers (§8) + confirm they match `/privacy`.
- [ ] Confirm support email + URLs (§6).
- [ ] Paste name/subtitle/promo/description/keywords (§1–4).
- [ ] (Play) Fill Data safety + content rating; decide Designed for Families.
