import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { axe } from 'vitest-axe';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('@/hooks/useChildSession', () => ({
  useChildSession: () => ({ data: { username: 'kid42' } }),
}));

function mockJsonRoute(routeMap: Record<string, unknown>) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : input.toString();
    for (const [path, body] of Object.entries(routeMap)) {
      if (url === path || url.endsWith(path)) {
        return new Response(JSON.stringify(body), { status: 200 });
      }
    }
    return new Response(JSON.stringify(null), { status: 200 });
  });
}

function renderAt(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/progress']}>
        <Routes>
          <Route path="/progress" element={<>{ui}</>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => vi.restoreAllMocks());

describe('a11y: Strengths & Gaps page', () => {
  it('passes axe audit with topics', async () => {
    mockJsonRoute({
      '/profile/strengths': {
        topics: [
          { topic: 'savings', mastery_score: 0.92, status: 'strong', weak_count: 0, due_for_review: 0, total_concepts: 5 },
          { topic: 'interest_rates', mastery_score: 0.58, status: 'needs_practice', weak_count: 2, due_for_review: 1, total_concepts: 4 },
          { topic: 'investing', mastery_score: 0, status: 'new', weak_count: 0, due_for_review: 0, total_concepts: 0 },
        ],
        overall_mastery: 0.75,
      },
    });
    const { default: StrengthsGaps } = await import('@/pages/child/StrengthsGaps');
    const { container } = renderAt(<StrengthsGaps />);
    await waitFor(() => expect(screen.getByText('My Progress')).toBeInTheDocument());
    expect(await axe(container)).toHaveNoViolations();
  });

  it('passes axe audit with empty state', async () => {
    mockJsonRoute({
      '/profile/strengths': { topics: [], overall_mastery: 0 },
    });
    const { default: StrengthsGaps } = await import('@/pages/child/StrengthsGaps');
    const { container } = renderAt(<StrengthsGaps />);
    await waitFor(() => expect(screen.getByText('My Progress')).toBeInTheDocument());
    expect(await axe(container)).toHaveNoViolations();
  });
});
