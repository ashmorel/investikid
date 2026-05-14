import { Link } from 'react-router-dom';
import type { LessonCompletionResult } from '@/api/content';
import { Button } from '@/components/ui/button';
import { Trophy } from './illustrations/Trophy';

type Props = {
  result: LessonCompletionResult;
  moduleId: string;
  nextLessonId: string | null;
};

export function CompletionPanel({ result, moduleId, nextLessonId }: Props) {
  const heading = result.already_completed ? "You've already done this one" : 'Quest Complete!';
  const xpInLevel = result.total_xp % 100;
  return (
    <div className="rounded-2xl border-2 border-amber-200 bg-white p-8 text-center space-y-4">
      <Trophy />
      <h2 className="text-2xl font-extrabold text-gray-900">{heading}</h2>
      {!result.already_completed && (
        <p className="text-3xl font-extrabold bg-gradient-to-r from-amber-400 to-orange-500 bg-clip-text text-transparent">
          +{result.xp_awarded} XP
        </p>
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
          <div className="h-full rounded-full bg-gradient-to-r from-amber-400 to-orange-500" style={{ width: `${xpInLevel}%` }} />
        </div>
        <p className="mt-1 text-xs text-gray-500">{xpInLevel} / 100 XP to Level {result.level + 1}</p>
      </div>
      <div className="flex justify-center gap-2 pt-2">
        {nextLessonId ? (
          <Button asChild className="bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-500 hover:to-orange-600 text-white font-bold rounded-xl">
            <Link to={`/lessons/${moduleId}/${nextLessonId}`}>Next Quest →</Link>
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
