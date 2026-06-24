import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { contentApi, type LessonOut, type LessonSummary, type LessonCompletionResult, type ModuleOut, type LevelOut } from '@/api/content';
import { ApiError } from '@/api/client';
import { CardLesson } from '@/components/child/lesson/CardLesson';
import { QuizLesson } from '@/components/child/lesson/QuizLesson';
import { ScenarioLesson } from '@/components/child/lesson/ScenarioLesson';
import { VideoLesson } from '@/components/child/lesson/VideoLesson';
import { CompletionPanel } from '@/components/child/lesson/CompletionPanel';
import { LessonIllustration } from '@/components/child/lesson/LessonIllustration';
import { PracticeQuiz } from '@/components/child/lesson/PracticeQuiz';
import { CoachPennyPanel } from '@/components/child/lesson/CoachPennyPanel';
import { LessonChrome } from '@/components/child/lesson/LessonChrome';
import { ApplyMissionCTA } from '@/components/child/lesson/ApplyMissionCTA';
import { BackButton } from '@/components/child/BackButton';
import { MachineTranslatedBadge } from '@/components/child/MachineTranslatedBadge';
import { useToast } from '@/hooks/use-toast';
import { usePremiumPaywall } from '@/hooks/usePremiumPaywall';
import { useActiveMissions } from '@/hooks/useActiveMissions';
import { useMarkets } from '@/hooks/useMarkets';
import { formatRewardToast } from '@/lib/marketReward';

