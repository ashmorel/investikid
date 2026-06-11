import { useEffect, useRef, useState } from 'react';

/**
 * Drives the kid-safety video lifecycle for a YouTube embed without depending on
 * a real player in tests. It reacts to two abstract events — `ended` and `error`
 * — delivered through `window.postMessage`:
 *
 *  - iOS: the `/yt.html` proxy runs the IFrame Player API and posts
 *    `{ type: 'investikid-yt', event: 'ended' | 'error', code? }` to the parent.
 *  - web/Android: the caller instantiates the IFrame Player API against the
 *    nocookie embed and re-posts `onStateChange === ENDED` / `onError` as the
 *    same message shape (so a single handler covers every platform).
 *
 * Security: the message handler accepts a message only when BOTH the
 * `event.origin` is one of the expected embed/app origins AND the payload is the
 * tagged `{ type: 'investikid-yt' }` shape. Anything else is ignored, so an
 * arbitrary cross-origin `postMessage` cannot end or fail the lesson.
 *
 * If no `ready`/`playing` signal arrives within `readyTimeoutMs` (~8s) the phase
 * flips to `error`, so a silently-broken embed degrades to the friendly fallback
 * instead of leaving the child staring at a dead frame.
 */

export const YT_MESSAGE_TYPE = 'investikid-yt';

export type YouTubePlayerPhase = 'playing' | 'ended' | 'error';

export interface YouTubeMessage {
  type: typeof YT_MESSAGE_TYPE;
  event: 'ready' | 'playing' | 'ended' | 'error';
  code?: number;
}

/** Type guard for the tagged player message shape. */
export function isYouTubeMessage(data: unknown): data is YouTubeMessage {
  if (typeof data !== 'object' || data === null) return false;
  const d = data as Record<string, unknown>;
  return (
    d.type === YT_MESSAGE_TYPE &&
    (d.event === 'ready' || d.event === 'playing' || d.event === 'ended' || d.event === 'error')
  );
}

export interface UseYouTubePlayerOptions {
  /** Whether to arm the listener + timeout (false for hosted / malformed-id paths). */
  enabled: boolean;
  /** Origins a player message may legitimately come from (embed origin + app web origin). */
  expectedOrigins: string[];
  /** How long to wait for a ready/playing signal before giving up. Default 8000ms. */
  readyTimeoutMs?: number;
}

const DEFAULT_READY_TIMEOUT_MS = 8000;

export function useYouTubePlayer({
  enabled,
  expectedOrigins,
  readyTimeoutMs = DEFAULT_READY_TIMEOUT_MS,
}: UseYouTubePlayerOptions): { phase: YouTubePlayerPhase } {
  const [phase, setPhase] = useState<YouTubePlayerPhase>('playing');
  // Keep the latest allow-list in a ref so the listener effect stays stable
  // (the effect should not re-run just because the origins array identity changed).
  const originsRef = useRef(expectedOrigins);
  useEffect(() => {
    originsRef.current = expectedOrigins;
  }, [expectedOrigins]);

  useEffect(() => {
    if (!enabled) return;

    const readyTimer: ReturnType<typeof setTimeout> = setTimeout(() => {
      setPhase((p) => (p === 'playing' ? 'error' : p));
    }, readyTimeoutMs);

    function handleMessage(event: MessageEvent) {
      // 1) Origin allow-list — reject anything not from the embed/app origin.
      if (!originsRef.current.includes(event.origin)) return;
      // 2) Tagged-shape check — reject anything that isn't our player message.
      if (!isYouTubeMessage(event.data)) return;

      if (event.data.event === 'ended') {
        setPhase('ended');
      } else if (event.data.event === 'error') {
        setPhase('error');
      } else {
        // ready/playing: the embed is alive, so cancel the ready-timeout fallback.
        clearTimeout(readyTimer);
      }
    }

    window.addEventListener('message', handleMessage);

    return () => {
      window.removeEventListener('message', handleMessage);
      clearTimeout(readyTimer);
    };
  }, [enabled, readyTimeoutMs]);

  return { phase };
}
