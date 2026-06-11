import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Disclosure } from '@/components/a11y/Disclosure';
import { buildYouTubeUrls, youtubeMessageOrigins } from '@/components/child/lesson/videoEmbed';
import { useYouTubePlayer, YT_MESSAGE_TYPE } from '@/components/child/lesson/useYouTubePlayer';
import { isAndroid, isNativeApp } from '@/lib/platform';

type Props = {
  contentJson: {
    video_source?: 'youtube' | 'hosted';
    video_url?: string;
    youtube_id?: string;
    caption?: string;
    transcript?: string;
    captions_available?: boolean;
  };
  onComplete: (score: number | null) => void;
  completing?: boolean;
};

// Minimal IFrame Player API typings (we don't pull in @types/youtube).
interface YTPlayer {
  destroy?: () => void;
}
interface YTNamespace {
  Player: new (el: HTMLElement, opts: unknown) => YTPlayer;
  PlayerState: { ENDED: number };
}
declare global {
  interface Window {
    YT?: YTNamespace;
    onYouTubeIframeAPIReady?: () => void;
  }
}

const IFRAME_API_SRC = 'https://www.youtube.com/iframe_api';

/** Load the YouTube IFrame Player API once (web/Android only). */
function ensureIframeApi(): void {
  if (window.YT?.Player) {
    window.onYouTubeIframeAPIReady?.();
    return;
  }
  if (!document.querySelector(`script[src="${IFRAME_API_SRC}"]`)) {
    const s = document.createElement('script');
    s.src = IFRAME_API_SRC;
    document.head.appendChild(s);
  }
}

