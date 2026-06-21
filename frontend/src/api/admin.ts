import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch, ApiError } from './client';

// ── Types ──────────────────────────────────────────────────────────
export interface AdminStats {
  modules: number;
  lessons: number;
  badges: number;
  challenges: number;
}

export interface StandardRef {
  framework: string;
  code: string;
  label: string;
}

export interface SourceRef {
  title: string;
  url: string;
}

export interface AdminModule {
  id: string;
  topic: string;
  title: string;
  icon: string;
  is_premium: boolean;
  country_codes: string[];
  /** Owning market; the API defaults it to GB. Optional so create payloads
   *  (which never set it) still satisfy `Omit<AdminModule, …>`. */
  market_code?: string;
  /** Child-visibility flag. Engine-staged modules are false until publish.
   *  Optional so create payloads (which never set it) still type-check. */
  published?: boolean;
  /** ISO timestamp when archived (NULL = active). Archived modules show in the
   *  admin "Archived" section and are hard-purged 30 days after this. */
  archived_at?: string | null;
  order_index: number;
  lesson_count: number;
  prerequisite_ids: string[];
  min_age: number | null;
  max_age: number | null;
  completion_cash_reward?: string | null;
  standards_alignment?: StandardRef[] | null;
  sources?: SourceRef[] | null;
}

export type MissionType = 'first_buy' | 'first_sell' | 'diversify' | 'invest_amount';

export interface ApplyMission {
  id?: string;
  mission_type: MissionType;
  params_json: Record<string, unknown>;
  title: string;
  prompt: string;
  xp_reward: number;
  cash_reward?: string | null;
}

export interface AdminLesson {
  id: string;
  module_id: string;
  type: 'card' | 'quiz' | 'scenario' | 'video';
  content_json: Record<string, unknown>;
  xp_reward: number;
  order_index: number;
  apply_mission?: ApplyMission | null;
}

/** Human-readable label for a lesson row in the admin UI. Each lesson type
 *  stores its display text under a different key (cards: title, quizzes:
 *  question, scenarios: prompt, videos: caption/youtube_id). */
export function lessonLabel(lesson: Pick<AdminLesson, 'type' | 'content_json'>): string {
  const cj = lesson.content_json as Record<string, string>;
  if (lesson.type === 'video') {
    return cj.caption || (cj.youtube_id ? `Video (${cj.youtube_id})` : 'Video');
  }
  return cj.title || cj.question || cj.prompt || 'Untitled';
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
  draft_count: number;
  learning_objectives?: string[] | null;
}

export interface AdminBadge {
  id: string;
  name: string;
  description: string;
  icon_url: string;
  condition_type: string;
  condition_value: number;
}

const BADGE_CONDITION_EMOJI: Record<string, string> = {
  lesson_count: '📚',
  streak_days: '🔥',
  trade_count: '📈',
  total_xp: '⭐',
};

/** Display icon for a badge. The icon_url field is meant to hold an emoji,
 *  but some rows store a (non-existent) /badges/*.svg path. If the value is a
 *  usable emoji/label we show it; otherwise we fall back to an icon derived
 *  from the badge's condition type so a badge always renders something. */
export function badgeIcon(badge: Pick<AdminBadge, 'icon_url' | 'condition_type'>): string {
  const v = (badge.icon_url || '').trim();
  if (v && !v.startsWith('/') && !v.startsWith('http')) return v;
  return BADGE_CONDITION_EMOJI[badge.condition_type] ?? '🏅';
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
  scope?: 'personal' | 'group';
}

// ── Fetch helper ───────────────────────────────────────────────────
function adminFetch<T>(path: string, init?: RequestInit): Promise<T> {
  return apiFetch<T>(path, init) as Promise<T>;
}

// ── Video assets (R2 direct upload) ────────────────────────────────
export interface VideoPresignResponse {
  asset_id: string;
  key: string;
  upload_url: string;
  public_url: string;
}

/** Ask the backend for a presigned R2 PUT URL for a video upload.
 *  Throws if the backend returns an error (e.g. 503 not_configured). */
