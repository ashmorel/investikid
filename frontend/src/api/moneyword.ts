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
  return useQuery({ queryKey: ['arcade', 'moneyword', 'today'], queryFn: getMoneyWordToday });
}
