import { apiFetch } from './client';

export type ModuleTopic = 'stocks' | 'savings' | 'real_estate';
export type LessonType = 'card' | 'quiz' | 'scenario' | 'video';

export type ModuleOut = {
  id: string;
  topic: ModuleTopic;
  title: string;
  country_codes: string[];
  is_premium: boolean;
  order_index: number;
  locked: boolean;
};

export type LessonSummary = {
  id: string;
  type: LessonType;
  title: string;
  xp_reward: number;
  order_index: number;
  completed: boolean;
};

export type LessonOut = {
  id: string;
  module_id: string;
  type: LessonType;
  content_json: Record<string, unknown>;
  xp_reward: number;
  order_index: number;
  completed: boolean;
  locked: boolean;
};

export type LessonCompletionResult = {
  xp_awarded: number;
  already_completed: boolean;
  total_xp: number;
  level: number;
  streak_count: number;
};

export type Progress = {
  xp: number;
  level: number;
  streak_count: number;
  last_activity_date: string | null; // YYYY-MM-DD
};

export const contentApi = {
  listModules: () => apiFetch<ModuleOut[]>('/modules'),
  listLessons: (moduleId: string) =>
    apiFetch<LessonSummary[]>(`/modules/${moduleId}/lessons`),
  getLesson: (lessonId: string) => apiFetch<LessonOut>(`/lessons/${lessonId}`),
  completeLesson: (lessonId: string, score: number | null) =>
    apiFetch<LessonCompletionResult>(`/lessons/${lessonId}/complete`, {
      method: 'POST', body: JSON.stringify({ score }),
    }),
  getProgress: () => apiFetch<Progress>('/users/me/progress'),
};
