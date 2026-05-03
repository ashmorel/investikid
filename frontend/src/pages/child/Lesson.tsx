import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { contentApi, type LessonOut, type LessonSummary, type LessonCompletionResult } from '@/api/content';
import { CardLesson } from '@/components/child/lesson/CardLesson';
import { QuizLesson } from '@/components/child/lesson/QuizLesson';
import { ScenarioLesson } from '@/components/child/lesson/ScenarioLesson';
import { VideoLesson } from '@/components/child/lesson/VideoLesson';
import { CompletionPanel } from '@/components/child/lesson/CompletionPanel';
import { useToast } from '@/hooks/use-toast';

export default function Lesson() {
  const { moduleId, lessonId } = useParams<{ moduleId: string; lessonId: string }>();
  const qc = useQueryClient();
  const { toast } = useToast();

  const lessonQ = useQuery<LessonOut | null>({
    queryKey: ['lesson', lessonId],
    queryFn: () => contentApi.getLesson(lessonId!),
    enabled: !!lessonId, retry: false,
  });

  const lessonsQ = useQuery<LessonSummary[] | null>({
    queryKey: ['module', moduleId, 'lessons'],
    queryFn: () => contentApi.listLessons(moduleId!),
    enabled: !!moduleId, retry: false, staleTime: 60_000,
  });

  const complete = useMutation<LessonCompletionResult | null, Error, number | null>({
    mutationFn: (score) => contentApi.completeLesson(lessonId!, score),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['progress'] });
      qc.invalidateQueries({ queryKey: ['module', moduleId, 'lessons'] });
      qc.invalidateQueries({ queryKey: ['modules'] });
    },
    onError: () => {
      toast({ title: 'Could not save your progress', description: 'Try again.' });
    },
  });

  if (lessonQ.isLoading) {
    return <div className="mx-auto max-w-2xl p-6 text-sm text-muted-foreground">Loading…</div>;
  }
  if (lessonQ.isError || !lessonQ.data) {
    return (
      <div className="mx-auto max-w-2xl p-6">
        <p>Lesson not found.</p>
        <Link to={`/lessons/${moduleId ?? ''}`} className="text-sm underline">← Back to module</Link>
      </div>
    );
  }

  const lesson = lessonQ.data;
  const lessons = (lessonsQ.data ?? []) as LessonSummary[];
  const total = lessons.length;
  const positionLabel = total > 0
    ? `Lesson ${lesson.order_index + 1} of ${total}`
    : `Lesson ${lesson.order_index + 1}`;

  if (complete.isSuccess && complete.data) {
    const idx = lessons.findIndex((l) => l.id === lesson.id);
    const next = lessons.slice(idx + 1).find((l) => !l.completed) ?? null;
    return (
      <div className="mx-auto max-w-2xl p-6">
        <CompletionPanel
          result={complete.data}
          moduleId={moduleId!}
          nextLessonId={next?.id ?? null}
        />
      </div>
    );
  }

  if (complete.isError) {
    return (
      <div className="mx-auto max-w-2xl p-6 space-y-4">
        <p>Something went wrong saving your progress.</p>
        <button
          type="button"
          className="rounded bg-primary px-3 py-1 text-sm text-primary-foreground"
          onClick={() => complete.reset()}
        >Try again</button>
      </div>
    );
  }

  const onComplete = (score: number | null) => complete.mutate(score);

  return (
    <div className="mx-auto max-w-2xl p-6">
      <header className="mb-4 flex items-center justify-between text-sm text-muted-foreground">
        <span>{positionLabel}</span>
        <span className="rounded bg-muted px-2 py-0.5">{lesson.xp_reward} XP</span>
      </header>
      {lesson.type === 'card' && <CardLesson contentJson={lesson.content_json as { title?: string; body?: string }} onComplete={onComplete} />}
      {lesson.type === 'quiz' && <QuizLesson contentJson={lesson.content_json as { question: string; choices: string[]; answer_index: number; explanation: string }} onComplete={onComplete} />}
      {lesson.type === 'scenario' && <ScenarioLesson contentJson={lesson.content_json as { prompt: string; choices: { label: string; outcome: string }[]; correct_index: number }} onComplete={onComplete} />}
      {lesson.type === 'video' && <VideoLesson contentJson={lesson.content_json as { youtube_id?: string; caption?: string }} onComplete={onComplete} />}
    </div>
  );
}
