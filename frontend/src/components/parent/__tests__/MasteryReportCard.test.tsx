import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import type { MasteryReport } from '@/api/parent';
import { MasteryReportCard } from '../MasteryReportCard';

let report: MasteryReport;
vi.mock('@/api/parent', () => ({
  parentApi: { getMasteryReport: () => Promise.resolve(report) },
}));

function renderCard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MasteryReportCard />
    </QueryClientProvider>,
  );
}

const childBase = {
  user_id: 'c1', username: 'maya', mastered_count: 2, mastered_total: 5,
  objectives: ['explain what a stock is', 'spot a scam'],
  standards: [{ framework: 'MaPS', code: 'MM-1' }],
  weak_topic: 'budgeting',
  next_recommendation: { module_title: 'Budgeting Basics', level_title: 'Level 1' },
};

describe('MasteryReportCard', () => {
  it('renders single-child headline, objective chips, standards and weak-area line', async () => {
    report = { window_days: 30, household_mastered_count: 2, children: [childBase] };
    renderCard();
    expect(await screen.findByText(/maya mastered 2 skills this month/i)).toBeInTheDocument();
    expect(screen.getByText(/can now: explain what a stock is/i)).toBeInTheDocument();
    expect(screen.getByText(/aligned to maps/i)).toBeInTheDocument();
    expect(screen.getByText(/worth a look/i)).toBeInTheDocument();
  });

  it('renders household headline for multiple children', async () => {
    report = {
      window_days: 30, household_mastered_count: 3,
      children: [childBase, { ...childBase, user_id: 'c2', username: 'tom', mastered_count: 1, objectives: [] }],
    };
    renderCard();
    expect(await screen.findByText(/3 skills mastered in the last 30 days/i)).toBeInTheDocument();
    expect(screen.getByText(/tom · 1 this month/i)).toBeInTheDocument();
  });

  it('shows an encouraging empty state', async () => {
    report = {
      window_days: 30, household_mastered_count: 0,
      children: [{ ...childBase, mastered_count: 0, objectives: [], weak_topic: null }],
    };
    renderCard();
    expect(await screen.findByText(/no new masteries yet/i)).toBeInTheDocument();
    expect(screen.getByText(/budgeting basics — level 1/i)).toBeInTheDocument();
  });

  it('renders nothing with no children', async () => {
    report = { window_days: 30, household_mastered_count: 0, children: [] };
    const { container } = renderCard();
    await waitFor(() => expect(container.querySelector('section')).toBeNull());
  });

  it('has no axe violations', async () => {
    report = { window_days: 30, household_mastered_count: 2, children: [childBase] };
    const { container } = renderCard();
    await screen.findByText(/maya mastered/i);
    expect(await axe(container)).toHaveNoViolations();
  });
});
