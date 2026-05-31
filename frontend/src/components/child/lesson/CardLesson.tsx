import { Button } from '@/components/ui/button';

type Props = {
  contentJson: { title?: string; body?: string };
  onComplete: (score: number | null) => void;
  illustration?: React.ReactNode;
  completing?: boolean;
};

export function CardLesson({ contentJson, onComplete, illustration, completing = false }: Props) {
  return (
    <div className="rounded-2xl border-2 border-amber-200 bg-white p-6 space-y-5">
      {illustration && <div>{illustration}</div>}
      <h2 className="text-xl font-extrabold text-gray-900">{contentJson.title ?? ''}</h2>
      <p className="leading-relaxed text-gray-700">{contentJson.body ?? ''}</p>
      <div className="flex justify-end">
        <Button
          onClick={() => onComplete(null)}
          disabled={completing}
          className="bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-500 hover:to-orange-600 text-white font-bold rounded-xl"
        >{completing ? 'Saving...' : 'Got it →'}</Button>
      </div>
    </div>
  );
}