export default function Lesson() {
  const { moduleId, levelId, lessonId } = useParams<{ moduleId: string; levelId: string; lessonId: string }>();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { open: openPaywall } = usePremiumPaywall();
  const { t } = useTranslation('lessons');
  const { t: tMarkets } = useTranslation('markets');
  const { data: markets } = useMarkets();
  const [showPractice, setShowPractice] = useState(false);
  const [showPenny, setShowPenny] = useState(false);
  const completionInFlight = useRef(false);
  const { data: missions } = useActiveMissions();
  const lessonMission = missions?.find((m) => m.lesson_id === lessonId);

  const lessonQ = useQuery<LessonOut | null>({
    queryKey: ['lesson', lessonId],
    queryFn: () => contentApi.getLesson(lessonId!),
    enabled: !!lessonId, retry: false,
  });

  const lessonsQ = useQuery<LessonSummary[] | null>({
    queryKey: ['level-lessons', levelId],
    queryFn: () => contentApi.listLevelLessons(levelId!),
    enabled: !!levelId, retry: false, staleTime: 60_000,
  });

  const modulesQ2 = useQuery<ModuleOut[] | null>({
    queryKey: ['modules'],
    queryFn: () => contentApi.listModules(),
    retry: false, staleTime: 60_000,
  });

  const levelsQ = useQuery<LevelOut[] | null>({
    queryKey: ['module-levels', moduleId],
    queryFn: () => contentApi.listLevels(moduleId!),
    enabled: !!moduleId, retry: false, staleTime: 60_000,
  });

  const complete = useMutation<LessonCompletionResult | null, Error, number | null>({
    mutationFn: (score) => contentApi.completeLesson(lessonId!, score),
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ['progress'] });
      qc.invalidateQueries({ queryKey: ['level-lessons', levelId] });
      qc.invalidateQueries({ queryKey: ['module-levels', moduleId] });
      // Celebrate a market-completion reward, but only the first time through.
      if (result && !result.already_completed) {
        const marketName = (markets ?? []).find((m) => m.is_selected)?.name ?? '';
        const msg = formatRewardToast(tMarkets, result.reward, marketName);
        if (msg) toast({ description: msg });
        // Toast any newly earned limited collectables.
        if (result.granted_collectables && result.granted_collectables.length > 0) {
          qc.invalidateQueries({ queryKey: ['collectables'] });
          toast({
            title: t('lesson.collectableEarned.title'),
            description: t('lesson.collectableEarned.description', {
              names: result.granted_collectables.join(', '),
            }),
          });
        }
      }
    },
    onError: (err) => {
      if (err instanceof ApiError && err.code === 'premium_required') {
        const label = (err.context as { label?: string } | undefined)?.label ?? t('lesson.premiumContent');
        openPaywall({ kind: 'home', label });
        return;
      }
      toast({ title: t('lesson.saveError'), description: t('lesson.tryAgain') });
    },
    onSettled: () => {
      completionInFlight.current = false;
    },
  });

  // Reset mutation state when navigating to a different lesson so the
  // CompletionPanel from the previous lesson doesn't flash on screen.
  useEffect(() => {
    complete.reset();
    completionInFlight.current = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- resetting UI state when lessonId changes is intentional; avoids stale panel showing on lesson navigation
    setShowPractice(false);
    setShowPenny(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lessonId]);

  // Compute post-completion destination
  const curId = lessonQ.data?.id;
  const levelLessons = (lessonsQ.data ?? []) as LessonSummary[];
  // Other lessons in THIS level still incomplete (exclude the just-finished one so stale data can't mislead)
  const moreInLevel = !!curId && levelLessons.some(l => l.id !== curId && !l.completed);
  const allLevels = (levelsQ.data ?? []) as LevelOut[];
  const moduleComplete = allLevels.length > 0 && allLevels.every(lv => lv.state === 'completed');
  const postCompleteDest = moreInLevel
    ? `/lessons/${moduleId}/${levelId}`
    : moduleComplete
      ? '/lessons'
      : `/lessons/${moduleId}`;

  useEffect(() => {
    if (!lessonId) return;
    contentApi.recordLessonView(lessonId).catch(() => { /* analytics ping — ignore */ });
  }, [lessonId]);

  // Auto-navigate 2 s after completion, unless child opened practice
  useEffect(() => {
    if (!complete.isSuccess || showPractice) return;
    const t = setTimeout(() => navigate(postCompleteDest, { replace: true }), 2000);
    return () => clearTimeout(t);
  }, [complete.isSuccess, showPractice, postCompleteDest, navigate]);

  if (lessonQ.isLoading) {
    return <div className="mx-auto max-w-2xl px-4 py-4 sm:px-6 sm:py-6 text-sm text-muted-foreground">{t('lesson.loading')}</div>;
  }
  if (lessonQ.isError || !lessonQ.data) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-4 sm:px-6 sm:py-6">
        <BackButton to={`/lessons/${moduleId ?? ''}/${levelId ?? ''}`} label={t('lesson.backLabel')} />
        <p className="mt-2">{t('lesson.notFound')}</p>
      </div>
    );
  }

  const lesson = lessonQ.data;
  const lessons = (lessonsQ.data ?? []) as LessonSummary[];
  const total = lessons.length;

  if (complete.isSuccess && complete.data) {
    if (showPractice) {
      return (
        <div className="mx-auto max-w-2xl px-4 py-4 sm:px-6 sm:py-6">
          <PracticeQuiz lessonId={lessonId!} onClose={() => setShowPractice(false)} />
        </div>
      );
    }

    return (
      <div className="mx-auto max-w-2xl px-4 py-4 sm:px-6 sm:py-6">
        <CompletionPanel
          result={complete.data}
          onContinue={() => navigate(postCompleteDest, { replace: true })}
        />
        {lessonMission && <ApplyMissionCTA mission={lessonMission} />}
        {complete.data.practice_available && !complete.data.already_completed && (
          <div className="mt-4 text-center">
            <button
              onClick={() => setShowPractice(true)}
              className="text-sm text-brand-700 hover:text-brand-800 underline font-medium"
            >
              {t('lesson.practiceCta')}
            </button>
          </div>
        )}
      </div>
    );
  }

  if (complete.isError) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-4 sm:px-6 sm:py-6 space-y-4">
        <p>{t('lesson.saveError')}</p>
        <button
          type="button"
          className="rounded bg-primary px-3 py-1 text-sm text-primary-foreground"
          onClick={() => complete.reset()}
        >{t('lesson.tryAgain')}</button>
      </div>
    );
  }

  const onComplete = (score: number | null) => {
    if (completionInFlight.current) return;
    completionInFlight.current = true;
    complete.mutate(score);
  };

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
    <div className="mx-auto max-w-2xl px-4 py-4 sm:px-6 sm:py-6">
      <LessonChrome
        position={lesson.order_index + 1}
        total={total}
        xpReward={lesson.xp_reward}
        onBack={() => navigate(-1)}
      />
      {lesson.machine_translated && (
        <div className="mb-2">
          <MachineTranslatedBadge />
        </div>
      )}
      {lesson.type === 'card' && <CardLesson contentJson={lesson.content_json as { title?: string; body?: string }} onComplete={onComplete} illustration={illustration} onShowPenny={() => setShowPenny(true)} completing={complete.isPending} />}
      {lesson.type === 'quiz' && <QuizLesson contentJson={lesson.content_json as { question: string; choices: string[]; answer_index: number; explanation: string }} onComplete={onComplete} illustration={illustration} onShowPenny={() => setShowPenny(true)} completing={complete.isPending} />}
      {lesson.type === 'scenario' && <ScenarioLesson contentJson={lesson.content_json as { prompt: string; choices: { label: string; outcome: string }[]; correct_index: number }} onComplete={onComplete} illustration={illustration} onShowPenny={() => setShowPenny(true)} completing={complete.isPending} />}
      {lesson.type === 'video' && <VideoLesson contentJson={lesson.content_json as { youtube_id?: string; caption?: string }} onComplete={onComplete} completing={complete.isPending} />}
      {showPenny && <CoachPennyPanel lessonId={lessonId!} onClose={() => setShowPenny(false)} />}
    </div>
  );
}
