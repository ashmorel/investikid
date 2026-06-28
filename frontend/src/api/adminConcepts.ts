import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from './client';

// ── Types ──────────────────────────────────────────────────────────

export interface ConceptOut {
  id: string;
  topic: string;
  slug: string;
  name: string;
  blurb: string | null;
  difficulty_tier: 1 | 2 | 3;
  order_index: number;
  lesson_count: number;
}

export interface TopicGroup {
  topic: string;
  concepts: ConceptOut[];
}

export interface ConceptsOverview {
  unmapped_lessons: number;
  groups: TopicGroup[];
}

export interface ConceptIn {
  topic: string;
  slug: string;
  name: string;
  blurb?: string | null;
  difficulty_tier: 1 | 2 | 3;
  order_index: number;
}

export interface ConceptPatch {
  topic?: string;
  slug?: string;
  name?: string;
  blurb?: string | null;
  difficulty_tier?: 1 | 2 | 3;
  order_index?: number;
}

// ── Query keys ──────────────────────────────────────────────────────

const CONCEPTS_KEY = ['admin', 'concepts'];

// ── Hooks ────────────────────────────────────────────────────────────

export function useConcepts() {
  return useQuery({
    queryKey: CONCEPTS_KEY,
    queryFn: () => apiFetch<ConceptsOverview>('/admin/concepts') as Promise<ConceptsOverview>,
  });
}

function useInvalidate() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: CONCEPTS_KEY });
}

export function useCreateConcept() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: ConceptIn) =>
      apiFetch<ConceptOut>('/admin/concepts', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: invalidate,
  });
}

export function usePatchConcept() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: ConceptPatch }) =>
      apiFetch<ConceptOut>(`/admin/concepts/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
    onSuccess: invalidate,
  });
}

export function usePatchLessonConcept() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ lessonId, conceptId }: { lessonId: string; conceptId: string | null }) =>
      apiFetch<{ id: string; concept_id: string | null }>(
        `/admin/lessons/${lessonId}/concept`,
        { method: 'PATCH', body: JSON.stringify({ concept_id: conceptId }) },
      ),
    onSuccess: invalidate,
  });
}
