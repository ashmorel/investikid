# Google Play — App content answers (paste-ready)

Drafted from `docs/compliance/DPIA.md` + `docs/compliance/privacy-notice.md` and the actual build (no third-party analytics/ad/crash SDKs; permissions = notifications + biometric only). **Verify against the live app and get a compliance/legal sign-off before submitting** — it's a children's app. Items marked **DECIDE** or **YOU SUPPLY** need your input.

Privacy policy URL (used throughout): `https://app.investikid.ai/privacy`

---

## 1. App access
- Choose: **"All or some functionality is restricted"** (the app requires login).
- Add instructions + credentials so Google can sign in. **YOU SUPPLY:**
  - **Learner login** — a pre-activated account with DOB in 8–16 (so the parental-consent email gate doesn't block the reviewer): username + password.
  - **Parent login** — email + password.
  - Note: "Educational app; simulator uses virtual money only — no real funds or real securities trading."

## 2. Ads
- **Does your app contain ads?** → **No.** (No ad SDKs are bundled.)

## 3. Content rating (IARC questionnaire)
Category: **Reference / Education**. Answers:
- Violence, sexual content/nudity, profanity, controlled substances (drugs/alcohol/tobacco), hate: **No** to all.
- **Gambling / simulated gambling:** **No.** (The stock simulator is *educational*, uses *virtual* money, has no wagering, no casino/betting mechanics, and virtual coins can't be cashed out.)
- **Users can interact / exchange content / user-to-user communication:** **No.** (The AI "Coach" is user-to-bot only; there's no user-to-user chat or social sharing, and no public leaderboard.)
- **Shares user's current location:** **No.**
- **Digital purchases:** **Yes** (auto-renewing subscriptions).
- Expected result: **Everyone / PEGI 3** (or local equivalent).

## 4. Target audience and content  — **DECIDE**
- **Target age groups:** select **9–12, 13–15, 16–17, and 18 & over** (matches the real audience; the age ceiling is now removed so adults can use it too).
- **Appeals to children?** → **Yes** (mixed audience including children).
- **Trade-off to know:** including **9–12** puts the app fully under Google Play's **Families policy** (privacy policy required ✓, no ads ✓, only approved SDKs ✓ — you meet all three). If you ever wanted lighter review you could target 13+, but that would misrepresent the audience — keep 9–12.
- Provide the **privacy policy URL** when asked.

## 5. Data safety (the matrix)
Top-level answers:
- **Does your app collect or share any of the required user data types?** → **Yes** (collect; **no sharing**).
- **Is all of the user data collected by your app encrypted in transit?** → **Yes** (HTTPS/TLS).
- **Do you provide a way for users to request that their data is deleted?** → **Yes** (in-app account deletion → 30-day purge; deletion can also be requested via the privacy contact).

For **every** data type below: **Collected = Yes, Shared = No, Processed ephemerally = No.** "Required" vs "Optional" and "Purposes" are noted per row.

| Play data type | Collected? | Required/Optional | Purposes |
|---|---|---|---|
| **Personal info → Email addresses** | Yes | Optional (children may omit; parent email required for under-consent-age) | Account management; Developer communications (account/consent emails) |
| **Personal info → User IDs** (username) | Yes | Required | Account management |
| **Personal info → Other info** (date of birth, country) | Yes | Required | Account management; **Fraud prevention, security & compliance** (age-gate / jurisdiction) |
| **Financial info → Purchase history** (subscription status) | Yes | Optional | Account management (entitlement). *Payment details themselves are handled by Google Play — not collected by the app.* |
| **Messages → Other in-app messages** (AI Coach inputs) | Yes | Optional | App functionality (AI coach); Fraud prevention, security & compliance (safety moderation) |
| **App activity → App interactions** (lessons, XP, taps) | Yes | Required | App functionality; **Analytics** (first-party only) |
| **Device or other IDs** (FCM push token) | Yes | Optional | App functionality (push notifications) |

**Explicitly NOT collected** (answer No / leave unchecked): Name (username is a login ID, not a real name), Location (precise or approximate), Phone number, Contacts, Photos/Videos, Audio/Voice, Files/Docs, Calendar, Health & fitness, Web browsing history, Installed apps, Race/ethnicity, Political/religious beliefs, Sexual orientation.

**Biometrics (Face ID / fingerprint):** **Do NOT declare.** The biometric secret is stored on-device (Android Keystore) and **never transmitted to the backend**, so it isn't "collected" in Play's sense.

## 6. Other declarations you may be asked
- **Government app:** No.
- **Financial features:** If prompted, declare it is **educational only — no real-money trading, lending, or money transfer; the simulator uses virtual currency.** (Avoids being treated as a regulated financial-services app.)
- **Health:** No.
- **News:** No.

## 7. Data deletion (Play requires this)
- In-app: account deletion is available in the app (→ soft-delete, hard purge after 30 days; see `docs/compliance/operations.md`).
- Also provide a **deletion-request URL/instructions** for users who can't sign in — point to `https://app.investikid.ai/privacy` (which explains contacting `privacy@investikid.ai`). If Play wants a dedicated URL, add a short "Request account deletion" section/page.

---

### Caveats
- These answers reflect the current build + DPIA. If you add any SDK, analytics, crash reporting, or ads later, the **Data safety form must be updated** (mismatches are a top rejection/enforcement cause).
- For a children's app, have these reviewed alongside the privacy notice/DPIA by whoever owns compliance before you submit to production.
