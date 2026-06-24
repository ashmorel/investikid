import { useQuery } from '@tanstack/react-query';
import { apiFetch } from './client';

export type MoneyWordGuess = { word: string; feedback: string[] };
export type MoneyWordState = {
  length: number;
  max_guesses: number;
  guesses: MoneyWordGuess[];
  completed: boolean;
  solved: boolean;
  definition: string | null;
  already_played: boolean;
};

export function getMoneyWordToday() {
  return apiFetch<MoneyWordState>('/arcade/moneyword/today');
}

export function submitMoneyWordGuess(guess: string) {
  return apiFetch<MoneyWordState>('/arcade/moneyword/guess', {
    method: 'POST',
    body: JSON.stringify({ guess }),
  });
}

export function useMoneyWordToday() {
  // The puzzle resets at 00:00 UTC (the backend keys play rows on the UTC date).
  // Encode that UTC day in the query key so a cached "completed" result can never
  // be served into a new day — when the day rolls over the key changes and React
  // Query refetches a fresh board instead of showing yesterday's "Done".
  const utcDay = new Date().toISOString().slice(0, 10);
  return useQuery({ queryKey: ['arcade', 'moneyword', 'today', utcDay], queryFn: getMoneyWordToday });
}
