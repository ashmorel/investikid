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
        { topic: 'stocks', status: 'strong', mastery_score: 0.88, weak_count: 1, due_for_review: 0, total_concepts: 8 },
        { topic: 'saving_budgeting', status: 'needs_practice', mastery_score: 0.45, weak_count: 3, due_for_review: 2, total_concepts: 6 },
        { topic: 'budgeting', status: 'new', mastery_score: 0, weak_count: 0, due_for_review: 0, total_concepts: 4 },
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
});
