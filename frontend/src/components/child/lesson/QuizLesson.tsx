import { useState } from 'react';
import { OptionCard, type OptionState } from '@/components/child/ui/OptionCard';
import { GradientButton } from '@/components/child/ui/GradientButton';
import { FeedbackPanel } from '@/components/child/ui/FeedbackPanel';

type QuizContent = { question: string; choices: string[]; answer_index: number; explanation: string };
type Props = { contentJson: QuizContent; onComplete: (score: number | null) => void; illustration?: React.ReactNode; onShowEddie?: () => void; completing?: boolean };
const LETTERS = ['A', 'B', 'C', 'D', 'E', 'F'];

export function QuizLesson({ contentJson, onComplete, illustration, onShowEddie, completing = false }: Props) {
  const [selected, setSelected] = useState<number | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const isCorrect = selected === contentJson.answer_index;

  function optionState(i: number): OptionState {
    if (!submitted) return selected === i ? 'selected' : 'default';
    if (i === contentJson.answer_index) return 'correct';
    if (i === selected) return 'incorrect';
    return 'default';
  }

  return (
    <div className="space-y-5 rounded-3xl bg-white p-6 shadow-lg shadow-orange-500/10">
      {illustration && <div>{illustration}</div>}
      <p className="text-lg font-extrabold leading-snug text-gray-900">{contentJson.question}</p>
      <div className="space-y-3" role="radiogroup" aria-label="Answer choices">
        {contentJson.choices.map((choice, i) => (
          <OptionCard key={i} letter={LETTERS[i] ?? '?'} state={optionState(i)} disabled={submitted} onSelect={() => setSelected(i)}>
            {choice}
          </OptionCard>
        ))}
      </div>
      {submitted ? (
        <>
          <FeedbackPanel correct={isCorrect} explanation={contentJson.explanation} correctAnswer={!isCorrect ? contentJson.choices[contentJson.answer_index] : undefined} />
          <GradientButton full onClick={() => onComplete(isCorrect ? 1.0 : 0.0)} disabled={completing}>
            {completing ? 'Saving…' : 'Continue →'}
          </GradientButton>
        </>
      ) : (
        <div className="flex items-center justify-between gap-4">
          {onShowEddie ? (
            <button type="button" onClick={onShowEddie} className="text-sm font-bold text-amber-600 underline hover:text-amber-700">Ask Coach Eddie</button>
          ) : <span />}
          <GradientButton disabled={selected === null} onClick={() => setSubmitted(true)}>Check answer</GradientButton>
        </div>
      )}
    </div>
  );
}
