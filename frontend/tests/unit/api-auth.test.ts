import { describe, it, expect, vi, beforeEach } from 'vitest';
import { authApi } from '@/api/auth';

beforeEach(() => {
  document.cookie = 'csrf_token=ct';
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify({ id: 'u', email: 'k@x.com' }), { status: 200 }),
  );
});

describe('authApi', () => {
  it('me is GET /users/me', async () => {
    await authApi.me();
    const call = (globalThis.fetch as any).mock.calls[0];
    expect(call[0]).toBe('/users/me');
    expect(call[1].method).toBe('GET');
  });

  it('login posts to /auth/login with email + password', async () => {
    await authApi.login('a@x.com', 'pw');
    const call = (globalThis.fetch as any).mock.calls[0];
    expect(call[0]).toBe('/auth/login');
    expect(call[1].method).toBe('POST');
    expect(JSON.parse(call[1].body)).toEqual({ email: 'a@x.com', password: 'pw' });
  });

  it('register posts to /auth/register with full body', async () => {
    await authApi.register({
      email: 'a@x.com', username: 'kid', password: 'pw123456789x',
      dob: '2015-01-01', country_code: 'GB', currency_code: 'GBP',
      parent_email: 'p@x.com', topic_path: null,
    });
    const call = (globalThis.fetch as any).mock.calls[0];
    expect(call[0]).toBe('/auth/register');
    expect(call[1].method).toBe('POST');
    expect(JSON.parse(call[1].body).parent_email).toBe('p@x.com');
  });

  it('logout posts to /auth/logout', async () => {
    await authApi.logout();
    const call = (globalThis.fetch as any).mock.calls[0];
    expect(call[0]).toBe('/auth/logout');
    expect(call[1].method).toBe('POST');
  });
});
