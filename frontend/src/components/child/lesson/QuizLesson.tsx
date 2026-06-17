import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { OptionCard, type OptionState } from '@/components/child/ui/OptionCard';
import { GradientButton } from '@/components/child/ui/GradientButton';
import { FeedbackPanel } from '@/components/child/ui/FeedbackPanel';
import { playSound } from '@/lib/sound';
import { haptic } from '@/lib/haptics';

type QuizContent = { question: string; choices: string[]; answer_index: number; explanation: string };
type Props = { contentJson: QuizContent; onComplete: (score: number | null) => void; illustration?: React.ReactNode; onShowPenny?: () => void; completing?: boolean };
const LETTERS = ['A', 'B', 'C', 'D', 'E', 'F'];

export function QuizLesson({ contentJson, onComplete, illustration, onShowPenny, completing = false }: Props) {
  const { t } = useTranslation('lessons');
  const [selected, setSelected] = useState<number | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const isCorrect = selected === contentJson.answer_index;

  // Judge moment: sound + haptic fire here exactly once — the Check answer
  // button is replaced by the feedback panel after submit.
  function handleCheck() {
    playSound(isCorrect ? 'correct' : 'wrong');
    void haptic(isCorrect ? 'success' : 'warning');
    setSubmitted(true);
  }

  function optionState(i: number): OptionState {
    if (!submitted) return selected === i ? 'selected' : 'default';
    if (i === contentJson.answer_index) return 'correct';
    if (i === selected) return 'incorrect';
    return 'default';
  }

  return (
    <div className="space-y-5 rounded-3xl bg-white p-6 shadow-lg shadow-brand-600/10">
      {illustration && <div>{illustration}</div>}
      <p className="text-lg font-extrabold leading-snug text-gray-900">{contentJson.question}</p>
      <div className="space-y-3" role="radiogroup" aria-label={t('quiz.answerChoicesLabel')}>
        {contentJson.choices.map((choice, i) => (
          <OptionCard key={i} letter={LETTERS[i] ?? '?'} state={optionState(i)} checked={selected === i} disabled={submitted} onSelect={() => setSelected(i)}>
            {choice}
          </OptionCard>
        ))}
      </div>
      {submitted ? (
        <>
          <FeedbackPanel correct={isCorrect} explanation={contentJson.explanation} correctAnswer={!isCorrect ? contentJson.choices[contentJson.answer_index] : undefined} />
          <GradientButton full onClick={() => onComplete(isCorrect ? 1.0 : 0.0)} disabled={completing}>
            {completing ? t('quiz.saving') : t('quiz.continue')}
          </GradientButton>
        </>
      ) : (
        <div className="flex items-center justify-between gap-4">
          {onShowPenny ? (
            <button type="button" onClick={onShowPenny} className="text-sm font-bold text-brand-700 underline hover:text-brand-800">{t('quiz.askCoachPenny')}</button>
          ) : <span />}
          <GradientButton disabled={selected === null} onClick={handleCheck}>{t('quiz.checkAnswer')}</GradientButton>
        </div>
      )}
    </div>
  );
}