export function VideoLesson({ contentJson, onComplete, completing = false }: Props) {
  const [checkedWatched, setCheckedWatched] = useState(false);
  const isHosted = contentJson.video_source === 'hosted' && !!contentJson.video_url;
  const youtubeUrls = !isHosted && contentJson.youtube_id ? buildYouTubeUrls(contentJson.youtube_id) : null;
  const isYouTube = !isHosted && !!youtubeUrls;

  // Player phase is only meaningful for the YouTube path. Hosted videos and the
  // malformed-id fallback never arm the listener/timeout.
  const expectedOrigins = isYouTube ? [...youtubeMessageOrigins(), window.location.origin] : [];
  const { phase } = useYouTubePlayer({ enabled: isYouTube, expectedOrigins });

  // When the video ends we auto-tick "I watched this" (derived, not stored) so
  // the "Mark complete" button is immediately actionable in the Finished panel.
  const watched = checkedWatched || (isYouTube && phase === 'ended');

  // web/Android: drive the IFrame Player API directly and forward its
  // ENDED/error signals through the SAME postMessage shape the iOS proxy uses,
  // so the hook's single handler covers every platform. Guarded so the absence
  // of a real API (tests, offline) simply leaves the ready-timeout to fire.
  const playerHostRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    if (!isYouTube || (isNativeApp() && !isAndroid())) return; // iOS uses the proxy iframe
    if (!contentJson.youtube_id) return;
    const host = playerHostRef.current;
    if (!host) return;

    let player: YTPlayer | undefined;
    const repost = (event: 'ready' | 'ended' | 'error', code?: number) => {
      window.postMessage({ type: YT_MESSAGE_TYPE, event, code }, window.location.origin);
    };

    const init = () => {
      if (!window.YT?.Player) return;
      player = new window.YT.Player(host, {
        videoId: contentJson.youtube_id,
        playerVars: { playsinline: 1, rel: 0, modestbranding: 1 },
        host: 'https://www.youtube-nocookie.com',
        events: {
          onReady: () => repost('ready'),
          onStateChange: (e: { data: number }) => {
            if (window.YT && e.data === window.YT.PlayerState.ENDED) repost('ended');
          },
          onError: (e: { data: number }) => repost('error', e.data),
        },
      });
    };

    window.onYouTubeIframeAPIReady = init;
    ensureIframeApi();

    return () => {
      player?.destroy?.();
    };
  }, [isYouTube, contentJson.youtube_id]);

  if (!isHosted && !youtubeUrls) {
    return (
      <div className="space-y-4">
        <p>Video unavailable.</p>
        <div className="flex justify-end">
          <Button onClick={() => onComplete(null)} disabled={completing}>
            {completing ? 'Saving...' : 'Continue →'}
          </Button>
        </div>
      </div>
    );
  }

  // Graceful failure: an embed error or the ~8s ready-timeout shows a friendly
  // card (never a raw YouTube error), with the transcript and a Continue button.
  if (isYouTube && phase === 'error') {
    return (
      <div className="space-y-4">
        <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <p className="font-medium">This video is taking a break — read the lesson and continue.</p>
        </div>
        {youtubeUrls && (
          <a
            href={youtubeUrls.watch}
            target="_blank"
            rel="noopener"
            referrerPolicy="strict-origin-when-cross-origin"
            className="text-sm font-medium text-primary underline-offset-4 hover:underline"
          >
            Open video on YouTube
          </a>
        )}
        {contentJson.transcript && (
          <Disclosure label="Show transcript">{contentJson.transcript}</Disclosure>
        )}
        <div className="flex justify-end">
          <Button onClick={() => onComplete(null)} disabled={completing}>
            {completing ? 'Saving...' : 'Continue →'}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Player: hidden once the video ends so YouTube's related-video end-screen
          never shows — we end into our own "Finished" panel instead. */}
      {!(isYouTube && phase === 'ended') && (
        <div className="aspect-video overflow-hidden rounded-md border">
          {isHosted ? (
            <video
              src={contentJson.video_url}
              title="Lesson video"
              controls
              playsInline
              preload="metadata"
              className="h-full w-full"
            >
              <track kind="captions" />
            </video>
          ) : isNativeApp() && !isAndroid() ? (
            <iframe
              src={youtubeUrls!.embed}
              title="Lesson video"
              referrerPolicy="strict-origin-when-cross-origin"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              allowFullScreen
              className="h-full w-full"
            />
          ) : (
            // web/Android: the IFrame Player API replaces this div with its iframe.
            <div ref={playerHostRef} title="Lesson video" data-testid="yt-player-host" className="h-full w-full">
              <iframe
                src={youtubeUrls!.embed}
                title="Lesson video"
                referrerPolicy="strict-origin-when-cross-origin"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowFullScreen
                className="h-full w-full"
              />
            </div>
          )}
        </div>
      )}

      {isYouTube && phase === 'ended' && (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
          <p className="font-medium">✓ Finished — Mark complete →</p>
        </div>
      )}

      {!isHosted && phase !== 'ended' && (
        <a
          href={youtubeUrls!.watch}
          target="_blank"
          rel="noopener"
          referrerPolicy="strict-origin-when-cross-origin"
          className="text-sm font-medium text-primary underline-offset-4 hover:underline"
        >
          Open video on YouTube
        </a>
      )}
      {contentJson.caption && phase !== 'ended' && (
        <p className="text-sm text-muted-foreground">{contentJson.caption}</p>
      )}
      {phase !== 'ended' && (
        <p className="text-xs text-muted-foreground">
          {contentJson.captions_available ? 'Captions available' : 'No captions'}
        </p>
      )}
      {contentJson.transcript && (
        <Disclosure label="Show transcript">{contentJson.transcript}</Disclosure>
      )}
      {/* "I watched this" is hidden once ended (auto-ticked); the panel above is
          the call to action. For the playing state it still gates completion. */}
      {phase !== 'ended' && (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={watched} onChange={(e) => setCheckedWatched(e.target.checked)} />
          I watched this
        </label>
      )}
      <div className="flex justify-end">
        <Button disabled={!watched || completing} onClick={() => onComplete(null)}>
          {completing ? 'Saving...' : 'Mark complete →'}
        </Button>
      </div>
    </div>
  );
}
