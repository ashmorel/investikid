import { apiFetch } from './client';

export type BadgeDefinition = {
  id: string;
  name: string;
  description: string;
  icon_url: string;
  condition_type: string;
  condition_value: number;
  earned_at: null;
};

export type EarnedBadge = {
  id: string;
  name: string;
  description: string;
  icon_url: string;
  earned_at: string;
};

export type ChallengeOut = {
  id: string;
  title: string;
  description: string;
  type: string;
  target_value: number;
  xp_reward: number;
  starts_at: string;
  ends_at: string;
  is_premium: boolean;
  progress: number;
  completed_at: string | null;
};

export type LeaderboardEntry = {
  username: string;
  country_code: string;
  xp_this_week: number;
};

export const gamificationApi = {
  getAllBadges: () => apiFetch<BadgeDefinition[]>('/badges'),
  getEarnedBadges: () => apiFetch<EarnedBadge[]>('/users/me/badges'),
  getChallenges: () => apiFetch<ChallengeOut[]>('/challenges'),
  getLeaderboard: () => apiFetch<LeaderboardEntry[]>('/leaderboard'),
};
