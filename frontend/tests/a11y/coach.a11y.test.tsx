import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axe } from 'vitest-axe';

vi.mock('@/hooks/useCoachGreeting', () => ({
  useCoachGreeting: () => ({
    greeting: 'Hey kid42! What would you like to learn about today?',
    isLoading: false,
  }),
}));

vi.mock('@/hooks/useChildSession', () => ({
  useChildSession: () => ({ data: { username: 'kid42' } }),
}));

vi.mock('@/api/ai', async () => {
  const actual = await vi.importActual('@/api/ai');
  return {
    ...actual,
    useRecommendations: () => ({
      data: {
        continue_learning: [],
        practise_again: [],
        something_new: [],
        review_summary: { due_count: 0, next_due_at: null },
      },
      isLoading: false,
    }),
    useStrengths: () => ({
      data: { topics: [], overall_mastery: 0 },
      isLoading: false,
    }),
  };
});

beforeEach(() => vi.restoreAllMocks());

describe('a11y: Coach Eddie', () => {
  it('Coach page has no axe violations', async () => {
    const { default: Coach } = await import('@/pages/child/Coach');
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { container } = render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={['/coach']}>
          <Routes>
            <Route path="/coach" element={<Coach />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );
    await waitFor(() => expect(screen.getByText(/Hey kid42/)).toBeInTheDocument());
    expect(await axe(container)).toHaveNoViolations();
  });

  it('EddieFAB has no axe violations', async () => {
    const { EddieFAB } = await import('@/components/child/EddieFAB');
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { container } = render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <EddieFAB dueCount={2} />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
