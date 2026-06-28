# App Store Listing Kit — InvestiKid (M11)

**Date:** 2026-06-15 · **Finalized:** 2026-06-28
**Status:** ✅ Paste-ready — copy refreshed to current features; contact + age-rating/category decisions resolved (§6, §7). Only the in-console operator steps remain (paste, screenshots, questionnaires, demo creds).
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
• Daily habits that stick — a kid-sized daily goal, streaks, gentle reminders, and
  Penny's Arcade (quick money games and a daily word puzzle) that make coming back fun.
• Made to be remembered — smart revision brings back the trickiest ideas at just the
  right time (spaced repetition), so skills actually last.
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
> simulator, an AI coach, smart revision that helps skills stick, Penny's Arcade
> games, daily goals and streaks, and a parent dashboard with a monthly Mastery
> Report. One subscription covers all your children.

## 6. Category, URLs, contact  *(RESOLVED 2026-06-28)*

- **Primary category:** Education · **Secondary:** Finance
- **Privacy Policy URL:** `https://app.investikid.ai/privacy` ✅ (route live, `Privacy.tsx`; version `PRIVACY_NOTICE_VERSION`)
- **Support / contact email:** **`privacy@investikid.ai`** ✅ (the live inbox used in-app for account deletion + parent settings; Cloudflare-routed). Use this as the App Review contact + the App Privacy "Contact" address.
- **Support URL:** `https://app.investikid.ai` (no dedicated `/support` page yet — the marketing/app URL + the in-app "Send Feedback" cover it; a 1-page `/support` with the email + an FAQ would be a nice-to-have, not a blocker).
- **Marketing URL (optional):** `https://app.investikid.ai`

## 7. Age rating + category  *(RESOLVED 2026-06-28 — recommendation below)*

**Category: list under Education, NOT the Kids Category.** Decisive reason: InvestiKid
targets **8–18** (Explorer + Investor modes; the 15–18 teen band feeds M10), but
Apple's **Kids Category is capped at under-11** (bands: 5-&-under / 6–8 / 9–11) — a
teen-inclusive app doesn't fit it. Education is the correct home, not a shortcut.
(You still follow all kids-data rules since the audience includes minors — parental
gate, no third-party trackers — which the app already does.)

**Age rating: 4+** (play-money investing education is **not** "Simulated Gambling" —
no real-money wagering, no prizes of value; answer that question **No**).

> ⚠️ **AI-coach questionnaire nuance (Apple's 2025 age-rating update).** The
> questionnaire now asks about **AI chatbots / AI-generated content** and
> **unrestricted web access**. Answer honestly but precisely: the coach is
> **moderated, curriculum-bounded, age-appropriate (guardrails), with NO
> unrestricted web access and NO user-to-user messaging** (leaderboards use safe
> handles only). Framed that way it stays **4+**; if the AI questions nudge it,
> **9+ is acceptable** and still broad. Do NOT describe the coach as an open/general
> chatbot — that can force 17+.

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

## Operator checklist (what's left for you in App Store Connect)

- [x] **Age rating + category decided** — Education (not Kids Category, per §7) + 4+; answer the AI-coach questions as "moderated/restricted" (§7).
- [x] **Support email + URLs confirmed** — `privacy@investikid.ai` + `https://app.investikid.ai` (§6).
- [ ] Paste name / subtitle / promotional text / description / keywords (§1–4).
- [ ] Run the age-rating questionnaire → confirm it lands 4+ (watch the gambling + AI questions, §7).
- [ ] Enter the App Privacy answers (§8); confirm they match `/privacy`.
- [ ] Capture + upload the 5 screenshots (§9) for each required device size (6.7" + 6.5").
- [ ] **App Review notes — REQUIRED or Apple rejects (Guideline 2.1):** add a **demo child account (DOB 8–16) + a parent account** (username + password), plus the "virtual/educational, not a real brokerage" statement. See [`app-store-review-prep.md`](app-store-review-prep.md).
- [ ] Subscription metadata (display name, description, review screenshot) for the Premium IAP — needs M5 pricing done first.
- [ ] (Play) Fill Data safety + content rating (IARC); decide Designed for Families.
