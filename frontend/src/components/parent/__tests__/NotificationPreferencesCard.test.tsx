import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axe } from 'vitest-axe';
import { NotificationPreferencesCard } from '../NotificationPreferencesCard';
import { parentApi } from '@/api/parent';

vi.mock('@/api/parent', () => ({
  parentApi: {
    getPreferences: vi.fn(),
    updatePreferences: vi.fn(),
  },
}));

function renderCard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <NotificationPreferencesCard />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.mocked(parentApi.getPreferences).mockResolvedValue({
    trial_reminder_opt_out: false,
    weekly_digest_opt_out: false,
  });
  vi.mocked(parentApi.updatePreferences).mockResolvedValue({
    trial_reminder_opt_out: true,
    weekly_digest_opt_out: false,
  });
});

describe('NotificationPreferencesCard', () => {
  it('renders the toggle ON when not opted out', async () => {
    renderCard();
    const sw = await screen.findByRole('switch', { name: /email me about my subscription/i });
    await waitFor(() => expect(sw).toBeChecked());
  });

  it('opting out calls updatePreferences with trial_reminder_opt_out true', async () => {
    renderCard();
    const sw = await screen.findByRole('switch', { name: /email me about my subscription/i });
    await waitFor(() => expect(sw).toBeChecked());
    fireEvent.click(sw);
    await waitFor(() =>
      expect(parentApi.updatePreferences).toHaveBeenCalledWith({ trial_reminder_opt_out: true }),
    );
  });

  it('renders the weekly digest toggle ON when not opted out', async () => {
    renderCard();
    const sw = await screen.findByRole('switch', { name: /weekly progress email/i });
    await waitFor(() => expect(sw).toBeChecked());
  });

  it('renders the weekly digest toggle OFF when opted out', async () => {
    vi.mocked(parentApi.getPreferences).mockResolvedValue({
      trial_reminder_opt_out: false,
      weekly_digest_opt_out: true,
    });
    renderCard();
    const sw = await screen.findByRole('switch', { name: /weekly progress email/i });
    await waitFor(() => expect(sw).not.toBeChecked());
  });

  it('opting out of the digest calls updatePreferences with weekly_digest_opt_out true', async () => {
    renderCard();
    const sw = await screen.findByRole('switch', { name: /weekly progress email/i });
    await waitFor(() => expect(sw).toBeChecked());
    fireEvent.click(sw);
    await waitFor(() =>
      expect(parentApi.updatePreferences).toHaveBeenCalledWith({ weekly_digest_opt_out: true }),
    );
  });

  it('has no axe violations', async () => {
    const { container } = renderCard();
    await screen.findAllByRole('switch');
    expect(await axe(container)).toHaveNoViolations();
  });
});
