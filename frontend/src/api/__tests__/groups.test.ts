import { describe, it, expect, vi } from 'vitest';
import { groupsApi } from '@/api/groups';
import { parentApi } from '@/api/parent';

vi.mock('@/api/client', () => ({
  apiFetch: vi.fn(),
}));

import { apiFetch } from '@/api/client';

describe('groupsApi', () => {
  it('myLeaderboards calls apiFetch on the child leaderboard path', () => {
    groupsApi.myLeaderboards();
    expect(apiFetch).toHaveBeenCalledWith('/groups/leaderboard');
  });
});

describe('parentApi groups', () => {
  it('createGroup POSTs to /parent/groups with the name body', () => {
    parentApi.createGroup('X');
    expect(apiFetch).toHaveBeenCalledWith('/parent/groups', {
      method: 'POST',
      body: JSON.stringify({ name: 'X' }),
    });
  });
});
