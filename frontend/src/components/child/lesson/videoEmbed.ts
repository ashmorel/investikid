const YOUTUBE_ID_RE = /^[a-zA-Z0-9_-]+$/;
const WEB_EMBED_ORIGIN = 'https://www.youtube-nocookie.com';
const NATIVE_EMBED_ORIGIN = 'https://www.youtube.com';

function getPageOrigin() {
  if (typeof window === 'undefined') return NATIVE_EMBED_ORIGIN;
  return window.location.origin;
}

function isHttpOrigin(origin: string) {
  return origin.startsWith('http://') || origin.startsWith('https://');
}

export function buildYouTubeUrls(youtubeId: string, pageOrigin = getPageOrigin()) {
  const trimmed = youtubeId.trim();
  if (!YOUTUBE_ID_RE.test(trimmed)) return null;

  const isNativeWebView = !isHttpOrigin(pageOrigin);
  const embedOrigin = isNativeWebView ? NATIVE_EMBED_ORIGIN : WEB_EMBED_ORIGIN;
  const identityOrigin = isNativeWebView ? NATIVE_EMBED_ORIGIN : pageOrigin;
  const encodedId = encodeURIComponent(trimmed);

  const params = new URLSearchParams({
    origin: identityOrigin,
    widget_referrer: identityOrigin,
    playsinline: '1',
  });

  return {
    embed: `${embedOrigin}/embed/${encodedId}?${params.toString()}`,
    watch: `${NATIVE_EMBED_ORIGIN}/watch?v=${encodedId}`,
  };
}
