import { useState } from 'react';
import { PlayCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Disclosure } from '@/components/a11y/Disclosure';
import { buildYouTubeUrls } from '@/components/child/lesson/videoEmbed';
import { isNativeApp } from '@/lib/platform';

type Props = {
  contentJson: {
    youtube_id?: string;
    caption?: string;
    transcript?: string;
    captions_available?: boolean;
  };
  onComplete: (score: number | null) => void;
  completing?: boolean;
};

export function VideoLesson({ contentJson, onComplete, completing = false }: Props) {
  const [watched, setWatched] = useState(false);
  const youtubeUrls = contentJson.youtube_id ? buildYouTubeUrls(contentJson.youtube_id) : null;
  const nativeApp = isNativeApp();

  if (!youtubeUrls) {
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

  return (
    <div className="space-y-4">
      {nativeApp ? (
        <a
          href={youtubeUrls.watch}
          target="_blank"
          rel="noopener"
          referrerPolicy="strict-origin-when-cross-origin"
          className="group relative block aspect-video overflow-hidden rounded-md border bg-black"
          aria-label="Open lesson video on YouTube"
        >
          <img
            src={youtubeUrls.thumbnail}
            alt="Lesson video thumbnail"
            className="h-full w-full object-cover"
          />
          <span className="absolute inset-0 flex items-center justify-center bg-black/25 transition-colors group-hover:bg-black/35">
            <PlayCircle className="h-16 w-16 text-white drop-shadow" aria-hidden="true" />
          </span>
        </a>
      ) : (
        <div className="aspect-video overflow-hidden rounded-md border">
          <iframe
            src={youtubeUrls.embed}
            title="Lesson video"
            referrerPolicy="strict-origin-when-cross-origin"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowFullScreen
            className="h-full w-full"
          />
        </div>
      )}
      <a
        href={youtubeUrls.watch}
        target="_blank"
        rel="noopener"
        referrerPolicy="strict-origin-when-cross-origin"
        className="text-sm font-medium text-primary underline-offset-4 hover:underline"
      >
        Open video on YouTube
      </a>
      {contentJson.caption && <p className="text-sm text-muted-foreground">{contentJson.caption}</p>}
      <p className="text-xs text-muted-foreground">
        {contentJson.captions_available ? 'Captions available' : 'No captions'}
      </p>
      {contentJson.transcript && (
        <Disclosure label="Show transcript">{contentJson.transcript}</Disclosure>
      )}
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={watched} onChange={(e) => setWatched(e.target.checked)} />
        I watched this
      </label>
      <div className="flex justify-end">
        <Button disabled={!watched || completing} onClick={() => onComplete(null)}>
          {completing ? 'Saving...' : 'Mark complete →'}
        </Button>
      </div>
    </div>
  );
}
