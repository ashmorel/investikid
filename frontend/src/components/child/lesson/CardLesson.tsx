import { Button } from '@/components/ui/button';

type Props = {
  contentJson: { title?: string; body?: string };
  onComplete: (score: number | null) => void;
};

export function CardLesson({ contentJson, onComplete }: Props) {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">{contentJson.title ?? ''}</h2>
      <p className="leading-relaxed">{contentJson.body ?? ''}</p>
      <div className="flex justify-end">
        <Button onClick={() => onComplete(null)}>Got it →</Button>
      </div>
    </div>
  );
}
