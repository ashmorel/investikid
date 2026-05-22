import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ChallengeList from '../ChallengeList';

vi.mock('@/api/admin', () => ({
  useChallenges: () => ({
    data: [
      { id: '1', title: 'Weekly Sprint', description: 'Complete 3 lessons', type: 'lessons_completed', target_value: 3, xp_reward: 50, badge_id: null, starts_at: '2026-05-21T00:00:00Z', ends_at: '2026-05-28T00:00:00Z', is_premium: false },
    ],
    isLoading: false,
  }),
  useDeleteChallenge: () => ({ mutate: vi.fn() }),
}));

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('ChallengeList', () => {
  it('renders challenge titles', () => {
    render(<ChallengeList />, { wrapper });
    expect(screen.getByText('Weekly Sprint')).toBeInTheDocument();
  });

  it('renders new challenge button', () => {
    render(<ChallengeList />, { wrapper });
    expect(screen.getByRole('link', { name: /new challenge/i })).toBeInTheDocument();
  });
});
