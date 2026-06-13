import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { EventStrip } from '../EventStrip';

let payload: { event: { title: string; emoji: string; ends_at: string; xp_bonus_pct: number } | null };
vi.mock('@/api/client', () => ({ apiFetch: () => Promise.resolve(payload) }));
let mockTier: 'explorer' | 'investor' = 'explorer';
vi.mock('@/lib/ageTier', async (importOriginal) => {
  const orig = await importOriginal<typeof import('@/lib/ageTier')>();
  return { ...orig, useAgeTier: () => mockTier };
});

function renderStrip() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <EventStrip />
    </QueryClientProvider>,
  );
}

const event = { title: 'Spooky Savings Week', emoji: '🎃', ends_at: '2026-10-31T00:00:00Z', xp_bonus_pct: 25 };

describe('EventStrip (m9)', () => {
  it('shows the active event with bonus', async () => {
    mockTier = 'explorer';
    payload = { event };
    renderStrip();
    expect(await screen.findByText(/spooky savings week/i)).toBeInTheDocument();
    expect(screen.getByText(/\+25% XP!/)).toBeInTheDocument();
    expect(screen.getByText('🎃')).toBeInTheDocument();
  });

  it('investor tier drops the emoji', async () => {
    mockTier = 'investor';
    payload = { event };
    renderStrip();
    await screen.findByText(/spooky savings week/i);
    expect(screen.queryByText('🎃')).toBeNull();
  });

  it('renders nothing without an active event', async () => {
    mockTier = 'explorer';
    payload = { event: null };
    const { container } = renderStrip();
    await waitFor(() => expect(container.firstChild).toBeNull());
  });

  it('has no axe violations', async () => {
    mockTier = 'explorer';
    payload = { event };
    const { container } = renderStrip();
    await screen.findByText(/spooky/i);
    expect(await axe(container)).toHaveNoViolations();
  });
});