export async function presignVideo(filename: string, contentType: string, sizeBytes: number) {
  return adminFetch<VideoPresignResponse>('/admin/video-assets/presign', {
    method: 'POST',
    body: JSON.stringify({ filename, content_type: contentType, size_bytes: sizeBytes }),
  });
}

/** Upload a file directly to R2 via the presigned PUT URL (XHR for progress).
 *  Sets Content-Type to file.type to match the signed PUT. Resolves on 2xx. */
export function uploadToPresigned(url: string, file: File, onProgress?: (pct: number) => void): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('PUT', url);
    xhr.setRequestHeader('Content-Type', file.type);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) onProgress(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onload = () => (xhr.status >= 200 && xhr.status < 300 ? resolve() : reject(new Error(`Upload failed (${xhr.status})`)));
    xhr.onerror = () => reject(new Error('Upload failed'));
    xhr.send(file);
  });
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

export function useRestoreModule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => adminFetch(`/admin/modules/${id}/restore`, { method: 'POST' }),
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

// ── Lesson drafts (AI-generated) ───────────────────────────────────
export type LessonDraft = {
  id: string;
  level_id: string;
  type: 'card' | 'quiz' | 'scenario';
  content_json: Record<string, unknown>;
  concept: string;
  moderation_safe: boolean;
  moderation_category: string | null;
  created_at: string;
  adaptation_flags?: { uk_residue: string[]; suspect: boolean };
};

export type GenerateLessonsBody = { concept: string; count: number; types: ('card' | 'quiz' | 'scenario')[] };

export type GenerateLessonsResult = { created: LessonDraft[]; skipped: number };

export function useLevelDrafts(levelId: string) {
  return useQuery({
    queryKey: ['admin', 'level-drafts', levelId],
    queryFn: () => adminFetch<LessonDraft[]>(`/admin/levels/${levelId}/drafts`),
    enabled: !!levelId,
  });
}

export function useGenerateLevelLessons(levelId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: GenerateLessonsBody) =>
      adminFetch<GenerateLessonsResult>(`/admin/levels/${levelId}/generate`, { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'level-drafts', levelId] }),
  });
}

export function useUpdateDraft(levelId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, content_json }: { id: string; content_json: Record<string, unknown> }) =>
      adminFetch<LessonDraft>(`/admin/lesson-drafts/${id}`, { method: 'PUT', body: JSON.stringify({ content_json }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'level-drafts', levelId] }),
  });
}

export function useApproveDraft(levelId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      adminFetch<AdminLesson>(`/admin/lesson-drafts/${id}/approve`, { method: 'POST' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'level-drafts', levelId] });
      qc.invalidateQueries({ queryKey: ['admin', 'level-lessons', levelId] });
      // The Market Content per-level "published" badge reads lesson_count from
      // the levels query — refresh it so the count updates without a page reload.
      qc.invalidateQueries({ queryKey: ['admin', 'levels'] });
      qc.invalidateQueries({ queryKey: ['admin', 'modules'] });
    },
  });
}

export type ApproveDraftsResult = { approved: number; replaced: number; skipped_unsafe: number };

/** Level-level commit: approve all moderation-safe drafts. When `replace`, the
 *  backend atomically deletes the level's published lessons first (one txn). */
export function useApproveDrafts(levelId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (replace: boolean) =>
      adminFetch<ApproveDraftsResult>(`/admin/levels/${levelId}/approve-drafts`,
        { method: 'POST', body: JSON.stringify({ replace }) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'level-drafts', levelId] });
      qc.invalidateQueries({ queryKey: ['admin', 'level-lessons', levelId] });
      qc.invalidateQueries({ queryKey: ['admin', 'levels'] });
      qc.invalidateQueries({ queryKey: ['admin', 'modules'] });
    },
  });
}

export function useRegenerateDraft(levelId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      adminFetch<LessonDraft>(`/admin/lesson-drafts/${id}/regenerate`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'level-drafts', levelId] }),
  });
}

