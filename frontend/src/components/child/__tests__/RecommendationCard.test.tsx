import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { RecommendationCard } from '../RecommendationCard';

const BASE_ITEM = {
  module_id: 'mod-1',
  lesson_id: 'les-1',
  score: 0.75,
  reason: 'Keep going!',
  review_prompt: null,
  weak_concepts: [],
};

function renderCard(props: Partial<Parameters<typeof RecommendationCard>[0]> = {}) {
  return render(
    <MemoryRouter>
      <RecommendationCard
        item={BASE_ITEM}
        category="continue_learning"
        moduleTitle="Saving & Budgeting"
        completedCount={3}
        totalCount={6}
        {...props}
      />
    </MemoryRouter>,
  );
}

describe('RecommendationCard', () => {
  it('renders module title and reason', () => {
    renderCard();
    expect(screen.getByText('Saving & Budgeting')).toBeInTheDocument();
    expect(screen.getByText('Keep going!')).toBeInTheDocument();
  });

  it('shows progress bar for continue_learning', () => {
    renderCard({ category: 'continue_learning' });
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
    expect(screen.getByText('3 of 6')).toBeInTheDocument();
  });

  it('shows weak concept chips for practise_again', () => {
    renderCard({
      category: 'practise_again',
      item: {
        ...BASE_ITEM,
        weak_concepts: ['compound interest', 'APR vs APY'],
        review_prompt: '2 concepts to review',
      },
    });
    expect(screen.getByText('compound interest')).toBeInTheDocument();
    expect(screen.getByText('APR vs APY')).toBeInTheDocument();
  });

  it('renders a link for navigation', () => {
    renderCard();
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/lessons/mod-1/les-1');
  });

  it('does not show progress bar for something_new', () => {
    renderCard({ category: 'something_new', completedCount: 0, totalCount: 5 });
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
  });

  it('renders the level eyebrow when level_title is present', () => {
    renderCard({ item: { ...BASE_ITEM, level_id: 'lvl-2', level_title: 'Level 2' } });
    expect(screen.getByText(/Level 2/)).toBeInTheDocument();
  });

  it('omits the level eyebrow when level_title is absent', () => {
    renderCard();
    expect(screen.queryByText(/Level \d/)).not.toBeInTheDocument();
  });
});
