import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

type QuizContent = {
  question: string;
  choices: string[];
  answer_index: number;
  explanation: string;
};

type Props = {
  contentJson: QuizContent;
  onComplete: (score: number | null) => void;
  illustration?: React.ReactNode;
  onShowEddie?: () => void;
  completing?: boolean;
};

export function QuizLesson({ contentJson, onComplete, illustration, onShowEddie, completing = false }: Props) {
  const [selected, setSelected] = useState<number | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const isCorrect = selected === contentJson.answer_index;

  return (
    <div className="rounded-2xl border-2 border-amber-200 bg-white p-6 space-y-5">
      {illustration && <div>{illustration}</div>}
      <p className="text-lg font-bold text-gray-900">{contentJson.question}</p>
      <div className="space-y-2" role="radiogroup">
        {contentJson.choices.map((choice, i) => {
          const showCorrect = submitted && i === contentJson.answer_index;
          const showWrongPick = submitted && i === selected && !isCorrect;
          return (
            <div key={i}>
              <label
                className={cn(
                  'flex cursor-pointer items-center gap-3 rounded-xl border-2 p-3 transition-all active:scale-[0.98]',
                  !submitted && selected === i && 'border-amber-400 bg-amber-50',
                  !submitted && selected !== i && 'border-gray-200',
                  showCorrect && 'border-green-500 bg-green-50',
                  showWrongPick && 'border-red-500 bg-red-50',
                  submitted && 'cursor-default',
                )}
              >
                <div className={cn(
                  'h-5 w-5 shrink-0 rounded-full border-2',
                  !submitted && selected === i && 'bg-gradient-to-br from-amber-400 to-orange-500 border-amber-400',
                  !submitted && selected !== i && 'border-gray-300',
                  showCorrect && 'bg-green-500 border-green-500',
                  showWrongPick && 'bg-red-500 border-red-500',
                )} />
                <input
                  type="radio"
                  name="quiz"
                  aria-label={choice}
                  checked={selected === i}
                  onChange={() => setSelected(i)}
                  disabled={submitted}
                  className="sr-only"
                />
                <span className={cn('text-sm', submitted && (showCorrect || (i === selected)) && 'font-semibold')}>{choice}</span>
              </label>
            </div>
          );
        })}
      </div>
      {submitted ? (
        <>
          <div className="rounded-xl border-2 border-amber-200 bg-amber-50 p-4 text-sm">
            <p className="font-bold text-gray-900">{isCorrect ? '✅ Correct!' : '❌ Not quite.'}</p>
            <p className="mt-1 text-gray-600">{contentJson.explanation}</p>
          </div>
          <div className="flex justify-end">
            <Button
              onClick={() => onComplete(isCorrect ? 1.0 : 0.0)}
              disabled={completing}
              className="bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-500 hover:to-orange-600 text-white font-bold rounded-xl"
            >{completing ? 'Saving...' : 'Continue →'}</Button>
          </div>
        </>
      ) : (
        <div className="flex justify-end items-center gap-4">
          {onShowEddie && (
            <button
              type="button"
              onClick={onShowEddie}
              className="text-sm text-amber-600 hover:text-amber-700 underline"
            >
              💡 Ask Coach Eddie
            </button>
          )}
          <Button
            disabled={selected === null}
            onClick={() => setSubmitted(true)}
            className="bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-500 hover:to-orange-600 text-white font-bold rounded-xl disabled:opacity-50"
          >Submit</Button>
        </div>
      )}
    </div>
  );
}