export function useRejectDraft(levelId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => adminFetch(`/admin/lesson-drafts/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'level-drafts', levelId] }),
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

// ── Settings ───────────────────────────────────────────────────────
export type SeasonalEvent = {
  title: string;
  emoji: string;
  starts_at: string;
  ends_at: string;
  xp_bonus_pct: number;
};

export interface AdminSettings {
  alert_emails: string[];
  market_enroll_bonus_coins: number;
  market_completion_bonus_coins: number;
  seasonal_event?: SeasonalEvent | null;
  enabled_content_languages: string[];
}

export type AdminSettingsUpdate = Omit<AdminSettings, 'market_enroll_bonus_coins' | 'market_completion_bonus_coins' | 'enabled_content_languages'> & {
  market_enroll_bonus_coins?: number;
  market_completion_bonus_coins?: number;
  enabled_content_languages?: string[];
  clear_seasonal_event?: boolean;
};

export function useAdminSettings() {
  return useQuery({ queryKey: ['admin', 'settings'], queryFn: () => adminFetch<AdminSettings>('/admin/settings') });
}

export function useUpdateAdminSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: AdminSettingsUpdate) =>
      adminFetch<AdminSettings>('/admin/settings', { method: 'PUT', body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'settings'] }),
  });
}

// ── Content translations (E1) ──────────────────────────────────────
export interface TranslationGenerateResult {
  translated: number;
  skipped_fresh: number;
  failed: number;
}

export interface CoverageBucket {
  active: number;
  failed: number;
  missing: number;
}

export interface TranslationCoverage {
  language: string;
  modules: CoverageBucket;
  levels: CoverageBucket;
  lessons: CoverageBucket;
}

/** Trigger a translation batch for a language (optionally scoped to a market).
 *  Returns per-action counts. May be slow (calls the LLM per entity). */
export function useGenerateTranslations() {
  return useMutation({
    mutationFn: ({ language, market_code }: { language: string; market_code?: string }) =>
      adminFetch<TranslationGenerateResult>('/admin/translations/generate', {
        method: 'POST',
        body: JSON.stringify({ language, ...(market_code ? { market_code } : {}) }),
      }),
  });
}

/** Coverage (active/failed/missing per entity type) for a language. */
export function useTranslationCoverage(language: string) {
  return useQuery({
    queryKey: ['admin', 'translation-coverage', language],
    queryFn: () => adminFetch<TranslationCoverage>(`/admin/translations/coverage?language=${encodeURIComponent(language)}`),
    enabled: !!language,
  });
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

// ── Engagement ─────────────────────────────────────────────────────
export interface LessonEngagement {
  lesson_id: string;
  type: string;
  label: string;
  order: number;
  views: number;
  completions: number;
  completion_rate: number | null;
  average_score: number | null;
  drop_off: number;
}

export interface ModuleEngagement {
  module_id: string;
  learners_started: number;
  learners_completed: number;
  completion_rate: number | null;
  average_score: number | null;
  lessons: LessonEngagement[];
}

export function useModuleEngagement(moduleId: string) {
  return useQuery({
    queryKey: ['admin', 'module-engagement', moduleId],
    queryFn: () => adminFetch<ModuleEngagement>(`/admin/modules/${moduleId}/engagement`),
    enabled: !!moduleId,
  });
}

// ── Video health ───────────────────────────────────────────────────
export interface VideoHealthItem {
  lesson_id: string;
  module_id: string;
  module_title: string;
  lesson_title: string;
  youtube_id: string;
  status: 'ok' | 'dead' | 'blocked' | 'unknown' | null;
  http_status: number | null;
  checked_at: string | null;
}

export function useVideoHealth() {
  return useQuery({ queryKey: ['admin', 'video-health'], queryFn: () => adminFetch<VideoHealthItem[]>('/admin/video-health') });
}

export function useCheckVideoHealth() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => adminFetch<{ summary: Record<string, number>; items: VideoHealthItem[] }>(
      '/admin/video-health/check', { method: 'POST' },
    ),
    onSuccess: (data) => qc.setQueryData(['admin', 'video-health'], data.items),
  });
}

// ── Product analytics (M4) ─────────────────────────────────────────
export interface AnalyticsCohort {
  week_start: string;
  signups: number;
  d7_pct: number | null;
  d30_pct: number | null;
}

export interface AnalyticsSummary {
  window_days: number;
  activation: { signups: number; activated: number; rate_pct: number | null };
  cohorts: AnalyticsCohort[];
  funnel: { paywall_view: number; trial_started: number; subscription_activated: number };
  engagement: {
    home_view: number;
    home_cta_tap: number;
    cta_through_pct: number | null;
    quicklink_taps: Record<string, number>;
    lesson_completed: number;
    digest_sent: number;
  };
}

export function useAnalyticsSummary(days: number) {
  return useQuery({
    queryKey: ['admin', 'analytics-summary', days],
    queryFn: () => adminFetch<AnalyticsSummary>(`/admin/analytics/summary?days=${days}`),
  });
}

// ── Market content pipeline (E2) ───────────────────────────────────
export interface MarketBrief {
  market_code: string;
  brief_json: Record<string, unknown>;
  status: 'draft' | 'verified';
  model_used: string;
}

export interface ScaffoldResult {
  modules_created: number;
  levels_created: number;
  already_scaffolded?: boolean;
}

export interface MarketPublishResult {
  code: string;
  has_content: boolean;
}

/** The per-market human-verified brief that grounds content generation.
 *  404 (no brief yet) surfaces as a query error; the UI treats it as absent. */
export function useMarketBrief(code: string) {
  return useQuery({
    queryKey: ['admin', 'market-brief', code],
    queryFn: () => adminFetch<MarketBrief>(`/admin/markets/${code}/brief`),
    enabled: !!code,
    retry: false,
  });
}

export function useGenerateMarketBrief(code: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => adminFetch<MarketBrief>(`/admin/markets/${code}/brief/generate`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'market-brief', code] }),
  });
}

export function useUpdateMarketBrief(code: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (brief_json: Record<string, unknown>) =>
      adminFetch<MarketBrief>(`/admin/markets/${code}/brief`, { method: 'PUT', body: JSON.stringify({ brief_json }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'market-brief', code] }),
  });
}

export function useVerifyMarketBrief(code: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => adminFetch<MarketBrief>(`/admin/markets/${code}/brief/verify`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'market-brief', code] }),
  });
}

export function useScaffoldMarket(code: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => adminFetch<ScaffoldResult>(`/admin/markets/${code}/scaffold`, { method: 'POST' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'modules'] });
      qc.invalidateQueries({ queryKey: ['markets'] });
    },
  });
}

/** Generate market-adapted drafts for a target level from a GB source level.
 *  Drafts are then reviewed/approved via the existing per-level draft UI. */
export function useGenerateMarketLessons(levelId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (source_level_id: string) =>
      adminFetch<GenerateLessonsResult>(`/admin/levels/${levelId}/generate-market`, {
        method: 'POST',
        body: JSON.stringify({ source_level_id }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'level-drafts', levelId] }),
  });
}

// ── Per-module batch generation (every level, GB sources resolved server-side) ─
export type ModuleBatchResult = {
  levels: { level_id: string; status: string; created: number; skipped: number }[];
  generated: number;
  skipped_populated: number;
  skipped_has_drafts: number;
  skipped_no_source: number;
  skipped_no_concepts: number;
  errored: number;
};

/** Generate market-adapted drafts for EVERY level of a module in one batch
 *  (GB sources resolved server-side). Skips levels that already have lessons
 *  unless `include_populated`. Rate-limited 5/min (one call per module). */
export function useGenerateModuleLessons(moduleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (include_populated: boolean) =>
      adminFetch<ModuleBatchResult>(`/admin/modules/${moduleId}/generate-native-batch`,
        { method: 'POST', body: JSON.stringify({ include_populated }) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'modules'] });
      qc.invalidateQueries({ queryKey: ['admin', 'levels'] });
    },
  });
}

/** Plain (hook-free) variant for the market-wide sequential runner, where the
 *  module list is dynamic and we can't call a hook per module. */
export function generateModuleLessons(moduleId: string, include_populated: boolean) {
  return adminFetch<ModuleBatchResult>(`/admin/modules/${moduleId}/generate-native-batch`,
    { method: 'POST', body: JSON.stringify({ include_populated }) });
}

// ── Intelligent market suggestions (proactive module creation) ───────
export type ModuleSuggestion = {
  title: string;
  topic: string;
  rationale: string;
  action: 'add' | 'replace';
  replaces: string | null;
  suggested_concepts: string[];
};

export type ModuleFromSuggestionResult = {
  module_id: string;
  level_id: string;
  suggested_concepts: string[];
};

/** Ask the model for modules this market needs that the GB set lacks.
 *  Requires a verified brief (backend 409s otherwise); returns [] on LLM failure. */
export function useSuggestModules(code: string) {
  return useMutation({
    mutationFn: () =>
      adminFetch<ModuleSuggestion[]>(`/admin/markets/${code}/module-suggestions`, { method: 'POST' }),
  });
}

/** Create a Module + starter Level from a suggestion. */
export function useCreateModuleFromSuggestion(code: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ title, topic, suggested_concepts, action, replaces }: ModuleSuggestion) =>
      adminFetch<ModuleFromSuggestionResult>(`/admin/markets/${code}/modules/from-suggestion`, {
        method: 'POST',
        body: JSON.stringify({ title, topic, suggested_concepts, action, replaces }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'modules'] });
      qc.invalidateQueries({ queryKey: ['markets'] });
    },
  });
}

/** Generate brief-grounded NATIVE drafts for a level from a list of concepts. */
export function useGenerateNativeLessons(levelId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (concepts: string[]) =>
      adminFetch<GenerateLessonsResult>(`/admin/levels/${levelId}/generate-native`, {
        method: 'POST',
        body: JSON.stringify({ concepts }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'level-drafts', levelId] }),
  });
}

export function usePublishMarket(code: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => adminFetch<MarketPublishResult>(`/admin/markets/${code}/publish`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['markets'] }),
  });
}

export function useUnpublishMarket(code: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => adminFetch<MarketPublishResult>(`/admin/markets/${code}/unpublish`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['markets'] }),
  });
}

// ── Curriculum engine (Task 8) ─────────────────────────────────────
export type CurriculumLevelNode = {
  title: string;
  order_index: number;
  complexity_tier: number;
  learning_objective: string;
  concepts: string[];
  backbone_keys: string[];
  level_id?: string | null;
};

export type CurriculumModuleNode = {
  topic: string;
  title: string;
  icon: string;
  min_age: number;
  max_age: number;
  order_index: number;
  levels: CurriculumLevelNode[];
  // Set once the proposal is accepted (modules materialised). Identifies the
  // live/staged Module rows this curriculum owns, regardless of published flag.
  module_id?: string | null;
};

export type CurriculumCoverage = {
  ok: boolean;
  missing_backbone: string[];
  spans_all_tiers: boolean;
  regressions: string[];
};

export type CurriculumDesign = {
  proposal_id: string;
  proposal: { market_code: string; modules: CurriculumModuleNode[] };
  coverage: CurriculumCoverage;
};

export function useCurriculum(marketCode: string) {
  return useQuery({
    queryKey: ['admin', 'curriculum', marketCode],
    queryFn: async (): Promise<CurriculumDesign | null> => {
      try {
        return await adminFetch<CurriculumDesign>(`/admin/markets/${marketCode}/curriculum`);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }
    },
    enabled: !!marketCode,
  });
}

export function useDesignCurriculum(marketCode: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      adminFetch<CurriculumDesign>(`/admin/markets/${marketCode}/curriculum/design`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'curriculum', marketCode] }),
  });
}

export function useAcceptCurriculum(marketCode: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      adminFetch<{ modules: number; levels: number }>(`/admin/markets/${marketCode}/curriculum/accept`, { method: 'POST' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'curriculum', marketCode] });
      qc.invalidateQueries({ queryKey: ['admin', 'modules'] });
      qc.invalidateQueries({ queryKey: ['admin', 'levels'] });
    },
  });
}

export function usePublishCurriculum(marketCode: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      adminFetch<{ published: number; retired: number }>(`/admin/markets/${marketCode}/curriculum/publish`, { method: 'POST' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'curriculum', marketCode] });
      qc.invalidateQueries({ queryKey: ['admin', 'modules'] });
      qc.invalidateQueries({ queryKey: ['admin', 'levels'] });
    },
  });
}
