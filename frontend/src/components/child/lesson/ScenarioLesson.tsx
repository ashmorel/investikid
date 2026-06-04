import { useState } from 'react';
import { OptionCard, type OptionState } from '@/components/child/ui/OptionCard';
import { GradientButton } from '@/components/child/ui/GradientButton';
import { FeedbackPanel } from '@/components/child/ui/FeedbackPanel';

type ScenarioContent = {
  prompt: string;
  choices: { label: string; outcome: string }[];
  correct_index: number;
};

type Props = {
  contentJson: ScenarioContent;
  onComplete: (score: number | null) => void;
  illustration?: React.ReactNode;
  onShowPenny?: () => void;
  completing?: boolean;
};

const LETTERS = ['A', 'B', 'C', 'D', 'E', 'F'];

export function ScenarioLesson({ contentJson, onComplete, illustration, onShowPenny, completing = false }: Props) {
  const [selected, setSelected] = useState<number | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const isCorrect = selected === contentJson.correct_index;

  function optionState(i: number): OptionState {
    if (!submitted) return selected === i ? 'selected' : 'default';
    if (i === contentJson.correct_index) return 'correct';
    if (i === selected) return 'incorrect';
    return 'default';
  }

  return (
    <div className="space-y-5 rounded-3xl bg-white p-6 shadow-lg shadow-brand-600/10">
      {illustration && <div>{illustration}</div>}
      <span className="inline-block rounded-full bg-violet-100 px-3 py-1.5 text-[11px] font-extrabold text-violet-700"><span aria-hidden="true">🧠 </span>Real-life scenario</span>
      <p className="text-lg font-extrabold leading-snug text-gray-900">{contentJson.prompt}</p>
      <div className="space-y-3" role="radiogroup" aria-label="Answer choices">
        {contentJson.choices.map((choice, i) => (
          <OptionCard key={i} letter={LETTERS[i] ?? '?'} state={optionState(i)} checked={selected === i} disabled={submitted} onSelect={() => setSelected(i)}>
            {choice.label}
          </OptionCard>
        ))}
      </div>
      {submitted ? (
        <>
          <FeedbackPanel correct={isCorrect} explanation={contentJson.choices[selected!].outcome} correctAnswer={!isCorrect ? contentJson.choices[contentJson.correct_index].label : undefined} />
          <GradientButton full onClick={() => onComplete(isCorrect ? 1.0 : 0.0)} disabled={completing}>
            {completing ? 'Saving…' : 'Continue →'}
          </GradientButton>
        </>
      ) : (
        <div className="flex items-center justify-between gap-4">
          {onShowPenny ? (
            <button type="button" onClick={onShowPenny} className="text-sm font-bold text-brand-700 underline hover:text-brand-800">Ask Coach Penny</button>
          ) : <span />}
          <GradientButton disabled={selected === null} onClick={() => setSubmitted(true)}>Check answer</GradientButton>
        </div>
      )}
    </div>
  );
}
