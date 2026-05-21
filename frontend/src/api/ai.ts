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

export type NextQuest = {
  module_id: string;
  lesson_id: string;
  reason: string;
};

export type SuggestedModule = {
  module_id: string;
  score: number;
  reason: string;
};

export type Recommendations = {
  next_quest: NextQuest | null;
  suggested_modules: SuggestedModule[];
};

export type PracticeQuiz = {
  question: string;
  choices: string[];
  answer_index: number;
  explanation: string;
  variant_rung?: string | null;
};

export type TutorResponse = {
  response: string;
  conversation_id: string;
  messages_remaining: number;
};

export const aiApi = {
  getRecommendations: () =>
    apiFetch<Recommendations>('/recommendations'),

  getMasteryProfile: () =>
    apiFetch<MasteryProfile>('/profile/mastery'),

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
};
