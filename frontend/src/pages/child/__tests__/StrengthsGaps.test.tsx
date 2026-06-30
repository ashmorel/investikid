import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'vitest-axe';
import StrengthsGaps from '../StrengthsGaps';

vi.mock('@/api/ai', () => ({
  useStrengths: () => ({
    isLoading: false,
    data: {
      overall_mastery: 0.72,
      topics: [
        {
          topic: 'stocks',
          status: 'strong',
          mastery_score: 0.88,
          weak_count: 1,
          due_for_review: 0,
          total_concepts: 8,
          concepts: [
            { concept_id: 'c1', slug: 'shares', name: 'Shares', mastery_score: 0.9, status: 'strong', attempts: 5 },
            { concept_id: 'c2', slug: 'dividends', name: 'Dividends', mastery_score: 0.4, status: 'needs_practice', attempts: 3 },
          ],
        },
        {
          topic: 'saving_budgeting',
          status: 'needs_practice',
          mastery_score: 0.45,
          weak_count: 3,
          due_for_review: 2,
          total_concepts: 6,
          concepts: [],
        },
        {
          topic: 'budgeting',
          status: 'new',
          mastery_score: 0,
          weak_count: 0,
          due_for_review: 0,
          total_concepts: 4,
          concepts: [],
        },
      ],
    },
  }),
}));

function renderPage() {
  return render(
    <MemoryRouter>
      <StrengthsGaps />
    </MemoryRouter>,
  );
}

describe('StrengthsGaps (Progress redesign)', () => {
  it('renders the progress screen on brand tokens (no dark-slate / off-brand surfaces)', () => {
    const { container } = renderPage();
    expect(screen.getByText('My Progress')).toBeInTheDocument();
    expect(container.querySelector('[class*="slate-800"]')).toBeNull();
    expect(container.querySelector('[class*="slate-500"]')).toBeNull();
    // The old off-brand purple ring stroke must be gone.
    expect(container.querySelector('[stroke="#7c3aed"]')).toBeNull();
  });

  it('shows a Revise CTA when concepts are due, linking to the Revise tab', () => {
    renderPage();
    const cta = screen.getByRole('link', { name: /concepts due — revise/i });
    expect(cta).toHaveAttribute('href', '/revise');
  });

  it('filters topics by status when a chip is selected', () => {
    renderPage();
    expect(screen.getByText('stocks')).toBeInTheDocument();
    expect(screen.getByText('saving budgeting')).toBeInTheDocument();
    expect(screen.getByText('budgeting')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Strong' }));
    expect(screen.getByText('stocks')).toBeInTheDocument();
    expect(screen.queryByText('saving budgeting')).toBeNull();
    expect(screen.queryByText('budgeting')).toBeNull();
  });

  it('has no accessibility violations', async () => {
    const { container } = renderPage();
    expect(await axe(container)).toHaveNoViolations();
  });

  // --- Concept drill-down (Task 4) ---

  it('shows an expand button on topics that have concepts, hidden for topics without', () => {
    renderPage();
    // stocks has 2 concepts → expander present
    const expanders = screen.getAllByRole('button', { name: /show concepts/i });
    expect(expanders.length).toBeGreaterThanOrEqual(1);
    // saving_budgeting and budgeting have concepts:[] → no separate expander for them
    // (only one expander should exist — for stocks)
    expect(expanders).toHaveLength(1);
  });

  it('concept drill-down is collapsed by default (aria-expanded=false)', () => {
    renderPage();
    const expander = screen.getByRole('button', { name: /show concepts/i });
    expect(expander).toHaveAttribute('aria-expanded', 'false');
    // Concept names are NOT visible before expansion
    expect(screen.queryByText('Shares')).toBeNull();
    expect(screen.queryByText('Dividends')).toBeNull();
  });

  it('expanding reveals concept names and their status pills', () => {
    renderPage();
    const expander = screen.getByRole('button', { name: /show concepts/i });
    fireEvent.click(expander);

    expect(expander).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Shares')).toBeInTheDocument();
    expect(screen.getByText('Dividends')).toBeInTheDocument();

    // Status pills for concepts appear (may be multiple "Strong" pills from topic + concept)
    const strongPills = screen.getAllByText(/Strong — keep it up!/i);
    expect(strongPills.length).toBeGreaterThanOrEqual(1);
    const practicePills = screen.getAllByText(/Needs practice/i);
    expect(practicePills.length).toBeGreaterThanOrEqual(1);
  });

  it('collapses the drill-down on a second tap and hides concept names', () => {
    renderPage();
    const expander = screen.getByRole('button', { name: /show concepts/i });
    fireEvent.click(expander); // expand
    expect(screen.getByText('Shares')).toBeInTheDocument();
    fireEvent.click(expander); // collapse
    expect(screen.queryByText('Shares')).toBeNull();
    expect(expander).toHaveAttribute('aria-expanded', 'false');
  });

  it('expander button meets the ≥44px minimum touch target', () => {
    renderPage();
    const expander = screen.getByRole('button', { name: /show concepts/i });
    // min-h-[44px] is applied via className — check that the class is present
    expect(expander.className).toMatch(/min-h-\[44px\]/);
  });

  it('has no accessibility violations with concepts expanded', async () => {
    const { container } = renderPage();
    const expander = screen.getByRole('button', { name: /show concepts/i });
    fireEvent.click(expander);
    expect(await axe(container)).toHaveNoViolations();
  });
});
