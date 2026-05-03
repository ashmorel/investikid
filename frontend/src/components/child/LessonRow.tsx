import { Link } from 'react-router-dom';
import { Check, Play, Circle } from 'lucide-react';
import type { LessonSummary } from '@/api/content';

type Status = 'done' | 'next' | 'later';

export function LessonRow({ moduleId, lesson, status }: { moduleId: string; lesson: LessonSummary; status: Status }) {
  return (
    <Link
      to={`/lessons/${moduleId}/${lesson.id}`}
      className="flex items-center gap-3 border-b px-4 py-3 last:border-b-0 hover:bg-muted"
    >
      <StatusIcon status={status} />
      <div className="flex-1">
        <p className="font-medium">{lesson.order_index + 1}. {lesson.title}</p>
      </div>
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="rounded bg-muted px-2 py-0.5 capitalize">{lesson.type}</span>
        <span>{lesson.xp_reward} XP</span>
      </div>
    </Link>
  );
}

function StatusIcon({ status }: { status: Status }) {
  if (status === 'done') return <Check aria-label="completed" className="h-5 w-5 text-green-600" />;
  if (status === 'next') return <Play aria-label="next up" className="h-5 w-5 text-primary" />;
  return <Circle aria-label="not started" className="h-5 w-5 text-muted-foreground" />;
}
