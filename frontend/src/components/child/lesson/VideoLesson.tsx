import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Disclosure } from '@/components/a11y/Disclosure';

type Props = {
  contentJson: {
    youtube_id?: string;
    caption?: string;
    transcript?: string;
    captions_available?: boolean;
  };
  onComplete: (score: number | null) => void;
};

export function VideoLesson({ contentJson, onComplete }: Props) {
  const [watched, setWatched] = useState(false);

  if (!contentJson.youtube_id) {
    return (
      <div className="space-y-4">
        <p>Video unavailable.</p>
        <div className="flex justify-end">
          <Button onClick={() => onComplete(null)}>Continue →</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="aspect-video overflow-hidden rounded-md border">
        <iframe
          src={`https://www.youtube-nocookie.com/embed/${contentJson.youtube_id}`}
          title="Lesson video"
          allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
          className="h-full w-full"
        />
      </div>
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
        <Button disabled={!watched} onClick={() => onComplete(null)}>Mark complete →</Button>
      </div>
    </div>
  );
}
