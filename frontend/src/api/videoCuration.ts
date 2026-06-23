import { apiFetch } from './client';

export type VideoCandidate = {
  id: string;
  youtube_id: string;
  title: string;
  thumbnail_url: string | null;
  source: 'recovered' | 'suggested';
  market_code: string;
  origin_context: string | null;
  suggested_module_id: string | null;
  suggested_level_id: string | null;
  embeddable: boolean | null;
  health_detail: string | null;
  status: string;
};

export const listVideoCandidates = (market?: string): Promise<VideoCandidate[] | null> =>
  apiFetch<VideoCandidate[]>(
    `/admin/video-candidates?status=pending${market ? `&market=${market}` : ''}`,
  );

export const approveVideoCandidate = (
  id: string,
  body: { module_id: string; level_id: string },
): Promise<VideoCandidate | null> =>
  apiFetch<VideoCandidate>(`/admin/video-candidates/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify(body),
  });

export const skipVideoCandidate = (id: string): Promise<VideoCandidate | null> =>
  apiFetch<VideoCandidate>(`/admin/video-candidates/${id}/skip`, { method: 'POST' });

export const suggestVideos = (body: {
  module_id: string;
  level_id: string;
}): Promise<{ created: number } | null> =>
  apiFetch<{ created: number }>(`/admin/video-candidates/suggest`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
