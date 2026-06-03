import { useEffect } from 'react';
import { motion } from 'framer-motion';
import confetti from 'canvas-confetti';
import type { LessonCompletionResult } from '@/api/content';
import { StatChip } from '@/components/child/ui/StatChip';
import { GradientButton } from '@/components/child/ui/GradientButton';

type Props = {
  result: LessonCompletionResult;
  onContinue: () => void;
};

export function CompletionPanel({ result, onContinue }: Props) {
  const heading = result.already_completed ? "You've already done this one" : 'Lesson complete!';
  const xpInLevel = result.total_xp % 100;

  useEffect(() => {
    if (!result.already_completed) {
      if (
        typeof window !== 'undefined' &&
        !window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
      ) {
        confetti({ particleCount: 80, spread: 60, origin: { y: 0.7 } });
      }
    }
  }, [result.already_completed]);

  return (
    <div className="flex flex-col items-center gap-4 text-center rounded-2xl border-2 border-amber-200 bg-white p-8">
      <motion.div
        className="flex h-24 w-24 items-center justify-center rounded-full bg-gradient-to-br from-amber-400 to-orange-500 text-4xl shadow-lg shadow-orange-500/40"
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 200, damping: 15, delay: 0.1 }}
      >
        <span aria-hidden="true">⭐</span>
      </motion.div>

      <h2 className="text-2xl font-extrabold text-gray-900">{heading}</h2>

      <div className="text-2xl" aria-hidden="true">⭐ ⭐ ⭐</div>

      <div className="flex w-full gap-3">
        <StatChip emoji="⭐" value={`+${result.xp_awarded}`} label="XP" />
        <StatChip emoji="🏆" value={String(result.level)} label="Level" />
        <StatChip emoji="🔥" value={String(result.streak_count)} label="Streak" />
      </div>

      <div className="w-full max-w-[240px]">
        <div className="h-2 w-full overflow-hidden rounded-full bg-amber-100">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-amber-400 to-orange-500"
            initial={{ width: 0 }}
            animate={{ width: `${xpInLevel}%` }}
            transition={{ duration: 0.8, delay: 0.3 }}
          />
        </div>
        <p className="mt-1 text-xs text-gray-500">{xpInLevel} / 100 XP to Level {result.level + 1}</p>
      </div>

      <GradientButton full onClick={onContinue}>
        Continue <span aria-hidden="true">→</span>
      </GradientButton>
    </div>
  );
}
