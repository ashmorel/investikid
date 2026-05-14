import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

type ScenarioContent = {
  prompt: string;
  choices: { label: string; outcome: string }[];
  correct_index: number;
};

type Props = {
  contentJson: ScenarioContent;
  onComplete: (score: number | null) => void;
  illustration?: React.ReactNode;
  onShowEddie?: () => void;
};

export function ScenarioLesson({ contentJson, onComplete, illustration, onShowEddie }: Props) {
  const [selected, setSelected] = useState<number | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const isCorrect = selected === contentJson.correct_index;

  return (
    <div className="rounded-2xl border-2 border-amber-200 bg-white p-6 space-y-5">
      {illustration && <div>{illustration}</div>}
      <p className="text-base italic text-gray-500 leading-relaxed">{contentJson.prompt}</p>
      <ul className="space-y-2" role="radiogroup">
        {contentJson.choices.map((choice, i) => {
          const showCorrect = submitted && i === contentJson.correct_index;
          const showPickedWrong = submitted && i === selected && !isCorrect;
          return (
            <li key={i} className="space-y-1">
              <label
                className={cn(
                  'flex cursor-pointer items-center gap-3 rounded-xl border-2 p-3 transition-colors',
                  !submitted && selected === i && 'border-amber-400 bg-amber-50',
                  !submitted && selected !== i && 'border-gray-200',
                  showCorrect && 'border-green-500 bg-green-50',
                  showPickedWrong && 'border-red-500 bg-red-50',
                  submitted && 'cursor-default',
                )}
              >
                <div className={cn(
                  'h-5 w-5 shrink-0 rounded-full border-2',
                  !submitted && selected === i && 'bg-gradient-to-br from-amber-400 to-orange-500 border-amber-400',
                  !submitted && selected !== i && 'border-gray-300',
                  showCorrect && 'bg-green-500 border-green-500',
                  showPickedWrong && 'bg-red-500 border-red-500',
                )} />
                <input
                  type="radio"
                  name="scenario"
                  aria-label={choice.label}
                  checked={selected === i}
                  onChange={() => setSelected(i)}
                  disabled={submitted}
                  className="sr-only"
                />
                <span className={cn('text-sm', submitted && (showCorrect || (i === selected)) && 'font-semibold')}>{choice.label}</span>
              </label>
              {submitted && (showCorrect || showPickedWrong) && (
                <p className="ml-9 text-sm text-gray-500">{choice.outcome}</p>
              )}
            </li>
          );
        })}
      </ul>
      {submitted ? (
        <div className="flex justify-end">
          <Button
            onClick={() => onComplete(isCorrect ? 1.0 : 0.0)}
            className="bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-500 hover:to-orange-600 text-white font-bold rounded-xl"
          >Continue →</Button>
        </div>
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
