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
};

export function ScenarioLesson({ contentJson, onComplete }: Props) {
  const [selected, setSelected] = useState<number | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const isCorrect = selected === contentJson.correct_index;

  return (
    <div className="space-y-4">
      <p className="italic text-muted-foreground">{contentJson.prompt}</p>
      <ul className="space-y-2" role="radiogroup">
        {contentJson.choices.map((choice, i) => {
          const showCorrect = submitted && i === contentJson.correct_index;
          const showPickedWrong = submitted && i === selected && !isCorrect;
          return (
            <li key={i} className="space-y-1">
              <label
                className={cn(
                  'flex cursor-pointer items-center gap-3 rounded-md border p-3',
                  selected === i && !submitted && 'border-primary',
                  showCorrect && 'border-green-600 bg-green-50',
                  showPickedWrong && 'border-red-600 bg-red-50',
                  submitted && 'cursor-default',
                )}
              >
                <input
                  type="radio"
                  name="scenario"
                  aria-label={choice.label}
                  checked={selected === i}
                  onChange={() => setSelected(i)}
                  disabled={submitted}
                />
                <span>{choice.label}</span>
              </label>
              {submitted && (showCorrect || showPickedWrong) && (
                <p className="ml-9 text-sm text-muted-foreground">{choice.outcome}</p>
              )}
            </li>
          );
        })}
      </ul>
      {submitted ? (
        <div className="flex justify-end">
          <Button onClick={() => onComplete(isCorrect ? 1.0 : 0.0)}>Continue →</Button>
        </div>
      ) : (
        <div className="flex justify-end">
          <Button disabled={selected === null} onClick={() => setSubmitted(true)}>Submit</Button>
        </div>
      )}
    </div>
  );
}
