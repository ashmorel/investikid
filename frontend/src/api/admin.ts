import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError } from './client';
import { getAdminToken, clearAdminToken } from '@/lib/adminAuth';

// ── Types ──────────────────────────────────────────────────────────
export interface AdminStats {
  modules: number;
  lessons: number;
  badges: number;
  challenges: number;
}

export interface AdminModule {
  id: string;
  topic: string;
  title: string;
  icon: string;
  is_premium: boolean;
  country_codes: string[];
  order_index: number;
  lesson_count: number;
  prerequisite_ids: string[];
  min_age: number | null;
  max_age: number | null;
}

export interface AdminLesson {
  id: string;
  module_id: string;
  type: 'card' | 'quiz' | 'scenario' | 'video';
  content_json: Record<string, unknown>;
  xp_reward: number;
  order_index: number;
}

export interface AdminLevel {
  id: string;
  module_id: string;
  title: string;
  order_index: number;
  is_premium: boolean;
  pass_threshold: number;
  content_source: string;
  icon: string;
  lesson_count: number;
}

export interface AdminBadge {
  id: string;
  name: string;
  description: string;
  icon_url: string;
  condition_type: string;
  condition_value: number;
}

export interface AdminChallenge {
  id: string;
  title: string;
  description: string;
  type: string;
  target_value: number;
  xp_reward: number;
  badge_id: string | null;
  starts_at: string;
  ends_at: string;
  is_premium: boolean;
}

// ── Fetch helper ───────────────────────────────────────────────────
async function adminFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getAdminToken();
  if (!token) throw new ApiError(401, 'No admin token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
    ...((init?.headers as Record<string, string>) ?? {}),
  };
  const res = await fetch(path, { ...init, headers });
  if (res.status === 401) {
    clearAdminToken();
    throw new ApiError(401, 'Invalid admin token');
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch { /* ignore */ }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

// ── Stats ──────────────────────────────────────────────────────────
export function useAdminStats() {
  return useQuery({ queryKey: ['admin', 'stats'], queryFn: () => adminFetch<AdminStats>('/admin/stats') });
}

// ── Modules ────────────────────────────────────────────────────────
export function useModules() {
  return useQuery({ queryKey: ['admin', 'modules'], queryFn: () => adminFetch<AdminModule[]>('/admin/modules') });
}

export function useCreateModule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Omit<AdminModule, 'id' | 'lesson_count'>) =>
      adminFetch<AdminModule>('/admin/modules', { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin', 'modules'] }); qc.invalidateQueries({ queryKey: ['admin', 'stats'] }); },
  });
}

export function useUpdateModule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<Omit<AdminModule, 'id' | 'lesson_count'>>) =>
      adminFetch<AdminModule>(`/admin/modules/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'modules'] }),
  });
}

export function useDeleteModule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => adminFetch(`/admin/modules/${id}`, { method: 'DELETE' }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin', 'modules'] }); qc.invalidateQueries({ queryKey: ['admin', 'stats'] }); },
  });
}

export function useReorderModules() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (order: { id: string; order_index: number }[]) =>
      adminFetch('/admin/modules/reorder', { method: 'PATCH', body: JSON.stringify({ order }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'modules'] }),
  });
}

// ── Lessons ────────────────────────────────────────────────────────
export function useLessons(moduleId: string) {
  return useQuery({
    queryKey: ['admin', 'lessons', moduleId],
    queryFn: () => adminFetch<AdminLesson[]>(`/admin/modules/${moduleId}/lessons`),
    enabled: !!moduleId,
  });
}

export function useCreateLesson() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ moduleId, ...data }: { moduleId: string } & Omit<AdminLesson, 'id' | 'module_id'>) =>
      adminFetch<AdminLesson>(`/admin/modules/${moduleId}/lessons`, { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: (_d, vars) => {
      qc.invalidateQueries({ queryKey: ['admin', 'lessons', vars.moduleId] });
      qc.invalidateQueries({ queryKey: ['admin', 'modules'] });
      qc.invalidateQueries({ queryKey: ['admin', 'stats'] });
    },
  });
}

export function useUpdateLesson() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<Omit<AdminLesson, 'id' | 'module_id'>>) =>
      adminFetch<AdminLesson>(`/admin/lessons/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin'] }),
  });
}

