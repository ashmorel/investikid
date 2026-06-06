import { apiFetch } from './client';

export type ModuleTopic = 'stocks' | 'savings' | 'real_estate' | 'budgeting' | 'risk' | 'crypto' | 'taxes' | 'debt' | 'entrepreneurship';

export const TOPIC_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'No preference' },
  { value: 'stocks', label: 'Stocks' },
  { value: 'savings', label: 'Savings' },
  { value: 'real_estate', label: 'Real estate' },
  { value: 'budgeting', label: 'Budgeting' },
  { value: 'risk', label: 'Risk' },
  { value: 'crypto', label: 'Crypto' },
  { value: 'taxes', label: 'Taxes' },
  { value: 'debt', label: 'Debt' },
  { value: 'entrepreneurship', label: 'Entrepreneurship' },
];
export type LessonType = 'card' | 'quiz' | 'scenario' | 'video';

export type ModuleOut = {
  id: string;
  topic: ModuleTopic;
  title: string;
  country_codes: string[];
  is_premium: boolean;
  order_index: number;
  icon: string;
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

export type LevelState = 'in_progress' | 'completed' | 'locked';

export type LevelOut = {
  id: string;
  module_id: string;
  title: string;
  order_index: number;
  is_premium: boolean;
  icon: string;
  state: LevelState;
  locked_reason: 'premium' | 'progression' | null;
  passed: boolean;
  lessons_total: number;
  lessons_completed: number;
};

export type LessonCompletionResult = {
  xp_awarded: number;
  already_completed: boolean;
  total_xp: number;
  level: number;
  streak_count: number;
  streak_freezes: number;
  practice_available: boolean;
};

export type Progress = {
  xp: number;
  level: number;
  streak_count: number;
  streak_freezes: number;
  last_activity_date: string | null; // YYYY-MM-DD
};

export type NextLesson = {
  module_id: string;
  module_title: string;
  module_icon: string | null;
  level_id: string;
  lesson_id: string;
  lesson_title: string;
  mode: 'start' | 'continue';
};

export const contentApi = {
  listModules: () => apiFetch<ModuleOut[]>('/modules'),
  nextLesson: () => apiFetch<{ next: NextLesson | null }>('/next-lesson'),
  listLessons: (moduleId: string) =>
    apiFetch<LessonSummary[]>(`/modules/${moduleId}/lessons`),
  getLesson: (lessonId: string) => apiFetch<LessonOut>(`/lessons/${lessonId}`),
  completeLesson: (lessonId: string, score: number | null) =>
    apiFetch<LessonCompletionResult>(`/lessons/${lessonId}/complete`, {
      method: 'POST', body: JSON.stringify({ score }),
    }),
  recordLessonView: (lessonId: string) =>
    apiFetch<null>(`/lessons/${lessonId}/view`, { method: 'POST' }),
  listLevels: (moduleId: string) =>
    apiFetch<LevelOut[]>(`/modules/${moduleId}/levels`),
  listLevelLessons: (levelId: string) =>
    apiFetch<LessonSummary[]>(`/levels/${levelId}/lessons`),
  getProgress: () => apiFetch<Progress>('/users/me/progress'),
};
