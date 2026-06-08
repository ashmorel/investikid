import { apiFetch } from './client';

export type ChildSummary = {
  username: string;
  age: number;
  country_code: string;
};

export type Decision = 'approve' | 'decline';

export const consentApi = {
  verify: (token: string) =>
    apiFetch<ChildSummary>(`/consent/verify?token=${encodeURIComponent(token)}`),
  decide: (token: string, decision: Decision, attestGuardian = false) =>
    apiFetch<{ status: string; decision: Decision }>(
      `/consent/decide?token=${encodeURIComponent(token)}`,
      { method: 'POST', body: JSON.stringify({ decision, attest_guardian: attestGuardian }) },
    ),
};
