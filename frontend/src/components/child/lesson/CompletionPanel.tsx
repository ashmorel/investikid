import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion, useMotionValue, useTransform, animate } from 'framer-motion';
import confetti from 'canvas-confetti';
import type { LessonCompletionResult } from '@/api/content';
import { Button } from '@/components/ui/button';
import { Trophy } from './illustrations/Trophy';

type Props = {
  result: LessonCompletionResult;
  moduleId: string;
  levelId: string;
  nextLessonId: string | null;
};

export function CompletionPanel({ result, moduleId, levelId, nextLessonId }: Props) {
  const heading = result.already_completed ? "You've already done this one" : 'Quest Complete!';
  const xpInLevel = result.total_xp % 100;

  const xpCount = useMotionValue(0);
  const xpDisplay = useTransform(xpCount, (v) => `+${Math.round(v)} XP`);

  useEffect(() => {
    if (!result.already_completed) {
      confetti({ particleCount: 80, spread: 60, origin: { y: 0.7 } });
      animate(xpCount, result.xp_awarded, { duration: 0.6 });
    }
  }, [result.already_completed, result.xp_awarded, xpCount]);

  return (
    <div className="rounded-2xl border-2 border-amber-200 bg-white p-8 text-center space-y-4">
      <motion.div
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 200, damping: 15, delay: 0.1 }}
      >
        <Trophy />
      </motion.div>
      <h2 className="text-2xl font-extrabold text-gray-900">{heading}</h2>
      {!result.already_completed && (
        <motion.p className="text-3xl font-extrabold bg-gradient-to-r from-amber-400 to-orange-500 bg-clip-text text-transparent">
          {xpDisplay}
        </motion.p>
      )}
      <div className="flex justify-center gap-3 text-sm text-gray-500">
        <span>Total: {result.total_xp} XP</span>
        <span>·</span>
        <span>Level {result.level}</span>
        <span>·</span>
        <span>🔥 {result.streak_count}-day streak</span>
      </div>
      <div className="mx-auto max-w-[240px]">
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
      <div className="flex justify-center gap-2 pt-2">
        {nextLessonId ? (
          <Button asChild className="bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-500 hover:to-orange-600 text-white font-bold rounded-xl">
            <Link to={`/lessons/${moduleId}/${levelId}/${nextLessonId}`}>Next Quest →</Link>
          </Button>
        ) : (
          <Button asChild className="bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-500 hover:to-orange-600 text-white font-bold rounded-xl">
            <Link to={`/lessons/${moduleId}`}>Back to module</Link>
          </Button>
        )}
      </div>
    </div>
  );
}
