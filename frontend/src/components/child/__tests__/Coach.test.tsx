import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

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
    aiApi: {
      ...((actual as { aiApi?: object }).aiApi ?? {}),
      sendCoachMessage: vi.fn().mockResolvedValue({
        response: 'Try Stocks 101!',
        conversation_id: 'c1',
        messages_remaining: 4,
        actions: [
          { type: 'module', module_id: 'mod-1', lesson_id: null, label: 'Go to Stocks 101' },
        ],
      }),
    },
  };
});

vi.mock('@/hooks/useChildSession', () => ({
  useChildSession: () => ({ data: { username: 'kid42' } }),
}));

function renderCoach() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Coach />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

let Coach: typeof import('@/pages/child/Coach').default;

beforeEach(async () => {
  Coach = (await import('@/pages/child/Coach')).default;
});

describe('Coach Page', () => {
  it('shows template greeting', async () => {
    renderCoach();
    expect(screen.getByText(/Hey kid42/)).toBeInTheDocument();
  });

  it('renders suggestion chips', () => {
    renderCoach();
    expect(screen.getByText('What should I learn next?')).toBeInTheDocument();
    expect(screen.getByText('Review my weak spots')).toBeInTheDocument();
    expect(screen.getByText('How am I doing?')).toBeInTheDocument();
  });

  it('sends chip text as first message', async () => {
    const { aiApi } = await import('@/api/ai');
    renderCoach();
    await userEvent.click(screen.getByText('What should I learn next?'));
    await waitFor(() =>
      expect(aiApi.sendCoachMessage).toHaveBeenCalledWith('What should I learn next?', undefined),
    );
  });

  it('renders action buttons from response', async () => {
    renderCoach();
    await userEvent.click(screen.getByText('What should I learn next?'));
    await waitFor(() =>
      expect(screen.getByText(/Go to Stocks 101/)).toBeInTheDocument(),
    );
  });
});
