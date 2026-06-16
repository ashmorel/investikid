# Web auth fix — same-site API subdomain

**Date:** 2026-06-15
**Status:** Approved (approach B; host-only cookies; prod web only)
**Problem owner:** web login on `app.investikid.ai` fails in Safari (and
increasingly Chrome).

## Problem

The prod web app (`app.investikid.ai`, Vercel) calls the API **cross-origin** at
`investikid.up.railway.app` (the bundle bakes that absolute URL; `vercel.json` has
no API proxy). The auth cookies (`access_token` / `refresh_token`, `SameSite=None;
Secure`) are therefore **third-party** from the web app's perspective, which Safari
ITP blocks and Chrome partitions → the cookie never sticks → `/me` 401s → the user
sees "Could not start your session."

CORS is **not** the cause (`app.investikid.ai` is already in `CORS_ORIGINS`), and
this is **pre-existing** (the web app has always been cross-origin); the native iOS
app is unaffected because CapacitorHttp persists the cookie natively.

## Fix — serve the API from a same-site subdomain

Point the web app at **`api.investikid.ai`** (a Railway custom domain on the prod
backend) instead of `investikid.up.railway.app`. Because `app.investikid.ai` and
`api.investikid.ai` share the registrable domain `investikid.ai`, the cookie is
**same-site, not third-party** — Safari/Chrome stop blocking it. It remains
cross-*origin* (different subdomain), which CORS already permits.

### Why no backend code change
- Cookies stay **host-only** on `api.investikid.ai` (decision: host-only, not a
  shared `Domain=.investikid.ai`) — sufficient because the web app is same-site.
- `SameSite=None; Secure` already set — fine for a same-site subdomain.
- **CORS** already allows `app.investikid.ai` (the request Origin). ✅
- **CSRF** already bypasses the double-submit check for the trusted origin
  `app.investikid.ai` (`backend/app/core/csrf.py` `_BASELINE_TRUSTED_ORIGINS`). ✅

## Steps

1. **Railway (prod `InvestiKid` backend):** add custom domain `api.investikid.ai`.
   Railway returns a CNAME target and provisions TLS once DNS resolves. The
   existing `investikid.up.railway.app` domain stays active in parallel.
2. **DNS (investikid.ai provider):** add `CNAME api.investikid.ai → <railway target>`.
3. **Vercel (web project, Production env):** set
   `VITE_API_BASE_URL=https://api.investikid.ai`; redeploy prod web.
4. **Verify:** in **Safari**, sign in at `app.investikid.ai`, confirm the session
   persists across a refresh and `/me` succeeds; then run the admin video-upload
   test.

## Out of scope (follow-ups)
- **Native** keeps calling `investikid.up.railway.app` (still live) — migrate the
  native `NATIVE_API_FALLBACK` to `api.investikid.ai` in a future build, no rush.
- **Testing/staging web** stay on railway domains for now; replicate with
  `api-testing` / `api-staging` later if web QA there is needed.

## Rollback
Revert the Vercel `VITE_API_BASE_URL` to the railway URL and redeploy — instantly
restores the prior (cross-origin) behaviour. The Railway custom domain and DNS can
be left in place harmlessly.

## Operational gotchas (learned the hard way, 2026-06-15)

Setting this up cost ~an hour of cert troubleshooting. The rules:

- **Railway custom domain behind Cloudflare MUST be "DNS only" (grey cloud).** If
  the `api` CNAME is **Proxied (orange)**, Railway reports **"Cloudflare proxy
  detected"** and **can never issue its Let's Encrypt cert** (Cloudflare intercepts
  the validation), so `https://api.investikid.ai` resets the TLS handshake. Grey
  cloud → Railway issues + serves the cert directly → works. This was the entire
  root cause of the outage.
- **The Cloudflare proxy toggle can silently revert.** After setting grey, **refresh
  the Cloudflare DNS page and re-confirm it stayed grey.** Railway's domain row is
  the authoritative signal: "Cloudflare proxy detected" = still orange; "Active" =
  cert issued.
- **`app.investikid.ai` (Vercel) is also grey/DNS-only** and serves its **own**
  Vercel cert. So both subdomains are grey, each fronted by its provider — they are
  intentionally **not** "matched" to anything else. Don't proxy them.
- **After any DNS edit, wait 15–30 min and verify in a *fresh* browser**
  (incognito / mobile data / flushed DNS) — **not** repeated `curl`. Heavy toggling
  churns resolver caches and makes *healthy* domains look broken (during this
  incident `app` appeared down purely from cache churn while Vercel was fine).
- **Don't toggle repeatedly.** Each failed attempt risks **Let's Encrypt's hourly
  rate limit** (failed issuances per hostname), which then blocks issuance for ~1h.
  Set the correct state once and let it settle.
- **Verify via the dashboards + the provider's own domain**, e.g.
  `investikid.up.railway.app/health` stays 200 throughout (it's a different
  hostname, unaffected by the custom-domain cert), so a backend that's "down" only
  on the custom domain is a cert/DNS problem, not an app problem.
