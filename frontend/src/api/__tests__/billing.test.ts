import { describe, it, expect, vi } from 'vitest';
import { billingApi } from '@/api/billing';
import { premiumApi } from '@/api/premium';

vi.mock('@/api/client', () => ({
  apiFetch: vi.fn(),
}));

import { apiFetch } from '@/api/client';

describe('billingApi', () => {
  it('appleVerify calls apiFetch with correct path, method and body', () => {
    billingApi.appleVerify('signed-jws');
    expect(apiFetch).toHaveBeenCalledWith('/billing/apple/verify', {
      method: 'POST',
      body: JSON.stringify({ jws: 'signed-jws' }),
    });
  });

  it('appleAccountToken calls apiFetch with the account-token path', () => {
    billingApi.appleAccountToken();
    expect(apiFetch).toHaveBeenCalledWith('/billing/apple/account-token');
  });
});

describe('premiumApi', () => {
  it('declineRequest calls apiFetch with the decline path and POST', () => {
    premiumApi.declineRequest('req-1');
    expect(apiFetch).toHaveBeenCalledWith('/parent/premium-requests/req-1/decline', {
      method: 'POST',
    });
  });
});
