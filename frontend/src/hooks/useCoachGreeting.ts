import { useRecommendations, useStrengths } from '@/api/ai';
import { useChildSession } from '@/hooks/useChildSession';

export function useCoachGreeting(): { greeting: string; isLoading: boolean } {
  const { data: me, isLoading: meLoading } = useChildSession();
  const { data: recs, isLoading: recsLoading } = useRecommendations();
  const { isLoading: strengthsLoading } = useStrengths();

  const isLoading = meLoading || recsLoading || strengthsLoading;

  if (isLoading || !me) {
    return { greeting: '', isLoading: true };
  }

  const username = me.username ?? 'there';
  let line: string;

  const dueCount = recs?.review_summary?.due_count ?? 0;
  const continueLearning = recs?.continue_learning ?? [];
  const somethingNew = recs?.something_new ?? [];

  if (dueCount > 0) {
    const plural = dueCount === 1 ? 'concept' : 'concepts';
    line = `You have ${dueCount} ${plural} ready for review — want to go over them?`;
  } else if (continueLearning.length > 0) {
    line = `Want to keep going with your current quests?`;
  } else if (somethingNew.length > 0) {
    line = `I found something new for you to explore!`;
  } else {
    line = `What would you like to learn about today?`;
  }

  return { greeting: `Hey ${username}! ${line}`, isLoading: false };
}
