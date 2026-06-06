import { apiFetch } from './client';

export type ActiveMission = {
  id: string;
  lesson_id: string;
  mission_type: string;
  title: string;
  prompt: string;
  params_json: Record<string, unknown>;
};

export const missionsApi = {
  getActive: () => apiFetch<ActiveMission[]>('/missions/active'),
};
