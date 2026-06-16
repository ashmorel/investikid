import { useQuery } from '@tanstack/react-query';
import { apiFetch } from './client';

export type ReviseQuestion = {
  ref: string;
  kind: 'weak' | 'refresher';
  module_id: string;
  lesson_id: string;
  concept: string;
  question: string;
  choices: string[];
};
export type ReviseSession = { items: ReviseQuestion[] };

export type ReviseModule = {
  module_id: string;
  title: string;
  icon: string;
  topic: string;
  due_weak_count: number;
};

export type ReviseAnswerResult = {
  correct: boolean;
  answer_index: number;
  explanation: string;
  xp_awarded: number;
  goal_met: boolean;
};

export const reviseApi = {
  getModules: () => apiFetch<ReviseModule[]>('/revise/modules'),
  getSession: (moduleId?: string) =>
    apiFetch<ReviseSession>(
      moduleId ? `/revise/session?module_id=${moduleId}` : '/revise/session',
    ),
  postAnswer: (ref: string, selectedIndex: number) =>
    apiFetch<ReviseAnswerResult>('/revise/answer', {
      method: 'POST',
      body: JSON.stringify({ ref, selected_index: selectedIndex }),
    }),
};

export function useRevisableModules() {
  return useQuery({
    queryKey: ['revise-modules'],
    queryFn: () => reviseApi.getModules(),
    retry: false,
    staleTime: 60_000,
  });
}
