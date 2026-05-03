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
};

export function QuizLesson({ contentJson, onComplete }: Props) {
  const [selected, setSelected] = useState<number | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const isCorrect = selected === contentJson.answer_index;

  return (
    <div className="space-y-4">
      <p className="text-lg font-medium">{contentJson.question}</p>
      <ul className="space-y-2" role="radiogroup">
        {contentJson.choices.map((choice, i) => {
          const showCorrect = submitted && i === contentJson.answer_index;
          const showWrongPick = submitted && i === selected && !isCorrect;
          return (
            <li key={i}>
              <label
                className={cn(
                  'flex cursor-pointer items-center gap-3 rounded-md border p-3',
                  selected === i && !submitted && 'border-primary',
                  showCorrect && 'border-green-600 bg-green-50',
                  showWrongPick && 'border-red-600 bg-red-50',
                  submitted && 'cursor-default',
                )}
              >
                <input
                  type="radio"
                  name="quiz"
                  aria-label={choice}
                  checked={selected === i}
                  onChange={() => setSelected(i)}
                  disabled={submitted}
                />
                <span>{choice}</span>
              </label>
            </li>
          );
        })}
      </ul>
      {submitted ? (
        <>
          <div className="rounded-md border bg-card p-3 text-sm">
            <p className="font-medium">{isCorrect ? 'Correct!' : 'Not quite.'}</p>
            <p className="mt-1 text-muted-foreground">{contentJson.explanation}</p>
          </div>
          <div className="flex justify-end">
            <Button onClick={() => onComplete(isCorrect ? 1.0 : 0.0)}>Continue →</Button>
          </div>
        </>
      ) : (
        <div className="flex justify-end">
          <Button disabled={selected === null} onClick={() => setSubmitted(true)}>Submit</Button>
        </div>
      )}
    </div>
  );
}
