import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import BadgeList from '../BadgeList';

vi.mock('@/api/admin', () => ({
  useBadges: () => ({
    data: [
      { id: '1', name: 'First Steps', description: 'Complete 1 lesson', icon_url: '🌟', condition_type: 'lesson_count', condition_value: 1 },
      { id: '2', name: 'Streak Master', description: '7 day streak', icon_url: '🔥', condition_type: 'streak_days', condition_value: 7 },
    ],
    isLoading: false,
  }),
  useDeleteBadge: () => ({ mutate: vi.fn() }),
  badgeIcon: (b: { icon_url: string }) => b.icon_url,
}));

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('BadgeList', () => {
  it('renders badge names', () => {
    render(<BadgeList />, { wrapper });
    expect(screen.getByText('First Steps')).toBeInTheDocument();
    expect(screen.getByText('Streak Master')).toBeInTheDocument();
  });

  it('renders new badge button', () => {
    render(<BadgeList />, { wrapper });
    expect(screen.getByRole('link', { name: /new badge/i })).toBeInTheDocument();
  });
});
