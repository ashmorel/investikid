import { apiFetch } from './client';

export type RecentLesson = {
  title: string;
  type: 'card' | 'quiz' | 'scenario' | 'video';
  score: number | null;
  completed_at: string;
};

export type BadgeInfo = {
  name: string;
  icon: string;
  earned_at: string;
};

export type ChildAnalytics = {
  level: number;
  xp: number;
  xp_to_next_level: number;
  streak_count: number;
  lessons_completed: number;
  lessons_total: number;
  recent_lessons: RecentLesson[];
  badges: BadgeInfo[];
};

export type Child = {
  user_id: string;
  username: string;
  country_code: string;
  is_active: boolean;
  is_premium: boolean;
  parent_consent_given_at: string | null;
  consent_declined_at: string | null;
  deleted_at: string | null;
  deletion_requested_at: string | null;
  analytics: ChildAnalytics | null;
};

export const parentApi = {
  requestMagicLink: (email: string) =>
    apiFetch<{ status: string }>('/parent/auth/request', {
      method: 'POST', body: JSON.stringify({ email }),
    }),
  magicCallback: (token: string) =>
    apiFetch<{ status: string; email: string }>(
      `/parent/auth/callback?token=${encodeURIComponent(token)}`,
    ),
  logout: () => apiFetch<{ status: string }>('/parent/auth/logout', { method: 'POST' }),
  listChildren: () => apiFetch<Child[]>('/parent/children'),
  freezeChild: (userId: string, frozen: boolean) =>
    apiFetch<{ status: string; frozen: boolean }>(
      `/parent/children/${userId}/freeze`,
      { method: 'POST', body: JSON.stringify({ frozen }) },
    ),
  eraseChild: (userId: string) =>
    apiFetch<{ status: string }>(
      `/parent/children/${userId}/erasure`,
      { method: 'POST' },
    ),
  setChildPremium: (userId: string, premium: boolean) =>
    apiFetch<{ status: string; premium: boolean }>(
      `/parent/children/${userId}/premium`,
      { method: 'POST', body: JSON.stringify({ premium }) },
    ),
};
