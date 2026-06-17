import { motion, useReducedMotion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';

type Props = { correct: boolean; explanation: string; correctAnswer?: string };

export function FeedbackPanel({ correct, explanation, correctAnswer }: Props) {
  const { t } = useTranslation('lessons');
  const reducedMotion = useReducedMotion();
  // Juice pack (spec C/D): correct → check pop, wrong → gentle wiggle. Both off under reduced motion.
  const wiggle = !correct && !reducedMotion ? { x: [0, -7, 7, -4, 4, 0] } : undefined;
  const pop = correct && !reducedMotion;

  return (
    <motion.div
      className={cn('rounded-2xl p-4', correct ? 'bg-success-50' : 'bg-danger-50')}
      animate={wiggle}
      transition={{ duration: 0.4, ease: 'easeInOut' }}
    >
      <div className="flex items-center gap-2">
        <motion.span
          className={cn('flex h-7 w-7 items-center justify-center rounded-full text-base font-extrabold text-white', correct ? 'bg-success-600' : 'bg-danger-500')}
          aria-hidden="true"
          initial={pop ? { scale: 0 } : false}
          animate={pop ? { scale: [0, 1.15, 1] } : undefined}
          transition={{ duration: 0.35, ease: 'easeOut' }}
        >
          {correct ? '✓' : '✕'}
        </motion.span>
        <p className={cn('text-lg font-extrabold', correct ? 'text-success-700' : 'text-danger-700')}>{correct ? t('feedback.correct') : t('feedback.notQuite')}</p>
      </div>
      {!correct && correctAnswer && <p className="mt-2 text-sm font-bold text-danger-700">{t('feedback.correctAnswer', { answer: correctAnswer })}</p>}
      <p className="mt-2 text-sm leading-relaxed text-gray-700">{explanation}</p>
    </motion.div>
  );
}
