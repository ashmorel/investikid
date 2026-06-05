import { isNativeApp } from '@/lib/platform';

const YOUTUBE_ID_RE = /^[a-zA-Z0-9_-]+$/;
const WEB_EMBED_ORIGIN = 'https://www.youtube-nocookie.com';
const WATCH_ORIGIN = 'https://www.youtube.com';

// Canonical deployed web origin. On iOS the WKWebView serves from the
// `capacitor://localhost` scheme, and WKWebView strips the HTTP Referer on the
// cross-origin request to YouTube (WebKit bug 169846) — YouTube then rejects the
// embed with "error 153". We work around it by loading the player through a tiny
// static proxy page (`/yt.html`) served from this real https origin, so the
// YouTube request carries a valid https Referer. Overridable via VITE_WEB_ORIGIN.
const DEFAULT_WEB_ORIGIN = 'https://lee-local-code-repo.vercel.app';

function defaultWebOrigin(): string {
  return import.meta.env.VITE_WEB_ORIGIN || DEFAULT_WEB_ORIGIN;
}

export interface BuildYouTubeOptions {
  /** True when running inside the native Capacitor shell. Defaults to runtime detection. */
  isNative?: boolean;
  /** Override the https origin that serves the proxy page (defaults to VITE_WEB_ORIGIN). */
  webOrigin?: string;
}

export function buildYouTubeUrls(youtubeId: string, opts: BuildYouTubeOptions = {}) {
  const trimmed = youtubeId.trim();
  if (!YOUTUBE_ID_RE.test(trimmed)) return null;

  const isNative = opts.isNative ?? isNativeApp();
  const webOrigin = opts.webOrigin ?? defaultWebOrigin();
  const encodedId = encodeURIComponent(trimmed);

  let embed: string;
  if (isNative) {
    // Route through the https proxy page so YouTube receives a valid Referer.
    embed = `${webOrigin}/yt.html?v=${encodedId}`;
  } else {
    const params = new URLSearchParams({ playsinline: '1', rel: '0', modestbranding: '1' });
    embed = `${WEB_EMBED_ORIGIN}/embed/${encodedId}?${params.toString()}`;
  }

  return {
    embed,
    thumbnail: `https://img.youtube.com/vi/${encodedId}/hqdefault.jpg`,
    watch: `${WATCH_ORIGIN}/watch?v=${encodedId}`,
  };
}
