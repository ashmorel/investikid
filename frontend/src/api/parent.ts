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

export type StandardRef = {
  framework: string;
  code: string;
  label: string;
};

export type LevelProgress = {
  level_id: string;
  title: string;
  state: 'in_progress' | 'completed' | 'locked';
  locked_reason: 'premium' | 'progression' | null;
  passed: boolean;
  lessons_completed: number;
  lessons_total: number;
  mastered_at: string | null;
};

export type ModuleProgress = {
  module_id: string;
  title: string;
  icon: string;
  lessons_completed: number;
  lessons_total: number;
  standards_alignment: StandardRef[] | null;
  levels: LevelProgress[];
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
  modules_progress: ModuleProgress[];
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

export type GroupMember = { child_user_id: string; username: string };
export type ParentGroup = { id: string; name: string; code: string | null; is_owner: boolean; members: GroupMember[] };

export type ParentPreferences = {
  trial_reminder_opt_out: boolean;
  weekly_digest_opt_out: boolean;
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
  listGroups: () => apiFetch<ParentGroup[]>('/parent/groups'),
  createGroup: (name: string) =>
    apiFetch<ParentGroup>('/parent/groups', { method: 'POST', body: JSON.stringify({ name }) }),
  joinGroup: (code: string, childUserId: string) =>
    apiFetch<ParentGroup>('/parent/groups/join', {
      method: 'POST', body: JSON.stringify({ code, child_user_id: childUserId }),
    }),
  removeGroupMember: (groupId: string, childUserId: string) =>
    apiFetch<{ status: string }>(`/parent/groups/${groupId}/members/${childUserId}`, { method: 'DELETE' }),
  deleteGroup: (groupId: string) =>
    apiFetch<{ status: string }>(`/parent/groups/${groupId}`, { method: 'DELETE' }),
  getPreferences: () => apiFetch<ParentPreferences>('/parent/preferences'),
  updatePreferences: (update: Partial<ParentPreferences>) =>
    apiFetch<ParentPreferences>('/parent/preferences', {
      method: 'PATCH',
      body: JSON.stringify(update),
    }),
};
