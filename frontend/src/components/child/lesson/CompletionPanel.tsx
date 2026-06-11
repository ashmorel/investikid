import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import confetti from 'canvas-confetti';
import type { LessonCompletionResult } from '@/api/content';
import { StatChip } from '@/components/child/ui/StatChip';
import { XpCountUp } from '@/components/child/ui/XpCountUp';
import { GradientButton } from '@/components/child/ui/GradientButton';
import { playSound } from '@/lib/sound';
import { haptic } from '@/lib/haptics';

type Props = {
  result: LessonCompletionResult;
  onContinue: () => void;
};

export function CompletionPanel({ result, onContinue }: Props) {
  const heading = result.already_completed ? "You've already done this one" : 'Lesson complete!';
  const xpInLevel = result.total_xp % 100;

  // One-shot celebration on mount (juice pack, spec C). Ref-guarded so
  // re-renders never replay it; skipped entirely for repeat completions.
  const celebrated = useRef(false);
  useEffect(() => {
    if (result.already_completed || celebrated.current) return;
    celebrated.current = true;
    playSound('lessonComplete');
    void haptic('success');
    if (
      typeof window !== 'undefined' &&
      !window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    ) {
      confetti({ particleCount: 80, spread: 60, origin: { y: 0.7 } });
    }
  }, [result.already_completed]);

  return (
    <div className="flex flex-col items-center gap-4 text-center rounded-2xl border-2 border-brand-200 bg-white p-8">
      <motion.div
        className="flex h-24 w-24 items-center justify-center rounded-full bg-brand-gradient text-4xl shadow-lg shadow-brand-600/40"
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 200, damping: 15, delay: 0.1 }}
      >
        <span aria-hidden="true">⭐</span>
      </motion.div>

      <h2 className="text-2xl font-extrabold text-gray-900">{heading}</h2>

      <div className="text-2xl" aria-hidden="true">⭐ ⭐ ⭐</div>

      <div className="flex w-full gap-3">
        <StatChip emoji="⭐" value={<XpCountUp value={result.xp_awarded} />} label="XP" />
        <StatChip emoji="🏆" value={String(result.level)} label="Level" />
        <StatChip emoji="🔥" value={String(result.streak_count)} label="Streak" />
      </div>

      <div className="w-full max-w-[240px]">
        <div className="h-2 w-full overflow-hidden rounded-full bg-brand-100">
          <motion.div
            className="h-full rounded-full bg-brand-gradient"
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
