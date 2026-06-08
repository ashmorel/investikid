import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axe } from 'vitest-axe';
import { PremiumRequestsCard } from '@/components/parent/PremiumRequestsCard';

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}><PremiumRequestsCard /></QueryClientProvider>);
}

describe('a11y: PremiumRequestsCard', () => {
  beforeEach(() => { vi.spyOn(globalThis, 'fetch'); });
  afterEach(() => { vi.restoreAllMocks(); });

  it('no axe violations with a pending request', async () => {
    (globalThis.fetch as any).mockResolvedValue(new Response(JSON.stringify([
      { id: 'r1', child_username: 'Ava', context_kind: 'level', context_label: 'Investing Basics', created_at: '2026-06-06T00:00:00Z' },
    ]), { status: 200 }));
    const { container } = wrap();
    await waitFor(() => expect(screen.getByText(/Ava/)).toBeInTheDocument());
    expect(await axe(container)).toHaveNoViolations();
  });
});
