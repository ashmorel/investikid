import { GradientButton } from '@/components/child/ui/GradientButton';

type Props = { contentJson: { title?: string; body?: string }; onComplete: (score: number | null) => void; illustration?: React.ReactNode; completing?: boolean };

export function CardLesson({ contentJson, onComplete, illustration, completing = false }: Props) {
  return (
    <div className="space-y-5 rounded-3xl bg-white p-7 text-center shadow-lg shadow-orange-500/10">
      {illustration && <div className="flex justify-center">{illustration}</div>}
      <h2 className="text-2xl font-extrabold leading-tight text-gray-900">{contentJson.title ?? ''}</h2>
      <p className="text-[15px] leading-relaxed text-gray-600">{contentJson.body ?? ''}</p>
      <GradientButton full onClick={() => onComplete(null)} disabled={completing}>{completing ? 'Saving…' : 'Got it →'}</GradientButton>
    </div>
  );
}
