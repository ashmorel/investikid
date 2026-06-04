import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Coach from '@/pages/child/Coach';

vi.mock('@/hooks/useCoachGreeting', () => ({
  useCoachGreeting: () => ({
    greeting: 'Hey kid42! You have 2 concepts ready for review — want to go over them?',
    isLoading: false,
  }),
}));

vi.mock('@/api/ai', async () => {
  const actual = await vi.importActual('@/api/ai');
  return {
    ...actual,
    useRecommendations: () => ({ data: null, isLoading: false }),
    useStrengths: () => ({ data: null, isLoading: false }),
  };
});

function renderCoachPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Coach />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Coach Page', () => {
  it('renders the coach chat with a home back link', () => {
    renderCoachPage();
    expect(screen.getByRole('link', { name: /back to home/i })).toHaveAttribute('href', '/home');
    expect(screen.getByText('Coach Penny')).toBeInTheDocument();
    expect(screen.getByText(/Hey kid42/)).toBeInTheDocument();
  });
});
