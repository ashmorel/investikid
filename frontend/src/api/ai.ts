import { useQuery } from '@tanstack/react-query';
import { apiFetch } from './client';

export type TopicMasteryOut = {
  topic: string;
  mastery_score: number;
  quizzes_attempted: number;
  quizzes_correct: number;
  last_activity_at: string;
};

export type WeakConceptOut = {
  topic: string;
  concept: string;
  times_wrong: number;
  times_reinforced: number;
};

export type MasteryProfile = {
  topics: TopicMasteryOut[];
  weak_concepts: WeakConceptOut[];
};

// --- Categorised Recommendations (Phase 2) ---

export type RecommendationCategoryItem = {
  module_id: string;
  lesson_id: string | null;
  score: number;
  reason: string;
  review_prompt: string | null;
  weak_concepts: string[];
};

export type ReviewSummary = {
  due_count: number;
  next_due_at: string | null;
};

export type CategorisedRecommendations = {
  continue_learning: RecommendationCategoryItem[];
  practise_again: RecommendationCategoryItem[];
  something_new: RecommendationCategoryItem[];
  review_summary: ReviewSummary;
};

// --- Strengths & Gaps ---

export type TopicStrength = {
  topic: string;
  mastery_score: number;
  status: 'strong' | 'needs_practice' | 'new';
  weak_count: number;
  due_for_review: number;
  total_concepts: number;
};

export type StrengthsAndGaps = {
  topics: TopicStrength[];
  overall_mastery: number;
};

// --- Practice Quiz ---

export type PracticeQuiz = {
  question: string;
  choices: string[];
  answer_index: number;
  explanation: string;
  variant_rung?: string | null;
};

// --- Tutor ---

export type TutorResponse = {
  response: string;
  conversation_id: string;
  messages_remaining: number;
};

// --- Coach Eddie ---

export type CoachAction = {
  type: 'lesson' | 'module' | 'review';
  module_id: string;
  lesson_id: string | null;
  label: string;
};

export type CoachChatResponse = {
  response: string;
  conversation_id: string;
  messages_remaining: number;
  actions: CoachAction[];
};

// --- Home Greeting ---

export type HomeGreetingCtxBody = {
  name: string;
  mode: 'start' | 'continue' | 'caught_up';
  lesson_label: string | null;
  streak_count: number;
  due_count: number;
};
export type HomeGreetingResponse = { greeting: string };

// --- API functions ---

export const aiApi = {
  getRecommendations: () =>
    apiFetch<CategorisedRecommendations>('/recommendations'),

  getMasteryProfile: () =>
    apiFetch<MasteryProfile>('/profile/mastery'),

  getStrengths: () =>
    apiFetch<StrengthsAndGaps>('/profile/strengths'),

  getPracticeQuiz: (lessonId: string, wrongAnswerIndex?: number) =>
    apiFetch<PracticeQuiz>(`/lessons/${lessonId}/practice`, {
      method: 'POST',
      body: JSON.stringify({ wrong_answer_index: wrongAnswerIndex ?? null }),
    }),

  sendTutorMessage: (lessonId: string, message: string, conversationId?: string) =>
    apiFetch<TutorResponse>('/tutor/chat', {
      method: 'POST',
      body: JSON.stringify({
        lesson_id: lessonId,
        message,
        conversation_id: conversationId ?? null,
      }),
    }),

  sendCoachMessage: (message: string, conversationId?: string) =>
    apiFetch<CoachChatResponse>('/tutor/coach', {
      method: 'POST',
      body: JSON.stringify({
        message,
        conversation_id: conversationId ?? null,
      }),
    }),

  homeGreeting: (body: HomeGreetingCtxBody) =>
    apiFetch<HomeGreetingResponse>('/home-greeting', { method: 'POST', body: JSON.stringify(body) }),
};

// --- Hooks ---

export function useRecommendations() {
  return useQuery({
    queryKey: ['recommendations'],
    queryFn: () => aiApi.getRecommendations(),
    retry: false,
    staleTime: 60_000,
  });
}

export function useStrengths() {
  return useQuery({
    queryKey: ['strengths'],
    queryFn: () => aiApi.getStrengths(),
    retry: false,
    staleTime: 60_000,
  });
}

export function useHomeGreeting(body: HomeGreetingCtxBody, enabled: boolean) {
  return useQuery({
    queryKey: ['home-greeting', body.mode, body.lesson_label, body.streak_count, body.due_count, body.name],
    queryFn: () => aiApi.homeGreeting(body),
    enabled,
    staleTime: Infinity,
    retry: false,
  });
}
