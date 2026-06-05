# Self-Hosted Video (Cloudflare R2) — Setup

The app can host curated lesson videos on **Cloudflare R2** and play them inline (ad-free, no "video unavailable", no iOS error 153). YouTube remains a per-lesson alternative. Until the `R2_*` env vars below are set, admin video upload shows **"Video upload not configured"** and YouTube keeps working.

## What you get
- Admin → edit a video lesson → **Video source: Uploaded video** → pick an MP4 → it uploads straight to R2 and the child plays it inline.
- Broken hosted files surface in **Admin → Video health** (and the dead-video email cron), same as YouTube ones.

## One-time setup

1. **Create an R2 bucket** in the Cloudflare dashboard (e.g. `investikid-videos`).
2. **Enable public access / a public domain** for the bucket — either the R2.dev managed subdomain or a custom domain (e.g. `https://videos.investikid.app`). This URL (no trailing slash) is `R2_PUBLIC_BASE_URL`. Files are served publicly by **unguessable random keys** (`videos/{uuid}.mp4`).
3. **Create an R2 API token** (S3 Auth) with object read/write on that bucket. From it you get:
   - Access Key ID → `R2_ACCESS_KEY_ID`
   - Secret Access Key → `R2_SECRET_ACCESS_KEY`
   - Your Cloudflare **Account ID** → `R2_ACCOUNT_ID` (the S3 endpoint is `https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com`)
   - Bucket name → `R2_BUCKET`
4. **Set bucket CORS** to allow the browser's presigned `PUT` from the app origins. In the bucket's CORS policy, allow:
   - **AllowedOrigins:** `https://lee-local-code-repo.vercel.app`, `http://localhost:5173`, `capacitor://localhost`
   - **AllowedMethods:** `PUT`, `GET`, `HEAD`
   - **AllowedHeaders:** `Content-Type`
   - (Example JSON)
     ```json
     [
       {
         "AllowedOrigins": ["https://lee-local-code-repo.vercel.app", "http://localhost:5173", "capacitor://localhost"],
         "AllowedMethods": ["PUT", "GET", "HEAD"],
         "AllowedHeaders": ["Content-Type"]
       }
     ]
     ```
5. **Set the env vars on Railway** (backend service):
   ```
   R2_ACCOUNT_ID=...
   R2_ACCESS_KEY_ID=...
   R2_SECRET_ACCESS_KEY=...
   R2_BUCKET=investikid-videos
   R2_PUBLIC_BASE_URL=https://videos.investikid.app
   ```
   (Optional: `R2_MAX_UPLOAD_BYTES` — defaults to 200 MB.)

## Constraints
- **MP4 only** (`video/mp4`, H.264/AAC recommended), **≤ 200 MB** per file — enforced server- and client-side. There is **no server-side transcoding**; upload a web-ready file.
- **Public-by-URL:** hosted files (including in premium modules) are reachable by anyone holding the unguessable URL — the same posture as the current public YouTube embeds. Signed/expiring URLs are a possible future hardening.

## Verifying
After setting the env + CORS and redeploying: Admin → a video lesson → Uploaded video → choose a small MP4 → it should show upload progress, then a preview. Open the lesson as a child (web + the iOS app) → it plays inline. If upload still says "not configured", the `R2_*` env isn't set on the running backend; if the PUT fails in the browser console with a CORS error, fix the bucket CORS (step 4).
