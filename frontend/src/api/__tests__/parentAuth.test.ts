import { describe, it, expect, vi } from 'vitest';
import { parentAuthApi } from '@/api/parentAuth';

vi.mock('@/api/client', () => ({
  apiFetch: vi.fn(),
}));

import { apiFetch } from '@/api/client';

describe('parentAuthApi', () => {
  it('oauthSignIn calls apiFetch with correct path and body', () => {
    parentAuthApi.oauthSignIn('google', 'tok', 'n1');
    expect(apiFetch).toHaveBeenCalledWith('/parent/auth/oauth/google', {
      method: 'POST',
      body: JSON.stringify({ id_token: 'tok', nonce: 'n1' }),
    });
  });

  it('oauthSignIn works for apple provider', () => {
    parentAuthApi.oauthSignIn('apple', 'apple-tok', 'n2');
    expect(apiFetch).toHaveBeenCalledWith('/parent/auth/oauth/apple', {
      method: 'POST',
      body: JSON.stringify({ id_token: 'apple-tok', nonce: 'n2' }),
    });
  });

  it('linkProvider calls apiFetch with correct path and body', () => {
    parentAuthApi.linkProvider('google', 'tok2', 'n3');
    expect(apiFetch).toHaveBeenCalledWith('/parent/auth/oauth/google/link', {
      method: 'POST',
      body: JSON.stringify({ id_token: 'tok2', nonce: 'n3' }),
    });
  });

  it('unlinkProvider calls apiFetch with DELETE on the link path', () => {
    parentAuthApi.unlinkProvider('apple');
    expect(apiFetch).toHaveBeenCalledWith('/parent/auth/oauth/apple/link', {
      method: 'DELETE',
    });
  });

  it('listIdentities calls apiFetch with GET on identities path', () => {
    parentAuthApi.listIdentities();
    expect(apiFetch).toHaveBeenCalledWith('/parent/auth/identities');
  });
});