export function useDeleteLesson() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => adminFetch(`/admin/lessons/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin'] });
    },
  });
}

export function useReorderLessons() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ moduleId, order }: { moduleId: string; order: { id: string; order_index: number }[] }) =>
      adminFetch(`/admin/modules/${moduleId}/lessons/reorder`, { method: 'PATCH', body: JSON.stringify({ order }) }),
    onSuccess: (_d, vars) => qc.invalidateQueries({ queryKey: ['admin', 'lessons', vars.moduleId] }),
  });
}

// ── Levels ─────────────────────────────────────────────────────────
export function useLevels(moduleId: string) {
  return useQuery({
    queryKey: ['admin', 'levels', moduleId],
    queryFn: () => adminFetch<AdminLevel[]>(`/admin/modules/${moduleId}/levels`),
    enabled: !!moduleId,
  });
}

export function useCreateLevel(moduleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { title: string; order_index: number; is_premium: boolean; pass_threshold: number; icon: string }) =>
      adminFetch<AdminLevel>(`/admin/modules/${moduleId}/levels`, { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'levels', moduleId] }),
  });
}

export function useUpdateLevel(moduleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<Omit<AdminLevel, 'id' | 'module_id' | 'content_source' | 'lesson_count'>>) =>
      adminFetch<AdminLevel>(`/admin/levels/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'levels', moduleId] }),
  });
}

export function useDeleteLevel(moduleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => adminFetch(`/admin/levels/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'levels', moduleId] }),
  });
}

// ── Level lessons ──────────────────────────────────────────────────
export function useLevelLessons(levelId: string) {
  return useQuery({
    queryKey: ['admin', 'level-lessons', levelId],
    queryFn: () => adminFetch<AdminLesson[]>(`/admin/levels/${levelId}/lessons`),
    enabled: !!levelId,
  });
}

export function useCreateLevelLesson(levelId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Omit<AdminLesson, 'id' | 'module_id'>) =>
      adminFetch<AdminLesson>(`/admin/levels/${levelId}/lessons`, { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'level-lessons', levelId] }),
  });
}

// ── Badges ─────────────────────────────────────────────────────────
export function useBadges() {
  return useQuery({ queryKey: ['admin', 'badges'], queryFn: () => adminFetch<AdminBadge[]>('/admin/badges') });
}

export function useCreateBadge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Omit<AdminBadge, 'id'>) =>
      adminFetch<AdminBadge>('/admin/badges', { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin', 'badges'] }); qc.invalidateQueries({ queryKey: ['admin', 'stats'] }); },
  });
}

export function useUpdateBadge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<Omit<AdminBadge, 'id'>>) =>
      adminFetch<AdminBadge>(`/admin/badges/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'badges'] }),
  });
}

export function useDeleteBadge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => adminFetch(`/admin/badges/${id}`, { method: 'DELETE' }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin', 'badges'] }); qc.invalidateQueries({ queryKey: ['admin', 'stats'] }); },
  });
}

// ── Challenges ─────────────────────────────────────────────────────
export function useChallenges() {
  return useQuery({ queryKey: ['admin', 'challenges'], queryFn: () => adminFetch<AdminChallenge[]>('/admin/challenges') });
}

export function useCreateChallenge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Omit<AdminChallenge, 'id'>) =>
      adminFetch<AdminChallenge>('/admin/challenges', { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin', 'challenges'] }); qc.invalidateQueries({ queryKey: ['admin', 'stats'] }); },
  });
}

export function useUpdateChallenge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<Omit<AdminChallenge, 'id'>>) =>
      adminFetch<AdminChallenge>(`/admin/challenges/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'challenges'] }),
  });
}

export function useDeleteChallenge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => adminFetch(`/admin/challenges/${id}`, { method: 'DELETE' }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin', 'challenges'] }); qc.invalidateQueries({ queryKey: ['admin', 'stats'] }); },
  });
}

// ── Countries ──────────────────────────────────────────────────────
export function useCountries() {
  return useQuery({ queryKey: ['admin', 'countries'], queryFn: () => adminFetch<string[]>('/admin/countries') });
}

// ── Feedback ───────────────────────────────────────────────────────
export type AdminFeedbackType = 'bug' | 'feature' | 'general';

export interface AdminFeedback {
  id: string;
  submitter: string;
  submitter_role: string;
  feedback_type: AdminFeedbackType;
  message: string;
  page_url: string | null;
  created_at: string;
}

export interface AdminFeedbackList {
  items: AdminFeedback[];
  total: number;
  page: number;
  per_page: number;
}

export function useFeedback(params: { type?: string; page: number }) {
  const search = new URLSearchParams();
  if (params.type) search.set('type', params.type);
  search.set('page', String(params.page));
  const qs = search.toString();
  return useQuery({
    queryKey: ['admin', 'feedback', params.type ?? 'all', params.page],
    queryFn: () => adminFetch<AdminFeedbackList>(`/admin/feedback?${qs}`),
  });
}
