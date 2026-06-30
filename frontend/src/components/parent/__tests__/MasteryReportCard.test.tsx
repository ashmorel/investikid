import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import type { MasteryReport, GrowthBlock } from '@/api/parent';
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
  growth: null,
};

const growthWithBaseline: GrowthBlock = {
  has_baseline: true,
  overall_delta: 0.18,
  baseline_overall: 0.42,
  latest_overall: 0.60,
  session_count: 5,
  topic_deltas: [
    { topic: 'Saving', baseline_score: 0.5, latest_score: 0.75, delta: 0.25 },
    { topic: 'Investing', baseline_score: 0.3, latest_score: 0.45, delta: 0.15 },
  ],
  focus_topic: 'Budgeting',
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

  // ── Growth block tests ────────────────────────────────────────────────

  it('shows growth delta, topic deltas, focus topic and conversation prompt when has_baseline is true', async () => {
    report = {
      window_days: 30, household_mastered_count: 2,
      children: [{ ...childBase, growth: growthWithBaseline }],
    };
    renderCard();
    await screen.findByText(/maya mastered/i);
    // Overall delta shown as percentage (appears in the big number AND the subtitle)
    expect(screen.getAllByText(/\+18%/).length).toBeGreaterThan(0);
    // Topic delta rows
    expect(screen.getAllByText(/Saving/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Investing/).length).toBeGreaterThan(0);
    // Focus topic — appears in the focus line and the conversation prompt
    expect(screen.getAllByText(/Budgeting/).length).toBeGreaterThan(0);
    // Conversation prompt contains "ask"
    expect(screen.getByText(/ask maya what they found most surprising/i)).toBeInTheDocument();
  });

  it('shows gentle baseline state when has_baseline is false', async () => {
    const noBaseline: GrowthBlock = {
      has_baseline: false,
      overall_delta: null,
      baseline_overall: null,
      latest_overall: null,
      session_count: null,
      topic_deltas: [],
      focus_topic: null,
    };
    report = {
      window_days: 30, household_mastered_count: 0,
      children: [{ ...childBase, mastered_count: 0, objectives: [], growth: noBaseline }],
    };
    renderCard();
    await screen.findAllByText(/maya/i);
    // Gentle "check back" message rendered
    expect(screen.getByText(/baseline captured/i)).toBeInTheDocument();
    // No delta percentage shown
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
  });

  it('renders fine and shows no growth section when growth is null', async () => {
    report = {
      window_days: 30, household_mastered_count: 2,
      children: [{ ...childBase, growth: null }],
    };
    renderCard();
    await screen.findByText(/maya mastered/i);
    expect(screen.queryByText(/baseline captured/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
  });

  it('has no axe violations with a growth child rendered', async () => {
    report = {
      window_days: 30, household_mastered_count: 2,
      children: [{ ...childBase, growth: growthWithBaseline }],
    };
    const { container } = renderCard();
    await screen.findAllByText(/\+18%/);
    expect(await axe(container)).toHaveNoViolations();
  });
});
