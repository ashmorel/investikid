import { cn } from '@/lib/utils';

type Props = { correct: boolean; explanation: string; correctAnswer?: string };

export function FeedbackPanel({ correct, explanation, correctAnswer }: Props) {
  return (
    <div className={cn('rounded-2xl p-4', correct ? 'bg-green-50' : 'bg-red-50')}>
      <div className="flex items-center gap-2">
        <span className={cn('flex h-7 w-7 items-center justify-center rounded-full text-base font-extrabold text-white', correct ? 'bg-green-600' : 'bg-red-500')} aria-hidden="true">{correct ? '✓' : '✕'}</span>
        <p className={cn('text-lg font-extrabold', correct ? 'text-green-700' : 'text-red-700')}>{correct ? 'Correct!' : 'Not quite!'}</p>
      </div>
      {!correct && correctAnswer && <p className="mt-2 text-sm font-bold text-red-700">Correct answer: {correctAnswer}</p>}
      <p className="mt-2 text-sm leading-relaxed text-gray-700">{explanation}</p>
    </div>
  );
}
