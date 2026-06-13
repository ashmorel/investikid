
export type GroupChallenge = {
  id: string;
  title: string;
  description: string;
  target_value: number;
  group_progress: number;
  completed: boolean;
  ends_at: string;
};

export type GroupChallenges = {
  group_id: string;
  group_name: string;
  challenges: GroupChallenge[];
};
import { apiFetch } from './client';

export type GroupLeaderboardEntry = { username: string; xp_this_week: number; is_me: boolean };
export type GroupLeaderboard = { group_id: string; group_name: string; entries: GroupLeaderboardEntry[] };

export const groupsApi = {
  myLeaderboards: () => apiFetch<GroupLeaderboard[]>('/groups/leaderboard'),
  myChallenges: () => apiFetch<GroupChallenges[]>('/groups/challenges'),
};
