import { useState } from 'react';
import { Button } from '@/components/ui/button';

type Props = {
  contentJson: { youtube_id?: string; caption?: string };
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
