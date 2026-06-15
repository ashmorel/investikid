# Decision record — R2 object storage (video assets)

**Date:** 2026-06-14
**Status:** Accepted
**Scope:** Lesson video assets stored in Cloudflare R2 and served to learners.
**Code:** `backend/app/services/storage.py`, `backend/app/routers/admin.py`
(`/admin/video-assets/presign`), `frontend/src/components/admin/LessonForm.tsx`.

## Context

Admins upload lesson videos. The backend issues a **presigned R2 PUT** URL; the
browser uploads the file directly to R2 (never through the API). Learners later
fetch the video by its **public URL** (`storage.public_url(key)`).

Two questions needed an explicit, recorded decision: (1) are objects
public-by-URL acceptable, and (2) is upload size enforced server-side.

## Decision 1 — Objects are public-by-URL (unguessable key), not ACL-gated

Video assets are served via a **public bucket URL** with an **unguessable key**:
`videos/<uuid4>.mp4`. There is no per-request authorization on the asset fetch.

**Why this is acceptable:**
- The content is **non-sensitive educational video** — the same lessons every
  learner sees. It is not user-generated, not personal, and carries no PII.
- Keys are random UUIDv4 (`admin.py` `f"videos/{uuid.uuid4()}.mp4"`), so URLs are
  not enumerable.
- Serving from a public CDN URL is the standard, low-latency path for static
  media and avoids proxying large files through the API.
- Premium gating is enforced at the **lesson/level** layer (a learner only
  receives the video URL for content they can access), not at the bytes layer.

**What this explicitly is NOT suitable for:** any future user-generated uploads,
anything containing PII, or anything that must be access-controlled per user. If
such a use case appears, it needs signed-GET URLs or an authorizing proxy — do
**not** reuse the public-by-URL pattern for it.

## Decision 2 — Upload size is enforced server-side at R2 (not just claimed)

Previously the presign endpoint validated the **client-claimed** `size_bytes`
against `settings.r2_max_upload_bytes` (200 MB), but the presigned PUT bound only
Bucket/Key/ContentType — so a client could claim a small size to pass the check
and then PUT a much larger file directly to R2.

**Now:** the validated size is **signed into the presigned URL** as
`ContentLength` (`storage.create_presigned_put(..., content_length=...)`). R2
rejects any upload whose actual `Content-Length` differs from the signed value,
so the 200 MB cap is enforced at the bytes layer, not merely advisory. The
request schema also rejects non-positive sizes (`size_bytes: Field(gt=0)`).

The browser upload (`uploadToPresigned`, XHR `PUT` of the actual `File`) sends a
matching `Content-Length` automatically, so legitimate uploads are unaffected;
only mismatched/oversized uploads are rejected.

> Abuse surface is small regardless — only authenticated **admins** can presign —
> but this closes the gap as defense-in-depth and satisfies the M2 ops-hardening
> item.

## Consequences / follow-ups

- `r2_max_upload_bytes` (200 MB) is the single source of truth for the cap; change
  it in config, not in scattered checks.
- Verify one real admin video upload on **testing/staging** after deploy — the R2
  `ContentLength` round-trip can't be exercised by the local unit tests (no R2
  credentials), so it needs a smoke test before promoting to production.
