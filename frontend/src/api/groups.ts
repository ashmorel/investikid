import { apiFetch } from './client';

export type GroupLeaderboardEntry = { username: string; xp_this_week: number; is_me: boolean };
export type GroupLeaderboard = { group_id: string; group_name: string; entries: GroupLeaderboardEntry[] };

export const groupsApi = {
  myLeaderboards: () => apiFetch<GroupLeaderboard[]>('/groups/leaderboard'),
};
