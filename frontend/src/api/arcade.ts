import { useQuery } from '@tanstack/react-query';
import { apiFetch } from './client';

export type QuizItem = { lesson_id: string; question: string; choices: string[]; answer_index: number };
export type QuizSession = { items: QuizItem[] };
export type QuizAnswer = { lesson_id: string; choice_index: number; time_ms: number };
export type QuizScoreBody = { session_items: QuizItem[]; answers: QuizAnswer[] };
export type QuizScoreResult = {
  points: number; coins_awarded: number; personal_best: number; leaderboard_rank: number | null;
};
export type ArcadeLeaderboard = { entries: { username: string; country_code: string; points: number }[] };

export function getQuizRushSession() {
  return apiFetch<QuizSession>('/arcade/quiz-rush/session');
}

export function submitQuizRushScore(body: QuizScoreBody) {
  return apiFetch<QuizScoreResult>('/arcade/quiz-rush/score', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function getArcadeLeaderboard(game = 'quiz_rush') {
  return apiFetch<ArcadeLeaderboard>(`/arcade/leaderboard?game=${encodeURIComponent(game)}`);
}

export function useArcadeLeaderboard(game = 'quiz_rush') {
  return useQuery({ queryKey: ['arcade', 'leaderboard', game], queryFn: () => getArcadeLeaderboard(game) });
}
