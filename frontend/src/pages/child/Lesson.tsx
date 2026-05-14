import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { contentApi, type LessonOut, type LessonSummary, type LessonCompletionResult, type ModuleOut } from '@/api/content';
import { CardLesson } from '@/components/child/lesson/CardLesson';
import { QuizLesson } from '@/components/child/lesson/QuizLesson';
import { ScenarioLesson } from '@/components/child/lesson/ScenarioLesson';
import { VideoLesson } from '@/components/child/lesson/VideoLesson';
import { CompletionPanel } from '@/components/child/lesson/CompletionPanel';
import { LessonIllustration } from '@/components/child/lesson/LessonIllustration';
import { PracticeQuiz } from '@/components/child/lesson/PracticeQuiz';
import { CoachEddiePanel } from '@/components/child/lesson/CoachEddiePanel';
import { useToast } from '@/hooks/use-toast';

export default function Lesson() {
  const { moduleId, lessonId } = useParams<{ moduleId: string; lessonId: string }>();
  const qc = useQueryClient();
  const { toast } = useToast();
  const [showPractice, setShowPractice] = useState(false);
  const [showEddie, setShowEddie] = useState(false);

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

  const modulesQ2 = useQuery<ModuleOut[] | null>({
    queryKey: ['modules'],
    queryFn: () => contentApi.listModules(),
    retry: false, staleTime: 60_000,
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

  // Reset mutation state when navigating to a different lesson so the
  // CompletionPanel from the previous lesson doesn't flash on screen.
  useEffect(() => {
    complete.reset();
    setShowPractice(false);
    setShowEddie(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lessonId]);

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

  if (complete.isSuccess && complete.data) {
    const idx = lessons.findIndex((l) => l.id === lesson.id);
    const next = lessons.slice(idx + 1).find((l) => !l.completed) ?? null;

    if (showPractice) {
      return (
        <div className="mx-auto max-w-2xl p-6">
          <PracticeQuiz lessonId={lessonId!} onClose={() => setShowPractice(false)} />
        </div>
      );
    }

    return (
      <div className="mx-auto max-w-2xl p-6">
        <CompletionPanel
          result={complete.data}
          moduleId={moduleId!}
          nextLessonId={next?.id ?? null}
        />
        {complete.data.practice_available && !complete.data.already_completed && (
          <div className="mt-4 text-center">
            <button
              onClick={() => setShowPractice(true)}
              className="text-sm text-amber-600 hover:text-amber-700 underline font-medium"
            >
              🎯 Practice this topic
            </button>
          </div>
        )}
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

  const currentModule = (modulesQ2.data ?? []).find((m) => m.id === moduleId);
  const topic = currentModule?.topic ?? 'stocks';
  const lessonTitle = lesson.type === 'card'
    ? (lesson.content_json as { title?: string }).title ?? ''
    : lesson.type === 'quiz'
    ? (lesson.content_json as { question?: string }).question ?? ''
    : lesson.type === 'scenario'
    ? (lesson.content_json as { prompt?: string }).prompt ?? ''
    : '';
  const illustration = <LessonIllustration lessonTitle={lessonTitle} topic={topic} />;

  return (
    <div className="mx-auto max-w-2xl p-6">
      <header className="mb-4 flex items-center justify-between text-sm text-gray-500">
        <span>Quest {lesson.order_index + 1} of {total || '…'}</span>
        <span className="rounded-lg bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-800">🏆 {lesson.xp_reward} XP</span>
      </header>
      {lesson.type === 'card' && <CardLesson contentJson={lesson.content_json as { title?: string; body?: string }} onComplete={onComplete} illustration={illustration} />}
      {lesson.type === 'quiz' && <QuizLesson contentJson={lesson.content_json as { question: string; choices: string[]; answer_index: number; explanation: string }} onComplete={onComplete} illustration={illustration} onShowEddie={() => setShowEddie(true)} />}
      {lesson.type === 'scenario' && <ScenarioLesson contentJson={lesson.content_json as { prompt: string; choices: { label: string; outcome: string }[]; correct_index: number }} onComplete={onComplete} illustration={illustration} onShowEddie={() => setShowEddie(true)} />}
      {lesson.type === 'video' && <VideoLesson contentJson={lesson.content_json as { youtube_id?: string; caption?: string }} onComplete={onComplete} />}
      {showEddie && <CoachEddiePanel lessonId={lessonId!} onClose={() => setShowEddie(false)} />}
    </div>
  );
}
