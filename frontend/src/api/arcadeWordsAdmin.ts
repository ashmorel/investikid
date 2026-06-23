import { useQuery } from '@tanstack/react-query';
import { apiFetch } from './client';

export type ArcadeWord = {
  id: string;
  word: string;
  definition: string;
  language: string;
  length: number;
  status: string;
  source: string;
  created_at: string;
};

export function listArcadeWords(status = 'pending') {
  return apiFetch<ArcadeWord[]>(`/admin/arcade-words?status=${encodeURIComponent(status)}`);
}

export function suggestArcadeWords(count = 10) {
  return apiFetch<ArcadeWord[]>('/admin/arcade-words/suggest', {
    method: 'POST',
    body: JSON.stringify({ count }),
  });
}

export function approveArcadeWord(id: string, edits?: { word?: string; definition?: string }) {
  return apiFetch<ArcadeWord>(`/admin/arcade-words/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify(edits ?? {}),
  });
}

export function rejectArcadeWord(id: string) {
  return apiFetch<ArcadeWord>(`/admin/arcade-words/${id}/reject`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

export function useArcadeWords(status = 'pending') {
  return useQuery({ queryKey: ['admin', 'arcade-words', status], queryFn: () => listArcadeWords(status) });
}
