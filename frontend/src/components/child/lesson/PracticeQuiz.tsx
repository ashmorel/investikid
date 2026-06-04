import { useQuery } from '@tanstack/react-query';
import { aiApi, type PracticeQuiz as PracticeQuizType } from '@/api/ai';
import { QuizLesson } from './QuizLesson';

type Props = {
  lessonId: string;
  wrongAnswerIndex?: number;
  onClose: () => void;
};

export function PracticeQuiz({ lessonId, wrongAnswerIndex, onClose }: Props) {
  const practiceQ = useQuery<PracticeQuizType | null>({
    queryKey: ['practice', lessonId],
    queryFn: () => aiApi.getPracticeQuiz(lessonId, wrongAnswerIndex),
    retry: false,
  });

  if (practiceQ.isLoading) {
    return (
      <div className="text-center py-8 text-sm text-muted-foreground">
        Generating practice question...
      </div>
    );
  }

  if (practiceQ.isError || !practiceQ.data) {
    return (
      <div className="text-center py-8 space-y-2">
        <p className="text-sm text-muted-foreground">Could not generate a practice question.</p>
        <button onClick={onClose} className="text-sm text-brand-700 underline">Go back</button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="rounded-lg bg-info-100 px-2.5 py-1 text-xs font-semibold text-info-600">
          Practice — no XP
        </span>
        {practiceQ.data.variant_rung && practiceQ.data.variant_rung !== 'core' && (
          <span className="rounded-lg bg-purple-100 px-2.5 py-1 text-xs font-semibold text-purple-800">
            {practiceQ.data.variant_rung === 'harder' ? 'Challenge' : 'Warm-up'}
          </span>
        )}
        <button onClick={onClose} className="text-sm text-brand-700 underline">
          Skip
        </button>
      </div>
      <QuizLesson
        contentJson={practiceQ.data}
        onComplete={() => onClose()}
      />
    </div>
  );
}
