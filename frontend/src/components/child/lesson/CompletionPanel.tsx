import { Link } from 'react-router-dom';
import type { LessonCompletionResult } from '@/api/content';
import { Button } from '@/components/ui/button';

type Props = {
  result: LessonCompletionResult;
  moduleId: string;
  nextLessonId: string | null;
};

export function CompletionPanel({ result, moduleId, nextLessonId }: Props) {
  const heading = result.already_completed ? "You've already done this one" : 'Great work!';
  return (
    <div className="space-y-4 rounded-lg border bg-card p-6 text-center">
      <h2 className="text-xl font-semibold">{heading}</h2>
      {!result.already_completed && (
        <p className="text-2xl">⭐ +{result.xp_awarded} XP</p>
      )}
      <p className="text-sm text-muted-foreground">
        Total: {result.total_xp} XP · Level {result.level} · 🔥 {result.streak_count}-day streak
      </p>
      <div className="flex justify-center gap-2">
        {nextLessonId ? (
          <Button asChild>
            <Link to={`/lessons/${moduleId}/${nextLessonId}`}>Next lesson →</Link>
          </Button>
        ) : (
          <Button asChild>
            <Link to={`/lessons/${moduleId}`}>Back to module</Link>
          </Button>
        )}
      </div>
    </div>
  );
}
