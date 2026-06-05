import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'vitest-axe';
import StrengthsGaps from '../StrengthsGaps';

vi.mock('@/api/ai', () => ({
  useStrengths: () => ({
    isLoading: false,
    data: {
      overall_mastery: 0.6,
      topics: [
        { topic: 'stocks', status: 'strong', mastery_score: 0.8, weak_count: 1, due_for_review: 0 },
        { topic: 'budgeting', status: 'new', mastery_score: 0, weak_count: 0, due_for_review: 0 },
      ],
    },
  }),
}));

describe('StrengthsGaps (light re-skin)', () => {
  it('renders the progress screen with no dark-slate surfaces', () => {
    const { container } = render(<StrengthsGaps />);
    expect(screen.getByText('My Progress')).toBeInTheDocument();
    expect(container.querySelector('[class*="slate-800"]')).toBeNull();
    expect(container.querySelector('[class*="slate-600"]')).toBeNull();
    expect(container.querySelector('[class*="slate-500"]')).toBeNull();
    expect(container.querySelector('[class*="slate-400"]')).toBeNull();
    expect(container.querySelector('[class*="text-success-500"]')).toBeNull();
    expect(container.querySelector('[class*="text-accent-500"]')).toBeNull();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<StrengthsGaps />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
