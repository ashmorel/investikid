import { useMutation } from '@tanstack/react-query';
import { apiFetch } from './client';

export type FeedbackType = 'bug' | 'feature' | 'general';

export interface FeedbackPayload {
  feedback_type: FeedbackType;
  message: string;
  page_url: string | null;
  /** Optional compressed JPEG data URL — attached to the notification email. */
  screenshot?: string | null;
}

export interface FeedbackCreateResponse {
  id: string;
}

/**
 * Submit feedback. `audience` selects the endpoint:
 * - 'child'  → POST /feedback        (child cookie session)
 * - 'parent' → POST /parent/feedback (parent magic-link session)
 */
export function useSubmitFeedback(audience: 'child' | 'parent') {
  const path = audience === 'parent' ? '/parent/feedback' : '/feedback';
  return useMutation({
    mutationFn: (payload: FeedbackPayload) =>
      apiFetch<FeedbackCreateResponse>(path, {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
  });
}
