import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from './client';

// ── Types ──────────────────────────────────────────────────────────

export type VerifierStatus = 'agree' | 'mismatch' | 'ambiguous' | 'error';

export interface DiagnosticItem {
  id: string;
  market_code: string;
  topic: string;
  concept_id: string | null;
  difficulty_tier: 1 | 2 | 3;
  question: string;
  choices: string[];
  answer_index: number;
  explanation: string;
  status: 'draft' | 'approved' | 'retired';
  source: string;
  times_shown: number;
  times_correct: number;
  approved_by: string | null;
  approved_at: string | null;
  created_at: string;
  verifier_status: VerifierStatus | null;
  verifier_answer_index: number | null;
  verifier_note: string | null;
  verified_at: string | null;
}

export interface CoverageCell {
  topic: string;
  difficulty_tier: 1 | 2 | 3;
  approved_count: number;
}

export interface DiagnosticItemsResponse {
  items: DiagnosticItem[];
  coverage: CoverageCell[];
}

export interface GenerateParams {
  market_code: string;
  topic: string;
  difficulty_tier: 1 | 2 | 3;
  count: number;
}

export interface DiagnosticItemPatch {
  question?: string;
  choices?: string[];
  answer_index?: number;
  explanation?: string;
  difficulty_tier?: 1 | 2 | 3;
  concept_id?: string | null;
}

export interface DiagnosticFilters {
  market_code?: string;
  topic?: string;
  status?: string;
  verifier?: 'needs_review' | '';
}

export interface VerifyParams {
  market_code?: string;
  topic?: string;
  status?: string;
  limit?: number;
  only_unverified?: boolean;
  tier?: 1 | 2 | 3;
}

export interface VerifyFlaggedItem {
  id: string;
  topic: string;
  difficulty_tier: number;
  answer_index: number;
  verifier_answer_index: number | null;
  verifier_status: VerifierStatus;
  verifier_note: string | null;
}

export interface VerifyResult {
  verified: number;
  agree: number;
  mismatch: number;
  ambiguous: number;
  error: number;
  flagged: VerifyFlaggedItem[];
}

// ── Query keys ──────────────────────────────────────────────────────

const DIAGNOSTIC_KEY = ['admin', 'diagnostic-items'];

// ── Hooks ────────────────────────────────────────────────────────────

function useInvalidate() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: DIAGNOSTIC_KEY });
}

export function useDiagnosticItems(filters: DiagnosticFilters = {}) {
  const params = new URLSearchParams();
  if (filters.market_code) params.set('market_code', filters.market_code);
  if (filters.topic) params.set('topic', filters.topic);
  if (filters.status) params.set('status', filters.status);
  if (filters.verifier) params.set('verifier', filters.verifier);
  const qs = params.toString();
  return useQuery({
    queryKey: [...DIAGNOSTIC_KEY, filters],
    queryFn: () =>
      apiFetch<DiagnosticItemsResponse>(
        `/admin/diagnostic-items${qs ? `?${qs}` : ''}`,
      ) as Promise<DiagnosticItemsResponse>,
  });
}

export function useVerifyItems() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: VerifyParams) =>
      apiFetch<VerifyResult>('/admin/diagnostic-items/verify', {
        method: 'POST',
        body: JSON.stringify(body),
      }) as Promise<VerifyResult>,
    onSuccess: invalidate,
  });
}

export function useGenerateItems() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: GenerateParams) =>
      apiFetch<{ items: DiagnosticItem[] }>('/admin/diagnostic-items/generate', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: invalidate,
  });
}

export function usePatchItem() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: DiagnosticItemPatch }) =>
      apiFetch<DiagnosticItem>(`/admin/diagnostic-items/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      }),
    onSuccess: invalidate,
  });
}

export function useApproveItem() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<DiagnosticItem>(`/admin/diagnostic-items/${id}/approve`, { method: 'POST' }),
    onSuccess: invalidate,
  });
}

export function useRejectItem() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<DiagnosticItem>(`/admin/diagnostic-items/${id}/reject`, { method: 'POST' }),
    onSuccess: invalidate,
  });
}

export function useRetireItem() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<DiagnosticItem>(`/admin/diagnostic-items/${id}/retire`, { method: 'POST' }),
    onSuccess: invalidate,
  });
}
