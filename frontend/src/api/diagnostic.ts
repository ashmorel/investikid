import { useQuery } from '@tanstack/react-query';
import { apiFetch } from './client';

// ── Types ──────────────────────────────────────────────────────────

export interface DiagnosticSessionItem {
  id: string;
  topic: string;
  difficulty_tier: 1 | 2 | 3;
  question: string;
  choices: string[];
}

export interface DiagnosticSession {
  session_id: string;
  items: DiagnosticSessionItem[];
}

export interface DiagnosticTopicResult {
  topic: string;
  correct: number;
  attempted: number;
}

export interface DiagnosticResult {
  kind: string;
  overall_score: number;
  topics: DiagnosticTopicResult[];
  session_count: number;
}

export interface DiagnosticEvidence {
  has_baseline: boolean;
  session_count: number;
  last_session_at: string | null;
  topics: DiagnosticTopicResult[];
}

export interface SubmitDiagnosticArgs {
  session_id: string;
  answers?: Record<string, number>;
  skipped?: boolean;
}

// ── Client functions ───────────────────────────────────────────────

export function startDiagnostic(): Promise<DiagnosticSession | null> {
  return apiFetch<DiagnosticSession>('/diagnostic/start', { method: 'POST' });
}

export function submitDiagnostic(body: SubmitDiagnosticArgs): Promise<DiagnosticResult | null> {
  return apiFetch<DiagnosticResult>('/diagnostic/submit', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

// ── Query hook ─────────────────────────────────────────────────────

export function useEvidence() {
  return useQuery({
    queryKey: ['diagnostic', 'evidence'],
    queryFn: () => apiFetch<DiagnosticEvidence>('/diagnostic/evidence'),
    retry: false,
    staleTime: 5 * 60_000,
  });
}
