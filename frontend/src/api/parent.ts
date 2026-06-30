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
  push_enabled?: boolean;
  biometric_allowed?: boolean;
  leaderboard_consent?: boolean;
  parent_consent_given_at: string | null;
  consent_declined_at: string | null;
  deleted_at: string | null;
  deletion_requested_at: string | null;
  age_tier: 'explorer' | 'investor';
  tier_override: 'explorer' | 'investor' | null;
  analytics: ChildAnalytics | null;
};

export type TierOverride = 'explorer' | 'investor' | null;

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
  getMasteryReport: () => apiFetch<MasteryReport>('/parent/mastery-report'),
  biometricEnroll: (device_id: string, label: string) =>
    apiFetch<{ secret: string }>('/parent/auth/biometric/enroll', { method: 'POST', body: JSON.stringify({ device_id, label }) }),
  biometricExchange: (device_id: string, secret: string) =>
    apiFetch<{ secret: string }>('/parent/auth/biometric/exchange', {
      method: 'POST', body: JSON.stringify({ device_id, secret }),
      headers: { 'X-Device-Id': device_id }, // per-device rate-limit bucket (cookieless route)
    }),
  biometricUnenroll: (device_id: string) =>
    apiFetch(`/parent/auth/biometric/devices/${device_id}`, { method: 'DELETE' }),
  setChildBiometric: (userId: string, enabled: boolean) =>
    apiFetch<{ status: string; biometric_allowed: boolean }>(`/parent/children/${userId}/biometric`, { method: 'POST', body: JSON.stringify({ enabled }) }),
  setChildPush: (userId: string, enabled: boolean) =>
    apiFetch<{ status: string; push_enabled: boolean }>(
      `/parent/children/${userId}/push`,
      { method: 'POST', body: JSON.stringify({ enabled }) },
    ),
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
  setChildTier: (userId: string, tierOverride: TierOverride) =>
    apiFetch<{ tier_override: TierOverride; age_tier: 'explorer' | 'investor' }>(
      `/parent/children/${userId}/tier`,
      { method: 'POST', body: JSON.stringify({ tier_override: tierOverride }) },
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
  deleteAccount: (confirmEmail: string) =>
    apiFetch<{ status: string; children_deleted: number }>('/parent/account/delete', {
      method: 'POST',
      body: JSON.stringify({ confirm_email: confirmEmail }),
    }),
  getPreferences: () => apiFetch<ParentPreferences>('/parent/preferences'),
  updatePreferences: (update: Partial<ParentPreferences>) =>
    apiFetch<ParentPreferences>('/parent/preferences', {
      method: 'PATCH',
      body: JSON.stringify(update),
    }),
  setChildLeaderboardConsent: (childId: string, consent: boolean) =>
    apiFetch(`/parent/children/${childId}/leaderboard-consent`, { method: 'POST', body: JSON.stringify({ consent }) }),
};


// ── Mastery report (M6) ────────────────────────────────────────────
export type TopicDelta = {
  topic: string;
  baseline_score: number | null;
  latest_score: number | null;
  delta: number | null;
};

export type GrowthBlock = {
  has_baseline: boolean;
  overall_delta: number | null;
  baseline_overall: number | null;
  latest_overall: number | null;
  session_count: number | null;
  topic_deltas: TopicDelta[];
  focus_topic: string | null;
};

export type MasteryReportChild = {
  user_id: string;
  username: string;
  mastered_count: number;
  mastered_total: number;
  objectives: string[];
  standards: { framework?: string; code?: string }[];
  weak_topic: string | null;
  next_recommendation: { module_title?: string; level_title?: string | null; reason?: string | null } | null;
  growth: GrowthBlock | null;
};

export type MasteryReport = {
  window_days: number;
  children: MasteryReportChild[];
  household_mastered_count: number;
};
