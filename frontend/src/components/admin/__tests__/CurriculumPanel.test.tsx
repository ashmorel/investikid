import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axe } from 'vitest-axe';
import { describe, it, expect, vi } from 'vitest';
import CurriculumPanel from '../CurriculumPanel';

vi.mock('@/api/admin', async (orig) => ({
  ...(await orig<typeof import('@/api/admin')>()),
  useCurriculum: () => ({ data: {
    proposal_id: 'p1',
    proposal: { market_code: 'US', modules: [
      { topic: 'money', title: 'Money basics', icon: '💵', min_age: 10, max_age: 14,
        order_index: 0, levels: [
          { title: 'L0', order_index: 0, complexity_tier: 1, learning_objective: 'o',
            concepts: ['c'], backbone_keys: ['saving_goals'] }] }] },
    coverage: { ok: false, missing_backbone: ['tax_giving'], spans_all_tiers: true, regressions: [] },
  }, isLoading: false }),
  useDesignCurriculum: () => ({ mutate: vi.fn(), isPending: false }),
  useAcceptCurriculum: () => ({ mutate: vi.fn(), isPending: false }),
}));

function wrap(ui: React.ReactNode) {
  return <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;
}

describe('CurriculumPanel', () => {
  it('shows modules, a tier badge and a coverage gap chip', () => {
    render(wrap(<CurriculumPanel marketCode="US" />));
    expect(screen.getByText('Money basics')).toBeInTheDocument();
    expect(screen.getByText(/tax_giving/)).toBeInTheDocument();      // gap chip
    expect(screen.getByText(/foundational/i)).toBeInTheDocument();   // tier badge
  });

  it('has no axe violations', async () => {
    const { container } = render(wrap(<CurriculumPanel marketCode="US" />));
    expect(await axe(container)).toHaveNoViolations();
  });
});
