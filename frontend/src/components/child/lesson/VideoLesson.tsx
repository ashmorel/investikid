import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Disclosure } from '@/components/a11y/Disclosure';
import { buildYouTubeUrls } from '@/components/child/lesson/videoEmbed';

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

export function VideoLesson({ contentJson, onComplete, completing = false }: Props) {
  const [watched, setWatched] = useState(false);
  const isHosted = contentJson.video_source === 'hosted' && !!contentJson.video_url;
  const youtubeUrls = !isHosted && contentJson.youtube_id ? buildYouTubeUrls(contentJson.youtube_id) : null;

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

  return (
    <div className="space-y-4">
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
        ) : (
          <iframe
            src={youtubeUrls!.embed}
            title="Lesson video"
            referrerPolicy="strict-origin-when-cross-origin"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowFullScreen
            className="h-full w-full"
          />
        )}
      </div>
      {!isHosted && (
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
