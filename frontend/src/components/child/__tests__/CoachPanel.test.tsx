import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CoachPanel } from '@/components/child/CoachPanel';

vi.mock('@/hooks/useMediaQuery', () => ({ useMediaQuery: vi.fn() }));

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

import { useMediaQuery } from '@/hooks/useMediaQuery';

function renderCoachPanel(onOpenChange = vi.fn()) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <CoachPanel open onOpenChange={onOpenChange} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return { onOpenChange };
}

beforeEach(() => vi.clearAllMocks());

describe('CoachPanel', () => {
  it('renders Coach Penny in a dialog', () => {
    (useMediaQuery as ReturnType<typeof vi.fn>).mockReturnValue(true);
    renderCoachPanel();
    expect(screen.getByRole('dialog', { name: /coach penny/i })).toBeInTheDocument();
    expect(screen.getByText(/Hey kid42/)).toBeInTheDocument();
  });

  it('closes when a response action is followed', async () => {
    (useMediaQuery as ReturnType<typeof vi.fn>).mockReturnValue(true);
    const { onOpenChange } = renderCoachPanel();
    await userEvent.click(screen.getByText('What should I learn next?'));
    await userEvent.click(await screen.findByRole('link', { name: /go to stocks 101/i }));
    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
  });

  it('renders a bottom sheet on mobile', () => {
    (useMediaQuery as ReturnType<typeof vi.fn>).mockReturnValue(false);
    renderCoachPanel();
    expect(screen.getByText('Coach Penny')).toBeInTheDocument();
    const dialog = screen.getByRole('dialog', { name: /coach penny/i });
    expect(dialog.className).toContain('rounded-t-2xl');
  });

  it('renders a right side panel on desktop', () => {
    (useMediaQuery as ReturnType<typeof vi.fn>).mockReturnValue(true);
    renderCoachPanel();
    const dialog = screen.getByRole('dialog', { name: /coach penny/i });
    expect(dialog.className).toContain('max-w-md');
  });
});
