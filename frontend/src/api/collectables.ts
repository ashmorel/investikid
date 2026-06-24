import { useQuery } from '@tanstack/react-query';
import { apiFetch } from './client';

export type CollectableGoal = { type: string; threshold: number; current: number };

export type CollectableDrop = {
  slug: string;
  name: string;
  emoji: string;
  type: string;
  rarity: string | null;
  ends_at: string | null;
  goal: CollectableGoal;
  earned: boolean;
};

export type OwnedCollectable = {
  slug: string;
  name: string;
  emoji: string;
  type: string;
  rarity: string | null;
  equipped: boolean;
};

export type CollectablesState = { active: CollectableDrop[]; owned: OwnedCollectable[] };

export const getCollectables = () => apiFetch<CollectablesState>('/collectables');

export function useCollectables() {
  return useQuery({ queryKey: ['collectables'], queryFn: getCollectables });
}
